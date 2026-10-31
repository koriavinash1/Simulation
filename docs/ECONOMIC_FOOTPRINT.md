# Economic footprint metrics

The application deliberately reports several economic quantities separately.

## 1. Ex-vessel landed value

$$
LV_t=\sum_i Catch_{i,t}Price_{i,t}.
$$

This is the closest measure to the value generated at first sale by the fishing fleet. The $9B and $13B controls are tested against this quantity in the final simulated year.

## 2. Fleet operating profit

$$
\Pi^{fleet}_t=\sum_i\Pi_{i,t}.
$$

This reflects vessel economics after the modeled operating, EM and expected compliance-risk costs.

## 3. Discounted NPV of fleet profit

$$
NPV=\sum_{t=1}^{T}\frac{\Pi^{fleet}_t}{(1+r_d)^{t-1}}.
$$

The app reports the mean paired NPV difference and the probability that EM NPV exceeds BAU NPV.

## 4. Supply-chain footprint proxy

$$
Footprint_t=LV_t\times m.
$$

Here $m$ is a user-controlled gross-output multiplier. This can represent downstream processing/distribution activity in a scenario, but it is **not** automatically GDP, welfare or value added. It should never be added to landed value or vessel profit because that would double count economic activity.

## 5. Stock asset proxy

The current engine also outputs a simple stock-asset proxy based on current profit, the discount rate and biomass state. This is exploratory and should not be used as a formal natural-capital valuation without a dedicated resource-rent model.

## Recommended headline results

Report at least:

- Year-1 fleet profit impact;
- percentage of EM vessels suffering more than the selected material-loss threshold;
- final-year landed value under BAU and EM;
- probability final-year landed value exceeds $9B and $13B (or user-selected benchmarks);
- paired long-run NPV difference;
- biomass and management-quality trajectories;
- results by vessel class.
