import numpy as np
from sim.config import SimulationConfig
from sim.data_adapter import demo_empirical_priors, validate_priors
from sim.engine import run_paired_monte_carlo


def tiny_cfg():
    return SimulationConfig(n_vessels=300, representative_agents=120, years=3, replications=2, adoption_pct=50, seed=7)


def test_demo_priors_valid():
    ok, msg = validate_priors(demo_empirical_priors(8))
    assert ok, msg


def test_simulation_runs_and_is_finite():
    cfg = tiny_cfg()
    out = run_paired_monte_carlo(cfg, demo_empirical_priors(8))
    assert set(out.annual.scenario.unique()) == {"BAU", "EM"}
    assert len(out.annual) == cfg.replications * cfg.years * 2
    cols = ["landed_value", "fleet_profit", "biomass_index", "management_quality"]
    assert np.isfinite(out.annual[cols].to_numpy()).all()
    assert (out.annual.biomass_index > 0).all()


def test_zero_adoption_near_identical_paired_worlds():
    cfg = tiny_cfg()
    cfg.adoption_pct = 0
    out = run_paired_monte_carlo(cfg, demo_empirical_priors(8))
    a = out.annual[out.annual.scenario=="BAU"].reset_index(drop=True)
    b = out.annual[out.annual.scenario=="EM"].reset_index(drop=True)
    assert np.allclose(a.landed_value, b.landed_value)
    assert np.allclose(a.fleet_profit, b.fleet_profit)
