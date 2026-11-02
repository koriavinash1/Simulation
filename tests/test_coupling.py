from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from sim.coupling import allocate_removals, conservative_exchange, monthly_stock_step
from sim.global_config import GlobalSimulationConfig
from sim.global_data import load_world
from sim.global_engine import run_paired_global, _polygon_exposure, _transform_mpa
from sim.config import SimulationConfig
from sim.engine import run_paired_monte_carlo


def zero_policy(**kwargs):
    return GlobalSimulationConfig(
        em_adoption_max_pct=0, em_awareness_effect_max_pct=0, premium_max_pct=0,
        government_mpa_push_max_pct=0, government_reallocation_support_max_pct=0,
        enforcement_push_max_pct=0, **kwargs)


def test_extraction_is_absolute_capped_and_shared_with_sales():
    B = np.array([1., 2.])
    units = np.array([10., 100.])
    region = np.array([0, 0, 1])
    weights = np.array([2., 1., 3.])
    catch, removal = allocate_removals(np.array([8., 4., 5.]), region, weights, B, units)
    np.testing.assert_allclose(catch, [4., 2., 5.])
    np.testing.assert_allclose(removal, [1., .15])
    assert np.sum(catch*weights) == pytest.approx(np.sum(removal*units))
    _, twice = allocate_removals(np.array([1., 1., 1.])*2, region, weights, B, units)
    _, once = allocate_removals(np.array([1., 1., 1.]), region, weights, B, units)
    np.testing.assert_allclose(twice, 2*once)


def test_migration_conserves_physical_stock_and_respects_capacity():
    B = np.array([.9, .1, 0.])
    K = np.ones(3)
    units = np.array([100., 10., 5.])
    edges = np.array([[0, 1], [1, 2]])
    delta = conservative_exchange(B, K, units, edges, 100.)
    assert np.sum(delta*units) == pytest.approx(0, abs=1e-12)
    assert np.all(B+delta >= 0)
    assert np.all(B+delta <= K)


def test_zero_stock_has_no_artificial_floor_or_catch():
    B = np.zeros(2)
    catch, removal = allocate_removals(np.ones(2), np.arange(2), np.ones(2), B, np.ones(2))
    assert not catch.any()
    updated = monthly_stock_step(B, np.ones(2), removal, .3, B, B, B)
    np.testing.assert_array_equal(updated, B)


def test_polygon_exposure_preserves_holes_and_wraps_dateline():
    geometry = {"type": "Polygon", "coordinates": [
        [[175,-10],[-175,-10],[-175,10],[175,10],[175,-10]],
        [[178,-2],[-178,-2],[-178,2],[178,2],[178,-2]]
    ]}
    transformed = _transform_mpa(geometry, [180,0], [180,0], 1)
    exposed = _polygon_exposure([transformed], np.array([176,-176,179,0]), np.zeros(4))
    np.testing.assert_array_equal(exposed, [1,1,0,0])


def test_zero_interventions_match_every_numeric_output():
    world,_ = load_world(Path('data'))
    out = run_paired_global(zero_policy(years=3, representative_agents=120, seed=19), world, 20)
    for name in ['monthly', 'annual', 'species_annual', 'animation']:
        a,b = (getattr(out[s],name).drop(columns='scenario') for s in ['BAU','EM'])
        pd.testing.assert_frame_equal(a,b,check_exact=True)
    pd.testing.assert_frame_equal(out['BAU'].vessel_summary,out['EM'].vessel_summary,check_exact=True)
    assert out['BAU'].annual.landed_value.iloc[0] == pytest.approx(6e9, rel=1e-12)


def test_extending_horizon_preserves_earlier_months_in_both_scenarios():
    world,_ = load_world(Path('data'))
    cfg = GlobalSimulationConfig(years=2, representative_agents=100, months_per_frame=6)
    short = run_paired_global(cfg, world, 10)
    long = run_paired_global(replace(cfg, years=4), world, 10)
    for scenario in short:
        pd.testing.assert_frame_equal(short[scenario].monthly, long[scenario].monthly.iloc[:24],check_exact=True)
        pd.testing.assert_frame_equal(short[scenario].annual, long[scenario].annual.iloc[:2],check_exact=True)


def test_stock_ledger_habitat_capacity_and_em_ceiling():
    world,_ = load_world(Path('data'))
    cfg = GlobalSimulationConfig(years=3, representative_agents=100, em_adoption_max_pct=10)
    result = run_paired_global(cfg,world,50)
    for scenario,r in result.items():
        np.testing.assert_allclose(r.monthly.catch_tonnes,r.monthly.stock_removals_tonnes,rtol=1e-13)
        assert (r.monthly.em_share <= .10+1e-12).all()
        assert (r.monthly.fishing_days <= cfg.n_vessels*365.25/12+1e-6).all()
        np.testing.assert_allclose(r.annual.real_landed_value,
            r.annual.landed_value/(1+cfg.annual_inflation_rate)**(r.annual.year-1))
        for frame in r.meta['bio_frames'].values():
            for code,biomass in frame.items():
                assert (biomass>=0).all()
                assert (biomass<=r.meta['capacities'][code]+1e-12).all()
        # Rendering and exposure use exactly the same monthly operating cells.
        for row in r.animation.itertuples():
            cells = world[(world.lon==row.lon)&(world.lat==row.lat)]
            assert len(cells)==1
            assert cells[f'suit_{row.target_species}'].iloc[0]>.015


@pytest.mark.parametrize("market_basis", ["planning", "historical"])
def test_fifteen_year_zero_policy_baseline_real_growth_matches_market_assumption(market_basis):
    world,_ = load_world(Path('data'))
    cfg = zero_policy(years=15, representative_agents=500, months_per_frame=180,
                      climate_extremity_max_pct=0, price_volatility=0,
                      biological_noise_annual=0)
    if market_basis == "historical":
        from sim.market import HISTORICAL_NOMINAL_VALUE_CAGR
        cfg = replace(cfg, annual_price_drift=HISTORICAL_NOMINAL_VALUE_CAGR)
    out = run_paired_global(cfg,world,0)
    a = out['BAU'].annual
    real_cagr = (a.real_landed_value.iloc[-1]/a.real_landed_value.iloc[0])**(1/14)-1
    if market_basis == "planning":
        assert .005 < real_cagr < .03
    else:
        assert real_cagr < 0  # Comparison remains possible; no real-revenue floor.
    pd.testing.assert_frame_equal(out['BAU'].annual.drop(columns='scenario'),
                                  out['EM'].annual.drop(columns='scenario'),check_exact=True)


def test_regional_horizon_and_zero_policy_identity():
    cfg = SimulationConfig(years=2, representative_agents=100, replications=1, adoption_pct=0)
    short = run_paired_monte_carlo(cfg).annual
    long = run_paired_monte_carlo(replace(cfg,years=4)).annual
    for scenario in ['BAU','EM']:
        pd.testing.assert_frame_equal(short[short.scenario==scenario].reset_index(drop=True),
            long[(long.scenario==scenario)&(long.year<=2)].reset_index(drop=True), check_exact=True)
    pd.testing.assert_frame_equal(short[short.scenario=='BAU'].drop(columns='scenario').reset_index(drop=True),
                                  short[short.scenario=='EM'].drop(columns='scenario').reset_index(drop=True),check_exact=True)
    assert short.landed_value.iloc[0] == pytest.approx(6e9,rel=1e-12)


@pytest.mark.parametrize('field,value', [('representative_agents',0),('em_adoption_max_pct',101),
                                       ('em_amortization_years',0),('initial_stock_fraction',1)])
def test_invalid_boundaries_raise(field,value):
    world,_ = load_world(Path('data'))
    cfg = replace(GlobalSimulationConfig(years=1,representative_agents=100),**{field:value})
    with pytest.raises(ValueError):
        run_paired_global(cfg,world,0)


def test_real_growth_and_inflation_compose_multiplicatively():
    from sim.market import nominal_price_growth
    assert nominal_price_growth(.015,.022) == pytest.approx(.03733)
    with pytest.raises(ValueError):
        nominal_price_growth(.015,-1)


def test_changing_inflation_preserves_real_revenue_for_same_real_growth():
    from sim.market import nominal_price_growth
    world,_ = load_world(Path('data'))
    cfg = zero_policy(years=3, representative_agents=100, months_per_frame=180,
                      annual_inflation_rate=0, annual_price_drift=.015)
    low = run_paired_global(cfg, world, 0)
    high = run_paired_global(replace(cfg, annual_inflation_rate=.05,
                           annual_price_drift=nominal_price_growth(.015,.05)), world, 0)
    for scenario in ['BAU','EM']:
        np.testing.assert_allclose(low[scenario].annual.real_landed_value,
                                   high[scenario].annual.real_landed_value,rtol=1e-12)
        np.testing.assert_allclose(low[scenario].annual.catch_tonnes,
                                   high[scenario].annual.catch_tonnes,rtol=1e-12)
