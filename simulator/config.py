from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Dict, Any


@dataclass
class BlueFinanceConfig:
    enabled: bool = True
    bond_size_musd: float = 15.0
    grant_fraction: float = 0.20
    loan_fraction: float = 0.80
    blue_loan_rate: float = 0.04
    market_loan_rate: float = 0.085
    loan_term_years: int = 15
    disbursement_years: int = 8
    max_loan_per_vessel_usd: float = 50000.0
    refinance_fraction: float = 0.45
    productive_capex_fraction: float = 0.55
    eligibility_trust: float = 0.55
    eligibility_compliance: float = 0.70
    capex_cost_reduction_max: float = 0.055
    capex_quality_gain_max: float = 0.020
    household_resilience_share: float = 0.20


@dataclass
class SimulationConfig:
    years: int = 30
    n_vessels: int = 7000
    n_replicates: int = 100
    seed: int = 20261107

    # Ecology
    initial_biomass_yft: float = 0.60
    initial_biomass_bet: float = 0.50
    initial_biomass_alb: float = 0.65
    avoidable_mortality_rate: float = 0.050
    awareness_mortality_reduction_max: float = 0.70
    recruitment_protection_max: float = 0.08

    # EM / behaviour
    initial_em_adoption: float = 0.30
    initial_awareness: float = 0.28
    em_gross_cost_usd: float = 9000.0
    em_subsidy_years_1_2: float = 0.75
    em_subsidy_years_3_5: float = 0.50
    em_subsidy_years_6_8: float = 0.25
    detection_strength: float = 0.58
    awareness_campaign_strength: float = 0.55

    # Governance / MPA
    initial_iuu: float = 0.11
    initial_mpa: float = 0.10
    max_mpa: float = 0.30
    dynamic_mpa: bool = True
    enforcement_multiplier: float = 1.25

    # Market / economics
    base_cost_per_vessel_usd: float = 138000.0
    demand_growth_yft: float = 0.012
    demand_growth_bet: float = 0.013
    demand_growth_alb: float = 0.010
    real_price_drift_yft: float = -0.006
    real_price_drift_bet: float = -0.004
    real_price_drift_alb: float = -0.007
    inflation: float = 0.024
    max_verified_premium: float = 0.05
    premium_market_capacity: float = 0.35
    bau_effort_cap: float = 1.45
    intervention_effort_cap: float = 1.32

    # Short/medium-term benefit stack
    reporting_saving_max: float = 0.019
    inspection_saving_max: float = 0.014
    operational_saving_max: float = 0.032
    quality_gain_max: float = 0.017
    payment_speed_gain_max: float = 0.006
    market_access_gain_max: float = 0.016
    insurance_saving_max: float = 0.010
    finance_saving_max: float = 0.015

    blue_finance: BlueFinanceConfig = None  # type: ignore

    def __post_init__(self) -> None:
        if self.blue_finance is None:
            self.blue_finance = BlueFinanceConfig()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
