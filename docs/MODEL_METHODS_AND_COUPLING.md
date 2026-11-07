# Technical Methodology: Coupled Tuna Fisheries, EM Adoption, Market and Blue-Finance Monte Carlo Model

## Purpose

This note documents the mathematical and computational model used in the 30-year tuna-longline Monte Carlo experiments accompanying the blog post. It explains the model families, state variables, equations, couplings, stochastic terms, execution order, economic pathways, blue-finance mechanism, and the distinction between **implemented assumptions** and **future calibration targets**.

The simulator is not intended to claim that any single parameter value is universally true. It is a **policy-experiment operating model**: biological, behavioural, market, monitoring, management and finance assumptions are made explicit, varied in scenario sweeps, and propagated through a coupled stochastic system.

The implementation is in:

- `simulator/engine.py` — state updates and Monte Carlo engine;
- `simulator/config.py` — scenario and parameter controls;
- `app.py` — Streamlit experiment interface.

---

# 1. Modelling philosophy

The system is represented as a hybrid stochastic bioeconomic model with vessel-level heterogeneity:

\[
X_{t+1}=F(X_t,U_t,\theta,\varepsilon_t),
\]

where:

- \(X_t\) is the latent fishery/economic state;
- \(U_t\) contains policy controls such as EM subsidy, MPA bounds and blue-finance terms;
- \(\theta\) contains biological, market and behavioural parameters;
- \(\varepsilon_t\) contains explicit climate, recruitment and market shocks.

The simulator deliberately separates four sources of variation:

1. **parameter uncertainty** — e.g. intrinsic growth, carrying capacity, catchability;
2. **process stochasticity** — e.g. annual recruitment and climate shocks;
3. **agent heterogeneity** — e.g. vessel catchability, fuel efficiency, debt, trust and quality skill;
4. **policy hypotheses** — e.g. EM subsidy rate, premium cap, blue-finance pool.

This separation is important because Monte Carlo simulation should not replace the dynamics with random draws. Randomness perturbs an explicit dynamical system.

---

# 2. Simulation domain

The current simulator represents a stylised tuna longline fleet over a 30-year horizon.

### Fleet

Default:

\[
N_v = 7{,}000 \text{ vessels/operators}.
\]

Each vessel is heterogeneous in:

- catchability multiplier;
- fuel efficiency;
- initial trust;
- wealth;
- debt;
- administrative burden;
- quality-handling skill.

### Species

The ecological state currently contains three commercially important tuna groups:

- Yellowfin tuna (YFT),
- Bigeye tuna (BET),
- Albacore tuna (ALB).

The implementation uses separate species-level biomass, carrying capacity, catchability and price parameters.

### Time

The current code updates the full system annually for computational efficiency in scenario sweeps. The architecture is designed so that ecology can later be sub-stepped monthly and vessel decisions can be simulated at trip/set resolution.

---

# 3. Biological model

## 3.1 Schaefer surplus-production dynamics

The MVP ecological engine uses a species-specific Schaefer/logistic surplus-production model:

\[
P_{s,t}=r_s B_{s,t}\left(1-\frac{B_{s,t}}{K_s}\right),
\]

where:

- \(B_{s,t}\) = biomass of species \(s\),
- \(r_s\) = intrinsic production/growth parameter,
- \(K_s\) = carrying capacity.

The Schaefer family is one of the classic surplus-production models used to link biomass, effort and sustainable yield. FAO describes the Schaefer model as a widely used simple bioeconomic framework and gives the associated catch relation \(C=qfB\). [1][2]

The simulator adds multiplicative environmental and recruitment disturbances:

\[
P^*_{s,t}=P_{s,t}
\exp\left(0.35\,\epsilon^{climate}_t+\epsilon^{recruit}_{s,t}\right).
\]

For the intervention scenario, recruitment production can also be modified by a bounded protection factor:

\[
P^{I}_{s,t}=P^*_{s,t}\left(1+\rho_R \cdot Protection_t\right),
\]

where:

\[
Protection_t=\operatorname{clip}(A_t Z_t T_t,0,1).
\]

Here:

- \(A_t\) = EM adoption fraction;
- \(Z_t\) = average awareness;
- \(T_t\) = average trust;
- \(\rho_R\) = maximum recruitment-protection effect.

This is a **policy hypothesis**, not an assertion that cameras directly increase recruitment. It represents the combined effect of reduced hidden mortality, better compliance and less avoidable mortality on effective stock productivity.

## 3.2 Catch equation

Species-level legal catch is:

\[
H_{s,t}=q_s E^{eff}_t B_{s,t},
\]

subject to a physical cap:

\[
H_{s,t}\leq 0.18B_{s,t}.
\]

This is the standard Schaefer/Gordon-Schaefer catch form, where catchability \(q\), effort \(E\), and biomass \(B\) jointly determine harvest. [1][3]

## 3.3 Hidden mortality

The simulator separates legal catch from two additional mortality terms.

### Illegal/unreported mortality

\[
M^{IUU}_t = 0.60\, I_t H_t,
\]

where \(I_t\) is the latent IUU intensity index.

### Avoidable bycatch/juvenile/handling mortality

Under BAU:

\[
M^{avoid}_{t}=H_t m_0(1+0.15I_t).
\]

Under intervention:

\[
m_t=m_0\left(1-\rho_M Protection_t\right),
\]

\[
M^{avoid}_{t}=H_t m_t.
\]

The ecological update is then:

\[
B_{s,t+1}=
B_{s,t}
+P_{s,t}
-H_{s,t}
-M^{IUU}_{s,t}
-M^{avoid}_{s,t}.
\]

The hidden mortality is allocated across species according to legal catch shares.

### Why this coupling matters

This is the mechanism through which awareness and EM can **slow biomass degradation before long-run stock rebuilding is visible**:

\[
EM\uparrow, Awareness\uparrow
\Rightarrow
IUU\downarrow, AvoidableMortality\downarrow
\Rightarrow
B_{t+1}\uparrow
\Rightarrow
CPUE\uparrow.
\]

It is this resource-productivity pathway—not the camera itself—that generates the long-run economic value.

---

# 4. Effort and CPUE model

## 4.1 Effective effort

Raw fleet effort is constructed from vessel-specific effort and catchability:

\[
E_t=\sum_i e_{i,t}q^{rel}_i.
\]

MPA access reduces effective effort:

\[
Access_t=1-0.70M_t.
\]

Under intervention, fishers with EM/awareness also reduce pressure when biomass is below a scarcity threshold:

\[
Scarcity_t=
\operatorname{clip}
\left(
\frac{0.62-B_t/K}{0.22},0,1
\right),
\]

\[
ConservationResponse_t=
1-0.18A_tZ_tScarcity_t.
\]

Thus:

\[
E^{eff}_t = E_t\cdot Access_t\cdot ConservationResponse_t.
\]

## 4.2 CPUE

The model computes:

\[
CPUE_t=\frac{H_t}{E_t}.
\]

A normalized CPUE index is reported for comparison across scenarios.

The biological interpretation is standard: in simple surplus-production formulations, CPUE is often used as an abundance proxy when catchability is stable. FAO documentation explicitly relates yield, fishing mortality, catchability, effort and CPUE in this framework. [3][4]

## 4.3 Profit-responsive but bounded effort

A pure open-access model would allow positive rents to attract effort until rents are dissipated. Gordon's classic common-property fishery model provides the economic foundation for this phenomenon. [5]

The simulator includes this mechanism but **bounds it**, because modern tuna fisheries face licences, vessel constraints, RFMO rules, capital limits and operational capacity.

Vessel effort evolves approximately as:

\[
e_{i,t+1}=e_{i,t}
\exp\left(
\gamma_s\,Margin_{i,t}\,Room_{i,t}
\right),
\]

where:

\[
Margin_{i,t}=\operatorname{clip}\left(\frac{\Pi_{i,t}}{Cost_{i,t}},-0.8,1.2\right),
\]

and:

\[
Room_{i,t}=\operatorname{clip}\left(1-\frac{e_{i,t}}{E^{cap}_s},0.05,0.85\right).
\]

The intervention uses a lower effort-response coefficient and lower effort cap than BAU. This is deliberate: better-managed fisheries should convert some productivity gains into **economic rent**, not automatically into additional hooks and trips.

This choice is aligned with the World Bank's *Sunken Billions Revisited*, which attributes a large portion of foregone fishery value to excessive fishing effort and depleted stocks, and estimates that better management could generate large additional economic benefits with materially lower aggregate effort. [6]

---

# 5. Awareness, trust and EM adoption

## 5.1 Awareness dynamics

Awareness is a bounded vessel-level state:

\[
Z_{i,t}\in[0,1].
\]

The intervention update combines:

- campaign exposure;
- peer adoption;
- observed adopter economic advantage;
- resource status;
- decay.

Conceptually:

\[
Z_{i,t+1}=Z_{i,t}
+\alpha_C Campaign_t
+\alpha_P Peer_t
+\alpha_B Benefit_tT_{i,t}
+\alpha_R Resource_t
-\delta_ZZ_{i,t}.
\]

## 5.2 Trust and compliance capital

The model distinguishes general trust from accumulated trusted-vessel status.

A trusted-vessel score rises with verified participation and awareness and falls when IUU conditions are high:

\[
VTrust_{i,t+1}
=0.90VTrust_{i,t}
+0.12A_{i,t}Z_{i,t}
-Penalty_t.
\]

General trust slowly adapts toward this verified-history state.

This is intended to represent **compliance capital**: verified history can later affect inspections, market access and finance.

## 5.3 Adoption model

Adoption is stochastic and reversible.

A latent adoption score is constructed from:

\[
S_{i,t}=
\beta_0
+\beta_ZZ_{i,t}
+\beta_PPeer_t
+\beta_TTrust_{i,t}
+\beta_BBenefit_t
+\beta_RRegPressure_t
-\beta_CCost_t.
\]

This is transformed by a logistic function:

\[
\sigma(S)=\frac{1}{1+e^{-S}}.
\]

The resulting probability is bounded to avoid instantaneous universal adoption.

The model also contains a churn probability, so adoption can reverse if perceived benefits or trust deteriorate.

This is inspired by diffusion models in which adoption depends on both innovation and imitation/peer effects. Bass's classic diffusion model formalized the idea that adoption timing depends partly on the number of prior adopters. [7]

The implementation is **not a literal Bass equation**; it is a richer logistic transition model using Bass-like peer diffusion plus economic and regulatory variables.

---

# 6. IUU and enforcement model

IUU is treated as a latent behavioural state rather than equated with detected violations.

## 6.1 Detection

For the intervention:

\[
P^{detect}_t=
\operatorname{clip}
\left(
0.12
+\delta_AA_t
+0.10 Enforcement
+0.08 Trusted_t,
0,0.94
\right).
\]

The logic is that EM coverage, enforcement and verified history increase the probability that illegal behaviour is detected or becomes economically risky.

## 6.2 IUU dynamics

Under intervention, IUU increases when resource scarcity and price incentives worsen, but decreases with detection and awareness:

\[
I_{t+1}=I_t
+\alpha_SScarcity_t
+\alpha_PPriceSignal_t
-\beta_DP^{detect}_tI_t
-\beta_ZZ_tI_t.
\]

BAU has weaker deterrence.

This behavioural structure is consistent with fisheries-compliance literature in which illegal fishing depends on economic gains, probability of detection/sanction, legitimacy/moral attitudes and social influence. Charles, Mazany and Cross model illegal fishing as a fisher-level economic response to imperfect enforcement; FAO reviews likewise identify expected penalties, detection probability, moral attitudes and peer effects as major compliance drivers. [8][9]

The model therefore does **not** assume:

\[
EM\Rightarrow IUU=0.
\]

Instead, EM modifies expected detection and the economics of illegal behaviour.

---

# 7. MPA / spatial-governance controller

The current simulator represents MPA coverage as a fleet-level proportion rather than a full spatial raster.

The state is:

\[
M_t\in[M_{min},M_{max}].
\]

When dynamic management is enabled:

\[
Risk_t=(0.62-B_t/K)+0.70(I_t-0.06),
\]

\[
Relief_t=0.10A_tZ_t,
\]

\[
\Delta M_t=
\operatorname{clip}
\left(
0.045(Risk_t-Relief_t),
-0.012,
0.028
\right),
\]

\[
M_{t+1}=\operatorname{clip}(M_t+\Delta M_t,M_{min},M_{max}).
\]

This captures an important policy hypothesis:

> Better monitoring and compliance can reduce the need for blunt spatial restrictions, while worsening stock/IUU conditions can trigger greater protection.

### Current limitation

The model does not yet represent individual MPA polygons, seasonal closures, migration corridors or cell-level effort displacement. A production version should replace this scalar controller with a spatial grid and vessel location-choice model.

---

# 8. Observation model: AIS/GFW, EM, observer and logbook data

The simulator conceptually distinguishes latent effort/catch from observation channels.

Global Fishing Watch apparent fishing activity should **not** be interpreted as exact fishing effort or legal proof. GFW states that its fishing model reflects a range of fishing-related behaviours, may contain false positives, and is affected by AIS coverage and classification limitations. [10][11]

Therefore future calibration should use a measurement equation such as:

\[
Y^{GFW}_{t}=H_{AIS}(E^{true}_t)+\epsilon^{AIS}_t.
\]

EM/observer/logbook observations should be represented separately:

\[
Y^{EM}_{t}=H_{EM}(Catch^{true}_t,Interactions_t)+\epsilon^{EM}_t,
\]

\[
Y^{logbook}_{t}=H_{log}(Catch^{true}_t,ReportingBehaviour_t)+\epsilon^{log}_t.
\]

NOAA's Hawaiʻi longline pre-implementation study found that EM reviewers detected 98% of observer-recorded retained fish in the shallow-set fishery and 100% in the deep-set fishery, while also identifying important species-level limitations; the study reported that EM review could reduce review time relative to collecting similar information through at-sea observers. [12]

These findings justify modelling EM as an **improved observation channel**, not as perfect truth.

---

# 9. Market and price model

The market model was deliberately changed from an earlier fixed market-capacity formulation because a fixed ceiling caused mechanically declining prices over a 30-year horizon.

## 9.1 Growing demand frontier

Species-specific market capacity evolves as:

\[
D_{s,t+1}=D_{s,t}
\exp(g_{D,s}+0.20\epsilon^{market}_{s,t}).
\]

Default central real-demand growth assumptions are approximately:

- YFT: 1.2%/year;
- BET: 1.3%/year;
- ALB: 1.0%/year.

These are scenario assumptions rather than fitted forecasts.

The model choice is motivated by the fact that global aquatic-food markets evolve over time. OECD-FAO provides forward projections for capture-fish production and prices and expects capture production to grow much more slowly than aquaculture, while real capture-fish prices can soften over the outlook period. [13][14]

## 9.2 Partial supply-price feedback

The simulated 7,000-vessel fleet is not assumed to set the entire global tuna price.

A supply-gap signal is:

\[
G_{s,t}=\ln\left(\frac{D_{s,t}}{H_{s,t}}\right).
\]

Real price changes according to:

\[
g^P_{s,t}
=0.70\mu_{P,s}
+0.025G_{s,t}
+\epsilon^{market}_{s,t}.
\]

Thus:

\[
P_{s,t+1}=P_{s,t}e^{g^P_{s,t}}.
\]

This means:

- demand growth supports price;
- excess supply can reduce price;
- exogenous real price drift can be negative;
- market shocks remain stochastic;
- the fleet has only partial price-setting power.

## 9.3 Nominal versus real economics

A separate CPI process is simulated:

\[
CPI_{t+1}=CPI_t e^{\pi}.
\]

Real profit is the primary welfare/economic-rent output; nominal profit is also reported.

This prevents the 30-year model from confusing inflation with real economic improvement.

---

# 10. Verified premium and market-access model

A nominal maximum sustainability premium does not apply to all verified catch.

Let:

- \(A_t\) = verified/adopting share;
- \(C^{premium}_t\) = premium-market capacity.

The premium-market capacity increases modestly with trusted-vessel history:

\[
C^{premium}_t=
\operatorname{clip}(C_0+0.10Trusted_t,0.15,0.70).
\]

Premium-covered verified supply is:

\[
Coverage_t=\min(A_t,C^{premium}_t).
\]

Therefore the realized premium per adopter is approximately:

\[
\rho^{real}_t=
\rho_t\frac{Coverage_t}{A_t}.
\]

This prevents the model from assuming that an unlimited amount of fish can receive a fixed 5% premium.

The premium itself evolves according to verified demand versus verified supply and decays when verified supply exceeds premium demand.

This is one reason the simulation does not require a permanent premium for long-run viability.

---

# 11. Short- and medium-term fisher benefit stack

The core economic insight of the simulator is that EM should not create only a distant ecological benefit.

For vessel \(i\):

\[
Revenue_{i,t}=
BaseCatchRevenue
+Premium
+QualityGain
+MarketAccessValue
+PaymentSpeedValue.
\]

Costs are reduced by several channels:

\[
Cost_{i,t}=
BaseOperatingCost
+FinanceCost
+EMCost
-ReportingSaving
-InspectionSaving
-OperationalSaving
-InsuranceSaving
-FinanceSaving.
\]

## 11.1 Reporting savings

\[
S^{report}_{i,t}
=Cost^{base}_{i,t}A_{i,t}
\min(S^{max}_{report},0.010+0.009Z_{i,t})
\times AdminBurden_i.
\]

Interpretation: automation/pre-population of e-logbooks, fewer duplicate reporting steps and less reconciliation.

## 11.2 Inspection savings

\[
S^{inspect}_{i,t}
=Cost^{base}_{i,t}A_{i,t}
\min(S^{max}_{inspect},0.004+0.010Trust_{i,t}).
\]

Interpretation: verified fleets may be eligible for more risk-based inspection regimes.

## 11.3 Operational savings

\[
S^{oper}_{i,t}
=Cost^{base}_{i,t}A_{i,t}
\min\left(S^{max}_{oper},0.008+0.030Z_{i,t}Maturity_t\right).
\]

Interpretation: trip analytics, CPUE learning, fuel-per-catch metrics, handling analytics and better operational feedback.

## 11.4 Quality gain

\[
QGain_{i,t}
=Revenue^{base}_{i,t}A_{i,t}
\left[(0.007+q_{max}QualitySkill_i)Z_{i,t}+CapexQuality_i\right].
\]

## 11.5 Market-access value

\[
MValue_{i,t}
=Revenue^{base}_{i,t}A_{i,t}
(0.006+m_{max}Trusted_i)VerifiedAccess_t.
\]

This is intentionally distinct from a price premium: traceability can have value by reducing rejection risk or maintaining access to restricted buyers even when no premium is paid.

## 11.6 Payment-speed value

\[
PValue_{i,t}=Revenue^{base}_{i,t}A_{i,t}(0.0025+p_{max}Trusted_i).
\]

This is a proxy for reduced working-capital friction when evidence is available more quickly.

## 11.7 Insurance and generic finance benefits

These mature after the early years:

\[
Maturity_t=\operatorname{clip}\left(\frac{t-2}{6},0,1\right).
\]

Insurance and finance savings increase with trust and mature verified history.

### Important status

These coefficients are currently **policy hypotheses**. They are deliberately exposed in the Streamlit UI and scenario sweeps. They should eventually be calibrated from vessel accounts, inspection costs, buyer contracts, insurance quotes and lending data.

---

# 12. Blue bond / blue-finance model

## 12.1 Financing architecture

The simulator does not assume that individual fishers issue bonds.

It models the chain:

\[
BlueBond
\rightarrow
CentralCapitalPool
\rightarrow
GrantTranche+ConcessionalLoanTranche
\rightarrow
EligibleFishers/Businesses.
\]

This structure is based on the Seychelles sovereign blue-bond precedent. The World Bank describes the Seychelles issuance as a US$15 million sovereign blue bond whose proceeds were channelled through the Blue Grants Fund and Blue Investment Fund for marine protection and sustainable fisheries. [15]

The Development Bank of Seychelles currently describes its Blue Investment Fund as offering eligible sustainable-fisheries loans from US$10,000 to US$3 million at 4% interest with repayment terms up to 15 years. [16]

## 12.2 Eligibility

The simulator computes a compliance score:

\[
C_{i,t}=
\operatorname{clip}
(0.55+0.40Trusted_{i,t}-0.30I_t,0,1).
\]

A vessel is eligible if:

\[
A_{i,t}=1,
\]

\[
Trust_{i,t}\geq\tau_T,
\]

and:

\[
C_{i,t}\geq\tau_C.
\]

Thus blue finance is **not automatically awarded to every EM vessel**.

## 12.3 Finite loan pool

If the bond contains a loan fraction \(\lambda_L\):

\[
Pool^{loan}_0=BondSize\cdot\lambda_L.
\]

Annual available capital is limited by the remaining pool and disbursement schedule.

Per-vessel disbursement is capped:

\[
Loan_{i,t}
\leq Loan^{max}.
\]

Therefore:

\[
\sum_i Loan_{i,t}
\leq Pool^{loan}_t.
\]

## 12.4 Refinancing channel

A fraction of concessional financing refinances more expensive conventional debt:

\[
Refinance_{i,t}
=\lambda_R Loan_{i,t}.
\]

Conventional debt is reduced accordingly.

The interest-rate benefit is:

\[
Saving^{interest}_{i,t}
=BlueDebt_{i,t}
(r_{market}-r_{blue}).
\]

## 12.5 Productive-capex channel

The remaining loan can finance productive upgrades:

\[
Capex_{i,t}=\lambda_CLoan_{i,t}.
\]

An upgrade state accumulates and is capped:

\[
Upgrade_{i,t+1}
=\operatorname{clip}
\left(Upgrade_{i,t}+\frac{Capex_{i,t}}{60{,}000},0,1\right).
\]

This produces bounded:

- operating-cost reduction;
- quality/value-realization gain.

## 12.6 Grant channel

The grant tranche is concentrated in the early transition period and offsets a portion of EM cost.

This represents a transition-finance mechanism rather than a permanent operating subsidy.

## 12.7 Blue-finance implication

The complete finance pathway is:

\[
EM/Traceability
\rightarrow
VerifiedHistory
\rightarrow
FinanceEligibility
\rightarrow
CheaperDebt+ProductiveCapex
\rightarrow
LowerCost+HigherResilience.
\]

The model explicitly reports:

- blue capital deployed;
- eligible-vessel share;
- finance reach;
- interest savings;
- capex benefits;
- debt-service ratio.

---

# 13. Fisher lifestyle / resilience model

The simulator does **not** claim to directly model subjective quality of life.

Instead, it reports transparent economic proxies.

## 13.1 Household income index

The index is based on median vessel profit and clipped to a bounded range.

## 13.2 Debt-service ratio

\[
DSR_{i,t}=
\frac{AnnualDebtService_{i,t}}{Revenue_{i,t}}.
\]

## 13.3 Effort / days-at-sea proxy

\[
DaysAtSeaIndex_t
\propto
\frac{MeanEffort_t}{CPUE_t}.
\]

Higher CPUE can therefore reduce the effort burden required to generate a given catch.

## 13.4 Resilience index

The implemented proxy is:

\[
Resilience_t=
0.45IncomeComponent_t
+0.30DebtComponent_t
+0.25EffortComponent_t.
\]

This represents the idea that fisher households/businesses are more resilient when:

- income is stronger;
- debt-service burden is lower;
- required effort/time at sea is lower.

This is explicitly a **simulation proxy**, not a validated social-science wellbeing metric.

---

# 14. Coupling structure

The central contribution of the model is not any single equation but the feedback loops between modules.

## 14.1 Ecological-economic loop

\[
B_t
\rightarrow
Catch_t
\rightarrow
Revenue_t
\rightarrow
Profit_t
\rightarrow
Effort_{t+1}
\rightarrow
Catch_{t+1}
\rightarrow
B_{t+1}.
\]

This is the core Gordon-Schaefer-style bioeconomic feedback.

## 14.2 Monitoring-compliance-resource loop

\[
EM
\rightarrow
Detection\uparrow
\rightarrow
IUU\downarrow
\rightarrow
HiddenMortality\downarrow
\rightarrow
Biomass\uparrow
\rightarrow
CPUE\uparrow.
\]

## 14.3 Awareness-adoption loop

\[
Awareness
\rightarrow
Adoption
\rightarrow
ObservedBenefit
\rightarrow
PeerEffect
\rightarrow
Awareness/Adoption\uparrow.
\]

Because churn exists, this loop can also reverse.

## 14.4 Market loop

\[
CatchSupply
\leftrightarrow
DemandCapacity
\rightarrow
Price
\rightarrow
Revenue
\rightarrow
Profit
\rightarrow
Effort.
\]

## 14.5 Premium loop

\[
Adoption\uparrow
\rightarrow
VerifiedSupply\uparrow
\rightarrow
PremiumCoverage\downarrow\;\text{if demand is saturated}.
\]

This prevents a permanent premium from being treated as free money.

## 14.6 Blue-finance loop

\[
EM+Trust+Compliance
\rightarrow
Eligibility
\rightarrow
BlueFinance
\rightarrow
LowerDebtCost+Capex
\rightarrow
Profit/Resilience\uparrow
\rightarrow
ObservedBenefit\uparrow
\rightarrow
Adoption\uparrow.
\]

## 14.7 Governance loop

\[
BiomassRisk+IUU
\rightarrow
MPAResponse
\rightarrow
AccessibleEffort
\rightarrow
HarvestPressure
\rightarrow
Biomass.
\]

At the same time:

\[
Compliance\uparrow
\rightarrow
GovernanceRelief
\rightarrow
LessNeedForBroadRestriction.
\]

---

# 15. Annual execution order

For each Monte Carlo world and each simulation year, the implemented engine executes approximately the following sequence:

1. Read current biomass, effort, awareness, adoption, trust, IUU, MPA, price, debt and blue-finance states.
2. Compute accessible/effective effort after MPA and conservation response.
3. Compute species catch \(H=qEB\).
4. Compute hidden IUU mortality and avoidable mortality.
5. Compute CPUE.
6. Compute verified supply, premium coverage and market access.
7. Calculate base species revenue.
8. Allocate fleet revenue across heterogeneous vessels.
9. Apply operating costs and any blue-capex efficiency improvements.
10. Calculate premium, quality, market-access and payment-speed value.
11. Calculate reporting, inspection, operational, insurance and finance savings.
12. Evaluate blue-finance eligibility and allocate finite grants/loans.
13. Refinance conventional debt and update productive-capex score.
14. Calculate vessel profit and household/resilience proxies.
15. Update wealth and debt.
16. Update biomass using biological production minus legal and hidden mortality.
17. Update demand capacity and real species prices.
18. Update effort using profit, liquidity, scarcity response and capacity limits.
19. Update awareness, trust, adoption and churn.
20. Update IUU using scarcity, price, detection and awareness.
21. Update dynamic MPA coverage.
22. Update verified premium based on demand/supply balance.
23. Proceed to the next year.

The update order matters because it defines causal timing. For example, the profit earned in year \(t\) changes effort and adoption decisions for \(t+1\), rather than retroactively changing the catch already taken in year \(t\).

---

# 16. Monte Carlo structure

BAU and intervention worlds use **common random numbers**.

For replicate \(j\):

\[
\epsilon^{climate,BAU}_{j,t}
=
\epsilon^{climate,INT}_{j,t},
\]

and similarly for recruitment and market shocks.

Therefore paired differences:

\[
\Delta Y_{j,t}=Y^{INT}_{j,t}-Y^{BAU}_{j,t}
\]

are less contaminated by unrelated stochastic worlds.

The simulator reports:

- mean;
- median;
- P5/P25/P75/P95;
- paired scenario differences;
- probability intervention exceeds BAU.

The scenario sweep varies policy controls rather than pretending that one configuration is the unique future.

---

# 17. Current parameter classes

The simulator conceptually uses the following classes.

### A. Observed/calibratable

Eventually sourced directly from operational or accounting data:

- vessel counts;
- prices;
- fuel/labour costs;
- debt rates;
- EM hardware costs;
- MPA areas;
- reported catch;
- observer/EM coverage.

### B. Estimated biological

- \(r_s\);
- \(K_s\);
- \(q_s\);
- biomass ratios;
- process variance.

These should ultimately come from RFMO stock assessments or an operating model.

### C. Behavioural

- awareness response;
- peer effect;
- trust formation;
- adoption coefficients;
- churn;
- IUU response to detection.

These require surveys, historical programme data or Bayesian calibration.

### D. Policy hypotheses

- 5% maximum premium;
- EM subsidy schedule;
- blue-finance pool;
- concessional rate;
- premium-market capacity;
- maximum MPA;
- assumed reporting/inspection/operational savings.

Scenario sweeps should concentrate particularly on Class C and D assumptions.

---

# 18. Calibration pathway

A decision-grade version should calibrate modules sequentially rather than fitting everything simultaneously.

## Stage 1 — Ecology

Fit or import:

- biomass trajectories;
- recruitment;
- fishing mortality;
- stock reference points;
- uncertainty.

Primary sources: WCPFC/SPC, IATTC, IOTC or ICCAT depending on domain.

## Stage 2 — Effort and catchability

Use:

- RFMO reported catch/effort;
- vessel registers;
- GFW apparent fishing activity;
- logbook/EM overlap.

GFW should be treated as an observation channel because its apparent fishing classifications are model-derived and subject to coverage and classification caveats. [10][11]

## Stage 3 — Fleet economics

Calibrate:

- fuel;
- bait;
- labour;
- repairs;
- insurance;
- financing;
- vessel utilization;
- landing price.

## Stage 4 — Observation model

Use overlap periods between:

- EM;
- human observers;
- logbooks;
- AIS/GFW.

NOAA's longline EM work is an example of this type of observer-vs-EM validation. [12]

## Stage 5 — Behaviour

Calibrate adoption, trust, awareness and IUU response from:

- EM programme roll-outs;
- fisher surveys;
- observed compliance;
- regulatory changes;
- incentive experiments.

## Stage 6 — Finance

Calibrate using actual lending terms, default experience, collateral requirements and blue-finance programme uptake.

The Seychelles BIF provides a useful real programme reference, but its loan terms should not be assumed to transfer unchanged to other jurisdictions. [15][16]

---

# 19. Implemented now versus future model upgrades

| Module | Implemented now | Preferred later upgrade |
|---|---|---|
| Biomass | Species-specific stochastic Schaefer surplus production | RFMO age/size-structured operating model |
| Recruitment | Production shock + bounded protection factor | Beverton-Holt/assessment recruitment with posterior draws |
| Space | Scalar MPA/access fraction | Spatial grid/H3 + migration + vessel location choice |
| Effort | Vessel heterogeneous bounded profit response | Trip/set-level discrete choice and capacity dynamics |
| Catch | \(qEB\) with biological cap | Gear/set/species selectivity and size composition |
| EM observation | Conceptual monitoring quality in behaviour | Explicit sensitivity/specificity by task and review fraction |
| Adoption | Logistic stochastic peer/economic model | Hierarchical behavioural calibration by fleet/community |
| IUU | Latent bounded intensity index | Separate under-reporting, MPA, quota, transshipment, discard states |
| MPA | Dynamic scalar coverage | Cell-level risk-driven closures and displacement |
| Market | Species price + growing demand frontier | Buyer classes, export markets, elasticities, contract/offtake models |
| Premium | Capacity-limited verified premium | Buyer-specific contracts/certification demand |
| Blue finance | Finite grants/loans + refi/capex | Full loan underwriting, defaults, collateral and portfolio model |
| Household wellbeing | Transparent economic resilience proxy | Validated social/household survey model |

---

# 20. Interpretation rules

The simulator should be read as a **mechanism-testing tool**, not as proof that EM universally guarantees a particular return.

A result such as:

\[
P(\Delta Profit_{30}>0)=0.88
\]

means:

> under the stated parameter distributions and policy assumptions, 88% of paired stochastic simulations produced greater year-30 profit under the intervention than BAU.

It does **not** mean there is an empirically established 88% probability that a specific fishery will become more profitable after installing EM.

The scientifically defensible use of the simulator is to identify:

1. which mechanisms dominate;
2. which assumptions are required for short-term fisher benefit;
3. which thresholds cause the result to reverse;
4. which parameters need empirical measurement;
5. what transition-finance package is sufficient but not excessive;
6. how ecological and economic outcomes co-evolve.

---

# 21. Principal hypotheses that can be tested with the simulator

### H1 — EM as information infrastructure

\[
EM\uparrow
\Rightarrow
ObservationQuality\uparrow
\Rightarrow
Management/Operations\uparrow.
\]

### H2 — monitoring and awareness reduce hidden mortality

\[
EM+Awareness\uparrow
\Rightarrow
IUU+AvoidableMortality\downarrow
\Rightarrow
Biomass\uparrow.
\]

### H3 — resource preservation improves fisher economics

\[
Biomass\uparrow
\Rightarrow
CPUE\uparrow
\Rightarrow
CostPerTonne\downarrow
\Rightarrow
EconomicRent\uparrow.
\]

### H4 — transition incentives should be temporary

\[
Premium/Subsidy\rightarrow AdoptionBarrier\downarrow
\]

but excessive permanent incentives may cause:

\[
Profit\uparrow\rightarrow Effort\uparrow\rightarrow RentDissipation.
\]

### H5 — verified data can become financial infrastructure

\[
EM+ComplianceHistory
\Rightarrow
InformationAsymmetry\downarrow
\Rightarrow
FinanceEligibility\uparrow
\Rightarrow
DebtCost\downarrow/Capex\uparrow.
\]

### H6 — optimal management is a coupled transition problem

The policy objective should not be to maximize adoption, MPA area or premium independently. It is to find a region in parameter space where:

\[
\Delta Profit_{1-3}>0,
\]

\[
\Delta Biomass_{10-30}>0,
\]

\[
\Delta CPUE_{10-30}>0,
\]

\[
\Delta IUU<0,
\]

and:

\[
\Delta Resilience>0.
\]

---

# References

[1] Schaefer, M.B. (1954). *Some aspects of the dynamics of populations important to the management of the commercial marine fisheries*. Inter-American Tropical Tuna Commission Bulletin 1(2), 23-56. IATTC copy: https://www.iattc.org/GetAttachment/62d510ee-13d0-40f2-847b-0fde415476b8/Vol-1-No-2-1954-SCHAEFER%2C-MILNER-B-_Some-aspects-of-the-dynamics-of-populations-important-to-the-management-of-the-commercial-marine-fisheries.pdf

[2] FAO. *UN Handbook / Annex III: Bio-economic models of fisheries and methods for stock assessment*. Describes the Gordon-Schaefer framework and logistic stock growth. https://www.fao.org/fishery/docs/DOCUMENT/UNhandbook/UNhandbook.pdf

[3] FAO. *Management techniques for elasmobranch fisheries — Surplus production models*. Gives the Schaefer logistic model and catch relation \(C=qfB\), and discusses assumptions/limitations. https://www.fao.org/4/a0212e/A0212E14.htm

[4] FAO. *FishCode STF review*. Relates yield, fishing mortality, catchability, effort and CPUE in surplus-production models. https://www.fao.org/fishery/docs/DOCUMENT/fishcode/stf/Workshop_20-9-05/2e.pdf

[5] Gordon, H.S. (1954). *The Economic Theory of a Common-Property Resource: The Fishery*. Journal of Political Economy 62(2), 124-142. https://www.journals.uchicago.edu/doi/10.1086/257497

[6] World Bank (2017). *The Sunken Billions Revisited: Progress and Challenges in Global Marine Fisheries*. Reports an estimated US$83 billion annual foregone net benefit in 2012 and identifies excessive effort/depleted stocks as major sources of loss. https://documents1.worldbank.org/curated/en/347431487184280381/pdf/112848-PUB-PUBLIC.pdf

[7] Bass, F.M. (1969). *A New Product Growth for Model Consumer Durables*. Management Science 15(5), 215-227. https://doi.org/10.1287/mnsc.15.5.215

[8] Charles, A.T., Mazany, R.L. & Cross, M.L. (1999). *The Economics of Illegal Fishing: A Behavioral Model*. Marine Resource Economics 14(2). https://www.journals.uchicago.edu/doi/10.1086/mre.14.2.42629256

[9] FAO. *Approaches to estimating benefits — fisheries compliance and deterrence*. Summarizes expected penalty/detection, moral attitudes and social influence as major determinants of compliance. https://www.fao.org/4/y3780e/y3780e08.htm

[10] Global Fishing Watch. *Data Caveats*. Apparent fishing is a model-based estimate and includes caveats concerning false positives, vessel classification, AIS coverage and event interpretation. https://api-doc.globalfishingwatch.org/our-apis/documentation/docs/v3/general-api-doc/data-caveats

[11] Global Fishing Watch. *Detailed Apparent Fishing Activity*. Describes apparent fishing activity, AIS/VMS limitations and the current fishing-model pipeline. https://globalfishingwatch.org/detailed-apparent-fishing-activity/

[12] Carnes, M.J., Stahl, J.P. & Bigelow, K.A. (2019). *Evaluation of Electronic Monitoring Pre-implementation in the Hawaiʻi-based Longline Fisheries*. NOAA Fisheries. https://www.fisheries.noaa.gov/resource/document/evaluation-electronic-monitoring-pre-implementation-hawaii-based-longline

[13] OECD-FAO. *Agricultural Outlook 2026-2035 — fish and other fishing products data*. Capture-fish production and price projections. https://data-explorer.oecd.org/

[14] OECD-FAO (2025). *Agricultural Outlook 2025-2034*, fish and aquatic-products chapter / price projections. https://www.oecd.org/content/dam/oecd/en/publications/reports/2025/07/oecd-fao-agricultural-outlook-2025-2034_3eb15914/601276cd-en.pdf

[15] World Bank Treasury (2025). *Seychelles: Introducing the World's First Sovereign Blue Bond*. Describes the US$15 million issuance and routing of proceeds through the Blue Grants Fund and Blue Investment Fund. https://thedocs.worldbank.org/en/doc/cbaf1cefc5164a7f340716ef0af6fd7e-0340012025/original/Case-Study-Blue-Bond-Seychelles.pdf

[16] Development Bank of Seychelles. *Blue Investment Fund Scheme*. Current published programme terms include loans from US$10,000 to US$3 million, 4% interest and repayment up to 15 years. https://dbs.sc/service/bif-scheme/

---

## Citation note

External references above support the **choice of model families, empirical context and calibration logic**. They do not validate every numerical coefficient currently used in the simulator. Coefficients exposed as policy or behavioural hypotheses must be calibrated before decision-grade use.
