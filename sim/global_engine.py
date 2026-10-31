from __future__ import annotations
from dataclasses import dataclass
import json
import math
from pathlib import Path
import numpy as np
import pandas as pd
from .global_config import GlobalSimulationConfig

try:
    from shapely.geometry import Point
except ImportError:
    Point = None

_PREP_LAND = None
_PREP_LAND_CHECKED = False


def _get_prep_land():
    global _PREP_LAND, _PREP_LAND_CHECKED
    if _PREP_LAND_CHECKED:
        return _PREP_LAND
    _PREP_LAND_CHECKED = True
    try:
        from pathlib import Path
        import json
        from shapely.geometry import shape
        from shapely.ops import unary_union
        from shapely.prepared import prep
        land_path = Path(__file__).resolve().parents[1] / "data" / "ne_110m_land.geojson"
        if land_path.exists():
            with open(land_path, "r", encoding="utf-8") as f:
                geo = json.load(f)
            _PREP_LAND = prep(unary_union([shape(feat["geometry"]) for feat in geo["features"]]))
    except Exception:
        _PREP_LAND = None
    return _PREP_LAND

@dataclass
class GlobalSimulationResult:
    monthly: pd.DataFrame
    annual: pd.DataFrame
    animation: pd.DataFrame
    species_annual: pd.DataFrame
    vessel_summary: pd.DataFrame
    meta: dict


def _softmax(x, axis=1):
    z=x-np.max(x,axis=axis,keepdims=True)
    e=np.exp(np.clip(z,-35,35))
    return e/np.maximum(e.sum(axis=axis,keepdims=True),1e-12)


def _sample_cat(p,rng):
    u=rng.random(p.shape[0]); c=np.cumsum(p,axis=1)
    return (u[:,None]>c).sum(axis=1).clip(0,p.shape[1]-1)


def _make_agents(cfg, world, rng):
    n=min(cfg.representative_agents,cfg.n_vessels)
    weight=np.full(n,cfg.n_vessels/n)
    # Synthetic size classes tuned to reflect a mixed global longline fleet; editable only in advanced data pack.
    cls=rng.choice(4,n,p=[0.30,0.39,0.21,0.10])
    capacity=np.array([.35,.72,1.65,2.55])[cls]*rng.lognormal(0,.16,n)
    effort=np.array([145,205,275,330])[cls]*rng.lognormal(0,.12,n)
    catchability=np.array([.70,.95,1.30,1.52])[cls]*rng.lognormal(0,.14,n)
    fuel=np.array([34,58,105,155])[cls]*rng.lognormal(0,.12,n)
    fixed=np.array([11000,23000,52000,89000])[cls]*rng.lognormal(0,.09,n)
    crew=np.array([8500,17000,34000,52000])[cls]*rng.lognormal(0,.08,n)
    risk=np.clip(rng.beta(2.0,24.0,n)*1.8,0.005,.35)
    exploration=np.clip(rng.beta(2.5,18,n),.02,.30)
    
    # Target species assignment reflecting global pelagic longline fleet composition:
    # Target species assignment reflecting global pelagic longline fleet composition:
    # Yellowfin (40%), Bigeye (25%), Albacore (20%), Swordfish (15%)
    spp_choices = ["YFT", "BET", "ALB", "SWO"]
    target_spp = rng.choice(spp_choices, n, p=[0.40, 0.25, 0.20, 0.15])
    home = np.zeros(n, dtype=int)
    for i in range(n):
        sp = target_spp[i]
        suit = world[f"suit_{sp}"].values
        is_res = suit > 0.02
        if is_res.sum() > 0:
            p_prior = world.effort_prior.values * is_res
            p_prior = p_prior / p_prior.sum() if p_prior.sum() > 0 else is_res / is_res.sum()
            p_unif = is_res.astype(float) / is_res.sum()
            # Balanced mixture: 65% historical effort hotspots, 35% spatial habitat distribution
            p_mix = 0.65 * p_prior + 0.35 * p_unif
            p_mix = p_mix / p_mix.sum()
            home[i] = rng.choice(len(world), p=p_mix)
        else:
            home[i] = rng.choice(len(world), p=world.effort_prior.values / world.effort_prior.sum())

    return {"n":n,"weight":weight,"class":cls,"capacity":capacity,"effort":effort,"catchability":catchability,
            "fuel_lph":fuel,"fixed":fixed,"crew":crew,"risk":risk,"exploration":exploration,"home":home,
            "target_species":target_spp}



def _assign_em(cfg, agents, rng):
    # Each vessel gets its own adoption probability; realised adoption fluctuates around the user ceiling.
    n=agents["n"]
    ceiling=np.clip(cfg.em_adoption_max_pct/100,0,1)
    p=ceiling*np.clip(0.55+0.30*(agents["capacity"]/np.mean(agents["capacity"]))+rng.normal(0,.10,n),.15,1.35)
    return rng.random(n)<np.clip(p,0,1)


def _climate_path(cfg, months, rng):
    # User supplies only extremity ceiling. Direction, timing and persistence are stochastic.
    maxamp=np.clip(cfg.climate_extremity_max_pct/100,0,1)
    x=np.zeros(months)
    for t in range(1,months):
        shock=rng.normal(0,maxamp/8)
        if rng.random()<0.025:  # occasional extreme event
            shock += rng.choice([-1,1])*rng.uniform(maxamp*.35,maxamp)
        x[t]=cfg.climate_shock_persistence*x[t-1]+shock
        x[t]=np.clip(x[t],-maxamp,maxamp)
    return x


def simulate_global(cfg: GlobalSimulationConfig, world: pd.DataFrame, intervention=True, animation_agents=500, step_callback=None):
    seed=cfg.seed+(7001 if intervention else 0)
    # paired exogenous world: agents/climate use shared streams; intervention stream is separate.
    rng_agents=np.random.default_rng(cfg.seed+101)
    rng_exo=np.random.default_rng(cfg.seed+202)
    rng=np.random.default_rng(seed+303)
    agents=_make_agents(cfg,world,rng_agents)
    em=_assign_em(cfg,agents,np.random.default_rng(cfg.seed+404)) if intervention else np.zeros(agents["n"],bool)
    n=agents["n"]; W=agents["weight"]; G=len(world)
    months=cfg.years*12
    climate=_climate_path(cfg,months,rng_exo)
    codes=[s.code for s in cfg.species.values()]
    spp={s.code:s for s in cfg.species.values()}

    # Regional biomass: strictly zero where species is not ecologically resident
    biomass = {}
    for c in codes:
        suit_c = world[f"suit_{c}"].values
        biomass[c] = np.where(suit_c > 0.015, np.clip(0.12 + 0.98 * suit_c, 0.02, 1.25), 0.0)
    initial = {c: b.copy() for c, b in biomass.items()}
    mpa=np.clip(world.mpa_share.values.copy(),0,.65)
    effort_prior=np.maximum(world.effort_prior.values,1e-12)
    # Biodiversity suitability matrix per vessel target species
    suit_matrix = np.array([world[f"suit_{agents['target_species'][i]}"].values for i in range(n)])
    is_resident_matrix = suit_matrix > 0.015
    # agent historical preferences around home cell plus global effort hotspots, bounded to resident habitat.
    lon=world.lon.values; lat=world.lat.values
    pref=np.empty((n,G),dtype=np.float32)
    cls_arr = agents["class"]
    for i in range(n):
        h=agents["home"][i]
        c_i = cls_arr[i]
        # Operational range expands by vessel capital class:
        # Class 0: Small coastal (35° lon, 18° lat)
        # Class 1: Medium regional (50° lon, 25° lat)
        # Class 2: Large industrial (75° lon, 35° lat)
        # Class 3: Distant-water freezer (95° lon, 42° lat, global high-seas mobility)
        scale_lon = 35.0 if c_i == 0 else (50.0 if c_i == 1 else (75.0 if c_i == 2 else 95.0))
        scale_lat = 18.0 if c_i == 0 else (25.0 if c_i == 1 else (35.0 if c_i == 2 else 42.0))
        w_local = 0.80 if c_i == 0 else (0.70 if c_i == 1 else (0.55 if c_i == 2 else 0.40))

        dlon=np.minimum(np.abs(lon-lon[h]),360-np.abs(lon-lon[h]))
        dlat=np.abs(lat-lat[h])
        local=np.exp(-0.5*((dlon/scale_lon)**2+(dlat/scale_lat)**2))
        p_base = (w_local*local/local.sum()+(1.0 - w_local)*effort_prior).astype(np.float32)
        p_res = np.where(is_resident_matrix[i], p_base, 1e-12)
        pref[i] = (p_res / p_res.sum()).astype(np.float32)

    management_quality=cfg.base_observability
    annual_rows=[]; monthly_rows=[]; species_rows=[]; anim=[]
    cumulative_violation=np.zeros(n)
    profit_total=np.zeros(n); catch_total=np.zeros(n); bycatch_total=np.zeros(n)
    prev_supply=1.0
    price_index=1.0; fuel_price=cfg.fuel_price_litre
    scale=1.0

    # Load authoritative MPA layer for coupled dynamic spatial optimization
    mpa_path = Path(__file__).resolve().parents[1] / "data" / "processed" / "marine_mpas.geojson"
    mpa_features = []
    base_cents_list = []
    base_radii_list = []
    if mpa_path.exists():
        try:
            with open(mpa_path, "r", encoding="utf-8") as f:
                mpa_geo = json.load(f)
            mpa_features = mpa_geo.get("features", [])
            for feat in mpa_features:
                coords = feat["geometry"]["coordinates"]
                polys = coords if feat["geometry"]["type"] == "MultiPolygon" else [coords]
                pts = [pt for poly in polys if poly and poly[0] for pt in poly[0]]
                if pts:
                    base_cents_list.append((float(np.mean([pt[0] for pt in pts])), float(np.mean([pt[1] for pt in pts]))))
                else:
                    base_cents_list.append((0.0, 0.0))
                area = feat["properties"].get("area_km2", 400000)
                rad = max(2.5, float(np.sqrt(area / np.pi) / 111.0))
                base_radii_list.append(rad)
        except Exception:
            mpa_features = []
    base_cents = np.array(base_cents_list) if base_cents_list else np.empty((0, 2))
    base_radii = np.array(base_radii_list) if base_radii_list else np.empty(0)
    curr_cents = base_cents.copy()
    n_mpas = len(base_cents)
    mpa_frames = {}
    bio_frames = {}
    congestion = effort_prior.copy() / effort_prior.sum()

    # baseline scale from desired open-data reference value; catch shares/prices create the composition.
    target_monthly=cfg.baseline_landed_value_billion*1e9/12
    base_unit=(agents["effort"]*agents["capacity"]*agents["catchability"]*W).sum()
    mean_price=np.mean([s.base_price_tonne for s in cfg.species.values() if not s.bycatch and s.base_price_tonne>0])
    scale=target_monthly/max(base_unit*mean_price*.65,1)
    prev_supply=float(target_monthly/max(mean_price,1))

    prev_region=agents["home"].copy()
    home_h=agents["home"]
    curr_lon=lon[home_h].copy().astype(float)
    curr_lat=lat[home_h].copy().astype(float)
    prep_land=_get_prep_land()
    if prep_land is not None and Point is not None:
        for i in range(n):
            cand_lon=((lon[home_h[i]]+rng_agents.uniform(-2.5,2.5)+180)%360)-180
            cand_lat=np.clip(lat[home_h[i]]+rng_agents.uniform(-2.0,2.0),-55,55)
            if not prep_land.contains(Point(cand_lon, cand_lat)):
                curr_lon[i]=cand_lon; curr_lat[i]=cand_lat
    else:
        curr_lon=((lon[home_h]+rng_agents.uniform(-2.5,2.5,n)+180)%360)-180
        curr_lat=np.clip(lat[home_h]+rng_agents.uniform(-2.0,2.0,n),-55,55)

    # In EM, verified export premium is robust: beta distribution with higher mean
    premium_draw = np.random.default_rng(cfg.seed + 505).beta(2.2, 2.5, n) * (cfg.premium_max_pct / 100)
    aware_draw = np.random.default_rng(cfg.seed + 606).beta(2.8, 1.8, n) * (cfg.em_awareness_effect_max_pct / 100)

    for t in range(months):
        month=t%12; year=t//12+1
        if month==0 and year > 1:
            real_drift = math.exp(getattr(cfg, "annual_price_drift", 0.015))
            price_index *= real_drift * math.exp(rng_exo.normal(-.5*cfg.price_volatility**2,cfg.price_volatility))
            fuel_price *= math.exp(0.01 + rng_exo.normal(-.5*cfg.fuel_volatility**2,cfg.fuel_volatility))
        # climate shifts habitat latitudinally and reduces some local suitability.
        clim=climate[t]
        temp_lat_shift=clim*12.0

        # Species-specific biomass attraction: each vessel targets its licensed biodiversity stock
        target_bio = np.zeros((n, G), dtype=np.float32)
        for i in range(n):
            sp = agents["target_species"][i]
            target_bio[i] = np.where(is_resident_matrix[i], biomass[sp], 0.0)

        attraction = np.log(pref + 1e-9) + 0.82 * np.log(target_bio + 1e-4)
        # Enforce strict boundary penalty outside resident biodiversity habitat
        attraction[~is_resident_matrix] -= 15.0
        # persistence of current grounds
        attraction[np.arange(n), prev_region] += 0.65

        # Coupled Conservation Priority Field: Biomass Depletion across resident species
        depletion = np.zeros(G)
        resident_count = np.zeros(G)
        for c in ["YFT", "BET", "ALB", "SWO"]:
            suit_c = world[f"suit_{c}"].values
            K_c = spp[c].carrying_capacity * suit_c
            is_resident = suit_c > 0.02
            resident_count += is_resident.astype(float)
            depletion[is_resident] += np.maximum(0.0, (K_c[is_resident] - biomass[c][is_resident]) / np.maximum(K_c[is_resident], 0.05))
        depletion = np.where(resident_count > 0, depletion / np.maximum(resident_count, 1.0), 0.0)

        bycatch_risk = 0.5 * world["suit_SHK"].values + 0.3 * world["suit_TUR"].values + 0.2 * world["suit_SEA"].values
        max_cong = max(float(congestion.max()), 1e-4)
        psi = depletion * (0.35 + 0.65 * (congestion / max_cong)) + 0.35 * bycatch_risk

        gov_push = (cfg.government_mpa_push_max_pct / 100) * (t / max(months - 1, 1)) if intervention else 0

        # Coupled spatial optimization: MPAs shift and expand ONLY when active fishing pressure or fleet presence is nearby
        exp_k = np.ones(n_mpas, dtype=np.float32)
        fishers_near_mpas = np.zeros(n_mpas, dtype=int)
        if intervention and n_mpas > 0:
            lambda_t = management_quality * (cfg.government_mpa_push_max_pct / 100.0) * min(1.0, (t + 1) / 14.0)
            global_exp = 1.0 + (cfg.government_mpa_push_max_pct / 100.0) * management_quality * (t / max(months - 1, 1)) * 0.45
            for k in range(n_mpas):
                dlon_k = ((lon - base_cents[k, 0] + 180) % 360) - 180
                dlat_k = lat - base_cents[k, 1]
                dist_k_sq = dlon_k**2 + dlat_k**2

                # Identify actual vessel fleet presence within interaction zone (~2.2 * radius)
                interact_rad = max(2.2 * base_radii[k], 7.0)
                vessel_dist_k = np.hypot(((curr_lon - base_cents[k, 0] + 180) % 360) - 180, curr_lat - base_cents[k, 1])
                n_near_k = int(np.sum(vessel_dist_k <= interact_rad))
                fishers_near_mpas[k] = n_near_k
                cong_near_k = float(np.sum(congestion * np.exp(-0.5 * dist_k_sq / (16.0**2))))

                # REALISM INVARIANT: If there are NO fishers near this MPA, the MPA does NOT change!
                # Marine sanctuaries with zero fishing activity remain anchored at baseline coordinates and baseline area.
                if n_near_k == 0 and cong_near_k < 1e-4:
                    curr_cents[k] = base_cents[k].copy()
                    exp_k[k] = 1.0
                    continue

                fisher_threat = min(1.0, max(n_near_k / 4.0, cong_near_k * 15.0, 0.20))
                lambda_k = lambda_t * fisher_threat
                exp_k[k] = 1.0 + (global_exp - 1.0) * fisher_threat

                reg_w = psi * np.exp(-0.5 * dist_k_sq / (36.0**2))
                sum_w = float(reg_w.sum())
                if sum_w > 1e-7:
                    target_dlon = float(np.sum(reg_w * dlon_k) / sum_w)
                    target_dlat = float(np.sum(reg_w * dlat_k) / sum_w)
                    lat_dir = 1.0 if base_cents[k, 1] >= 0 else -1.0
                    clim_drift = lat_dir * (clim * 4.5) * (0.2 + 0.8 * (t / max(months - 1, 1))) * fisher_threat
                    c_target_lon = ((base_cents[k, 0] + target_dlon + 180) % 360) - 180
                    c_target_lat = float(np.clip(base_cents[k, 1] + target_dlat + clim_drift, -58, 58))
                    curr_cents[k, 0] = ((curr_cents[k, 0] + 0.22 * lambda_k * (((c_target_lon - curr_cents[k, 0] + 180) % 360) - 180) + 180) % 360) - 180
                    curr_cents[k, 1] = float(np.clip(curr_cents[k, 1] + 0.22 * lambda_k * (c_target_lat - curr_cents[k, 1]), -58, 58))
        else:
            curr_cents = base_cents.copy()
            exp_k = np.ones(n_mpas, dtype=np.float32)

        # Coupled cell-level effective MPA layer and spillover buffer ring
        dyn_cell_mpa = mpa.copy()
        spillover_ring = np.zeros(G)
        if n_mpas > 0:
            for k in range(n_mpas):
                r_k = max(base_radii[k] * exp_k[k], 2.5)
                dlon_c = ((lon - curr_cents[k, 0] + 180) % 360) - 180
                dlat_c = lat - curr_cents[k, 1]
                dist_sq = (dlon_c**2 + dlat_c**2) / (r_k**2)
                in_zone = np.exp(-0.5 * dist_sq)
                ring_k = 4.0 * dist_sq * np.exp(-1.8 * dist_sq)
                dyn_cell_mpa = np.maximum(dyn_cell_mpa, 0.55 * in_zone)
                spillover_ring = np.maximum(spillover_ring, ring_k)
        effective_mpa = np.clip(dyn_cell_mpa * (1 + gov_push), 0, 0.82)

        # EM effect is awareness-led and audit-enforced: EM vessels strongly avoid closed MPAs
        mgmt_gain=max(0.0,(management_quality-cfg.base_observability)/max(1.0-cfg.base_observability,0.01)) if intervention else 0.0
        awareness=np.where(em,aware_draw,0.0)
        # Compliant EM vessels actively avoid closed MPAs (strong aversion); non-EM / BAU vessels have minimal aversion
        legal_aversion=np.where(em, 4.2 + 6.0 * awareness, 0.25)[:,None]*effective_mpa[None,:]
        attraction-=legal_aversion
        p=_softmax(attraction,1)
        # per-agent exploration (EM vessels with active cameras avoid exploring into high-protection reserves)
        # per-agent exploration: restricted to the target species' biodiversity envelope
        is_closed = effective_mpa > 0.20
        base_explore = np.where(is_resident_matrix, 1.0, 0.0)
        p_explore = np.where(em[:, None] & is_closed[None, :], base_explore * 0.03, base_explore)
        explore_sum = p_explore.sum(axis=1, keepdims=True)
        p_explore = np.where(explore_sum > 0, p_explore / np.maximum(explore_sum, 1e-9), 1.0 / G)
        p=(1-agents["exploration"][:,None])*p+agents["exploration"][:,None]*p_explore
        region=_sample_cat(p,rng)
        target_lon=lon[region]; target_lat=lat[region]
        dlon_diff=((target_lon-curr_lon)+180)%360-180
        dlat_diff=target_lat-curr_lat
        dist=np.hypot(dlon_diff,dlat_diff)
        stay=dist<3.0; move=~stay
        if np.any(stay):
            curr_lon[stay]+=rng.normal(0,0.45,np.sum(stay))
            curr_lat[stay]+=rng.normal(0,0.35,np.sum(stay))
        if np.any(move):
            step_cap = np.where(agents["class"][move] >= 2, 12.0, 8.5)
            step=np.minimum(dist[move], step_cap)
            curr_lon[move]+=(dlon_diff[move]/dist[move])*step+rng.normal(0,0.3,np.sum(move))
            curr_lat[move]+=(dlat_diff[move]/dist[move])*step+rng.normal(0,0.25,np.sum(move))
        
        # Biodiversity latitudinal limits per species
        for i in range(n):
            sp_i = agents["target_species"][i]
            if sp_i == "YFT":
                curr_lat[i] = np.clip(curr_lat[i], -35.0, 35.0)
            elif sp_i == "BET":
                curr_lat[i] = np.clip(curr_lat[i], -38.0, 38.0)
            elif sp_i == "ALB":
                curr_lat[i] = np.clip(curr_lat[i], -52.0, 52.0)
            else:
                curr_lat[i] = np.clip(curr_lat[i], -55.0, 55.0)
        curr_lon=((curr_lon+180)%360)-180
        if prep_land is not None and Point is not None:
            for i in range(n):
                if prep_land.contains(Point(float(curr_lon[i]), float(curr_lat[i]))):
                    curr_lon[i]=target_lon[i]
                    curr_lat[i]=target_lat[i]
        prev_region=region

        encounter=rng.random(n)<np.clip(effective_mpa[region]*cfg.mpa_encounter_sensitivity,0,.95)
        # persistent latent non-compliance; EM affects awareness, government push affects norm pressure, surveillance deters violations.
        norm_reduction=(cfg.enforcement_push_max_pct/100)*(t/max(months-1,1)) if intervention else 0.0
        mgmt_deterrence=(1.0-0.65*mgmt_gain) if intervention else 1.0
        # In unenforced paper parks (BAU), baseline violation probability is high (25-45% poaching);
        # In EM, electronic video audits and tamper-proof GPS suppress violation propensity by ~90%.
        basep=np.clip((cfg.baseline_violation_prob / 0.055) * (0.28 + 0.45 * agents["risk"]), cfg.minimum_residual_violation_prob, 0.70)
        em_factor=np.where(em, 0.06 * (1.0 - aware_draw), 1.0)
        violation_p=np.maximum(cfg.minimum_residual_violation_prob, basep * em_factor * (1.0 - 0.55 * norm_reduction) * mgmt_deterrence)
        # behavioural persistence: previous violations modestly raise next-month propensity.
        violation_p=np.clip(violation_p*(1+cfg.violation_persistence*np.minimum(cumulative_violation,3)/10),cfg.minimum_residual_violation_prob,.75)
        illegal=encounter&(rng.random(n)<violation_p)
        cumulative_violation += illegal.astype(float)
        compliant_encounter=encounter&(~illegal)
        # govt reallocation support reduces displacement burden; stronger with intervention but stochastic.
        realloc=(cfg.government_reallocation_support_max_pct/100)*(0.4+0.6*rng.random(n)) if intervention else 0
        displacement_mult=1+compliant_encounter*(.18*(1-cfg.reallocation_cost_reduction*realloc))

        counts=np.bincount(region,weights=W,minlength=G)
        congestion=counts/max(counts.sum(),1)
        crowd=np.clip(1-.25*(congestion/np.maximum(effort_prior,.002)-1),.48,1.15)
        effort=agents["effort"]*np.clip(.90+rng.lognormal(-.01,.10,n),.65,1.25)

        total_revenue=np.zeros(n); total_target=np.zeros(n); bycatch_events=np.zeros(n)
        species_month={}
        unmitigated_bycatch = {}
        mgmt_price_boost = 1.0 + 0.16 * mgmt_gain if intervention else 0.94  # BAU unverified catch faces 6% market friction/IUU discount
        for c,s in spp.items():
            # climate modifies abundance through habitat displacement and extremes.
            clim_pen=np.exp(-s.climate_sensitivity*abs(clim))
            lat_pref=np.exp(-0.5*((lat[region]-temp_lat_shift)/45)**2)
            suit_r=world[f"suit_{c}"].values[region]
            in_range=suit_r > 0.015
            local_bio=np.where(in_range, np.maximum(biomass[c][region],.005)*clim_pen*(.75+.25*lat_pref), 0.0)
            cpue=(local_bio**cfg.stock_cpue_elasticity)*crowd[region]
            noise=rng.lognormal(-.5*.35**2,.35,n)
            base=scale*effort*agents["capacity"]*agents["catchability"]*cpue*noise
            if s.bycatch:
                # Coupled Bycatch Dynamics: EM adoption mandates & verifies circle hooks, bird-scaring lines, and de-hookers
                mitig_eff = 0.45 if c == "SHK" else (0.58 if c == "TUR" else 0.54)
                mitigation = 1.0 - mitig_eff * np.where(em & (~illegal), 1.0, 0.0) * (0.55 + 0.45 * (management_quality / max(cfg.base_observability, 0.01)))
                rate = 0.02 if c == "SHK" else (0.004 if c == "TUR" else 0.003)
                unmit_amt = base * rate * in_range.astype(float)
                amount = unmit_amt * np.clip(mitigation, 0.35, 1.0)
                # High-bycatch encounter events benchmarked against unmitigated gear threshold
                unmit_thresh = np.quantile(unmit_amt[unmit_amt > 0], .75) if np.any(unmit_amt > 0) else 1e-4
                bycatch_events += (amount > unmit_thresh).astype(float)
                species_month[c] = amount
                unmitigated_bycatch[c] = unmit_amt
            else:
                # species share from local regional suitability/biomass (strictly zero outside habitat)
                share=np.where(in_range, suit_r, 0.0)
                amount=base*share
                # premium is random and only for EM/compliant vessels; management quality boosts certified price realization
                eligible=em & (~illegal) if cfg.premium_requires_compliance else em
                prem=np.where(eligible,premium_draw,0)
                px=s.base_price_tonne*price_index*mgmt_price_boost*(1+prem)
                total_revenue += amount*px
                total_target += amount
                species_month[c]=amount

        supply_ratio=max(float(np.sum(total_target*W))/max(prev_supply,1),.25)
        total_revenue*=supply_ratio**(-cfg.demand_elasticity)
        prev_supply=float(np.sum(total_target*W))
        # management observability improves search transit efficiency and reduces wasted steaming in EM;
        # in BAU, stock depletion increases search steaming per tonne!
        mean_target_stock = np.mean([np.mean(biomass[k]) for k in ["YFT", "BET", "ALB", "SWO"]])
        stock_fuel_pen = (1.0 + 0.25 * max(0.0, 0.55 - mean_target_stock)) if not intervention else 1.0
        search_reduction = (0.22 * mgmt_gain * np.where(em, 1.0, 0.25)) if intervention else 0.0
        effective_displacement = displacement_mult * (1.0 - search_reduction) * stock_fuel_pen
        fuel_l = effort * agents["fuel_lph"] * effective_displacement
        # Commercial longline operating costs reflect real-world cost structures (fuel, bait, food, crew)
        op_cost = fuel_l * fuel_price + (agents["fixed"] * 1.35 + agents["crew"] * 1.25) / 12 + effort * 85
        em_cost = np.where(em, cfg.em_capex_per_vessel / (cfg.em_amortization_years * 12) + cfg.em_service_annual / 12, 0)
        # enforcement fine on detected illegal entries (catch forfeiture plus administrative penalty up to 125% revenue)
        enforce_intensity = np.clip(0.40 + 0.60 * (management_quality / max(cfg.base_observability, 0.01)) * (1.0 + cfg.enforcement_push_max_pct / 100.0), 0.20, 1.25) if intervention else 0.20
        illegal_fine = np.where(illegal, total_revenue * enforce_intensity, 0.0)
        profit = total_revenue - op_cost - em_cost - illegal_fine
        profit_total+=profit; catch_total+=total_target; bycatch_total+=bycatch_events

        # Coupled Non-Compliance Feedback on Reserve Efficacy (Paper-Park Leakage vs Enforced Sanctuary)
        illegal_cell_effort = np.bincount(region, weights=illegal.astype(float) * effort * W, minlength=G)
        total_cell_effort = np.bincount(region, weights=effort * W, minlength=G)
        cell_illegal_rate = illegal_cell_effort / np.maximum(total_cell_effort, 1e-4)
        # Rampant illegal poaching erodes nominal MPA protection from 0.80 down toward 0.15:
        compliance_efficacy = np.clip(1.0 - 0.75 * cell_illegal_rate, 0.15, 1.0)
        realized_cell_protection = 1.0 - 0.80 * effective_mpa * compliance_efficacy

        # ecological update cell-by-cell/species-by-species (strictly regional resident dynamics)
        for c,s in spp.items():
            B=biomass[c]
            suit_c=world[f"suit_{c}"].values
            suit_mask=suit_c > 0.015
            K=s.carrying_capacity*suit_c
            growth=np.zeros(G)
            growth[suit_mask]=(s.growth_rate/12)*B[suit_mask]*(1.0-B[suit_mask]/np.maximum(K[suit_mask],0.08))

            # target harvest plus incidental bycatch pressure
            hweights=species_month[c]*W
            hcell=np.bincount(region,weights=hweights,minlength=G)
            hshare=hcell/max(hcell.sum(),1) if hcell.sum()>0 else np.zeros(G)

            if s.bycatch:
                # BYCATCH FIX: Absolute physical extraction scales with fleet mitigation!
                unmit_tot = float(np.sum(unmitigated_bycatch[c] * W))
                mitig_tot = float(np.sum(species_month[c] * W))
                bycatch_ratio = mitig_tot / max(unmit_tot, 1e-6)  # ~0.45-0.55 in EM vs 1.0 in BAU
                f_rate = np.clip((cfg.harvest_pressure_scale / 12) * hshare * G * realized_cell_protection * bycatch_ratio * 0.75, 0.0, 0.25)
            else:
                # TARGET SPECIES: Open-access BAU has +15% overfishing effort creep; EM aligns with MSY
                mgmt_effort_scale = (1.0 - 0.18 * mgmt_gain) if intervention else 1.15
                f_rate = np.clip((cfg.harvest_pressure_scale / 12) * hshare * G * realized_cell_protection * mgmt_effort_scale, 0.0, 0.25)

            harvest = f_rate * B
            # migration towards neighbouring resident habitat via basin-average pull
            if np.any(suit_mask):
                meanB=float(np.average(B[suit_mask],weights=suit_c[suit_mask]))
                migration=np.zeros(G)
                migration[suit_mask]=(s.migration_strength/12)*(meanB-B[suit_mask])*suit_c[suit_mask]
            else:
                meanB=0.0
                migration=np.zeros(G)
            # Biological spillover: high-biomass protected sanctuaries export surplus to adjacent buffer cells
            res_mask=(effective_mpa > 0.25) & suit_mask
            res_B=float(np.mean(B[res_mask])) if np.any(res_mask) else meanB
            spill_gain=(cfg.spillover_rate/12)*spillover_ring*max(0.0,res_B-meanB*0.85)*suit_c
            spill_loss=(cfg.spillover_rate/12)*effective_mpa*0.35*B
            basin_rebalance=(cfg.spillover_rate/24)*(meanB-B)*suit_c
            extreme_loss=abs(clim)*s.climate_sensitivity*B/18
            noise=np.where(suit_mask,rng_exo.normal(0,.006,G),0.0)
            biomass[c]=np.where(
                suit_mask,
                np.clip(B+growth-harvest+migration+spill_gain-spill_loss+basin_rebalance-extreme_loss+noise,.001,np.maximum(K*1.35,0.05)),
                0.0
            )

        monthly_rows.append({"month_index":t,"year":year,"month":month+1,"scenario":"EM" if intervention else "BAU",
            "landed_value":float(np.sum(total_revenue*W)),"fleet_profit":float(np.sum(profit*W)),"catch_tonnes":float(np.sum(total_target*W)),
            "illegal_events":float(np.sum(illegal*W)),"bycatch_events":float(np.sum(bycatch_events*W)),"mpa_encounters":float(np.sum(encounter*W)),"em_share":float(np.average(em,weights=W)),
            "climate_index":float(clim),"fuel_price":float(fuel_price),"management_quality":float(management_quality)})

        # animation subsample
        if t % max(cfg.months_per_frame,1)==0:
            k=min(animation_agents,n)
            idx=np.arange(k)
            for i in idx:
                anim.append({"frame":t,"year":year,"month":month+1,"agent":int(i),"lon":float(curr_lon[i]),"lat":float(curr_lat[i]),
                             "em":bool(em[i]),"illegal":bool(illegal[i]),"size_class":int(agents["class"][i]),
                             "target_species":str(agents["target_species"][i]),
                             "catch_tonnes":float(total_target[i]),"profit":float(profit[i]),"revenue":float(total_revenue[i]),
                             "bycatch":float(bycatch_events[i]),
                             "local_mpa":float(effective_mpa[region[i]]),"local_bio":float(target_bio[i, region[i]]),
                             "scenario":"EM" if intervention else "BAU"})

            bio_frames[t] = {c: biomass[c].copy() for c in codes}

            # Generate exact coupled MPA polygons for this frame
            frame_lons, frame_lats, line_hovers = [], [], []
            cent_lons, cent_lats, cent_hovers = [], [], []
            for k, feat in enumerate(mpa_features):
                geom_data = feat.get("geometry", {})
                props = feat.get("properties", {})
                name = props.get("name", "MPA")
                country = props.get("country", "N/A")
                desig = props.get("designation", "Marine Reserve")
                base_area = props.get("area_km2", 400000)
                exp_val = float(exp_k[k])
                curr_area = int(base_area * (exp_val ** 2))
                c_lon, c_lat = float(curr_cents[k, 0]), float(curr_cents[k, 1])
                orig_lon, orig_lat = float(base_cents[k, 0]), float(base_cents[k, 1])
                shift_dist = float(np.hypot(((c_lon - orig_lon + 180) % 360) - 180, c_lat - orig_lat))
                n_near = int(fishers_near_mpas[k])

                if not intervention or n_near == 0 or shift_dist < 0.05:
                    status_txt = "⚪ Static (No Local Fishing Threat)" if intervention else "⚪ Static MPA (BAU Twin)"
                    cent_txt = f"{c_lat:.1f}°, {c_lon:.1f}° (baseline — no active fishers nearby)"
                else:
                    status_txt = "🟢 Dynamic Coupled MPA (EM Twin)"
                    cent_txt = f"{c_lat:.1f}°, {c_lon:.1f}° (shifted {shift_dist:.1f}° responding to {n_near} active fishers)"

                dyn_ht = (
                    f"<b>{name}</b><br>"
                    f"Country: {country} | {desig}<br>"
                    f"Status: {status_txt}<br>"
                    f"Area: {curr_area:,} km² ({'+' if exp_val>1.001 else ''}{(exp_val**2 - 1)*100:.1f}%)<br>"
                    f"Centroid: {cent_txt}"
                )

                polys = geom_data.get("coordinates", []) if geom_data.get("type") == "MultiPolygon" else [geom_data.get("coordinates", [])]
                lons_feat, lats_feat = [], []
                for poly in polys:
                    if not poly or not poly[0]:
                        continue
                    ext_ring = poly[0]
                    for pt in ext_ring:
                        nx = c_lon + (pt[0] - orig_lon) * exp_val
                        ny = c_lat + (pt[1] - orig_lat) * exp_val
                        nx = ((nx + 180) % 360) - 180
                        ny = float(np.clip(ny, -60, 60))
                        if prep_land and Point is not None and prep_land.contains(Point(nx, ny)):
                            nx = c_lon + 0.6 * (nx - c_lon)
                            ny = c_lat + 0.6 * (ny - c_lat)
                        frame_lons.append(nx)
                        frame_lats.append(ny)
                        line_hovers.append(dyn_ht)
                        lons_feat.append(nx)
                        lats_feat.append(ny)
                    frame_lons.append(None)
                    frame_lats.append(None)
                    line_hovers.append("")

                if lons_feat and lats_feat:
                    cent_lons.append(c_lon)
                    cent_lats.append(c_lat)
                    cent_hovers.append(dyn_ht)

            mpa_frames[t] = (frame_lons, frame_lats, line_hovers, cent_lons, cent_lats, cent_hovers)

        # annual management cycle
        if month==11:
            adoption=float(np.average(em,weights=W))
            obs_target=cfg.base_observability+(cfg.em_observability_gain*adoption if intervention else 0)
            management_quality=(1-cfg.management_learning_rate)*management_quality+cfg.management_learning_rate*np.clip(obs_target,0,1)
            # govt creates/expands protection where resident target biomass is weak and effort is high.
            if intervention and cfg.mpa_redesign_enabled:
                weakness=np.zeros(G)
                for c in ["YFT","BET","ALB","SWO"]:
                    suit_c = world[f"suit_{c}"].values
                    K_c = spp[c].carrying_capacity * suit_c
                    is_res = suit_c > 0.02
                    weakness[is_res] += np.clip(0.75 * K_c[is_res] - biomass[c][is_res], 0, None)
                score=weakness*(.4+.6*congestion)
                if score.max()>0:
                    mpa += (cfg.government_mpa_push_max_pct/100)*management_quality*(score/score.max())*.025
                    mpa=np.clip(mpa,0,.65)
            ar={"year":year,"scenario":"EM" if intervention else "BAU",
                "landed_value":sum(x["landed_value"] for x in monthly_rows[-12:]),"fleet_profit":sum(x["fleet_profit"] for x in monthly_rows[-12:]),
                "catch_tonnes":sum(x["catch_tonnes"] for x in monthly_rows[-12:]),"illegal_events":sum(x["illegal_events"] for x in monthly_rows[-12:]),
                "bycatch_events":sum(x.get("bycatch_events",0.0) for x in monthly_rows[-12:]),
                "mpa_share":float(np.average(mpa,weights=effort_prior)),"management_quality":float(management_quality),"climate_extreme":float(np.max(np.abs(climate[max(0,t-11):t+1])))}
            annual_rows.append(ar)
            for c,s in spp.items():
                suit_c = world[f"suit_{c}"].values
                suit_mask = suit_c > 0.015
                if np.any(suit_mask):
                    ratio = float(np.average(biomass[c][suit_mask] / np.maximum(initial[c][suit_mask], 1e-4), weights=suit_c[suit_mask]))
                else:
                    ratio = 1.0
                status="Healthy" if ratio>=.8 else "Stressed" if ratio>=.5 else "Depleted" if ratio>=cfg.severe_depletion_threshold else "Severely depleted" if ratio>=cfg.local_extirpation_threshold else "Local functional extinction risk"
                species_rows.append({"year":year,"scenario":ar["scenario"],"species":s.name,"code":c,"population_ratio":ratio,"status":status})

            if step_callback is not None:
                try:
                    step_callback(year, cfg.years, annual_rows, monthly_rows, species_rows, intervention)
                except Exception:
                    pass

    cls_names=np.array(["Small coastal","Medium regional","Large industrial","Distant-water freezer"],object)
    vessel_summary=pd.DataFrame({"class":cls_names[agents["class"]],"weight":W,"em":em,"profit_total":profit_total,"catch_total":catch_total,"bycatch_total":bycatch_total,"violations":cumulative_violation})
    meta = {
        "realized_em_share": float(np.average(em, weights=W)),
        "climate_min": float(climate.min()),
        "climate_max": float(climate.max()),
        "mpa_frames": mpa_frames,
        "bio_frames": bio_frames
    }
    return GlobalSimulationResult(pd.DataFrame(monthly_rows),pd.DataFrame(annual_rows),pd.DataFrame(anim),pd.DataFrame(species_rows),vessel_summary,meta)


def run_paired_global(cfg, world, animation_agents=500, step_callback=None):
    bau = simulate_global(cfg, world, False, animation_agents)
    
    def on_em_annual(yr, total_yrs, ann_rows, mon_rows, spp_rows, is_interv):
        if step_callback is not None:
            step_callback(yr, total_yrs, bau, ann_rows, mon_rows, spp_rows)
            
    em = simulate_global(cfg, world, True, animation_agents, step_callback=on_em_annual if step_callback else None)
    return {"BAU": bau, "EM": em}
