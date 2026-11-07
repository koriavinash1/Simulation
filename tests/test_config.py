from simulator import SimulationConfig


def test_default_blue_finance_config_is_created():
    cfg = SimulationConfig()
    assert cfg.blue_finance is not None
    assert cfg.blue_finance.loan_fraction == 0.80
