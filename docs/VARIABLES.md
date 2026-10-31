# Main variables and controls

| Variable | Meaning | Role |
|---|---|---|
| `n_vessels` | Total fleet represented | System scale |
| `representative_agents` | Number of explicit simulated vessel agents | Performance vs granularity |
| `adoption_pct` | Share of agents assigned EM | Main intervention |
| `adoption_strategy` | Random, capacity-targeted, impact-targeted | Determines who receives EM |
| `baseline_landed_value_billion` | Initial annual ex-vessel value target | Calibration anchor |
| `base_price_per_tonne` | Average first-sale price | Revenue |
| `fuel_price_per_litre` | Fuel price | Cost |
| `em_capex_per_vessel` | EM hardware/install capital cost | Short-run cost |
| `em_annual_service_cost` | Annual EM service cost | Recurring cost |
| `baseline_expected_compliance_loss_annual` | Expected annual loss exposure before vessel risk scaling | Risk economics |
| `em_risk_reduction_pct` | Reduction in expected compliance risk | Potential EM benefit |
| `traceability_premium_pct` | Optional price premium | Scenario; defaults to zero |
| `non_em_mpa_violation_prob` | Conditional protected-area violation probability | BAU behavior |
| `em_mpa_violation_prob` | Conditional violation probability with EM | Compliance effect |
| `displacement_extra_distance_pct` | Extra travel for a displaced compliant vessel | Short-run MPA cost |
| `crowding_strength` | Penalty when vessels concentrate in the same region | Multi-agent interaction |
| `intrinsic_growth_rate` | Biological growth parameter | Stock dynamics |
| `carrying_capacity_index` | Maximum biomass index | Stock dynamics |
| `harvest_pressure_scale` | Strength of catch pressure on biomass | Stock dynamics |
| `em_information_gain` | Strength of EM's effect on manager information | Management pathway |
| `management_response_strength` | How strongly effort responds to perceived stock | Policy feedback |
| `adaptive_mpa_enabled` | Allow effective protection to adapt | Spatial management |
| `mpa_demarcation_gain` | Speed/strength of targeting improvement | MPA pathway |
| `discount_rate` | NPV discount rate | Long-run economics |
| `supply_chain_multiplier` | Gross-output multiplier | Broader footprint scenario |

## Vessel-class variables

Each class has a share, capacity index, monthly effort, catchability, fuel use per fishing hour, transit factor, fixed cost, variable cost, crew cost and compliance-risk propensity. These are editable directly in the app. Shares are normalized internally.
