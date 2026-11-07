# Execution pathway

1. **Select scenario** in the Streamlit sidebar: fleet size, horizon, EM adoption, awareness, premium, MPA and market assumptions.
2. **Configure blue finance**: pool size, grant share, concessional rate, market-rate counterfactual, term, deployment period, productive-capex share and eligibility thresholds.
3. **Generate paired stochastic worlds** using one master seed. BAU and intervention receive common climate, recruitment and market shocks.
4. **Initialize heterogeneous vessel agents** with catchability, fuel efficiency, trust, wealth, debt, administrative burden and quality skill.
5. **Evolve ecological state** by species using growth, recruitment noise, catch, IUU mortality and avoidable mortality.
6. **Evolve monitoring/behaviour**: awareness, trust, adoption/churn, detection and IUU intensity.
7. **Evolve regulation**: bounded dynamic MPA response and bounded effort adaptation.
8. **Evolve markets**: species-specific demand frontier, real-price drift, premium saturation and market-access value.
9. **Allocate blue finance** from a finite pool to eligible vessels. Split proceeds between refinancing and productive capex. Grant tranches can reduce early transition costs.
10. **Update vessel economics**: revenue, operating cost, finance cost, insurance/administrative savings, cash-flow proxies, wealth, debt and solvency.
11. **Aggregate annual outcomes** across Monte Carlo worlds.
12. **Report uncertainty**: median, mean, P5/P25/P75/P95 and probability intervention exceeds BAU.
13. Optional **blue-finance attribution** reruns the intervention with the finance channel disabled to isolate incremental finance effects.
14. Export CSVs and run configuration from the UI.

## Production-calibration path

Before policy use, replace illustrative priors with versioned data snapshots and run hindcast validation:

- RFMO stock trajectories and posterior parameter draws;
- GFW spatial apparent effort plus coverage/error model;
- observer / EM event-level catch, bycatch and detection performance;
- fleet accounts and debt/insurance data;
- buyer/offtake/premium evidence;
- blue-finance application, collateral, approval, default and realized upgrade data.
