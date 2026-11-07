from __future__ import annotations
import numpy as np
import pandas as pd
from dataclasses import asdict
from typing import Dict, Any, Tuple
from .config import SimulationConfig

SPECIES = ("YFT", "BET", "ALB")


def _transition_subsidy_rate(cfg: SimulationConfig, year: int) -> float:
    if year <= 2:
        return cfg.em_subsidy_years_1_2
    if year <= 5:
        return cfg.em_subsidy_years_3_5
    if year <= 8:
        return cfg.em_subsidy_years_6_8
    return 0.0


def _quantiles(a: np.ndarray) -> Dict[str, np.ndarray]:
    return {
        "mean": a.mean(axis=0),
        "median": np.median(a, axis=0),
        "p05": np.quantile(a, 0.05, axis=0),
        "p25": np.quantile(a, 0.25, axis=0),
        "p75": np.quantile(a, 0.75, axis=0),
        "p95": np.quantile(a, 0.95, axis=0),
    }


def run_paired_simulation(cfg: SimulationConfig) -> Dict[str, Any]:
    """Run paired BAU/intervention Monte Carlo worlds with common exogenous shocks.

    The model is illustrative until calibrated to a frozen RFMO/GFW/EM/market data version.
    Policy controls (premium, subsidies, blue-finance terms) are scenario hypotheses.
    """
    nr, nv, years = cfg.n_replicates, cfg.n_vessels, cfg.years
    master = np.random.default_rng(cfg.seed)

    # Common random numbers across scenarios.
    climate_shock = master.normal(0, 0.045, size=(nr, years)).astype(np.float32)
    recruit_shock = master.normal(0, 0.07, size=(nr, years, 3)).astype(np.float32)
    market_shock = master.normal(0, 0.018, size=(nr, years, 3)).astype(np.float32)

    # Illustrative biological priors.
    r = np.clip(master.lognormal(np.log([0.34, 0.27, 0.30]), [0.16, 0.18, 0.16], size=(nr, 3)),
                [0.18, 0.14, 0.16], [0.60, 0.50, 0.52]).astype(np.float32)
    K = master.lognormal(np.log([2.8e6, 1.2e6, 1.0e6]), [0.12, 0.14, 0.12], size=(nr, 3)).astype(np.float32)
    q = master.lognormal(np.log([1.10e-5, 1.22e-5, 0.92e-5]), [0.12, 0.14, 0.12], size=(nr, 3)).astype(np.float32)
    initial_frac = np.array([cfg.initial_biomass_yft, cfg.initial_biomass_bet, cfg.initial_biomass_alb], dtype=np.float32)
    B0 = K * initial_frac

    price0 = np.clip(master.lognormal(np.log([5200, 6500, 4200]), [0.07, 0.08, 0.08], size=(nr, 3)),
                     [3800, 4800, 3000], [7600, 9000, 6500]).astype(np.float32)
    base_cost = np.clip(master.lognormal(np.log(cfg.base_cost_per_vessel_usd), 0.10, size=nr), 100000, 190000).astype(np.float32)
    demand_growth_center = np.array([cfg.demand_growth_yft, cfg.demand_growth_bet, cfg.demand_growth_alb])
    demand_growth = np.clip(master.normal(demand_growth_center, [0.004, 0.004, 0.004], size=(nr, 3)), 0.001, 0.025).astype(np.float32)
    price_drift_center = np.array([cfg.real_price_drift_yft, cfg.real_price_drift_bet, cfg.real_price_drift_alb])
    real_price_drift = np.clip(master.normal(price_drift_center, [0.003, 0.003, 0.003], size=(nr, 3)), -0.018, 0.006).astype(np.float32)
    inflation = np.clip(master.normal(cfg.inflation, 0.005, size=nr), 0.008, 0.050).astype(np.float32)

    # Heterogeneity; same vessels/worlds for paired scenarios.
    catchability = master.lognormal(0, 0.22, size=(nr, nv)).astype(np.float32)
    fuel_eff = master.lognormal(0, 0.12, size=(nr, nv)).astype(np.float32)
    trust0 = np.clip(master.beta(3.0, 2.7, size=(nr, nv)), 0, 1).astype(np.float32)
    wealth0 = master.lognormal(np.log(220000), 0.35, size=(nr, nv)).astype(np.float32)
    debt0 = master.lognormal(np.log(90000), 0.45, size=(nr, nv)).astype(np.float32)
    admin_burden = np.clip(master.lognormal(np.log(1.0), 0.22, size=(nr, nv)), 0.5, 1.8).astype(np.float32)
    quality_skill = np.clip(master.beta(3.5, 2.2, size=(nr, nv)), 0, 1).astype(np.float32)

    demand_capacity0 = q * (nv * 0.93) * B0

    metrics = [
        "biomass_ratio", "catch_t", "cpue_index", "effort_index", "profit_musd", "nominal_profit_musd",
        "cumulative_profit_musd", "adoption", "awareness", "iuu", "mpa", "real_price_index",
        "demand_capacity_t", "premium_realized", "vessels_positive_profit", "economic_value_per_tonne",
        "avoidable_mortality_t", "illegal_mortality_t", "trusted_vessel_share", "short_term_benefit_musd",
        "operational_saving_musd", "regulatory_saving_musd", "market_value_musd", "finance_saving_musd",
        "transition_support_musd", "blue_bond_deployed_musd", "blue_loan_interest_saving_musd",
        "blue_capex_benefit_musd", "blue_eligible_share", "blue_finance_reach", "debt_service_ratio",
        "household_income_index", "household_resilience_index", "days_at_sea_index", "solvent_vessel_share",
    ]
    store = {s: {m: np.zeros((nr, years + 1), dtype=np.float32) for m in metrics} for s in ("BAU", "INTERVENTION")}

    def simulate(scenario: str) -> None:
        intervention = scenario == "INTERVENTION"
        B = B0.copy()
        effort = np.ones((nr, nv), dtype=np.float32)
        wealth = wealth0.copy()
        debt = debt0.copy()
        awareness = np.full((nr, nv), cfg.initial_awareness if intervention else 0.12, dtype=np.float32)
        trust = trust0.copy()
        local_rng = np.random.default_rng(cfg.seed + (11 if intervention else 10))
        adopt = (local_rng.random((nr, nv)) < cfg.initial_em_adoption) if intervention else np.zeros((nr, nv), dtype=bool)
        trusted = np.zeros((nr, nv), dtype=np.float32)
        upgrade_score = np.zeros((nr, nv), dtype=np.float32)
        blue_debt = np.zeros((nr, nv), dtype=np.float32)
        iuu = np.full(nr, cfg.initial_iuu, dtype=np.float32)
        mpa = np.full(nr, cfg.initial_mpa, dtype=np.float32)
        price = price0.copy()
        demand_capacity = demand_capacity0.copy()
        cpi = np.ones(nr, dtype=np.float32)
        premium = np.full(nr, cfg.max_verified_premium if intervention else 0.0, dtype=np.float32)
        prev_adopter_adv = np.zeros(nr, dtype=np.float32)
        cumulative_profit = np.zeros(nr, dtype=np.float32)
        bond_loan_remaining = np.full(nr, cfg.blue_finance.bond_size_musd * 1e6 * cfg.blue_finance.loan_fraction if (intervention and cfg.blue_finance.enabled) else 0.0, dtype=np.float32)
        bond_grant_remaining = np.full(nr, cfg.blue_finance.bond_size_musd * 1e6 * cfg.blue_finance.grant_fraction if (intervention and cfg.blue_finance.enabled) else 0.0, dtype=np.float32)

        for yr in range(years + 1):
            adfrac = adopt.mean(axis=1).astype(np.float32)
            aw = awareness.mean(axis=1)
            trust_mean = trust.mean(axis=1)
            total_eff = (effort * catchability).sum(axis=1)
            biomass_ratio = (B / K).mean(axis=1)

            access = 1.0 - 0.70 * mpa
            conservation_response = np.ones(nr, dtype=np.float32)
            if intervention:
                scarcity_gap = np.clip((0.62 - biomass_ratio) / 0.22, 0, 1)
                conservation_response = 1.0 - 0.18 * adfrac * aw * scarcity_gap
            effective_eff = total_eff * access * conservation_response

            legal_catch_species = q * effective_eff[:, None] * B
            legal_catch_species = np.minimum(legal_catch_species, 0.18 * B)
            legal_catch = legal_catch_species.sum(axis=1)
            illegal_mortality = legal_catch * (0.60 * iuu)

            if intervention:
                protection = np.clip(adfrac * aw * trust_mean, 0, 1)
                avoidable_rate = cfg.avoidable_mortality_rate * (1.0 - cfg.awareness_mortality_reduction_max * protection)
                recruitment_protection = 1.0 + cfg.recruitment_protection_max * protection
            else:
                avoidable_rate = cfg.avoidable_mortality_rate * (1.0 + 0.15 * iuu)
                recruitment_protection = np.ones(nr, dtype=np.float32)
            avoidable_mortality = legal_catch * avoidable_rate

            cpue = legal_catch / np.maximum(total_eff, 1)
            cpue_idx = cpue / 31.0

            if intervention:
                verified_supply = adfrac
                premium_capacity = np.clip(cfg.premium_market_capacity + 0.10 * trusted.mean(axis=1), 0.15, 0.70)
                premium_coverage = np.minimum(verified_supply, premium_capacity)
                realized_premium = np.where(verified_supply > 1e-6, premium * premium_coverage / verified_supply, 0)
                verified_market_access = np.clip(0.55 + 0.35 * trusted.mean(axis=1), 0, 0.95)
            else:
                realized_premium = np.zeros(nr, dtype=np.float32)
                verified_market_access = np.zeros(nr, dtype=np.float32)

            base_revenue_species = legal_catch_species * price
            base_revenue = base_revenue_species.sum(axis=1)
            weights = catchability * effort
            weights /= np.maximum(weights.sum(axis=1, keepdims=True), 1e-9)
            vessel_base_revenue = weights * base_revenue[:, None]

            # Productive blue-finance upgrades reduce vessel costs and modestly improve value realization.
            capex_cost_reduction = cfg.blue_finance.capex_cost_reduction_max * np.clip(upgrade_score, 0, 1)
            capex_quality_gain = cfg.blue_finance.capex_quality_gain_max * np.clip(upgrade_score, 0, 1)
            real_cost_trend = np.exp(0.002 * yr)
            vessel_base_cost = (base_cost * real_cost_trend)[:, None] * (0.55 * effort + 0.45 * effort * fuel_eff) * (1 + 0.34 * mpa[:, None])
            vessel_base_cost *= (1 - capex_cost_reduction)

            if intervention:
                premium_value = vessel_base_revenue * adopt * realized_premium[:, None]
                quality_gain = vessel_base_revenue * adopt * ((0.007 + cfg.quality_gain_max * quality_skill) * np.clip(awareness, 0, 1) + capex_quality_gain)
                market_access_value = vessel_base_revenue * adopt * (0.006 + cfg.market_access_gain_max * trusted) * verified_market_access[:, None]
                payment_speed_value = vessel_base_revenue * adopt * (0.0025 + cfg.payment_speed_gain_max * trusted)

                reporting_saving = vessel_base_cost * adopt * np.minimum(cfg.reporting_saving_max, (0.010 + 0.009 * np.clip(awareness, 0, 1))) * admin_burden
                inspection_saving = vessel_base_cost * adopt * np.minimum(cfg.inspection_saving_max, 0.004 + 0.010 * trusted)
                operational_saving = vessel_base_cost * adopt * np.minimum(cfg.operational_saving_max, 0.008 + 0.030 * np.clip(awareness, 0, 1) * np.clip(yr / 6, 0, 1))

                maturity = np.clip((yr - 2) / 6, 0, 1)
                insurance_saving = vessel_base_cost * adopt * maturity * np.minimum(cfg.insurance_saving_max, 0.003 + 0.007 * trusted)
                generic_finance_saving = vessel_base_cost * adopt * maturity * np.minimum(cfg.finance_saving_max, 0.005 + 0.010 * trusted)

                # Blue bond / concessional finance allocation.
                compliance_score = np.clip(0.55 + 0.40 * trusted - 0.30 * iuu[:, None], 0, 1)
                eligible = adopt & (trust >= cfg.blue_finance.eligibility_trust) & (compliance_score >= cfg.blue_finance.eligibility_compliance)
                eligible_count = eligible.sum(axis=1)
                blue_disbursed = np.zeros((nr, nv), dtype=np.float32)
                if cfg.blue_finance.enabled and yr < cfg.blue_finance.disbursement_years:
                    annual_available = np.minimum(bond_loan_remaining, (cfg.blue_finance.bond_size_musd * 1e6 * cfg.blue_finance.loan_fraction) / max(cfg.blue_finance.disbursement_years, 1))
                    per_eligible = np.where(eligible_count > 0, annual_available / np.maximum(eligible_count, 1), 0)
                    per_eligible = np.minimum(per_eligible, cfg.blue_finance.max_loan_per_vessel_usd)
                    blue_disbursed = eligible * per_eligible[:, None]
                    deployed = blue_disbursed.sum(axis=1)
                    bond_loan_remaining = np.maximum(0, bond_loan_remaining - deployed)
                    blue_debt += blue_disbursed
                    refinance = blue_disbursed * cfg.blue_finance.refinance_fraction
                    debt = np.maximum(0, debt - refinance)
                    productive = blue_disbursed * cfg.blue_finance.productive_capex_fraction
                    upgrade_score = np.clip(upgrade_score + productive / 60000.0, 0, 1)
                else:
                    deployed = np.zeros(nr, dtype=np.float32)

                # Annual concessional interest saving versus counterfactual market-rate finance.
                blue_interest_saving = blue_debt * max(cfg.blue_finance.market_loan_rate - cfg.blue_finance.blue_loan_rate, 0)
                # Simple straight-line amortization of blue principal after disbursement.
                blue_principal_payment = blue_debt / max(cfg.blue_finance.loan_term_years, 1)
                blue_interest_cost = blue_debt * cfg.blue_finance.blue_loan_rate
                blue_debt = np.maximum(0, blue_debt - blue_principal_payment)
                blue_capex_benefit = vessel_base_cost * capex_cost_reduction + vessel_base_revenue * capex_quality_gain

                sub_rate = _transition_subsidy_rate(cfg, yr)
                em_cost = adopt * cfg.em_gross_cost_usd * (1 - sub_rate)
                # Grant tranche: early transition support from the blue-finance program.
                if cfg.blue_finance.enabled and yr < min(4, cfg.blue_finance.disbursement_years):
                    adopter_count = adopt.sum(axis=1)
                    annual_grant_available = np.minimum(bond_grant_remaining, (cfg.blue_finance.bond_size_musd * 1e6 * cfg.blue_finance.grant_fraction) / max(min(4, cfg.blue_finance.disbursement_years), 1))
                    grant_per_adopter = np.where(adopter_count > 0, annual_grant_available / np.maximum(adopter_count, 1), 0)
                    grant_per_adopter = np.minimum(grant_per_adopter, 1500.0)
                    blue_grant_support = adopt * grant_per_adopter[:, None]
                    grant_deployed = blue_grant_support.sum(axis=1)
                    bond_grant_remaining = np.maximum(0, bond_grant_remaining - grant_deployed)
                else:
                    blue_grant_support = np.zeros((nr, nv), dtype=np.float32)
                    grant_deployed = np.zeros(nr, dtype=np.float32)
                em_cost = np.maximum(0, em_cost - blue_grant_support)
                data_dividend = adopt * (700.0 * np.exp(-yr / 8.0))
                authority_rebate = adopt * (650.0 * np.exp(-yr / 6.0))
                transition_support = adopt * (cfg.em_gross_cost_usd * sub_rate) + blue_grant_support + data_dividend + authority_rebate

                conventional_interest_cost = debt * cfg.blue_finance.market_loan_rate
                vessel_revenue = vessel_base_revenue + premium_value + quality_gain + market_access_value + payment_speed_value
                vessel_cost = vessel_base_cost + conventional_interest_cost + em_cost + blue_interest_cost - reporting_saving - inspection_saving - operational_saving - insurance_saving - generic_finance_saving
                vessel_profit = vessel_revenue - vessel_cost + data_dividend + authority_rebate

                short_term_benefit = premium_value + quality_gain + market_access_value + payment_speed_value + reporting_saving + inspection_saving + operational_saving + data_dividend + authority_rebate
                operational_total = operational_saving.sum(axis=1)
                regulatory_total = (reporting_saving + inspection_saving).sum(axis=1)
                market_total = (premium_value + quality_gain + market_access_value + payment_speed_value).sum(axis=1)
                finance_total = (insurance_saving + generic_finance_saving + blue_interest_saving).sum(axis=1)
                transition_total = transition_support.sum(axis=1)
                deployed = deployed + grant_deployed
                blue_interest_total = blue_interest_saving.sum(axis=1)
                blue_capex_total = blue_capex_benefit.sum(axis=1)
                blue_eligible_share = eligible.mean(axis=1)
                blue_finance_reach = (blue_debt > 0).mean(axis=1)
            else:
                vessel_revenue = vessel_base_revenue
                vessel_cost = vessel_base_cost + debt * cfg.blue_finance.market_loan_rate
                vessel_profit = vessel_revenue - vessel_cost
                short_term_benefit = np.zeros_like(vessel_profit)
                operational_total = regulatory_total = market_total = finance_total = transition_total = np.zeros(nr, dtype=np.float32)
                deployed = blue_interest_total = blue_capex_total = blue_eligible_share = blue_finance_reach = np.zeros(nr, dtype=np.float32)

            # Household/livelihood proxies: economic wellbeing, not demographic inference.
            revenue = vessel_revenue.sum(axis=1)
            profit = vessel_profit.sum(axis=1)
            cumulative_profit += profit / 1e6
            nominal_profit = profit * cpi
            real_price_index = np.average(price / price0, axis=1, weights=np.maximum(legal_catch_species, 1))
            econ_value_per_tonne = revenue / np.maximum(legal_catch, 1)
            conventional_principal_payment = debt * 0.06
            annual_debt_service = debt * cfg.blue_finance.market_loan_rate + conventional_principal_payment + blue_debt * cfg.blue_finance.blue_loan_rate + blue_principal_payment if intervention else debt * cfg.blue_finance.market_loan_rate + conventional_principal_payment
            debt_service_ratio = np.median(annual_debt_service / np.maximum(vessel_revenue, 1), axis=1)
            household_income_index = np.median(np.maximum(vessel_profit, -50000), axis=1) / 25000.0 + 1.0
            household_income_index = np.clip(household_income_index, 0, 3)
            # Higher income, lower debt burden and lower effort at a given catch improve resilience proxy.
            days_at_sea_index = np.clip(effort.mean(axis=1) / np.maximum(cpue_idx, 0.35), 0.4, 2.5)
            resilience = 0.45 * np.clip(household_income_index / 1.5, 0, 1) + 0.30 * (1 - np.clip(debt_service_ratio / 0.30, 0, 1)) + 0.25 * (1 - np.clip((days_at_sea_index - 0.7) / 1.2, 0, 1))
            solvent = (wealth > -50000).mean(axis=1)

            vals = {
                "biomass_ratio": biomass_ratio,
                "catch_t": legal_catch,
                "cpue_index": cpue_idx,
                "effort_index": total_eff / nv,
                "profit_musd": profit / 1e6,
                "nominal_profit_musd": nominal_profit / 1e6,
                "cumulative_profit_musd": cumulative_profit,
                "adoption": adfrac,
                "awareness": aw,
                "iuu": iuu,
                "mpa": mpa,
                "real_price_index": real_price_index,
                "demand_capacity_t": demand_capacity.sum(axis=1),
                "premium_realized": realized_premium,
                "vessels_positive_profit": (vessel_profit > 0).mean(axis=1),
                "economic_value_per_tonne": econ_value_per_tonne,
                "avoidable_mortality_t": avoidable_mortality,
                "illegal_mortality_t": illegal_mortality,
                "trusted_vessel_share": (trusted > 0.60).mean(axis=1),
                "short_term_benefit_musd": short_term_benefit.sum(axis=1) / 1e6,
                "operational_saving_musd": operational_total / 1e6,
                "regulatory_saving_musd": regulatory_total / 1e6,
                "market_value_musd": market_total / 1e6,
                "finance_saving_musd": finance_total / 1e6,
                "transition_support_musd": transition_total / 1e6,
                "blue_bond_deployed_musd": deployed / 1e6,
                "blue_loan_interest_saving_musd": blue_interest_total / 1e6,
                "blue_capex_benefit_musd": blue_capex_total / 1e6,
                "blue_eligible_share": blue_eligible_share,
                "blue_finance_reach": blue_finance_reach,
                "debt_service_ratio": debt_service_ratio,
                "household_income_index": household_income_index,
                "household_resilience_index": resilience,
                "days_at_sea_index": days_at_sea_index,
                "solvent_vessel_share": solvent,
            }
            for m, v in vals.items():
                store[scenario][m][:, yr] = v

            if yr == years:
                break

            principal_cash = conventional_principal_payment + (blue_principal_payment if intervention else 0)
            wealth = np.maximum(-180000, wealth + vessel_profit.astype(np.float32) - principal_cash.astype(np.float32))
            # Conventional debt amortization; refinance/blue finance accelerates reduction.
            debt = np.maximum(0, debt - conventional_principal_payment)

            climate = climate_shock[:, yr]
            prod = r * B * (1 - B / K)
            prod *= np.exp(0.35 * climate[:, None] + recruit_shock[:, yr, :])
            prod *= recruitment_protection[:, None]
            shares = legal_catch_species / np.maximum(legal_catch[:, None], 1e-9)
            hidden_species = shares * (illegal_mortality + avoidable_mortality)[:, None]
            B = np.clip(B + prod - legal_catch_species - hidden_species, 0.05 * K, 1.15 * K)

            # Growing global/regional demand; fleet supply has partial, not total, price-setting power.
            demand_capacity *= np.exp(demand_growth + 0.20 * market_shock[:, yr, :])
            supply_gap = np.log(np.maximum(demand_capacity, 1.0) / np.maximum(legal_catch_species, 1.0))
            price_growth = 0.70 * real_price_drift + 0.025 * supply_gap + market_shock[:, yr, :]
            price = np.clip(price * np.exp(price_growth), 2200, 14000)
            cpi *= np.exp(inflation)

            profit_margin = np.clip(vessel_profit / np.maximum(vessel_cost, 1), -0.8, 1.2)
            liquidity = np.clip((wealth + 180000) / 380000, 0, 1.3)
            cap = cfg.intervention_effort_cap if intervention else cfg.bau_effort_cap
            logistic_room = np.clip(1.0 - effort / cap, 0.05, 0.85)
            effort_gamma = 0.030 if intervention else 0.045
            effort *= np.exp(np.clip(effort_gamma * profit_margin * logistic_room, -0.07, 0.055))
            effort *= np.clip(0.90 + 0.10 * liquidity, 0.80, 1.04)
            if intervention:
                scarcity_gap = np.clip((0.60 - biomass_ratio) / 0.20, 0, 1)
                effort *= (1 - adopt * (0.035 * scarcity_gap[:, None] * np.clip(awareness, 0, 1)))
            effort = np.clip(effort, 0.25, cap)

            pidx = np.average(price / price0, axis=1)
            if intervention:
                peer = adopt.mean(axis=1)[:, None]
                campaign = cfg.awareness_campaign_strength * np.exp(-yr / 18)
                benefit_signal = np.tanh(prev_adopter_adv[:, None] / 16000.0)
                resource_signal = np.clip((biomass_ratio - 0.52) / 0.18, -1, 1)[:, None]
                awareness += 0.16 * campaign + 0.10 * peer + 0.07 * benefit_signal * trust + 0.035 * resource_signal - 0.075 * awareness
                awareness = np.clip(awareness, 0, 1)
                trusted = np.clip(0.90 * trusted + 0.12 * adopt * awareness - 0.18 * (iuu[:, None] > 0.16), 0, 1)
                trust = np.clip(0.97 * trust + 0.03 * (0.35 + 0.65 * trusted), 0, 1)

                perceived_cost = (cfg.em_gross_cost_usd * (1 - _transition_subsidy_rate(cfg, yr))) / np.maximum(base_cost, 1)
                reg_pressure = 0.16 + 0.28 * mpa
                score = (-2.20 + 1.8 * awareness + 1.10 * peer + 0.65 * trust + 1.05 * benefit_signal + reg_pressure[:, None] - 1.6 * perceived_cost[:, None])
                p_adopt = 1 / (1 + np.exp(-score))
                p_adopt = np.clip(0.035 + 0.20 * p_adopt, 0.025, 0.28)
                churn = np.clip(0.055 - 0.025 * trust - 0.018 * np.maximum(benefit_signal, 0), 0.008, 0.07)
                u = local_rng.random((nr, nv))
                adopt = (adopt & (u > churn)) | ((~adopt) & (u < p_adopt))

                ap = np.where(adopt, vessel_profit, np.nan)
                npf = np.where(~adopt, vessel_profit, np.nan)
                prev_adopter_adv = np.nanmean(ap, axis=1) - np.nanmean(npf, axis=1)
                prev_adopter_adv = np.nan_to_num(prev_adopter_adv, 0.0).astype(np.float32)

                detect = np.clip(0.12 + cfg.detection_strength * adopt.mean(axis=1) + 0.10 * cfg.enforcement_multiplier + 0.08 * trusted.mean(axis=1), 0, 0.94)
                scarcity = np.clip(0.62 - biomass_ratio, -0.3, 0.4)
                iuu += 0.045 * scarcity + 0.010 * (pidx - 1) - 0.17 * detect * iuu - 0.06 * awareness.mean(axis=1) * iuu
                iuu = np.clip(iuu, 0.008, 0.30)

                if cfg.dynamic_mpa:
                    risk = (0.62 - biomass_ratio) + 0.70 * (iuu - 0.06)
                    compliance_relief = 0.10 * adopt.mean(axis=1) * awareness.mean(axis=1)
                    delta = np.clip(0.045 * (risk - compliance_relief), -0.012, 0.028)
                    mpa = np.clip(mpa + delta, cfg.initial_mpa, cfg.max_mpa)

                verified = adopt.mean(axis=1)
                demand = cfg.premium_market_capacity + 0.08 * trusted.mean(axis=1)
                premium += 0.07 * (demand - verified) - 0.018 * premium
                premium = np.clip(premium, 0, cfg.max_verified_premium)
            else:
                scarcity = np.clip(0.62 - biomass_ratio, -0.3, 0.4)
                iuu += 0.050 * scarcity + 0.010 * (pidx - 1) - 0.018 * iuu
                iuu = np.clip(iuu, 0.05, 0.35)
                mpa[:] = cfg.initial_mpa
                awareness += 0.01 - 0.07 * awareness
                awareness = np.clip(awareness, 0, 1)

    for scenario in ("BAU", "INTERVENTION"):
        simulate(scenario)

    # Long form summaries.
    years_idx = np.arange(years + 1)
    rows = []
    for scenario in ("BAU", "INTERVENTION"):
        for metric in metrics:
            stats = _quantiles(store[scenario][metric])
            for j, y in enumerate(years_idx):
                rows.append({"scenario": scenario, "year": int(y), "metric": metric, **{k: float(v[j]) for k, v in stats.items()}})
    summary = pd.DataFrame(rows)

    final_rows = []
    for metric in metrics:
        b = store["BAU"][metric][:, -1]
        i = store["INTERVENTION"][metric][:, -1]
        d = i - b
        final_rows.append({
            "metric": metric,
            "bau_median": float(np.median(b)),
            "intervention_median": float(np.median(i)),
            "delta_median": float(np.median(d)),
            "delta_p05": float(np.quantile(d, 0.05)),
            "delta_p95": float(np.quantile(d, 0.95)),
            "p_intervention_gt_bau": float(np.mean(i > b)),
        })
    final = pd.DataFrame(final_rows)

    return {
        "config": asdict(cfg),
        "raw": store,
        "summary": summary,
        "final": final,
        "species": SPECIES,
    }
