from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict

@dataclass
class SpeciesConfig:
    name: str
    code: str
    base_price_tonne: float
    growth_rate: float
    carrying_capacity: float
    natural_mortality: float
    migration_strength: float
    climate_sensitivity: float
    bycatch: bool = False

DEFAULT_SPECIES: Dict[str, SpeciesConfig] = {
    "Yellowfin tuna": SpeciesConfig("Yellowfin tuna", "YFT", 4200, 0.34, 1.30, 0.10, 0.16, 0.45),
    "Bigeye tuna": SpeciesConfig("Bigeye tuna", "BET", 6500, 0.23, 1.20, 0.11, 0.13, 0.55),
    "Albacore tuna": SpeciesConfig("Albacore tuna", "ALB", 3600, 0.29, 1.25, 0.10, 0.18, 0.50),
    "Swordfish": SpeciesConfig("Swordfish", "SWO", 5700, 0.26, 1.15, 0.12, 0.12, 0.55),
    "Sharks (aggregate)": SpeciesConfig("Sharks (aggregate)", "SHK", 1200, 0.08, 1.00, 0.07, 0.08, 0.70, True),
    "Marine turtles (index)": SpeciesConfig("Marine turtles (index)", "TUR", 0, 0.06, 1.00, 0.05, 0.10, 0.80, True),
    "Seabirds (index)": SpeciesConfig("Seabirds (index)", "SEA", 0, 0.09, 1.00, 0.06, 0.06, 0.65, True),
}

@dataclass
class GlobalSimulationConfig:
    # world/fleet
    n_vessels: int = 7288
    representative_agents: int = 1500
    years: int = 15
    seed: int = 42
    months_per_frame: int = 1
    grid_deg: int = 10

    # intervention controls exposed to user
    em_adoption_max_pct: float = 75.0
    em_awareness_effect_max_pct: float = 75.0
    premium_max_pct: float = 10.0
    climate_extremity_max_pct: float = 35.0
    government_mpa_push_max_pct: float = 25.0
    government_reallocation_support_max_pct: float = 30.0
    enforcement_push_max_pct: float = 30.0

    # reference defaults / calibrated priors
    baseline_landed_value_billion: float = 6.0
    baseline_violation_prob: float = 0.22
    minimum_residual_violation_prob: float = 0.0075
    violation_persistence: float = 0.72
    mpa_encounter_sensitivity: float = 1.0
    em_capex_per_vessel: float = 28000.0
    em_service_annual: float = 9500.0
    em_amortization_years: float = 5.0
    fuel_price_litre: float = 0.85
    fuel_volatility: float = 0.18
    price_volatility: float = 0.12
    annual_price_drift: float = 0.015  # 1.5% real annual price growth per World Bank Fish to 2030 benchmark
    annual_inflation_rate: float = 0.022  # 2.2% global baseline inflation rate
    demand_elasticity: float = 0.12
    discount_rate: float = 0.07

    # ecology
    harvest_pressure_scale: float = 0.075
    stock_cpue_elasticity: float = 0.85
    spillover_rate: float = 0.16
    migration_temperature_pull: float = 0.45
    climate_shock_persistence: float = 0.60
    severe_depletion_threshold: float = 0.25
    local_extirpation_threshold: float = 0.08

    # management
    base_observability: float = 0.42
    em_observability_gain: float = 0.45
    management_learning_rate: float = 0.30
    management_response_strength: float = 0.35
    mpa_redesign_enabled: bool = True
    reallocation_cost_reduction: float = 0.45

    # premium eligibility
    premium_requires_em: bool = True
    premium_requires_compliance: bool = True

    # species
    species: Dict[str, SpeciesConfig] = field(default_factory=lambda: DEFAULT_SPECIES.copy())
