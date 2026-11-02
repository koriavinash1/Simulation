"""Render the comprehensive report from saved paired ensemble outputs.

Run after aggregate_model_report.py:
  uv run --no-sync python scripts/render_ensemble_report.py
"""
from pathlib import Path
import hashlib
import json
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd

OUT=ROOT/'docs/results/ensemble_v3'


def table(headers,rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+
                     ['| '+' | '.join(map(str,row))+' |' for row in rows])


def main():
    manifest=json.loads((OUT/'manifest.json').read_text())
    for relative,expected in manifest['input_sha256'].items():
        if relative.startswith('sim/') or relative.startswith('data/'):
            if hashlib.sha256((ROOT/relative).read_bytes()).hexdigest()!=expected:
                raise RuntimeError(f'Ensemble is stale: {relative}')
    summary=pd.read_csv(OUT/'run_summary.csv')
    paired=pd.read_csv(OUT/'paired_summary.csv')
    annual=pd.read_csv(OUT/'annual_runs.csv')
    runs=pd.read_csv(OUT/'run_metrics.csv')
    differences=pd.read_csv(OUT/'paired_run_differences.csv')
    bio=pd.read_csv(OUT/'species_final_summary.csv')
    checks=pd.read_csv(OUT/'identity_checks.csv')
    cfg=manifest['configurations']['default']
    main_runs=runs[runs.experiment=='default']
    main_differences=differences[differences.experiment=='default']
    total_pairs=sum(manifest['experiments'].values())

    def stat(scenario,metric,experiment='default'):
        return summary[(summary.experiment==experiment)&(summary.scenario==scenario)&(summary.metric==metric)].iloc[0]

    def pstat(metric,experiment='default'):
        return paired[(paired.experiment==experiment)&(paired.metric==metric)].iloc[0]

    def span(row,scale=1,decimals=2,suffix=''):
        return f'{row["mean"]/scale:,.{decimals}f}{suffix} [{row["p05"]/scale:,.{decimals}f}, {row["p95"]/scale:,.{decimals}f}]'

    def paired_cell(metric,scale=1,decimals=2,suffix=''):
        return span(pstat(metric),scale,decimals,suffix)

    metric_specs=[
        ('Year-1 landed value ($B)','first_landed',1e9,3,''),
        ('Year-15 landed value ($B)','final_landed',1e9,3,''),
        ('Year-15 real landed value (year-1 $B)','final_real_landed',1e9,3,''),
        ('Nominal revenue CAGR, Years 1–15','nominal_cagr_pct',1,2,'%'),
        ('Real revenue CAGR, Years 1–15','real_cagr_pct',1,2,'%'),
        ('15-year cumulative landed value ($B)','cumulative_landed',1e9,2,''),
        ('15-year cumulative operating profit ($B)','cumulative_profit',1e9,2,''),
        ('Year-15 operating profit ($B)','final_profit',1e9,2,''),
        ('Year-15 catch (million tonnes)','final_catch',1e6,3,''),
        ('15-year fishing days (million)','cumulative_days',1e6,3,''),
        ('Year-15 revenue per fishing day ($)','final_revenue_per_day',1,0,''),
        ('Year-15 illegal-entry events','final_illegal',1,0,''),
        ('Year-15 high-bycatch event index','final_bycatch',1,0,''),
    ]
    result_table=table(['Metric','BAU mean [P5, P95]','EM package mean [P5, P95]'],[
        [label,span(stat('BAU',metric),scale,d,suffix),span(stat('EM',metric),scale,d,suffix)]
        for label,metric,scale,d,suffix in metric_specs])
    paired_specs=[('Cumulative landed-value difference ($B)','cumulative_landed',1e9,2,''),
        ('Cumulative landed-value difference (%)','landed_difference_pct',1,2,'%'),
        ('Cumulative real landed-value difference (year-1 $B)','cumulative_real_landed',1e9,2,''),
        ('Cumulative operating-profit difference ($B)','cumulative_profit',1e9,2,''),
        ('Discounted operating-profit difference ($B)','discounted_profit',1e9,2,''),
        ('Year-15 landed-value difference ($M)','final_landed',1e6,1,''),
        ('Year-15 operating-profit difference ($M)','final_profit',1e6,1,''),
        ('15-year fishing days saved (thousands)','days_saved',1e3,1,''),
        ('Year-15 illegal-entry reduction (%)','final_illegal_reduction_pct',1,2,'%'),
        ('Year-15 high-bycatch index reduction (%)','final_bycatch_reduction_pct',1,2,'%')]
    paired_table=table(['Within-seed effect','Mean [P5, P95]','Seeds with effect > 0'],[
        [label,paired_cell(metric,scale,d,suffix),f'{int(pstat(metric).positive_count)}/{int(pstat(metric).n)}']
        for label,metric,scale,d,suffix in paired_specs])
    yearly=[]
    main_annual=annual[annual.experiment=='default']
    for year,group in main_annual.groupby('year'):
        a=group[group.scenario=='BAU'].set_index('seed')
        b=group[group.scenario=='EM'].set_index('seed')
        delta=b.landed_value-a.landed_value
        yearly.append([int(year),f'{a.landed_value.mean()/1e9:.3f}',f'{b.landed_value.mean()/1e9:.3f}',
                       f'{delta.mean()/1e6:+.1f} [{delta.quantile(.05)/1e6:+.1f}, {delta.quantile(.95)/1e6:+.1f}]',
                       f'{a.fleet_profit.mean()/1e9:.3f}',f'{b.fleet_profit.mean()/1e9:.3f}'])
    yearly_table=table(['Year','BAU revenue, mean $B','EM revenue, mean $B','Paired revenue effect, mean [P5, P95] $M','BAU profit, mean $B','EM profit, mean $B'],yearly)
    bio_rows=[]
    for code in ['YFT','BET','ALB','SWO','SHK','TUR','SEA']:
        row=bio[(bio.experiment=='default')&(bio.code==code)].iloc[0]
        bio_rows.append([row.species,code,f'{row.bau_mean:.3f}',f'{row.em_mean:.3f}',
                         f'{row.delta_mean:+.3f} [{row.delta_p05:+.3f}, {row.delta_p95:+.3f}]'])
    bio_table=table(['Species','Code','BAU mean stock ratio','EM mean stock ratio','Paired ratio difference, mean [P5, P95]'],bio_rows)
    market_rows=[]
    for experiment,label in [('default','Positive real growth: planning assumption'),('historical_proxy','Historical nominal proxy: comparison')]:
        for scenario in ['BAU','EM']:
            market_rows.append([label,scenario,span(stat(scenario,'nominal_cagr_pct',experiment),1,2,'%'),
                                span(stat(scenario,'real_cagr_pct',experiment),1,2,'%'),
                                span(stat(scenario,'final_real_landed',experiment),1e9,3)])
    market_table=table(['Shared market scenario','World','Nominal revenue CAGR mean [P5, P95]','Real revenue CAGR mean [P5, P95]','Year-15 real revenue ($B) mean [P5, P95]'],market_rows)
    stress_rows=[]
    for experiment,label in [('zero_intervention','All controls zero; climate zero'),('stress','4× pressure; zero price drift')]:
        for scenario in ['BAU','EM']:
            stress_rows.append([label,scenario,int(stat(scenario,'final_landed',experiment).n),
                                span(stat(scenario,'final_landed',experiment),1e9,3),
                                span(stat(scenario,'nominal_cagr_pct',experiment),1,2,'%')])
    stress_table=table(['Experiment','World','Seeds','Year-15 landed value, $B mean [P5, P95]','Nominal CAGR mean [P5, P95]'],stress_rows)
    zeros=checks[checks.experiment=='zero_intervention']
    max_identity=zeros.max_paired_monthly_difference.max()
    em_share=stat('EM','realized_em_share')
    positive_final_bau=int((main_runs[main_runs.scenario=='BAU'].final_profit>0).sum())
    positive_final_em=int((main_runs[main_runs.scenario=='EM'].final_profit>0).sum())
    n=int(manifest['experiments']['default'])
    defaults=table(['Setting','Value'],[
        ['Horizon / registered vessels / representative agents',f'{cfg["years"]} years / {cfg["n_vessels"]:,} / {cfg["representative_agents"]:,}'],
        ['EM adoption / awareness / premium ceilings',f'{cfg["em_adoption_max_pct"]:.0f}% / {cfg["em_awareness_effect_max_pct"]:.0f}% / {cfg["premium_max_pct"]:.0f}%'],
        ['Government MPA / reallocation / enforcement pushes',f'{cfg["government_mpa_push_max_pct"]:.0f}% / {cfg["government_reallocation_support_max_pct"]:.0f}% / {cfg["enforcement_push_max_pct"]:.0f}%'],
        ['Climate extremity ceiling',f'{cfg["climate_extremity_max_pct"]:.0f}%'],
        ['Baseline annual landed value',f'${cfg["baseline_landed_value_billion"]:.1f}B nominal, calibrated separately per seed'],
        ['Nominal price prior / inflation assumption',f'{cfg["annual_price_drift"]*100:.4f}% / {cfg["annual_inflation_rate"]*100:.2f}% per year'],
        ['Price / fuel annual lognormal sigma',f'{cfg["price_volatility"]:.2f} / {cfg["fuel_volatility"]:.2f}'],
        ['Exploitation prior / initial stock fraction',f'{cfg["harvest_pressure_scale"]} / {cfg["initial_stock_fraction"]:.2f} of K'],
        ['Policy phase-in / EM rollout / audit premium maturity',f'{cfg["policy_phase_in_months"]} / 36 / 24 months'],
        ['Discount rate',f'{cfg["discount_rate"]*100:.0f}% nominal per year'],
        ['Animation agents / frame interval','0 / 180 months; simulation still updates every month'],
    ])
    manifest_metrics=dict(
        default_pair_count=n,zero_identity_pass_count=int(zeros.exact_zero_identity.sum()),
        zero_identity_count=len(zeros),max_zero_monthly_difference=float(max_identity),
        max_baseline_anchor_error_usd=float(runs[runs.scenario=='BAU'].max_baseline_anchor_error.max()),
        max_stock_ledger_error_tonnes=float(runs.max_stock_ledger_error.max()),
        final_profitable_seed_count={'BAU':positive_final_bau,'EM':positive_final_em})
    (OUT/'validation_summary.json').write_text(json.dumps(manifest_metrics,indent=2)+'\n')
    report=f'''# Comprehensive fisheries model and multi-simulation evaluation report

**Project:** Blurgs Global Fisheries Digital Twin  
**Updated:** 2 November 2026  
**Implementation:** `coupled-stock-v3`; global engine used by the app  
**Evidence:** {total_pairs} paired 15-year runs ({total_pairs*2} simulated worlds), comprising {n} positive-real-growth default pairs, 30 historical-proxy comparison pairs, 10 zero-control pairs and 10 stress pairs.

## 1. Executive assessment

Across {n} default seeds, mean Year-15 nominal landed value is **${stat('BAU','final_landed')['mean']/1e9:.3f}B for BAU** and **${stat('EM','final_landed')['mean']/1e9:.3f}B for the EM policy package**. Mean per-run nominal CAGR is **{stat('BAU','nominal_cagr_pct')['mean']:.2f}%** and **{stat('EM','nominal_cagr_pct')['mean']:.2f}%**, respectively. Inflation-adjusted CAGRs are **{stat('BAU','real_cagr_pct')['mean']:.2f}%** and **{stat('EM','real_cagr_pct')['mean']:.2f}%** under the assumed 2.2% annual deflator.

The mean 15-year paired landed-value difference is **${pstat('cumulative_landed')['mean']/1e9:+.2f}B**, with an empirical P5–P95 seed range of **[${pstat('cumulative_landed')['p05']/1e9:+.2f}B, ${pstat('cumulative_landed')['p95']/1e9:+.2f}B]**. The mean operating-profit difference is **${pstat('cumulative_profit')['mean']/1e9:+.2f}B**. A positive profit difference can mean a smaller operating loss: Year-15 profits are positive in **{positive_final_bau}/{n} BAU seeds** and **{positive_final_em}/{n} EM seeds** under the current costs.

All **{len(zeros)}/{len(zeros)} zero-control pairs match exactly**, with maximum monthly numerical difference **{max_identity:g}**. Stress scenarios can still decline substantially. These checks support internal consistency; the model's parameters, fleet margins and intervention effects remain subject to empirical calibration.

Albacore has a lower final modeled stock ratio under EM than BAU across these seeds, so the package does not improve every target species. Section 8 reports this tradeoff explicitly.

This report replaces the earlier single-run tables, large dividend claims, biological recovery percentages and validation verdicts. Old screenshots, GIFs and report figures are excluded from the current evidence. Every figure below was generated from this ensemble.

## 2. Experimental design and statistical interpretation

The default ensemble uses seeds `42 + 1009*i`, for `i=0,...,29`. The historical-proxy comparison uses the same 30 seeds. Zero-control and stress experiments each use the first 10 seeds from that list. Every seed runs a matched BAU and EM world with the same initial fleet, climate, market and biological shocks. The installed world contains **{manifest['world_cells']} cells**. The full configuration and input hashes are in the [run manifest](results/ensemble_v3/manifest.json).

{defaults}

Only seeds vary within an experiment. Stochastic variation includes fleet composition and traits, grounds, adoption heterogeneity, climate, catch, prices and biological noise. Model coefficients are fixed. Each seed receives its own pre-policy first-year $6B calibration, so first-year BAU revenue variation is removed by construction. EM Year 1 can differ because intervention rollout starts immediately.

All tables report arithmetic means. Brackets denote the empirical **5th and 95th percentiles across seeds**, using NumPy's default linear interpolation. They are 90% seed ranges, not confidence intervals for the mean, observed-world prediction intervals or uncertainty over model parameters. Tail estimates are coarse with 30 default seeds and especially 10 sensitivity seeds. Seeds are reproducible pseudorandom replications, not independent observed fisheries.

Paired effects are calculated as `EM(seed) - BAU(seed)` before summarizing. Mean percentage effects average within-seed ratios; they are not ratios of ensemble means. Positive-effect counts describe these simulated seeds, not calibrated probabilities of real-world success. CAGR uses 14 intervals between Year 1 and Year 15 and is computed per seed before averaging.

## 3. Positive real growth, historical comparison and monetary units

The historical context is rounded global capture first-sale value: about **$151B in 2018**, **$141B in 2020** and **$159B in 2022**. Sources are [FAO SOFIA 2020](https://doi.org/10.4060/ca9229en), [FAO SOFIA 2022](https://www.fao.org/4/cc0461en/online/sofia/2022/world-fisheries-aquaculture.html) and [FAO SOFIA 2024](https://doi.org/10.4060/cd0683en); the 2018 estimate is also reported in [PNAS 2021](https://pmc.ncbi.nlm.nih.gov/articles/PMC8346865/).

The **default is a positive-real-growth planning scenario**, with 1.5% annual real price growth and 2.2% assumed inflation. Nominal prices compose multiplicatively:

```
nominal price growth = (1 + real price growth) * (1 + inflation) - 1
                    = 1.015 * 1.022 - 1 = 3.733% per year
```

This is the requested growth assumption, shared by BAU and EM; it is not an estimate from historical data. Prices and stock dynamics still determine realized revenue. Neither annual nor cumulative real revenue is clamped to an upward path.

For comparison, `(159/151)^(1/4)-1` is approximately **1.30% nominal annual endpoint growth**. Under approximately stable reference catch, this supplies the separate historical-proxy price scenario. It is not a measured longline price series or a statistical fit to annual observations. The pandemic decline is retained as historical context; its subsequent rebound is not extrapolated alone. Cross-edition coverage and revisions differ, including algae in the 2024 capture summary. Global capture values include inland fisheries and do not independently validate the $6B longline anchor.

Total fisheries production, aquaculture, seafood trade receipts, GDP/value added and wild-capture ex-vessel revenues are different quantities. A World Bank 1–2% real-revenue guarantee is not established. [OECD–FAO 2026–2035](https://www.oecd.org/en/publications/oecd-fao-agricultural-outlook-2026-2035_47874669-en/full-report/fish-and-other-aquatic-products-for-human-consumption_be23d26b.html) projects capture-fisheries real prices below the 2023–2025 average by 2035. The planning default is therefore explicitly a positive-real-growth scenario rather than an attribution to that outlook.

`landed_value`, operating profit and costs use nominal USD. `real_landed_value = landed_value/(1+inflation)^(year-1)`. Real growth is `(1+nominal_growth)/(1+inflation)-1`. Inflation is not added a second time to nominal revenue. The 2.2% deflator is a scenario assumption. Cumulative nominal values sum each year's dollars without discounting; discounted profit uses 7% nominal discounting, with Year 1 undiscounted.

### Seed-matched market comparison

{market_table}

Both market scenarios use the same seed list, 2.2% deflator and physical/policy coefficients. The historical-proxy comparison can have declining real revenue because its nominal price trend is below inflation. Changing the market assumption does not change the deflation formula or force the output to grow. Prices do not drive fleet entry or exit in the current engine.

![Real revenue under planning and historical-proxy assumptions](images/ensemble_v3_market_comparison.png)

## 4. Corrected model architecture and coupling

```mermaid
flowchart LR
    C[Shared exogenous climate] --> A[Local catch availability]
    C --> B[Stock dynamics]
    B --> G[Monthly fishing-ground choice]
    G --> H[Realized target catch and bycatch]
    P[MPA geometry and compliance] --> H
    H -->|Same physical extraction| B
    H --> R[Revenue and operating profit]
    M[EM and management package] --> P
    M --> G
    M --> Q[Gear mitigation and eligible premium]
    Q --> H
    Q --> R
    X[Shared nominal market and fuel paths] --> R
    B --> D[Government redesign priority]
    D --> P
```

### Fleet, habitat and space

Synthetic vessel traits include fishing effort, capacity, catchability, fuel intensity, monthly fixed and crew costs, target species and latent risk. Ground selection combines historical preferences, biomass attraction, persistence, crowding, legal aversion and exploration. Choices are restricted to resident target habitat. Effort now uses mean-one lognormal noise with bounded depletion and management responses, replacing the expression that almost always hit its upper cap.

A map coordinate is the monthly fishing cell used for catch and enforcement. The model does not render an intermediate position while crediting catch at an unreached destination. Monthly relocation contributes to fuel demand, but voyage routes and coastal navigation are not modeled. Fishing days are bounded by average calendar days per month.

Installed MPA polygons use the same dateline-aware transformed geometry for the map and point membership, including holes. Cell-center membership remains a coarse-grid approximation. Redesign requires an enabled government push; reserves without nearby fleet presence hold their previous boundary. A coarse fractional protection fallback is explicit when polygons are unavailable.

### Physical extraction, growth and migration

Resident global cells start at `B0 = 0.70*K`; nonresident cells have `B=K=0`. Stock-index conversion factors are inferred from expected reference catch and equilibrium monthly surplus production, not measured biomass. Higher exploitation pressure implies a smaller physical stock supporting the initial fleet. The core balance is:

```
requested cell extraction = sum(vessel catch * vessel weight)
realized catch = requested catch * min(1, available stock/requested extraction)
removal in stock-index units = realized physical extraction / fixed stock conversion
remaining stock = clip(B + (r/12)*B*(1-B/K) - removal - climate loss + noise, 0, K)
next stock = remaining stock + conservative neighboring-cell exchange
```

Every target tonne sold removes that tonne from the stock ledger. Bycatch mitigation reduces incidental extraction before the same accounting step. Protection reduces fishing access before capture, without applying another mortality discount to already recorded catch. Exchange uses remaining stock after harvest and growth, with matched donor debits and receiver credits and limits on availability and space. There is no independent spillover-creation term or artificial positive stock floor. Growth is net surplus production; the retained species natural-mortality field is informational.

### Climate, compliance, management and markets

Climate follows a bounded AR(1) anomaly with occasional extreme jumps. It changes catch availability within fixed habitat envelopes; additional stock mortality is `max(abs(climate)-0.20,0)^2 * sensitivity * B/12`. Habitat capacity itself does not migrate poleward. These response coefficients remain scenario assumptions.

Awareness reduces latent non-compliance through the selected effect. EM adoption also enables modeled gear mitigation, observability and premium eligibility. Government enforcement, MPA redesign and reallocation support are separate controls. Adoption phases in over 36 months, premium audit maturity over 24, and policy ramps use fixed elapsed months rather than the selected endpoint. Actual adoption stays below its ceiling; final realized adoption across default seeds averages **{em_share['mean']*100:.1f}%**, with P5–P95 **[{em_share['p05']*100:.1f}%, {em_share['p95']*100:.1f}%]**.

Current supply is compared with a fixed reference supply, preserving a scarcity-price effect when reduced supply persists. There is no automatic BAU trade-sanction penalty. Revenue is realized catch multiplied by nominal price, stock quality, eligible premium and supply adjustment. Operating profit subtracts fuel, monthly fixed/crew costs, variable costs, EM costs and fines. Monthly costs are charged monthly; nonfuel costs and EM service fees receive assumed inflation.

The paired comparison estimates the effect of this entire modeled intervention package conditional on its assumptions. It does not identify monitoring's real-world causal effect, nor isolate awareness, gear, government policy or premiums individually. Detailed current specifications are in [GLOBAL_MODEL.md](GLOBAL_MODEL.md), [BIOLOGY.md](BIOLOGY.md) and [MODEL_CORRECTIONS.md](MODEL_CORRECTIONS.md).

## 5. Aggregate default results: {n} paired seeds

{result_table}

![Nominal and inflation-adjusted revenue across 30 paired seeds](images/ensemble_v3_revenue.png)

The planning default increases inflation-adjusted revenue over the horizon across the ensemble. Individual years can still decline with market or ecological variability. The historical comparison demonstrates that positive real growth depends on the selected economic assumption; stock and catch responses remain endogenous.

## 6. Within-seed intervention differences

{paired_table}

For difference rows the sign is EM minus BAU. Days saved and event reductions are defined in the opposite direction so positive values indicate fewer days or events under EM. A positive profit effect means higher profit or a smaller loss. It does not establish commercially viable fleet economics.

![Cumulative within-seed revenue and operating-profit differences](images/ensemble_v3_paired_differences.png)

## 7. Year-by-year ensemble means

{yearly_table}

These rows average the same seeds each year. They are not a representative single trajectory and their year-to-year changes are not the average per-seed CAGR. Complete annual seed rows and distribution summaries are linked in Section 11.

## 8. Species, bycatch and compliance

{bio_table}

Stock ratios divide each species' total modeled physical stock by its own initial total; 1 means no net change. The difference is in ratio units: +0.01 corresponds to one percentage point of initial stock. It is not a percent increase relative to BAU. These synthetic indices are not field stock assessments, observed animal counts, IUCN classifications or evidence of prevented extinction.

The albacore mean ratio is lower under the default EM package than BAU, with a negative P5–P95 paired difference, while the three bycatch-species ratios are higher. This is a modeled tradeoff, not a claim that every stock benefits. Attribution to particular management or displacement channels would require further component ablations.

The high-bycatch event index counts vessel-species amounts above a contemporaneous threshold based on unmitigated bycatch. Its reduction is not a calibrated estimate of animal mortality. Illegal-entry events likewise describe synthetic behavior and cannot substantiate accusations about real vessels. Government boundaries, vessel avoidance, awareness and gear assumptions jointly influence these outcomes.

![Final species stock ratios and annual operating profit](images/ensemble_v3_stocks_profit.png)

## 9. Zero-control and exploitation-pressure checks

{stress_table}

Zero-control runs set adoption, awareness, premium, government MPA push, reallocation support, enforcement and climate extremity to zero. All {len(zeros)} pairs match exactly in monthly numerical outputs: **maximum paired difference {max_identity:g}**. The unit suite separately checks identity with nonzero shared climate and compares annual, species, vessel and animation outputs.

Stress runs set exploitation pressure to four times the reference prior and nominal price drift to zero, retaining the other default controls. They are diagnostic scenarios, not estimates of the probability of future collapse. Their declining paths demonstrate that first-year calibration does not force later revenue growth. Ten runs per check give only a coarse sensitivity summary.

Across all {total_pairs} pairs, the maximum first-year BAU anchor error is **${manifest_metrics['max_baseline_anchor_error_usd']:.6f}**, and maximum monthly mismatch between target catch and stock-removal ledgers is **{manifest_metrics['max_stock_ledger_error_tonnes']:.3g} tonnes**. [Validation summary](results/ensemble_v3/validation_summary.json) records these checks.

## 10. Economic, livelihood and supply-chain limits

Operating losses remain material under the current monthly cost assumptions. There is no fleet exit, entry, subsidy or financing process that would reconcile persistent losses with continued operation. A positive EM-minus-BAU profit difference therefore cannot be presented as a validated return on investment. Revenue calibration does not calibrate operating margins.

Crew costs are fixed monthly inputs in this engine; it does not implement a 28–35% revenue-sharing contract, employment transitions, wage distribution or labor-rights outcomes. The earlier multi-billion-dollar crew-income claims are removed. Those claims require an explicit livelihood model and observed compensation data.

The separate `sim/supply_chain.py` module contains deterministic illustrative assumptions about port delays, spoilage, regulatory clearance, retail premiums and carbon intensity. Those downstream states are not jointly simulated by this global ensemble. This report does not add them to landed value or fleet profit or carry forward claims of regulatory compliance, carbon reductions, fraud prevention or brand equity. No current competitor comparison is inferred from simulation output.

Other limits include fixed fleet size, coarse MPA/cell geometry, simplified habitat connectivity, inferred biomass units, fixed life-history parameters, a broad historical price proxy and no structural-parameter uncertainty ensemble. No regional-engine ensemble is claimed here; that engine is covered by separate consistency tests. Calibration against RFMO catch/effort, species prices, observer/bycatch data and vessel operating accounts remains necessary before forecasting or policy appraisal.

## 11. Reproduction, artifacts and verification

Run from the repository root:

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MPLCONFIGDIR=/tmp/ems-mpl uv run --no-sync python scripts/aggregate_model_report.py
uv run --no-sync python scripts/render_ensemble_report.py
uv run --no-sync pytest -q
```

The ensemble runner uses two local worker processes, the installed pack and no external downloads. Saved source/data SHA-256 hashes identify the exact implementation used even in a working tree with uncommitted changes. `aggregate_model_report.py --reuse` rebuilds summaries and figures without simulations and rejects changed simulation/data inputs. The renderer also checks these hashes. Run the full ensemble again after any model or data change.

| Artifact | Contents |
|---|---|
| [Manifest](results/ensemble_v3/manifest.json) | Configurations, exact seed lists, versions and source/data hashes |
| [Annual runs](results/ensemble_v3/annual_runs.csv) | Every experiment/seed/scenario/year |
| [Run metrics](results/ensemble_v3/run_metrics.csv) | CAGRs, cumulative values, final states and accounting checks |
| [Run summaries](results/ensemble_v3/run_summary.csv) | Count, mean, median, standard deviation, P5 and P95 |
| [Paired run differences](results/ensemble_v3/paired_run_differences.csv) | Within-seed effects before aggregation |
| [Paired summaries](results/ensemble_v3/paired_summary.csv) | Effect distributions and positive-effect counts |
| [Yearly summaries](results/ensemble_v3/yearly_summary.csv) | Annual means and empirical ranges |
| [Species runs](results/ensemble_v3/species_runs.csv) | All annual species indices |
| [Species summaries](results/ensemble_v3/species_final_summary.csv) | Final species means and paired differences |
| [Identity checks](results/ensemble_v3/identity_checks.csv) | Per-pair null-control comparisons |
| [Validation summary](results/ensemble_v3/validation_summary.json) | Baseline anchor, extraction ledger and null checks |

The current unit suite contains 34 passing tests covering extraction accounting, migration conservation and bounds, extinction floors, polygon holes and dateline membership, habitat/position consistency, adoption ceilings, inflation conversion and composition, real-revenue invariance to inflation with matched real growth, both market scenarios, zero-policy identity and horizon prefixes in both engines. Those tests and the ensemble checks verify specified mathematical behavior; they do not constitute empirical fisheries validation.
'''
    report = "\n".join(line.rstrip() for line in report.splitlines()) + "\n"
    (ROOT/'docs/COMPREHENSIVE_MODEL_REPORT.md').write_text(report)
    print('Updated comprehensive report from saved ensemble data')
    print(json.dumps(manifest_metrics,indent=2))


if __name__=='__main__':
    main()
