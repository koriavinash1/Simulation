# Blue finance / blue bond module

## Conceptual role

The simulator treats a blue bond as an **upstream financing instrument** whose proceeds are placed into a finite program pool. Fishers do not issue the sovereign bond themselves. The program can channel proceeds into grants, concessional refinancing, and productive investments in sustainable fisheries.

The Seychelles precedent is the primary reference pattern: the sovereign blue-bond proceeds were routed through a Blue Grants Fund and a Blue Investment Fund. The current Development Bank of Seychelles Blue Investment Fund advertises loans for sustainable fisheries from US$10,000 to US$3 million, at a 4% rate for up to 15 years and financing up to 90% of project cost. The exact simulator defaults are policy hypotheses and can be changed in the UI.

## State and flows

For vessel i:

- `Debt_i`: conventional debt principal.
- `BlueDebt_i`: concessional blue-finance principal.
- `Upgrade_i in [0,1]`: productive-capex stock.
- `Eligible_i`: EM + trust + compliance eligibility flag.

Program-level state:

- `BondPool_t >= 0`: undistributed blue-finance proceeds.
- `AnnualDisbursement_t <= BondPool_t`.

Eligibility is modeled as:

`Eligible = EM_adopted AND Trust >= tau_T AND Compliance >= tau_C`.

Allocation is constrained by the remaining pool and a per-vessel maximum.

## Economic pathways

### 1. Refinancing

A configurable share of each blue loan refinances conventional debt:

`Debt_new = max(0, Debt_old - refinance_share * BlueLoan)`.

The interest saving is approximately:

`InterestSaving = BlueDebt * max(MarketRate - BlueRate, 0)`.

### 2. Productive capex

A second share is invested in fuel efficiency, cold chain, gear, safety, digital systems or related productive assets.

The simplified model maps capex to a bounded `UpgradeScore` and then to:

- lower operating cost;
- improved quality/value realization.

These effects are capped to prevent finance from creating unbounded productivity.

### 3. Livelihood / household resilience proxy

The model reports three non-demographic economic proxies:

- household income index;
- debt-service ratio;
- days-at-sea / effort-burden index.

A composite resilience index rises with income stability and falls with debt burden and excessive effort. This is a scenario-level economic proxy, not a direct measurement of quality of life.

## Recommended interpretation

Use blue finance to test questions such as:

1. How large must the concessional pool be for 10%, 25% or 50% of eligible vessels to receive finance?
2. Is refinancing or productive capex more valuable?
3. How much does a 100-300 bp rate reduction matter relative to a catch premium?
4. Does finance accelerate adoption by making the first 3-5 years cash-flow positive?
5. Does financing efficiency upgrades increase long-run economic rent without increasing total fishing effort?
6. Does a finite pool disproportionately benefit larger/better-capitalized operators? If so, add targeted allocation rules.

## Calibration priorities

Before policy use, replace defaults with lender/program evidence for:

- market borrowing rates and collateral constraints;
- loan approval rates;
- average loan sizes;
- default rates;
- upgrade cost and realized operating savings;
- share of vessels eligible/able to apply;
- administrative barriers for small-scale operators.
