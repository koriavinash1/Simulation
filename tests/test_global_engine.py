import numpy as np
from sim.global_config import GlobalSimulationConfig
from sim.global_data import generate_fallback_world
from sim.global_engine import run_paired_global

def test_global_runs_and_residual_noncompliance():
    cfg=GlobalSimulationConfig(years=2,representative_agents=300,seed=7,em_adoption_max_pct=70,climate_extremity_max_pct=25)
    r=run_paired_global(cfg,generate_fallback_world(20),100)
    assert len(r["EM"].annual)==2
    assert 0 <= r["EM"].meta["realized_em_share"] <= 1
    assert np.isfinite(r["EM"].annual["fleet_profit"]).all()
    assert (r["EM"].annual["illegal_events"]>=0).all()

def test_climate_bound():
    cfg=GlobalSimulationConfig(years=2,representative_agents=200,seed=9,climate_extremity_max_pct=18)
    r=run_paired_global(cfg,generate_fallback_world(20),50)
    assert abs(r["EM"].meta["climate_min"]) <= .180001
    assert abs(r["EM"].meta["climate_max"]) <= .180001


def test_animation_plotly_frames():
    import plotly.graph_objects as go
    cfg = GlobalSimulationConfig(years=1, representative_agents=100, seed=42, months_per_frame=3)
    r = run_paired_global(cfg, generate_fallback_world(20), 50)
    ad = r["EM"].animation
    assert not ad.empty
    sample_frames = sorted(ad.frame.unique())
    frames = []
    for fr in sample_frames:
        z = ad[ad.frame == fr]
        trace = go.Scattergeo(
            lon=z.lon,
            lat=z.lat,
            mode="markers",
            marker=dict(
                size=np.where(z.em, 6, 4),
                symbol=np.where(z.illegal, "x", "circle"),
                color=np.where(z.em, 1, 0),
                colorscale=[[0, "#888"], [1, "#ff8c42"]],
                cmin=0,
                cmax=1,
                opacity=0.75,
            ),
            hovertext=[f"agent {a}" for a in z.agent],
            hoverinfo="text",
        )
        frames.append(go.Frame(name=str(fr), data=[trace], traces=[2]))
    assert len(frames) == len(sample_frames)


def test_realistic_data_pack_loaded_and_zero_land():
    from pathlib import Path
    import json
    from shapely.geometry import Point
    from sim.global_data import load_world, load_mpas
    from sim.global_engine import _get_prep_land

    data_dir = Path(__file__).resolve().parents[1] / "data"
    world, src = load_world(data_dir)
    assert "verified open-data pack" in src
    assert len(world) >= 300
    assert (world.mpa_share >= 0).all()

    mpa_path = load_mpas(data_dir)
    assert mpa_path is not None
    with open(mpa_path, "r", encoding="utf-8") as f:
        geo = json.load(f)
    assert len(geo["features"]) == 15

    cfg = GlobalSimulationConfig(years=2, representative_agents=150, seed=123, months_per_frame=2)
    r = run_paired_global(cfg, world, 80)
    prep_land = _get_prep_land()
    assert prep_land is not None

    for scen in ["BAU", "EM"]:
        ad = r[scen].animation
        assert not ad.empty
        land_hits = sum(prep_land.contains(Point(r.lon, r.lat)) for _, r in ad.iterrows())
        assert land_hits == 0, f"Found {land_hits} vessels on land in scenario {scen}!"


def test_dynamic_mpas_shift_and_expand_over_time():
    import json
    from pathlib import Path
    from sim.global_data import get_frame_mpas
    from sim.global_engine import _get_prep_land

    data_dir = Path(__file__).resolve().parents[1] / "data"
    mpa_path = data_dir / "processed" / "marine_mpas.geojson"
    assert mpa_path.exists()
    with open(mpa_path, "r", encoding="utf-8") as f:
        geo = json.load(f)
    features = geo["features"]
    prep_land = _get_prep_land()

    # Under EM: frame 0 vs frame 120 (with warming climate +0.35 and 30% push)
    l0, a0, h0, c_l0, c_a0, ch0 = get_frame_mpas(features, 0, 120, 0.0, True, 30.0, prep_land)
    l1, a1, h1, c_l1, c_a1, ch1 = get_frame_mpas(features, 120, 120, 0.35, True, 30.0, prep_land)

    # In EM, northern reserves shift poleward (latitude increases)
    assert c_a1[0] > c_a0[0], "Northern MPA should shift northward under climate warming in EM twin"
    # Area should expand by ~29%
    assert "expansion" in h1[0] or "%" in h1[0]

    # Under BAU: frame 0 vs frame 120 remains static
    b_l0, b_a0, b_h0, bc_l0, bc_a0, bch0 = get_frame_mpas(features, 0, 120, 0.0, False, 30.0, prep_land)
    b_l1, b_a1, b_h1, bc_l1, bc_a1, bch1 = get_frame_mpas(features, 120, 120, 0.35, False, 30.0, prep_land)

    assert bc_a0 == bc_a1, "BAU MPA centroids should remain static across time"
    assert b_l0 == b_l1, "BAU MPA boundaries should remain static across time"


def test_coupled_engine_dynamic_mpas():
    from pathlib import Path
    from sim.global_data import load_world
    from sim.global_engine import run_paired_global

    data_dir = Path(__file__).resolve().parents[1] / "data"
    world, _ = load_world(data_dir)
    cfg = GlobalSimulationConfig(
        years=2,
        representative_agents=150,
        seed=42,
        months_per_frame=4,
        government_mpa_push_max_pct=35.0,
        em_adoption_max_pct=75.0,
    )
    r = run_paired_global(cfg, world, 60)

    # Verify both scenarios generated coupled mpa_frames
    assert "mpa_frames" in r["EM"].meta
    assert "mpa_frames" in r["BAU"].meta
    em_frames = r["EM"].meta["mpa_frames"]
    bau_frames = r["BAU"].meta["mpa_frames"]
    assert len(em_frames) > 1
    assert len(bau_frames) > 1

    sample_frames = sorted(em_frames.keys())
    f0 = sample_frames[0]
    f_last = sample_frames[-1]

    # In BAU, centroids must remain static
    _, _, _, bau_c0_lon, bau_c0_lat, _ = bau_frames[f0]
    _, _, _, bau_clast_lon, bau_clast_lat, _ = bau_frames[f_last]
    assert np.allclose(bau_c0_lon, bau_clast_lon, atol=1e-5)
    assert np.allclose(bau_c0_lat, bau_clast_lat, atol=1e-5)

    # In EM, dynamic coupling must shift centroids toward fishing congestion and depleted stocks
    _, _, _, em_c0_lon, em_c0_lat, _ = em_frames[f0]
    _, _, _, em_clast_lon, em_clast_lat, _ = em_frames[f_last]

    # Total distance shifted across all 15 reserves
    total_shift = float(np.sum(np.hypot(
        ((np.array(em_clast_lon) - np.array(em_c0_lon) + 180) % 360) - 180,
        np.array(em_clast_lat) - np.array(em_c0_lat)
    )))
    assert total_shift > 1.5, f"Expected dynamic MPAs to shift toward pressure/depletion, got total shift {total_shift:.2f}°"


def test_fisheries_management_economic_dividend():
    from pathlib import Path
    from sim.global_data import load_world
    from sim.global_engine import run_paired_global

    data_dir = Path(__file__).resolve().parents[1] / "data"
    world, _ = load_world(data_dir)
    cfg = GlobalSimulationConfig(
        years=5,
        representative_agents=150,
        seed=42,
        months_per_frame=6,
        government_mpa_push_max_pct=25.0,
        em_adoption_max_pct=65.0,
    )
    r = run_paired_global(cfg, world, 60)

    # Multi-year economic dividend: EM intervention twin must outperform unmanaged BAU baseline
    em_prof = float(r["EM"].annual["fleet_profit"].sum())
    bau_prof = float(r["BAU"].annual["fleet_profit"].sum())
    profit_dividend = em_prof - bau_prof

    em_landed = float(r["EM"].annual["landed_value"].sum())
    bau_landed = float(r["BAU"].annual["landed_value"].sum())
    landed_dividend = em_landed - bau_landed

    assert landed_dividend > 0, f"Expected positive landed value dividend, got {landed_dividend/1e6:.1f}M"
    assert profit_dividend > 0, f"Expected positive fleet operating profit dividend, got {profit_dividend/1e6:.1f}M"


def test_coupled_bycatch_and_compliance_dynamics():
    from pathlib import Path
    from sim.global_data import load_world
    from sim.global_engine import run_paired_global

    data_dir = Path(__file__).resolve().parents[1] / "data"
    world, _ = load_world(data_dir)
    cfg = GlobalSimulationConfig(
        years=3,
        representative_agents=150,
        seed=42,
        months_per_frame=4,
        em_adoption_max_pct=70.0,
        government_mpa_push_max_pct=20.0,
    )
    r = run_paired_global(cfg, world, 50)

    # 1. Bycatch mitigation: EM verified gear reduces bycatch encounter events
    em_byc = r["EM"].annual["bycatch_events"].sum()
    bau_byc = r["BAU"].annual["bycatch_events"].sum()
    assert em_byc < bau_byc, f"Expected EM bycatch ({em_byc:.0f}) to be lower than BAU ({bau_byc:.0f})"

    # 2. Vessel summary contains bycatch total and within each size class, EM vessels have lower bycatch
    v_em = r["EM"].vessel_summary
    assert "bycatch_total" in v_em.columns
    for cls_name in ["Medium regional", "Large industrial", "Distant-water freezer"]:
        sub = v_em[v_em["class"] == cls_name]
        if sub.em.any() and (~sub.em).any():
            mean_byc_em = sub[sub.em].bycatch_total.mean()
            mean_byc_non = sub[~sub.em].bycatch_total.mean()
            assert mean_byc_em < mean_byc_non, f"In {cls_name}: EM bycatch ({mean_byc_em:.1f}) should be lower than non-EM ({mean_byc_non:.1f})"

    # 3. Monthly rows include bycatch_events and finite values
    assert "bycatch_events" in r["EM"].monthly.columns
    assert np.isfinite(r["EM"].monthly["bycatch_events"]).all()

    # 4. Compliance: EM adoption suppresses illegal poaching events compared to unmonitored BAU
    em_ill = r["EM"].annual["illegal_events"].sum()
    bau_ill = r["BAU"].annual["illegal_events"].sum()
    assert em_ill < bau_ill, f"Expected EM illegal events ({em_ill:.0f}) to be lower than BAU ({bau_ill:.0f})"


def test_regional_species_bounds_and_zero_polar_yft():
    from pathlib import Path
    from sim.global_data import load_world
    from sim.global_engine import run_paired_global

    data_dir = Path(__file__).resolve().parents[1] / "data"
    world, _ = load_world(data_dir)

    # 1. YFT is strictly tropical/subtropical (|lat| <= 35) and 0 at polar/sub-polar latitudes
    polar_mask = np.abs(world.lat.values) >= 36.0
    trop_mask = np.abs(world.lat.values) <= 30.0
    assert np.all(world.loc[polar_mask, "suit_YFT"] == 0.0), "YFT suitability must be strictly 0 outside |lat| <= 35"
    assert (world.loc[trop_mask, "suit_YFT"] > 0.0).any(), "YFT suitability must be positive in tropical basins"

    # 2. Albacore avoids equatorial doldrums (|lat| <= 8)
    eq_mask = np.abs(world.lat.values) <= 8.0
    assert np.all(world.loc[eq_mask, "suit_ALB"] == 0.0), "Albacore must be 0 in equatorial doldrums"

    # 3. Seabirds avoid tropical waters (|lat| <= 16)
    subtrop_eq = np.abs(world.lat.values) <= 16.0
    assert np.all(world.loc[subtrop_eq, "suit_SEA"] == 0.0), "Seabirds must be 0 in equatorial belt"

    # 4. Simulation preserves zero biomass and zero catch for YFT in non-resident cells
    cfg = GlobalSimulationConfig(years=2, representative_agents=150, seed=42, months_per_frame=2)
    res = run_paired_global(cfg, world, 40)
    for sc in ["BAU", "EM"]:
        bio_frames = res[sc].meta["bio_frames"]
        for fr, frame in bio_frames.items():
            yft_bio = frame["YFT"]
            assert np.all(yft_bio[polar_mask] == 0.0), f"YFT biomass unexpectedly positive at |lat| >= 36 in {sc} fr {fr}"
            assert np.any(yft_bio[trop_mask] > 0.0), f"YFT biomass missing in tropics in {sc} fr {fr}"




