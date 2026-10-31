# Vessel-level economic impact

## In plain language

The immediate economic question is not simply “does EM hurt fishers?”. It is: **what costs and benefits change for each vessel, and how are those impacts distributed across vessel types?**

EM can impose short-term costs through hardware/service charges, longer routes when a preferred area is protected, additional fuel use, and potentially lower catch if legal alternatives are less productive. It can offset some of those costs by reducing expected compliance losses. A traceability premium is available as a scenario control but defaults to zero so the model does not rely on an assumed market premium.

The app reports the distribution of Year-1 profit changes for EM vessels rather than only the fleet average. That matters because a policy that raises fleet-wide value could still harm a subgroup such as smaller vessels.

## Main equations

Revenue:

$$
R_{i,t}=C_{i,t}P_{i,t}.
$$

Fuel:

$$
C^{fuel}_{i,t}=E_{i,t}\cdot LPH_i\cdot Transit_i\cdot DistanceMultiplier_{i,t}\cdot P^{fuel}_t.
$$

EM monthly cost:

$$
C^{EM}_{i,t}=\frac{Capex_i}{12Y_{amort}}+\frac{Service_i}{12}.
$$

Expected compliance-risk loss:

$$
E[L_i]=L_0\cdot Risk_i\cdot (1-Reduction_{EM}).
$$

Profit:

$$
\Pi_{i,t}=R_{i,t}-C_{i,t}.
$$

Short-term paired economic impact:

$$
\Delta \Pi_{i,1}=\Pi^{EM}_{i,1}-\Pi^{BAU}_{i,1}.
$$

Percentage change:

$$
100\times\frac{\Delta\Pi_{i,1}}{|\Pi^{BAU}_{i,1}|}.
$$

The denominator uses absolute BAU profit for numerical stability when a representative agent has a small or negative baseline profit.

## Recommended interpretation

Treat a user-selected loss threshold, e.g. 5%, as a *materiality criterion*, not a universal economic standard. Report both the fleet average and the share of EM vessels whose Year-1 profit falls beyond that threshold.
