from simulator import BlueFinanceConfig, SimulationConfig, run_paired_simulation
from simulator.reporting import build_horizon_table


def test_small_run_smoke():
    cfg = SimulationConfig(
        years=3,
        n_vessels=80,
        n_replicates=3,
        seed=7,
        blue_finance=BlueFinanceConfig(enabled=True, bond_size_musd=1.0),
    )
    result = run_paired_simulation(cfg)
    assert not result["summary"].empty
    assert not result["final"].empty
    assert set(result["summary"]["scenario"].unique()) == {"BAU", "INTERVENTION"}
    assert (result["final"]["metric"] == "biomass_ratio").any()
    assert not build_horizon_table(result).empty
