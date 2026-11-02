from __future__ import annotations
from dataclasses import dataclass
import math
import numpy as np
import pandas as pd

from .config import SimulationConfig
from .coupling import allocate_removals, conservative_exchange, monthly_stock_step
from .data_adapter import demo_empirical_priors, priors_to_arrays

@dataclass
class SimulationResult:
    annual: pd.DataFrame
    vessel_impacts: pd.DataFrame
    summary: dict


def _softmax(x, axis=1):
    z = x - np.nanmax(x, axis=axis, keepdims=True)
    e = np.exp(np.clip(z, -40, 40))
    s = e.sum(axis=axis, keepdims=True)
    return e / np.where(s == 0, 1, s)


def _generate_agents(cfg: SimulationConfig, rng: np.random.Generator):
    names = list(cfg.fleet_classes)
    shares = np.array([cfg.fleet_classes[n].share for n in names], dtype=float)
    shares = shares / shares.sum()
    n = min(max(100, int(cfg.representative_agents)), cfg.n_vessels)
    cls_idx = rng.choice(len(names), size=n, p=shares)
    weight = np.full(n, cfg.n_vessels / n)

    def arr(attr):
        base = np.array([getattr(cfg.fleet_classes[nm], attr) for nm in names], dtype=float)
        return base[cls_idx]

    agents = {
        "n": n,
        "class_idx": cls_idx,
        "class_name": np.array(names, dtype=object)[cls_idx],
        "weight": weight,
        "capacity": arr("capacity_index") * rng.lognormal(0, 0.12, n),
        "effort": arr("effort_hours_month") * rng.lognormal(0, 0.10, n),
        "catchability": arr("catchability") * rng.lognormal(0, 0.12, n),
        "fuel_lph": arr("fuel_l_per_fishing_hour") * rng.lognormal(0, 0.10, n),
        "transit": arr("transit_factor") * rng.lognormal(0, 0.08, n),
        "fixed": arr("fixed_cost_month") * rng.lognormal(0, 0.06, n),
        "var_cost_h": arr("variable_cost_per_fishing_hour") * rng.lognormal(0, 0.06, n),
        "crew": arr("crew_cost_month") * rng.lognormal(0, 0.06, n),
        "risk": np.clip(arr("risk_propensity") * rng.lognormal(0, 0.20, n), 0, 0.8),
        "skill": rng.lognormal(0, 0.14, n),
    }
    return agents


def _assign_em(cfg: SimulationConfig, agents, region_mpa, rng):
    n = agents["n"]
    k = int(round(n * cfg.adoption_pct / 100.0))
    if k <= 0:
        return np.zeros(n, dtype=bool)
    if k >= n:
        return np.ones(n, dtype=bool)

    if cfg.adoption_strategy == "Random":
        score = rng.random(n)
    elif cfg.adoption_strategy == "Capacity-targeted":
        score = agents["capacity"] + rng.normal(0, 0.02, n)
    else:  # Impact-targeted
        exposure_proxy = rng.choice(region_mpa, size=n, replace=True)
        score = agents["capacity"] * agents["effort"] * (0.25 + exposure_proxy)
        score *= rng.lognormal(0, 0.08, n)
    idx = np.argpartition(score, -k)[-k:]
    out = np.zeros(n, dtype=bool)
    out[idx] = True
    return out


def _categorical_sample(p, rng):
    u = rng.random(p.shape[0])
    c = np.cumsum(p, axis=1)
    return (u[:, None] > c).sum(axis=1).clip(0, p.shape[1]-1)


def _run_one(cfg: SimulationConfig, adoption_pct: float, empirical_priors: pd.DataFrame, seed: int, return_vessel_year1=False, _calibration_factor=None):
    if cfg.years < 1 or cfg.n_vessels < 1 or cfg.representative_agents < 1 or cfg.n_regions < 1:
        raise ValueError("Years, regions and vessel counts must be positive")
    if not 0 < cfg.initial_biomass_index < cfg.carrying_capacity_index:
        raise ValueError("Initial stock must be positive and below carrying capacity")
    if not 0 <= adoption_pct <= 100 or cfg.em_amortization_years <= 0 or cfg.harvest_pressure_scale <= 0:
        raise ValueError("Adoption must be in [0, 100]; amortization must be positive")
    if cfg.annual_price_drift <= -1 or cfg.annual_inflation_rate <= -1 or cfg.annual_fuel_drift <= -1:
        raise ValueError("Price, fuel and inflation rates must exceed -100%")
    if _calibration_factor is None:
        from dataclasses import replace
        pilot, _ = _run_one(replace(cfg, years=1), 0, empirical_priors, seed,
                            _calibration_factor=1.0)
        observed = float(pilot.landed_value.iloc[0])
        if observed <= 0:
            raise ValueError("Priors must support positive baseline catch")
        _calibration_factor = cfg.baseline_landed_value_billion*1e9 / observed
    local_cfg = SimulationConfig(**{**cfg.__dict__, "adoption_pct": adoption_pct})
    # Split random streams so paired BAU/EM worlds share agent traits and exogenous shocks.
    rng_agents = np.random.default_rng(seed + 11)
    rng_adoption = np.random.default_rng(seed + 23)
    rng = np.random.default_rng(seed + 37)
    rng_market = np.random.default_rng(seed + 41)
    rng_bio = np.random.default_rng(seed + 43)
    effort_prior, region_mpa, cpue_prior = priors_to_arrays(empirical_priors, cfg.n_regions)
    if region_mpa.mean() > 0:
        region_mpa = np.clip(region_mpa * (cfg.baseline_mpa_share / region_mpa.mean()), 0, 0.70)
    agents = _generate_agents(local_cfg, rng_agents)
    em = _assign_em(local_cfg, agents, region_mpa, rng_adoption)
    n = agents["n"]
    W = agents["weight"]

    # Individual historical preference vectors. Dirichlet concentration preserves GFW-style hotspots.
    base_pref = effort_prior.mean(axis=0)
    alpha = np.maximum(base_pref * 30.0, 0.05)
    prefs = rng.dirichlet(alpha, size=n)
    beliefs = np.tile(cpue_prior.mean(axis=0), (n, 1))

    biomass = np.full(cfg.n_regions, cfg.initial_biomass_index, dtype=float)
    mpa_effective = np.clip(region_mpa.copy(), 0, 0.70)
    management_quality = cfg.base_management_quality

    base_catch_units = (agents["effort"] * agents["catchability"] * agents["capacity"] * agents["skill"]).sum()
    # Calibrate catch scale so year-zero expected landed value approximates the user-specified baseline.
    annual_target_revenue = cfg.baseline_landed_value_billion * 1e9
    catch_scale = annual_target_revenue / max(base_catch_units * 12 * cfg.base_price_per_tonne * (cfg.n_vessels / n), 1) * _calibration_factor
    capacity = np.full(cfg.n_regions, cfg.carrying_capacity_index)
    # A transparent equilibrium prior converts catch tonnes to stock-index units.
    reference_catch = np.zeros(cfg.n_regions)
    vessel_units = agents["effort"]*agents["catchability"]*agents["capacity"]*agents["skill"]*W
    for month in range(12):
        attraction = np.log(np.maximum(effort_prior[month], 1e-8))[None,:] + .55*np.log(np.maximum(beliefs, 1e-6))
        probability = _softmax(attraction - .30*mpa_effective[None,:])
        probability = (1-cfg.exploration_rate)*probability + cfg.exploration_rate/cfg.n_regions
        crowd = np.sum(probability*W[:,None],axis=0)/W.sum()
        crowd_pen = np.clip(1-cfg.crowding_strength*(crowd/np.maximum(base_pref,.01)-1),.55,1.15)
        baseline_effort = np.clip(1+cfg.management_response_strength*(.5+management_quality)*
                                 (biomass-cfg.target_biomass_index),.60,1.12)
        reference_catch += (probability*vessel_units[:,None]).sum(axis=0)*catch_scale*cpue_prior[month]*biomass**cfg.stock_cpue_elasticity*crowd_pen*baseline_effort
    reference_catch /= 12
    production = cfg.intrinsic_growth_rate/12*biomass*(1-biomass/capacity)
    stock_units = reference_catch / np.maximum(production,1e-12)
    stock_units *= 0.05 / cfg.harvest_pressure_scale
    reference_supply = float(reference_catch.sum())
    # Regional engine has no geographic adjacency; conservative all-region exchange
    # is explicitly a mixing approximation rather than geographic spillover.
    edges = np.argwhere(np.triu(np.ones((cfg.n_regions,cfg.n_regions),dtype=bool),1))

    annual_rows = []
    year1_profit = np.zeros(n)
    stock_asset_proxy = 0.0
    annual_price = cfg.base_price_per_tonne
    fuel_price = cfg.fuel_price_per_litre

    for year in range(cfg.years):
        annual_price = cfg.base_price_per_tonne * ((1.0 + cfg.annual_price_drift) ** year) * math.exp(-0.5 * cfg.annual_price_volatility**2 + rng_market.normal(0, cfg.annual_price_volatility))
        fuel_price = cfg.fuel_price_per_litre * ((1.0 + cfg.annual_fuel_drift) ** year) * math.exp(-0.5 * cfg.annual_fuel_volatility**2 + rng_market.normal(0, cfg.annual_fuel_volatility))

        year_rev = year_profit = year_cost = year_catch = year_effort = year_fuel = year_em_cost = 0.0
        year_mpa_attempts = year_mpa_actual = 0.0
        class_profit = {name: 0.0 for name in cfg.fleet_classes}
        class_revenue = {name: 0.0 for name in cfg.fleet_classes}

        for month in range(12):
            # Management can cap effort if observed stock is poor. Better EM information lowers observation noise.
            observed_adoption = em.mean()
            obs_sigma = max(cfg.observation_error_floor, cfg.observation_error_without_em * (1 - cfg.em_information_gain*observed_adoption))
            observed_stock = np.clip(biomass * rng.lognormal(-0.5*obs_sigma**2, obs_sigma, cfg.n_regions), 0.05, None)
            effective_response = cfg.management_response_strength * (0.5 + management_quality)
            regional_effort_modifier = np.clip(1.0 + effective_response * (observed_stock - cfg.target_biomass_index), 0.60, 1.12)

            historical = effort_prior[month]
            attractiveness = np.log(np.maximum(historical, 1e-8))[None, :] + 0.55*np.log(np.maximum(beliefs, 1e-6))
            attractiveness += 0.65*np.log(np.maximum(biomass[None, :], 1e-6))

            # EM vessels strongly avoid MPA exposure; non-EM only mildly internalize legal risk.
            legal_penalty = np.where(em[:, None], 4.5*mpa_effective[None, :], 0.30*mpa_effective[None, :])
            utility = attractiveness - legal_penalty
            p = _softmax(utility, axis=1)
            p = (1-cfg.exploration_rate)*p + cfg.exploration_rate/cfg.n_regions
            region = _categorical_sample(p, rng)

            # Crowding feedback from simultaneous agent decisions.
            counts = np.bincount(region, weights=W, minlength=cfg.n_regions)
            crowd_share = counts / max(counts.sum(), 1)
            crowd_pen = np.clip(1.0 - cfg.crowding_strength * (crowd_share / np.maximum(base_pref, 0.01) - 1.0), 0.55, 1.15)

            regional_mpa = mpa_effective[region]
            violation_prob = np.where(em, cfg.em_mpa_violation_prob, cfg.non_em_mpa_violation_prob * (0.5 + agents["risk"]))
            attempted = rng.random(n) < regional_mpa
            violated = attempted & (rng.random(n) < violation_prob)
            year_mpa_attempts += np.sum(W * attempted)
            year_mpa_actual += np.sum(W * violated)

            # MPA avoidance creates displacement/travel cost for agents that encounter protected space and comply.
            displaced = attempted & (~violated)
            distance_mult = 1.0 + displaced * (cfg.displacement_extra_distance_pct/100.0)

            effort = agents["effort"] * regional_effort_modifier[region]
            cpue = cpue_prior[month, region] * (biomass[region] ** cfg.stock_cpue_elasticity)
            cpue *= crowd_pen[region]
            catch_noise = rng.lognormal(-0.5*cfg.catch_noise_sigma**2, cfg.catch_noise_sigma, n)
            catch_t = catch_scale * effort * agents["catchability"] * agents["capacity"] * agents["skill"] * cpue * catch_noise

            # Legal access reduces extraction before both stock removal and sales.
            catch_t *= np.where(displaced, 1-regional_mpa, 1.0)
            catch_t, removals = allocate_removals(catch_t, region, W, biomass, stock_units)

            # Landed price includes market supply effect; EM premium is optional and default zero.
            expected_month_supply = max(reference_supply, 1)
            total_catch = float(np.sum(catch_t*W))
            supply_ratio = max(total_catch/expected_month_supply, 0.2)
            price = annual_price * (supply_ratio ** (-cfg.supply_elasticity))
            vessel_price = price * (1.0 + (em & ~violated)*(cfg.traceability_premium_pct/100.0))
            revenue = catch_t * vessel_price

            fuel_l = effort * agents["fuel_lph"] * agents["transit"] * distance_mult
            fuel_cost = fuel_l * fuel_price
            cost_inflation = (1+cfg.annual_inflation_rate)**year
            operating_cost = fuel_cost + (agents["fixed"] + agents["crew"] + agents["var_cost_h"]*effort)*cost_inflation
            em_monthly = em * (cfg.em_capex_per_vessel/(12*max(cfg.em_amortization_years,0.25)) + cfg.em_annual_service_cost*cost_inflation/12)
            risk_loss = cfg.baseline_expected_compliance_loss_annual/12.0 * agents["risk"]
            risk_loss *= np.where(em, 1-cfg.em_risk_reduction_pct/100.0, 1.0)
            total_cost = operating_cost + em_monthly + risk_loss
            profit = revenue - total_cost

            if year == 0:
                year1_profit += profit

            # Learning from realized CPUE; agents update the selected region only.
            realized_index = np.maximum(catch_t / np.maximum(catch_scale*effort*agents["catchability"]*agents["capacity"]*agents["skill"],1e-9), 0.01)
            beliefs[np.arange(n), region] = 0.82*beliefs[np.arange(n), region] + 0.18*realized_index

            # The same physical catch is removed from stock exactly once.
            noise = rng_bio.normal(0, cfg.natural_variability/math.sqrt(12), cfg.n_regions)*biomass
            after_extraction = monthly_stock_step(biomass, capacity, removals, cfg.intrinsic_growth_rate,
                                                 np.zeros(cfg.n_regions), np.zeros(cfg.n_regions), noise)
            exchange = conservative_exchange(after_extraction, capacity, stock_units, edges,
                                             cfg.spillover_rate/(12*max(cfg.n_regions-1,1)))
            biomass = after_extraction + exchange

            year_rev += float(np.sum(revenue*W))
            year_cost += float(np.sum(total_cost*W))
            year_profit += float(np.sum(profit*W))
            year_catch += total_catch
            year_effort += float(np.sum(effort*W))
            year_fuel += float(np.sum(fuel_l*W))
            year_em_cost += float(np.sum(em_monthly*W))
            for cls in cfg.fleet_classes:
                mask = agents["class_name"] == cls
                class_profit[cls] += float(np.sum(profit[mask]*W[mask]))
                class_revenue[cls] += float(np.sum(revenue[mask]*W[mask]))


        # Annual management cycle. Quality improves with EM-derived observability.
        adoption = em.mean()
        info_quality = np.clip(cfg.base_management_quality + cfg.em_information_gain*adoption, 0, 1)
        management_quality = 0.7*management_quality + 0.3*info_quality
        if cfg.adaptive_mpa_enabled:
            # Better information focuses protection toward biologically weak / high-pressure regions.
            weakness = np.clip(cfg.target_biomass_index - biomass, 0, None)
            targeting = weakness / max(weakness.max(), 1e-9)
            delta = cfg.mpa_demarcation_gain * management_quality * targeting * 0.02
            mpa_effective = np.clip(mpa_effective + delta, 0, 0.45)

        stock_asset_proxy = year_profit / max(cfg.discount_rate, 0.01) * max(biomass.mean(),0.1)
        row = {
            "year": year+1,
            "landed_value": year_rev,
            "real_landed_value": year_rev/(1+cfg.annual_inflation_rate)**year,
            "fleet_profit": year_profit,
            "fleet_cost": year_cost,
            "catch_tonnes": year_catch,
            "effort_hours": year_effort,
            "fishing_days": year_effort / 13.5,
            "revenue_per_day": year_rev / max(year_effort / 13.5, 1),
            "fuel_litres": year_fuel,
            "em_cost": year_em_cost,
            "biomass_index": float(biomass.mean()),
            "management_quality": float(management_quality),
            "effective_mpa_share": float(mpa_effective.mean()),
            "mpa_violation_rate": float(year_mpa_actual/max(year_mpa_attempts,1)),
            "supply_chain_footprint": year_rev * cfg.supply_chain_multiplier,
            "stock_asset_proxy": stock_asset_proxy,
        }
        for cls in cfg.fleet_classes:
            row[f"profit::{cls}"] = class_profit[cls]
            row[f"revenue::{cls}"] = class_revenue[cls]
        annual_rows.append(row)

    return pd.DataFrame(annual_rows), pd.DataFrame({
        "class": agents["class_name"],
        "weight": W,
        "em": em,
        "year1_profit": year1_profit,
    }) if return_vessel_year1 else None


def run_paired_monte_carlo(cfg: SimulationConfig, empirical_priors: pd.DataFrame | None = None, progress_cb=None) -> SimulationResult:
    priors = empirical_priors if empirical_priors is not None else demo_empirical_priors(cfg.n_regions)
    reps = max(1, int(cfg.replications))
    all_rows = []
    vessel_impacts = []
    for r in range(reps):
        seed = cfg.seed + r*1009
        bau, bau_v = _run_one(cfg, 0.0, priors, seed, return_vessel_year1=(r==0))
        em, em_v = _run_one(cfg, cfg.adoption_pct, priors, seed, return_vessel_year1=(r==0))
        for name, df in [("BAU", bau), ("EM", em)]:
            z = df.copy()
            z["scenario"] = name
            z["replication"] = r
            all_rows.append(z)
        if r == 0 and bau_v is not None and em_v is not None:
            vi = em_v.copy()
            vi["bau_year1_profit"] = bau_v["year1_profit"].values
            vi["delta_profit"] = vi["year1_profit"] - vi["bau_year1_profit"]
            vi["delta_profit_pct"] = 100*vi["delta_profit"] / np.maximum(np.abs(vi["bau_year1_profit"]), 1)
            vessel_impacts.append(vi)
        if progress_cb:
            progress_cb((r+1)/reps)

    annual = pd.concat(all_rows, ignore_index=True)
    impacts = pd.concat(vessel_impacts, ignore_index=True) if vessel_impacts else pd.DataFrame()

    em_last = annual[(annual.scenario=="EM") & (annual.year==cfg.years)]
    bau_last = annual[(annual.scenario=="BAU") & (annual.year==cfg.years)]
    em_first = annual[(annual.scenario=="EM") & (annual.year==1)]
    bau_first = annual[(annual.scenario=="BAU") & (annual.year==1)]
    paired_first = em_first.sort_values("replication").fleet_profit.values - bau_first.sort_values("replication").fleet_profit.values
    paired_last = em_last.sort_values("replication").fleet_profit.values - bau_last.sort_values("replication").fleet_profit.values

    def npv_for(scenario):
        x = annual[annual.scenario==scenario].pivot(index="replication", columns="year", values="fleet_profit").sort_index(axis=1)
        disc = np.array([(1+cfg.discount_rate)**(-(y-1)) for y in x.columns])
        return (x.values*disc).sum(axis=1)

    npv_em = npv_for("EM")
    npv_bau = npv_for("BAU")
    summary = {
        "year1_profit_delta_mean": float(np.mean(paired_first)),
        "year1_profit_delta_pct_of_bau": float(np.mean(paired_first)/max(abs(np.mean(bau_first.fleet_profit)),1)*100),
        "final_profit_delta_mean": float(np.mean(paired_last)),
        "npv_delta_mean": float(np.mean(npv_em-npv_bau)),
        "p_npv_positive": float(np.mean(npv_em>npv_bau)),
        "p_final_landed_gt_lower": float(np.mean(em_last.landed_value > cfg.lower_value_benchmark_billion*1e9)),
        "p_final_landed_gt_upper": float(np.mean(em_last.landed_value > cfg.upper_value_benchmark_billion*1e9)),
        "em_final_landed_mean": float(em_last.landed_value.mean()),
        "bau_final_landed_mean": float(bau_last.landed_value.mean()),
        "em_final_biomass_mean": float(em_last.biomass_index.mean()),
        "bau_final_biomass_mean": float(bau_last.biomass_index.mean()),
        "em_final_management_mean": float(em_last.management_quality.mean()),
        "bau_final_management_mean": float(bau_last.management_quality.mean()),
    }
    return SimulationResult(annual=annual, vessel_impacts=impacts, summary=summary)
