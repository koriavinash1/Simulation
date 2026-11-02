"""Run paired ensembles and write auditable report inputs and figures.

Run from the repository root:
  uv run --no-sync python scripts/aggregate_model_report.py
Rebuild figures/report from saved simulations:
  uv run --no-sync python scripts/aggregate_model_report.py --reuse
"""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict, replace
import hashlib
import json
import platform
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
import pandas as pd

from sim.global_config import GlobalSimulationConfig
from sim.global_data import load_world
from sim.global_engine import run_paired_global

OUT = ROOT / 'docs' / 'results' / 'ensemble_v3'
IMAGES = ROOT / 'docs' / 'images'


def configuration(experiment, seed):
    cfg = GlobalSimulationConfig(seed=seed, months_per_frame=180)
    if experiment == 'historical_proxy':
        from sim.market import HISTORICAL_NOMINAL_VALUE_CAGR
        cfg = replace(cfg, annual_price_drift=HISTORICAL_NOMINAL_VALUE_CAGR)
    elif experiment == 'zero_intervention':
        cfg = replace(cfg, em_adoption_max_pct=0, em_awareness_effect_max_pct=0,
                      premium_max_pct=0, government_mpa_push_max_pct=0,
                      government_reallocation_support_max_pct=0, enforcement_push_max_pct=0,
                      climate_extremity_max_pct=0)
    elif experiment == 'stress':
        cfg = replace(cfg, harvest_pressure_scale=4*cfg.harvest_pressure_scale, annual_price_drift=0)
    return cfg


def run_one(experiment, seed):
    cfg = configuration(experiment, seed)
    world, _ = load_world(ROOT / 'data')
    paired = run_paired_global(cfg, world, animation_agents=0)
    annual, species, runs = [], [], []
    checks = {'experiment': experiment, 'seed': seed}
    numeric = paired['BAU'].monthly.select_dtypes(include=np.number).columns
    checks['max_paired_monthly_difference'] = float(np.max(np.abs(
        paired['EM'].monthly[numeric].values-paired['BAU'].monthly[numeric].values)))
    checks['exact_zero_identity'] = bool(paired['BAU'].monthly.drop(columns='scenario').equals(
                                       paired['EM'].monthly.drop(columns='scenario')))
    for scenario, result in paired.items():
        a = result.annual.copy()
        a['experiment'], a['seed'] = experiment, seed
        annual.append(a)
        sp = result.species_annual.copy()
        sp['experiment'], sp['seed'] = experiment, seed
        species.append(sp)
        first, last = a.iloc[0], a.iloc[-1]
        months = result.monthly
        runs.append(dict(
            experiment=experiment, seed=seed, scenario=scenario,
            first_landed=first.landed_value, final_landed=last.landed_value,
            final_real_landed=last.real_landed_value,
            nominal_cagr_pct=100*((last.landed_value/first.landed_value)**(1/(cfg.years-1))-1),
            real_cagr_pct=100*((last.real_landed_value/first.real_landed_value)**(1/(cfg.years-1))-1),
            cumulative_landed=float(a.landed_value.sum()),
            cumulative_real_landed=float(a.real_landed_value.sum()),
            cumulative_profit=float(a.fleet_profit.sum()), final_profit=last.fleet_profit,
            discounted_profit=float(np.sum(a.fleet_profit/(1+cfg.discount_rate)**(a.year-1))),
            cumulative_catch=float(a.catch_tonnes.sum()), final_catch=last.catch_tonnes,
            cumulative_days=float(a.fishing_days.sum()), final_days=last.fishing_days,
            final_revenue_per_day=last.revenue_per_day,
            cumulative_illegal=float(a.illegal_events.sum()), final_illegal=last.illegal_events,
            cumulative_bycatch=float(a.bycatch_events.sum()), final_bycatch=last.bycatch_events,
            final_mpa_share=last.mpa_share, realized_em_share=result.meta['realized_em_share'],
            max_stock_ledger_error=float(np.max(np.abs(months.catch_tonnes-months.stock_removals_tonnes))),
            max_baseline_anchor_error=abs(first.landed_value-6e9) if scenario=='BAU' else np.nan,
        ))
    return pd.concat(annual), pd.concat(species), runs, checks


def describe(values):
    a = np.asarray(values, dtype=float)
    a = a[np.isfinite(a)]
    if not len(a):
        return dict(n=0,mean=np.nan,median=np.nan,std=np.nan,p05=np.nan,p95=np.nan)
    return dict(n=len(a), mean=float(np.mean(a)), median=float(np.median(a)),
                std=float(np.std(a, ddof=1)) if len(a)>1 else 0.,
                p05=float(np.quantile(a,.05)), p95=float(np.quantile(a,.95)))


def paired_differences(runs):
    index = ['experiment','seed']
    cols = runs.select_dtypes(include=np.number).columns.drop('seed')
    a = runs[runs.scenario=='BAU'].set_index(index)[cols]
    b = runs[runs.scenario=='EM'].set_index(index)[cols]
    delta = b-a
    delta['landed_difference_pct'] = 100*delta.cumulative_landed/a.cumulative_landed
    delta['profit_difference_pct_abs_bau'] = 100*delta.cumulative_profit/a.cumulative_profit.abs()
    delta['final_illegal_reduction_pct'] = 100*(a.final_illegal-b.final_illegal)/a.final_illegal.replace(0,np.nan)
    delta['final_bycatch_reduction_pct'] = 100*(a.final_bycatch-b.final_bycatch)/a.final_bycatch.replace(0,np.nan)
    delta['days_saved'] = a.cumulative_days-b.cumulative_days
    return delta.reset_index()


def aggregate(annual, species, runs):
    records=[]
    for (experiment,scenario), group in runs.groupby(['experiment','scenario']):
        for metric in group.select_dtypes(include=np.number).columns.drop('seed'):
            records.append(dict(experiment=experiment,scenario=scenario,metric=metric,**describe(group[metric])))
    summary=pd.DataFrame(records)
    summary.to_csv(OUT/'run_summary.csv',index=False)
    deltas=paired_differences(runs)
    deltas.to_csv(OUT/'paired_run_differences.csv',index=False)
    records=[]
    for experiment,group in deltas.groupby('experiment'):
        for metric in group.select_dtypes(include=np.number).columns.drop('seed'):
            stats=describe(group[metric])
            records.append(dict(experiment=experiment,metric=metric,**stats,
                                positive_count=int((group[metric]>0).sum()),
                                positive_fraction=float((group[metric]>0).mean())))
    pd.DataFrame(records).to_csv(OUT/'paired_summary.csv',index=False)
    yearly=[]
    for (experiment,scenario,year),group in annual.groupby(['experiment','scenario','year']):
        for metric in ['landed_value','real_landed_value','fleet_profit','catch_tonnes','fishing_days','illegal_events','bycatch_events']:
            yearly.append(dict(experiment=experiment,scenario=scenario,year=year,metric=metric,**describe(group[metric])))
    pd.DataFrame(yearly).to_csv(OUT/'yearly_summary.csv',index=False)
    bio=[]
    last=species[species.year==species.year.max()]
    for (experiment,code),group in last.groupby(['experiment','code']):
        a=group.pivot(index='seed',columns='scenario',values='population_ratio')
        bio.append(dict(experiment=experiment,code=code,species=group.species.iloc[0],
                        bau_mean=float(a.BAU.mean()),em_mean=float(a.EM.mean()),
                        **{'delta_'+k:v for k,v in describe(a.EM-a.BAU).items()}))
    pd.DataFrame(bio).to_csv(OUT/'species_final_summary.csv',index=False)
    return summary,deltas,pd.DataFrame(bio)


def figures(annual, species):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    colors={'BAU':'#b34437','EM':'#187d76'}
    main=annual[annual.experiment=='default']
    fig,axes=plt.subplots(1,2,figsize=(12,4.4))
    for ax,metric,title in zip(axes,['landed_value','real_landed_value'],['Nominal landed value','Inflation-adjusted landed value']):
        for scenario,g in main.groupby('scenario'):
            pivot=g.pivot(index='seed',columns='year',values=metric)/1e9
            ax.plot(pivot.columns,pivot.mean(),label=scenario,color=colors[scenario])
            ax.fill_between(pivot.columns,pivot.quantile(.05),pivot.quantile(.95),alpha=.15,color=colors[scenario])
        ax.set(title=title,xlabel='Simulation year',ylabel='USD billions' if metric=='landed_value' else 'Year-1 USD billions')
        ax.grid(alpha=.15);ax.legend()
    fig.suptitle('30 paired seeds · means and empirical P5–P95 seed ranges')
    fig.tight_layout();fig.savefig(IMAGES/'ensemble_v3_revenue.png',dpi=180);plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(12,4.4))
    for ax,metric,title in zip(axes,['landed_value','fleet_profit'],['Cumulative revenue difference','Cumulative operating-profit difference']):
        a=main[main.scenario=='BAU'].pivot(index='seed',columns='year',values=metric)
        b=main[main.scenario=='EM'].pivot(index='seed',columns='year',values=metric)
        d=(b-a).cumsum(axis=1)/1e9
        ax.plot(d.columns,d.mean(),color='#225ca6')
        ax.fill_between(d.columns,d.quantile(.05),d.quantile(.95),color='#225ca6',alpha=.18)
        ax.axhline(0,color='gray',lw=.8)
        ax.set(title=title,xlabel='Simulation year',ylabel='EM − BAU, nominal USD billions');ax.grid(alpha=.15)
    fig.suptitle('Paired differences computed within each seed before aggregation')
    fig.tight_layout();fig.savefig(IMAGES/'ensemble_v3_paired_differences.png',dpi=180);plt.close(fig)
    fig,ax=plt.subplots(figsize=(9,4.8))
    for experiment,style,label in [('default','-','Planning'),('historical_proxy','--','Historical proxy')]:
        for scenario in ['BAU','EM']:
            group=annual[(annual.experiment==experiment)&(annual.scenario==scenario)]
            pivot=group.pivot(index='seed',columns='year',values='real_landed_value')/1e9
            ax.plot(pivot.columns,pivot.mean(),linestyle=style,color=colors[scenario],label=f'{label} · {scenario}')
            ax.fill_between(pivot.columns,pivot.quantile(.05),pivot.quantile(.95),color=colors[scenario],alpha=.09)
    ax.set(title='Shared market assumptions change real revenue',xlabel='Simulation year',ylabel='Year-1 USD billions')
    ax.grid(alpha=.15);ax.legend()
    fig.tight_layout();fig.savefig(IMAGES/'ensemble_v3_market_comparison.png',dpi=180);plt.close(fig)
    last=species[(species.experiment=='default')&(species.year==species.year.max())]
    codes=['YFT','BET','ALB','SWO','SHK','TUR','SEA']
    fig,axes=plt.subplots(1,2,figsize=(12,4.4))
    for scenario,offset in [('BAU',-.18),('EM',.18)]:
        groups=[last[(last.code==c)&(last.scenario==scenario)].population_ratio for c in codes]
        means=np.array([g.mean() for g in groups])
        low=np.array([g.quantile(.05) for g in groups]);high=np.array([g.quantile(.95) for g in groups])
        axes[0].bar(np.arange(7)+offset,means,width=.34,color=colors[scenario],label=scenario)
        axes[0].vlines(np.arange(7)+offset,low,high,color='#222',lw=1)
    axes[0].axhline(1,color='gray',lw=.8,ls='--');axes[0].set_xticks(np.arange(7),codes)
    axes[0].set(title='Year-15 stock ratio to initial stock',ylabel='Initial stock = 1');axes[0].legend()
    for scenario,g in main.groupby('scenario'):
        p=g.pivot(index='seed',columns='year',values='fleet_profit')/1e9
        axes[1].plot(p.columns,p.mean(),color=colors[scenario],label=scenario)
        axes[1].fill_between(p.columns,p.quantile(.05),p.quantile(.95),alpha=.15,color=colors[scenario])
    axes[1].axhline(0,color='gray',lw=.8);axes[1].set(title='Operating profit under current cost priors',xlabel='Simulation year',ylabel='Nominal USD billions');axes[1].legend()
    fig.suptitle('Scenario outcomes; stock indices and operating costs require empirical calibration')
    fig.tight_layout();fig.savefig(IMAGES/'ensemble_v3_stocks_profit.png',dpi=180);plt.close(fig)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reuse',action='store_true')
    parser.add_argument('--workers',type=int,default=2)
    args=parser.parse_args()
    OUT.mkdir(parents=True,exist_ok=True);IMAGES.mkdir(parents=True,exist_ok=True)
    if not args.reuse:
        experiments={'default':30,'historical_proxy':30,'zero_intervention':10,'stress':10}
        jobs=[(name,42+1009*i) for name,n in experiments.items() for i in range(n)]
        world,source=load_world(ROOT/'data')
        inputs=list((ROOT/'sim').glob('*.py'))+[Path(__file__),ROOT/'data/processed/world_cells.parquet',ROOT/'data/processed/marine_mpas.geojson',ROOT/'data/ne_110m_land.geojson']
        hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs if p.exists()}
        manifest=dict(report_date='2026-11-02',model_version='coupled-stock-v3',world_source=source,
                      world_cells=len(world),experiments=experiments,
                      seeds={name:[42+1009*i for i in range(n)] for name,n in experiments.items()},
                      configurations={name:asdict(configuration(name,42)) for name in experiments},
                      python=platform.python_version(),numpy=np.__version__,pandas=pd.__version__,
                      input_sha256=hashes,statistical_range='Empirical P5–P95 across seeds; not a confidence interval or structural uncertainty band')
        (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
        annual=[];species=[];runs=[];checks=[]
        with ProcessPoolExecutor(max_workers=args.workers) as executor:
            futures={executor.submit(run_one,*job):job for job in jobs}
            for i,future in enumerate(as_completed(futures),1):
                a,sp,r,c=future.result();annual.append(a);species.append(sp);runs.extend(r);checks.append(c)
                if i%5==0 or i==len(jobs): print(f'Completed {i}/{len(jobs)} paired 15-year runs',flush=True)
        annual=pd.concat(annual).sort_values(['experiment','seed','scenario','year']).reset_index(drop=True)
        species=pd.concat(species).sort_values(['experiment','seed','scenario','year','code']).reset_index(drop=True)
        runs=pd.DataFrame(runs).sort_values(['experiment','seed','scenario']).reset_index(drop=True)
        annual.to_csv(OUT/'annual_runs.csv',index=False)
        species.to_csv(OUT/'species_runs.csv',index=False)
        runs.to_csv(OUT/'run_metrics.csv',index=False)
        pd.DataFrame(checks).sort_values(['experiment','seed']).to_csv(OUT/'identity_checks.csv',index=False)
    else:
        annual=pd.read_csv(OUT/'annual_runs.csv');species=pd.read_csv(OUT/'species_runs.csv');runs=pd.read_csv(OUT/'run_metrics.csv')
        manifest=json.loads((OUT/'manifest.json').read_text())
        # Refuse to attribute saved results to modified simulation/data inputs.
        for relative,expected in manifest['input_sha256'].items():
            if relative==str(Path(__file__).relative_to(ROOT)): continue
            if hashlib.sha256((ROOT/relative).read_bytes()).hexdigest()!=expected:
                raise RuntimeError(f'Saved result inputs changed: {relative}; rerun without --reuse')
    summary,deltas,bio=aggregate(annual,species,runs)
    checks=pd.read_csv(OUT/'identity_checks.csv')
    assert checks[checks.experiment=='zero_intervention'].exact_zero_identity.all()
    assert np.isfinite(annual.select_dtypes(include=np.number)).all().all()
    assert np.all(runs[runs.scenario=='BAU'].max_baseline_anchor_error<1e-3)
    assert np.all(runs.max_stock_ledger_error<1e-6)
    figures(annual,species)
    manifest['postprocess_sha256'] = {str(Path(__file__).relative_to(ROOT)): hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    manifest['output_sha256'] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.glob('*.csv')}
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(summary[(summary.experiment=='default')&summary.metric.isin(['final_landed','nominal_cagr_pct','final_profit'])].to_string(index=False),flush=True)
    print('Paired default means:',deltas[deltas.experiment=='default'][['cumulative_landed','cumulative_profit','discounted_profit']].mean().to_dict(),flush=True)


if __name__=='__main__':
    main()
