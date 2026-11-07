from __future__ import annotations
import io
import json
import copy
import pandas as pd
import plotly.express as px
import streamlit as st
from simulator import SimulationConfig, BlueFinanceConfig, run_paired_simulation
from simulator.reporting import build_horizon_table

st.set_page_config(page_title="Tuna Fisheries Monte Carlo", layout="wide")
st.title("Tuna Fisheries Monte Carlo Simulator")
st.caption("Paired BAU vs monitored/traceable fishery with dynamic ecology, markets, IUU, MPA, and blue finance.")
st.warning("Research/policy sandbox: defaults are illustrative policy hypotheses until calibrated to frozen RFMO, GFW, observer/EM and market datasets.")

with st.sidebar:
    st.header("Simulation")
    years = st.slider("Years", 5, 40, 30)
    nrep = st.select_slider("Monte Carlo replicates", options=[20, 50, 100, 200, 400], value=100)
    nv = st.select_slider("Vessels / operators", options=[500, 1000, 3000, 7000], value=7000)
    seed = st.number_input("Master seed", value=20261107, step=1)

    st.header("Monitoring & behaviour")
    adoption = st.slider("Initial EM adoption", 0.0, 1.0, 0.30, 0.05)
    premium = st.slider("Maximum verified premium", 0.0, 0.15, 0.05, 0.005)
    campaign = st.slider("Awareness campaign strength", 0.0, 1.0, 0.55, 0.05)
    detection = st.slider("EM/detection strength", 0.0, 0.90, 0.58, 0.05)

    st.header("Ecology & governance")
    initial_mpa = st.slider("Initial MPA/closure share", 0.0, 0.40, 0.10, 0.01)
    max_mpa = st.slider("Maximum dynamic MPA share", initial_mpa, 0.50, 0.30, 0.01)
    dyn_mpa = st.checkbox("Dynamic MPA", True)
    avoid_red = st.slider("Max awareness-linked avoidable mortality reduction", 0.0, 0.90, 0.70, 0.05)
    recruit_prot = st.slider("Max recruitment protection effect", 0.0, 0.20, 0.08, 0.01)

    st.header("Market")
    dg = st.slider("Real demand growth (all species, %/yr)", 0.0, 3.0, 1.2, 0.1) / 100
    effort_cap = st.slider("Intervention effort-cap index", 0.8, 1.6, 1.32, 0.02)

    st.header("Blue bond / blue finance")
    blue_enabled = st.checkbox("Enable blue-finance channel", True)
    bond_size = st.number_input("Blue bond capital pool (US$ m)", min_value=0.0, value=15.0, step=5.0)
    blue_rate = st.slider("Concessional loan rate", 0.0, 0.12, 0.04, 0.005)
    market_rate = st.slider("Counterfactual market loan rate", 0.0, 0.20, 0.085, 0.005)
    term = st.slider("Loan term (years)", 3, 25, 15)
    max_loan = st.number_input("Max blue loan / vessel (US$)", min_value=0.0, value=50000.0, step=5000.0)
    grant_share = st.slider("Bond proceeds allocated to grants", 0.0, 0.50, 0.20, 0.05)
    productive_share = st.slider("Loan share used for productive capex", 0.0, 1.0, 0.55, 0.05)
    refinance_share = 1.0 - productive_share
    st.caption(f"Refinancing share is set to {refinance_share:.0%} so productive capex + refinancing = 100% of the loan tranche.")
    disbursement_years = st.slider("Capital deployment period (years)", 1, 15, 8)
    with st.expander("Advanced blue-finance eligibility"):
        eligibility_trust = st.slider("Minimum trust score", 0.0, 1.0, 0.55, 0.05)
        eligibility_compliance = st.slider("Minimum compliance score", 0.0, 1.0, 0.70, 0.05)
    blue_attribution = st.checkbox("Also run intervention without blue finance (attribution)", False)

run = st.button("Run paired Monte Carlo", type="primary", use_container_width=True)

if run or "results" not in st.session_state:
    bf = BlueFinanceConfig(
        enabled=blue_enabled,
        bond_size_musd=bond_size,
        blue_loan_rate=blue_rate,
        market_loan_rate=market_rate,
        loan_term_years=term,
        max_loan_per_vessel_usd=max_loan,
        grant_fraction=grant_share,
        loan_fraction=1.0-grant_share,
        productive_capex_fraction=productive_share,
        refinance_fraction=refinance_share,
        disbursement_years=disbursement_years,
        eligibility_trust=eligibility_trust,
        eligibility_compliance=eligibility_compliance,
    )
    cfg = SimulationConfig(
        years=years, n_vessels=nv, n_replicates=nrep, seed=int(seed),
        initial_em_adoption=adoption, max_verified_premium=premium,
        awareness_campaign_strength=campaign, detection_strength=detection,
        initial_mpa=initial_mpa, max_mpa=max_mpa, dynamic_mpa=dyn_mpa,
        awareness_mortality_reduction_max=avoid_red, recruitment_protection_max=recruit_prot,
        demand_growth_yft=dg, demand_growth_bet=dg, demand_growth_alb=dg,
        intervention_effort_cap=effort_cap, blue_finance=bf,
    )
    with st.spinner("Running paired Monte Carlo worlds..."):
        st.session_state.results = run_paired_simulation(cfg)
        st.session_state.cfg = cfg
        if blue_attribution and blue_enabled:
            no_blue_cfg = copy.deepcopy(cfg)
            no_blue_cfg.blue_finance.enabled = False
            no_blue_cfg.blue_finance.bond_size_musd = 0.0
            st.session_state.no_blue_results = run_paired_simulation(no_blue_cfg)
        else:
            st.session_state.no_blue_results = None

res = st.session_state.results
summary = res["summary"]
final = res["final"].set_index("metric")
horizons = build_horizon_table(res)

# Headline cards
c1, c2, c3, c4, c5 = st.columns(5)
def delta(metric): return float(final.loc[metric, "delta_median"])
c1.metric("Year-30 real profit Δ", f"${delta('profit_musd'):,.1f}m/yr")
c2.metric("Year-30 biomass Δ", f"{delta('biomass_ratio'):+.3f} B/K")
c3.metric("Year-30 CPUE Δ", f"{delta('cpue_index'):+.2f}")
c4.metric("Blue-finance reach", f"{final.loc['blue_finance_reach','intervention_median']:.1%}")
c5.metric("Household resilience Δ", f"{delta('household_resilience_index'):+.3f}")

p_profit = final.loc["profit_musd", "p_intervention_gt_bau"]
p_bio = final.loc["biomass_ratio", "p_intervention_gt_bau"]
st.markdown(f"**Paired year-30 probabilities:** profit > BAU **{p_profit:.1%}** · biomass > BAU **{p_bio:.1%}**")

metric_labels = {
    "profit_musd":"Real fleet profit (US$m/y)", "biomass_ratio":"Biomass B/K", "cpue_index":"CPUE index",
    "catch_t":"Catch (t/y)", "iuu":"IUU intensity", "adoption":"EM adoption", "effort_index":"Effort index",
    "cumulative_profit_musd":"Cumulative real profit (US$m)", "blue_bond_deployed_musd":"Blue capital deployed (US$m/y)",
    "blue_loan_interest_saving_musd":"Blue-loan interest saving (US$m/y)", "blue_capex_benefit_musd":"Productive capex benefit (US$m/y)",
    "debt_service_ratio":"Median debt-service ratio", "household_income_index":"Household income index",
    "household_resilience_index":"Household resilience index", "days_at_sea_index":"Days-at-sea / effort burden index",
}

def chart(metric, title=None):
    d = summary[summary.metric.eq(metric)].copy()
    fig = px.line(d, x="year", y="median", color="scenario", title=title or metric_labels.get(metric, metric))
    # Add 90% uncertainty ribbons as light traces.
    for scenario in d.scenario.unique():
        s = d[d.scenario.eq(scenario)]
        fig.add_scatter(x=list(s.year)+list(s.year[::-1]), y=list(s.p95)+list(s.p05[::-1]), fill="toself", opacity=0.10, line_width=0, name=f"{scenario} P5-P95", showlegend=False)
    fig.update_layout(height=390, legend_title_text="")
    return fig

st.subheader("Ecology and fishery economics")
a,b = st.columns(2); a.plotly_chart(chart("biomass_ratio"), use_container_width=True); b.plotly_chart(chart("profit_musd"), use_container_width=True)
a,b = st.columns(2); a.plotly_chart(chart("cpue_index"), use_container_width=True); b.plotly_chart(chart("catch_t"), use_container_width=True)
a,b = st.columns(2); a.plotly_chart(chart("iuu"), use_container_width=True); b.plotly_chart(chart("adoption"), use_container_width=True)

st.subheader("Blue finance and fisher wellbeing")
a,b = st.columns(2); a.plotly_chart(chart("blue_bond_deployed_musd"), use_container_width=True); b.plotly_chart(chart("blue_finance_reach"), use_container_width=True)
a,b = st.columns(2); a.plotly_chart(chart("blue_loan_interest_saving_musd"), use_container_width=True); b.plotly_chart(chart("blue_capex_benefit_musd"), use_container_width=True)
a,b = st.columns(2); a.plotly_chart(chart("debt_service_ratio"), use_container_width=True); b.plotly_chart(chart("household_resilience_index"), use_container_width=True)
a,b = st.columns(2); a.plotly_chart(chart("household_income_index"), use_container_width=True); b.plotly_chart(chart("days_at_sea_index"), use_container_width=True)


if st.session_state.get("no_blue_results") is not None:
    st.subheader("Incremental blue-finance attribution")
    nb = st.session_state.no_blue_results["final"].set_index("metric")
    x1,x2,x3,x4 = st.columns(4)
    x1.metric("Blue-finance profit effect", f"${final.loc['profit_musd','intervention_median']-nb.loc['profit_musd','intervention_median']:,.1f}m/yr")
    x2.metric("Resilience effect", f"{final.loc['household_resilience_index','intervention_median']-nb.loc['household_resilience_index','intervention_median']:+.3f}")
    x3.metric("Debt-service effect", f"{final.loc['debt_service_ratio','intervention_median']-nb.loc['debt_service_ratio','intervention_median']:+.3f}")
    x4.metric("Solvency effect", f"{final.loc['solvent_vessel_share','intervention_median']-nb.loc['solvent_vessel_share','intervention_median']:+.1%}")
    st.caption("This isolates the incremental effect of the blue-finance channel while keeping the EM/awareness/market intervention otherwise unchanged.")

st.subheader("Benefit by horizon")
st.dataframe(horizons, use_container_width=True, hide_index=True)

st.subheader("Year-30 comparison")
show = res["final"].copy()
show = show[show.metric.isin(list(metric_labels.keys()) + ["vessels_positive_profit","economic_value_per_tonne","solvent_vessel_share"])]
st.dataframe(show, use_container_width=True, hide_index=True)

st.subheader("Download run outputs")
summary_csv = summary.to_csv(index=False).encode()
final_csv = res["final"].to_csv(index=False).encode()
horizon_csv = horizons.to_csv(index=False).encode()
config_json = json.dumps(st.session_state.cfg.to_dict(), indent=2).encode()
d1,d2,d3,d4 = st.columns(4)
d1.download_button("Timeseries CSV", summary_csv, "summary_timeseries.csv", "text/csv")
d2.download_button("Year-30 CSV", final_csv, "final_comparison.csv", "text/csv")
d3.download_button("Horizons CSV", horizon_csv, "horizon_outcomes.csv", "text/csv")
d4.download_button("Config JSON", config_json, "run_config.json", "application/json")

with st.expander("Model notes"):
    st.markdown("""
- Blue bonds are modeled as a **finite upstream capital pool**, not as direct bonds issued by individual fishers.
- Eligibility depends on EM adoption, trust and modeled compliance; capital is allocated as concessional loans for refinancing and productive capex.
- Productive capex can reduce operating costs and improve quality realization within configured caps.
- Household indices are **economic resilience proxies** derived from modeled vessel income, debt burden and effort; they are not demographic or welfare measurements.
- All intervention coefficients should be treated as scenario hypotheses until empirically calibrated.
""")
