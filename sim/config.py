from __future__ import annotations
from dataclasses import dataclass, asdict, field
from typing import Dict

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
    "Small coastal": FleetClass(0.30, 0.35, 145, 0.70, 34, 0.75, 11000, 42, 8500, 0.08),
    "Medium regional": FleetClass(0.39, 0.70, 205, 0.95, 58, 1.00, 23000, 55, 17000, 0.07),
    "Large industrial": FleetClass(0.21, 1.65, 275, 1.30, 105, 1.35, 52000, 78, 34000, 0.055),
    "Distant-water freezer": FleetClass(0.10, 2.60, 330, 1.52, 155, 1.70, 89000, 96, 52000, 0.045),
}

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
    annual_price_drift: float = 0.01
    annual_price_volatility: float = 0.12
    supply_elasticity: float = 0.12
    supply_chain_multiplier: float = 2.0

    # Fuel/economics
    fuel_price_per_litre: float = 0.85
    annual_fuel_drift: float = 0.01
    annual_fuel_volatility: float = 0.18
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
        d = asdict(self)
        return d
