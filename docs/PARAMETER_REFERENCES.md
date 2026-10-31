### Active Scenario Controls

The scenario sidebar exposes 5 primary bioeconomic policy and environmental forcing controls:

1. **EM Adoption Ceiling (`em_adoption_max_pct`):** Upper fleet adoption tendency (0–100%). Installation is assigned across vessel size classes; realized coverage drives management observability ($Q_t$), mandates circle hooks/tori lines, eliminates non-compliance on equipped vessels, and unlocks export certification eligibility.
2. **Verified Market Premium (`premium_max_pct`):** Export market price premium (0–20%) realized exclusively by compliant EM vessels, driving the economic reform dividend.
3. **Dynamic MPA Expansion / Spatial Push (`government_mpa_push_max_pct`):** Policy pressure (0–50%) that endogenously shifts marine reserve centroids $\vec{C}_k(t)$ toward the Conservation Priority Field $\Psi(g, t)$ (depleted tuna stocks + fleet congestion + bycatch corridors) and expands reserve radii.
4. **General Compliance & Enforcement Push (`enforcement_push_max_pct`):** Surveillance fine intensity multiplier (0–60%) and norm pressure ($1 - 0.55 G_t$) that deters unmonitored vessels from poaching inside reserves.
5. **Climate Extremity Ceiling (`climate_extremity_max_pct`):** Maximum warming anomaly amplitude (0–80%) driving stochastic temperature paths, shifting species isotherms poleward ($\Delta \text{lat} = c_t \times 12^\circ$), drifting MPAs, and inducing heatwave mortality.

---

### Reference / Default Calibrated Model Parameters

The remaining parameters are calibrated scientific priors located in `sim/global_config.py`:

| Parameter | Default | Meaning | Calibration Target / Empirical Reference |
|:---|---:|:---|:---|
| Registered longliners | 7,288 | Global longline fleet population | FAO / Tuna-RFMO / ISSF global vessel registries |
| Baseline violation probability | 5.5% | Reference non-compliance propensity | Empirical paper-park poaching scenarios |
| Residual violation floor | 0.75% | Non-zero non-compliance floor | Prevents artificial zero violation assumptions |
| EM equipment Capex | $28,000 | Hardware & camera installation amortized over 5 yrs | Commercial hardware BOM & industry estimates |
| EM ongoing Opex | $9,500/yr | Video review, audit & satellite communications | Operational industry averages |
| Bunker fuel price | $0.85/L | Marine diesel fuel reference | World Bank / EIA / IMO global fuel series |
| Baseline global landed value | $6.0B/yr | Global tuna longline catch valuation anchor | FAO / World Bank global fisheries statistics |
| Base management observability | 0.42 | Baseline information quality index ($Q_0$) | RFMO observer coverage baselines (~5%) |
| EM observability gain | 0.45 | Maximum gain in $Q_t$ from full fleet EM coverage | Electronic logbook & video audit fidelity |
