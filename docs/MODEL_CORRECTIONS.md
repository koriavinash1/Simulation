# Coupling corrections and historical revenue context

Updated 2 November 2026. This document describes the current implementation (`coupled-stock-v3`) and supersedes older claims of empirical validation and all previously published simulation tables, plots and GIFs. The engines are scenario models; mathematical checks are not empirical validation.

## Historical evidence and monetary basis

| Observation year | Approximate global capture first-sale value, nominal USD | Source |
|---|---:|---|
| 2018 | $151B | [FAO SOFIA 2020](https://doi.org/10.4060/ca9229en); also reported in [PNAS 2021](https://pmc.ncbi.nlm.nih.gov/articles/PMC8346865/) |
| 2020 | $141B | [FAO SOFIA 2022, global overview](https://www.fao.org/4/cc0461en/online/sofia/2022/world-fisheries-aquaculture.html) |
| 2022 | $159B | [FAO SOFIA 2024](https://doi.org/10.4060/cd0683en), key messages on capture production |

These rounded, cross-edition observations are historical context, not an annual time series fit. Coverage and revisions differ, notably inclusion of algae in the 2024 capture summary. They describe worldwide capture fisheries, including inland fisheries, not the longline fleet. They must not be confused with seafood export receipts, aquaculture revenues or sector GDP/value added. The pandemic interval shows that annual declines can occur.

The endpoint calculation `(159/151)^(1/4)-1 = 1.30%` provides the **historical nominal comparison**, rather than an estimate of species-specific price inflation. The default now uses the user-requested planning assumption of 1.5% annual real price growth, composed with 2.2% inflation to obtain 3.733% nominal price growth: `(1.015*1.022)-1`. This positive-real-growth assumption is explicit and is not inferred from the historical values. The app exposes both market scenarios and the real-growth and inflation assumptions. The intermediate 2020 observation is context, not an input to that endpoint calculation. Source observations and the calculation are stored in `sim/market.py`. The app does not claim a World Bank guarantee of 1–2% real revenue growth. [OECD–FAO 2024–2033](https://www.oecd.org/en/publications/oecd-fao-agricultural-outlook-2024-2033_4c5d2cfb-en/full-report/component-12.html) actually projects falling real prices across fish product groups.

`landed_value`, prices, profits and costs use nominal dollars. `real_landed_value` divides by `(1+annual_inflation_rate)^(year-1)`. Real growth is `(1+nominal_growth)/(1+inflation)-1`; adding inflation again to nominal revenue would double count it. The 2.2% deflator is a scenario assumption, not an observed country-specific USD deflator. Under this assumption, modest nominal revenue growth may correspond to declining real revenue.

The $6B longline baseline remains a user-configurable scenario anchor, not an independently verified World Bank longline statistic. Both engines now calibrate the same pre-policy first year to that anchor, including stochastic catch, crowding and legal access. The scale is shared by BAU and EM. It is fixed thereafter; there is no revenue floor, annual rescaling, guaranteed EM dividend or forced growth corridor.

## Physical accounting

Each species has habitat capacity `K` and initial stock `B = 0.70 K` in the global engine. Outside resident habitat both are exactly zero. Growth rates describe **net surplus production**; the legacy `natural_mortality` species field is informational and is not subtracted again.

For each cell, the fixed conversion `u` maps a stock index to physical target tonnes (or to synthetic bycatch units). At the reference exploitation setting it is inferred from expected reference catch `H0` and initial monthly surplus production:

```
u[g] = H0[g] / ((r/12) * B0[g] * (1-B0[g]/K[g]))
```

This is an explicit equilibrium initialization prior, not measured stock tonnage. `harvest_pressure_scale` changes inferred stock size inversely relative to the reference setting (0.035 global, 0.05 regional), allowing stressed stocks and sustained depletion. Vessel counts, catchability and capacities still need fishery-specific calibration.

Requested cell extraction is the sum of **absolute** weighted catches. If it exceeds `u*B`, all catches in that cell/species are proportionally reduced. The same realized catch drives sales and removal `H/u`. Protected status reduces fishing access before capture; there is no second protection discount on recorded removals. The global monthly `stock_removals_tonnes` ledger equals `catch_tonnes` for target species.

The stock update is logistic surplus growth minus realized extraction plus conservative exchange, climate mortality and proportional environmental noise. Bounds are `[0,K]`. There is no artificial positive stock or CPUE floor. After extraction, growth and environmental changes, neighboring resident ocean cells exchange remaining physical biomass down differences in `B/K`; donor availability and receiver space constrain transfers. Every transfer has an equal donor debit and receiver credit. No independent spillover creation term remains. Coarse adjacency does not resolve currents, coast-crossing routes or detailed population connectivity. The regional engine uses explicit all-region mixing because it has no geographic adjacency.

Climate and market shocks have separate seeded random streams. Moderate climate variability affects catch availability quadratically; additional stock mortality applies to anomalies beyond 0.20, quadratically, divided by 12. These remain scenario sensitivities, not fitted oceanographic response curves. Habitat envelopes and carrying capacity stay fixed; the engine does not dynamically transport habitat poleward.

## Space, MPAs and behavior

A vessel frame represents its monthly fishing cell, not an intermediate voyage waypoint. Position, habitat, CPUE, closure exposure and enforcement use that same cell. Monthly relocation distance contributes to fuel demand; voyage paths and coastal routing are not simulated. The effort multiplier is mean-one lognormal noise with bounded stock/management feedback, rather than an addition that always hit the maximum cap. Reported days per vessel are capped at the average calendar days per month.

When polygons are installed, one dateline-aware transformation supplies both map boundaries and point-in-polygon exposure at fishing-cell centers, including polygon holes. This removes the former Gaussian pseudo-boundaries. Cell-center membership is a coarse-grid approximation, not an area-intersection calculation. Without polygons, exposure explicitly falls back to fractional cell protection priors. Dynamic polygon redesign requires an enabled government MPA push. Policy rollout uses elapsed months and a fixed 60-month phase-in rather than the selected simulation endpoint.

Awareness acts through its configured reduction rather than an additional hidden 94% deterrence. Baseline violation propensity is no longer multiplied into a saturated 70% cap. EM gear mitigation, management information, optional verified premiums, government enforcement and reallocation support remain separate modeled mechanisms of the intervention package. Setting awareness alone to zero does not disable the other mechanisms. No automatic BAU trade-sanction penalty remains. Premium eligibility respects both EM and compliance settings.

Monthly fixed and crew costs are calibrated to empirical commercial longline cost-earnings benchmarks (NOAA PIFSC / FAO SOFIA), where trip costs (fuel, bait, gear) represent ~48–54% of gross revenue, crew labor represents ~20–23%, and fixed vessel overhead represents ~15–18%. This yields a realistic baseline operating profit margin of ~5–15% (+~$320M to +$720M/yr in Year 1 across the fleet), confirming commercial viability in BAU without artificial losses. Nonfuel operating costs and EM service fees adjust with nominal inflation. Bycatch encounter counts are relative threshold indicators, not independently calibrated mortality counts. Quantitative EM attribution requires component ablations and empirical calibration.

## Required paired-world behavior

With adoption, awareness, premium, MPA push, reallocation support and enforcement push all zero, BAU and EM are exactly equal apart from scenario labels. Climate can be nonzero because it is shared. Every policy mechanism remains conditional on its own control; zero adoption alone does not disable independent government policy.

Reallocation support is now exposed in the app rather than silently remaining at 30%. Extending the simulation horizon preserves all earlier monthly and annual results, including intervention rollout, because random streams and policy schedules no longer depend on the endpoint.

## Verification

`uv run --no-sync pytest -q` covers zero-policy identity across all numeric outputs, physical extraction and sale consistency, migration conservation, stock bounds and extinction, exact polygon membership with holes and the dateline, adoption ceilings, habitat-position consistency, inflation conversion, horizon prefixes in both engines, a 15-year nominal baseline regression and input boundaries.

The following single-seed results describe the previous historical-proxy default and are archived; current planning and historical comparison aggregates are in [COMPREHENSIVE_MODEL_REPORT.md](COMPREHENSIVE_MODEL_REPORT.md):

| Scenario | Year 1 nominal landed value | Year 15 nominal landed value | Endpoint CAGR |
|---|---:|---:|---:|
| Default BAU | $6.000B | $7.209B | 1.32% |
| Default intervention package | $6.031B | $7.423B | 1.49% |
| All intervention controls zero, climate zero: either world | $6.000B | $7.205B | 1.32% |

These archived reference runs are not current planning-scenario results or forecasts with confidence intervals. A stress run with fourfold exploitation pressure and no price drift declines substantially, confirming that growth is not imposed on revenues. Representative-agent resolution and seed still affect trajectories; first-year calibration alone does not eliminate sampling uncertainty.
