# Model: what the simulator is doing

## Plain-language view

The application creates a synthetic population of longline vessels. Each vessel has a size class, fishing capacity, fishing effort, catch efficiency, fuel use, crew/fixed costs, risk propensity and an EM status. Every month each vessel chooses a fishing region using a mixture of historical-like fishing attractiveness, its own learned catch expectations, the current stock state, MPA restrictions and a small amount of exploration.

Vessels do **not** operate independently. If many vessels select the same region, crowding lowers their expected catch rate. Their combined catch removes biomass. Biomass then grows, is harvested and can spill between regions. Because fish abundance changes, future CPUE changes too. This creates an economic-ecological feedback loop.

EM does not directly create fish or revenue. In the simulator it changes only: (1) the probability of fishing in protected areas, (2) monitoring/service costs, (3) expected compliance-risk costs, and (4) the quality of information available to the management agent. Any later increase in biomass, CPUE, profit or landed value must emerge through those pathways.

At the end of each simulated year, a management agent observes the fishery imperfectly. As EM coverage rises, observation error falls and management quality rises. The manager can change effective effort pressure and, when enabled, adapt MPA targeting. Better or worse management then feeds back into the biological state and next year's vessel economics.

## Mathematical state

At month `t`, the system state is approximately

$$
\mathcal{S}_t = \{V_{1:N,t}, B_{1:G,t}, P_t, F_t, M_t\}
$$

where:

- $V_{i,t}$: vessel-agent state;
- $B_{g,t}$: biomass index in region $g$;
- $P_t$: ex-vessel fish price;
- $F_t$: fuel price;
- $M_t$: management state.

Each agent takes an action

$$
a_{i,t} \in \{g_1,\ldots,g_G\}
$$

representing the region selected for fishing in that monthly step.

### Region choice

The region utility combines a historical effort prior, the agent's learned CPUE expectation, current biomass and a legal/MPA penalty:

$$
U_{i,g,t} = \log H_{g,m} + \beta_1\log \hat{q}_{i,g,t} + \beta_2\log B_{g,t} - \beta_3 L_{i,g,t}
$$

where $H_{g,m}$ is the month/region fishing-effort prior and $L$ is stronger for EM-equipped vessels in regions with higher MPA exposure.

Choice probabilities are softmax:

$$
P(a_{i,t}=g)=\frac{\exp(U_{i,g,t})}{\sum_h \exp(U_{i,h,t})}.
$$

A small exploration term prevents vessels from being permanently trapped in historical grounds:

$$
P^*(g)=(1-\epsilon)P(g)+\epsilon/G.
$$

### Catch

For vessel $i$ in region $g$:

$$
C_{i,t}=\kappa E_{i,t}q_iK_iS_i\,CPUE_{g,m,t}\,\epsilon_{i,t}
$$

where:

- $E$: fishing effort hours;
- $q_i$: vessel catchability;
- $K_i$: capacity index;
- $S_i$: vessel skill multiplier;
- $\epsilon$: log-normal stochastic catch success;
- $\kappa$: calibration factor chosen so the initial synthetic fishery approximately matches the user-entered baseline landed value.

CPUE responds to biomass and congestion:

$$
CPUE_{g,m,t}=CPUE^{prior}_{g,m}B_{g,t}^{\eta_B}\,\Gamma_{g,t}.
$$

### Congestion / competition

If too many agents select the same fishing ground, catch efficiency falls:

$$
\Gamma_{g,t}=\operatorname{clip}\left(1-\lambda_c\left(\frac{s_{g,t}}{s_g^0}-1\right)\right).
$$

This creates interaction between vessel agents without requiring direct communication.

### Biomass

The regional biomass model is a simplified stochastic logistic system:

$$
B_{g,t+1}=B_{g,t}+\frac{r}{12}B_{g,t}\left(1-\frac{B_{g,t}}{K}\right)-H_{g,t}+S_{g,t}+\xi_{g,t}.
$$

Harvest pressure is reduced by effective MPA protection; spillover moves biomass toward lower-biomass regions.

This is an **index model**, not a stock-assessment replacement. For publication-grade work, replace it with stock-specific operating models derived from RFMO assessments.

### Price feedback

The model optionally responds to aggregate fleet supply:

$$
P_t=P_t^{base}\left(\frac{Q_t}{Q_t^0}\right)^{-\eta_P}.
$$

The parameter $\eta_P$ controls how strongly price reacts to monthly supply.

### Profit

For vessel $i$:

$$
\Pi_{i,t}=R_{i,t}-C^{fuel}_{i,t}-C^{fixed}_{i,t}-C^{crew}_{i,t}-C^{variable}_{i,t}-C^{EM}_{i,t}-E[L^{compliance}_{i,t}].
$$

EM capex is amortised over the selected amortisation period and service cost is charged annually/monthly.

### Management observation

The manager sees noisy biomass:

$$
\hat{B}_{g,t}=B_{g,t}\varepsilon_{g,t}
$$

with observation uncertainty decreasing as EM adoption rises:

$$
\sigma_{obs}=\max(\sigma_{floor},\sigma_0(1-\rho A_{EM})).
$$

Management quality is updated toward

$$
Q_M=Q_0+\rho A_{EM}.
$$

The current implementation uses that information to alter effort pressure and, if enabled, improve effective MPA targeting toward weak-stock regions.

### Adaptive MPA demarcation

The current app does not draw literal new MPA polygons. It models *demarcation quality* as a regional targeting process. Regions further below the target biomass receive a larger incremental effective-protection adjustment:

$$
\Delta MPA_g \propto Q_M\max(B^*-B_g,0).
$$

For a spatially explicit production model, replace this abstraction with real protected-area polygons, a grid-based optimizer, displacement costs and species habitat/stock surfaces.

## Paired counterfactual design

Every Monte Carlo replication is run twice with the same seed:

1. BAU: 0% EM.
2. Intervention: selected EM adoption rate.

Because price, fuel and biological random shocks share the same random seed, the paired difference is much less noisy than comparing unrelated simulations.

The primary causal estimand is therefore approximately

$$
\Delta Y_r=Y_{r,EM}-Y_{r,BAU}.
$$

Across replications the app estimates expected impacts and probabilities such as

$$
P(NPV_{EM}>NPV_{BAU}).
$$

## What is and is not causal

This is a **counterfactual simulation**, not an observational causal estimate. It answers: *if the encoded mechanisms and calibrated distributions are reasonable, what system outcomes emerge?* Confidence in the answer depends on validation of the behavioral, biological, economic and management submodels.
