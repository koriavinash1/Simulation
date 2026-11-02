from __future__ import annotations
from dataclasses import dataclass, asdict, field
from typing import Dict
from .market import DEFAULT_NOMINAL_PRICE_GROWTH, DEFAULT_INFLATION_RATE

# =============================================================================
# 1. Species Configuration (Global High-Resolution Model)
# =============================================================================

@dataclass
class SpeciesConfig:
    name: str
    code: str
    base_price_tonne: float
    growth_rate: float
    carrying_capacity: float
    # Informational life-history prior; growth_rate is NET surplus production.
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

# =============================================================================
# 2. Fleet Class Configuration (Shared Across Engines)
# =============================================================================

@dataclass
class FleetClass:
    share: float
    capacity_index: float
    effort_hours_month: float
    catchability: float
    fuel_l_per_fishing_hour: float
    transit_factor: float
    fixed_cost_month: float
    variable_cost_per_fishing_hour: float
    crew_cost_month: float
    risk_propensity: float

DEFAULT_FLEET_CLASSES: Dict[str, FleetClass] = {
    "Small coastal": FleetClass(0.30, 0.35, 145, 0.70, 34, 0.75, 4500, 42, 6500, 0.08),
    "Medium regional": FleetClass(0.39, 0.70, 205, 0.95, 58, 1.00, 8500, 55, 12500, 0.07),
    "Large industrial": FleetClass(0.21, 1.65, 275, 1.30, 105, 1.35, 18000, 78, 24000, 0.055),
    "Distant-water freezer": FleetClass(0.10, 2.60, 330, 1.52, 155, 1.70, 32000, 96, 38000, 0.045),
}

# =============================================================================
# 3. Global Simulation Configuration (Primary Engine: Spatial Ocean Grid Twin)
# =============================================================================

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
    fuel_volatility: float = 0.03
    price_volatility: float = 0.02
    annual_price_drift: float = DEFAULT_NOMINAL_PRICE_GROWTH  # nominal composition of 1.5% real growth and 2.2% inflation
    annual_inflation_rate: float = DEFAULT_INFLATION_RATE  # 2.2% global baseline inflation rate
    demand_elasticity: float = 0.12
    policy_phase_in_months: int = 60
    initial_stock_fraction: float = 0.70
    biological_noise_annual: float = 0.01
    discount_rate: float = 0.07

    # ecology
    harvest_pressure_scale: float = 0.035
    stock_cpue_elasticity: float = 0.85
    spillover_rate: float = 0.35
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

    def to_dict(self):
        return asdict(self)

# =============================================================================
# 4. Regional Simulation Configuration (Stylized 8-Region Monte Carlo Model)
# =============================================================================

@dataclass
class SimulationConfig:
    n_vessels: int = 7288
    representative_agents: int = 1200
    years: int = 20
    replications: int = 40
    seed: int = 42
    adoption_pct: float = 50.0
    adoption_strategy: str = "Impact-targeted"
    fleet_classes: Dict[str, FleetClass] = field(default_factory=lambda: DEFAULT_FLEET_CLASSES.copy())

    # Empirical baseline calibration
    baseline_landed_value_billion: float = 6.0
    base_price_per_tonne: float = 6200.0
    baseline_fishing_hours_per_vessel_month: float = 220.0
    annual_price_drift: float = DEFAULT_NOMINAL_PRICE_GROWTH
    annual_price_volatility: float = 0.02
    annual_inflation_rate: float = DEFAULT_INFLATION_RATE
    supply_elasticity: float = 0.12
    supply_chain_multiplier: float = 2.0

    # Fuel/economics
    fuel_price_per_litre: float = 0.85
    annual_fuel_drift: float = 0.01
    annual_fuel_volatility: float = 0.03
    em_capex_per_vessel: float = 28000.0
    em_annual_service_cost: float = 9500.0
    em_amortization_years: float = 5.0
    baseline_expected_compliance_loss_annual: float = 12000.0
    em_risk_reduction_pct: float = 75.0
    traceability_premium_pct: float = 0.0

    # Spatial / MPA behavior
    n_regions: int = 8
    baseline_mpa_share: float = 0.08
    non_em_mpa_violation_prob: float = 0.05
    em_mpa_violation_prob: float = 0.002
    displacement_extra_distance_pct: float = 12.0
    crowding_strength: float = 0.22
    exploration_rate: float = 0.10

    # Biology
    initial_biomass_index: float = 1.0
    carrying_capacity_index: float = 1.35
    intrinsic_growth_rate: float = 0.22
    natural_variability: float = 0.06
    harvest_pressure_scale: float = 0.05
    spillover_rate: float = 0.05

    # Management / information
    base_management_quality: float = 0.42
    em_information_gain: float = 0.42
    observation_error_without_em: float = 0.25
    observation_error_floor: float = 0.06
    management_response_strength: float = 0.35
    adaptive_mpa_enabled: bool = True
    mpa_demarcation_gain: float = 0.35
    target_biomass_index: float = 1.05

    # Stock-to-CPUE
    stock_cpue_elasticity: float = 0.85
    catch_noise_sigma: float = 0.30

    # Benchmarks
    lower_value_benchmark_billion: float = 9.0
    upper_value_benchmark_billion: float = 13.0
    short_term_loss_threshold_pct: float = 5.0
    discount_rate: float = 0.07

    def to_dict(self):
        return asdict(self)
