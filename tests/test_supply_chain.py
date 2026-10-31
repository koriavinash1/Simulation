import pytest
import pandas as pd
from sim.supply_chain import (
    COMPETITOR_DATABASE,
    compute_supply_chain_metrics,
    generate_sample_gdst_record,
    CompetitorProfile
)
from sim.global_config import GlobalSimulationConfig
from sim.global_engine import GlobalSimulationResult


def test_competitor_database():
    assert len(COMPETITOR_DATABASE) >= 8
    names = [c.name for c in COMPETITOR_DATABASE]
    assert "Satlink" in names
    assert "ThisFish" in names
    assert "Trace Register" in names
    assert "Wholechain" in names
    assert "Marine Instruments" in names

    for c in COMPETITOR_DATABASE:
        assert isinstance(c, CompetitorProfile)
        assert c.stage in ["First Mile", "Middle Mile", "Last Mile", "Cross-Chain"]
        assert len(c.flagship_products) > 0
        assert len(c.technology_stack) > 10
        assert len(c.relationship_to_our_platform) > 20


def test_supply_chain_metrics_computation():
    cfg = GlobalSimulationConfig()

    # Mock simulation results
    bau_annual = pd.DataFrame({
        "year": list(range(1, 16)),
        "catch_tonnes": [1_000_000.0] * 15,
        "landed_value": [4_000_000_000.0] * 15,
    })
    em_annual = pd.DataFrame({
        "year": list(range(1, 16)),
        "catch_tonnes": [1_200_000.0] * 15,
        "landed_value": [5_200_000_000.0] * 15,
    })

    bau_res = GlobalSimulationResult(
        monthly=pd.DataFrame(),
        annual=bau_annual,
        animation=pd.DataFrame(),
        species_annual=pd.DataFrame(),
        vessel_summary=pd.DataFrame(),
        meta={"realized_em_share": 0.0}
    )
    em_res = GlobalSimulationResult(
        monthly=pd.DataFrame(),
        annual=em_annual,
        animation=pd.DataFrame(),
        species_annual=pd.DataFrame(),
        vessel_summary=pd.DataFrame(),
        meta={"realized_em_share": 0.75}
    )

    metrics = compute_supply_chain_metrics(bau_res, em_res, cfg)
    assert "comparison_table" in metrics
    assert "metrics" in metrics
    assert metrics["metrics"]["first_mile_fidelity_gain"] > 15.0
    assert metrics["metrics"]["port_delay_reduction_hours"] > 40.0
    assert metrics["metrics"]["demurrage_savings_billion"] > 0.0
    assert metrics["metrics"]["spoilage_avoided_tonnes"] > 0.0
    assert metrics["metrics"]["gdst_score_em"] > 70.0
    assert metrics["metrics"]["retail_premium_dividend_billion"] > 0.0
    assert metrics["metrics"]["co2_saved_million_tonnes"] > 0.0

    df = metrics["comparison_table"]
    assert len(df) >= 10
    assert "Supply Chain Dimension" in df.columns
    assert "BAU Legacy" in df.columns
    assert "EM Connected" in df.columns


def test_sample_gdst_record():
    rec = generate_sample_gdst_record()
    assert rec["standard"] == "GDST 1.2 / GS1 EPCIS 2.0"
    ctes = rec["critical_tracking_events"]
    assert "harvest_cte" in ctes
    assert "landing_cte" in ctes
    assert "processing_cte" in ctes
    assert "distribution_and_retail_cte" in ctes
    assert "vessel_name" in ctes["harvest_cte"]
    assert "consumer_qr_code" in ctes["distribution_and_retail_cte"]
