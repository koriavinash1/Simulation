# Model notes

## Current model family

Hybrid stochastic state-space + heterogeneous vessel-agent simulator.

- Ecology: Schaefer-style species production with stochastic recruitment/climate shocks.
- Catch: catchability x effective effort x biomass, species-specific.
- Effort: bounded profit-responsive utilization with intervention scarcity response.
- Awareness/adoption: peer, trust, campaign and observed-benefit dynamics.
- IUU: latent intensity modified by scarcity, price, monitoring/detection and awareness.
- MPA: bounded dynamic response to biomass/IUU risk.
- Market: species-specific growing demand capacity plus real-price drift and partial supply feedback.
- Economics: vessel revenue/cost, short-term benefit stack, real and nominal profits.
- Finance: conventional debt plus finite blue-finance pool and productive upgrades.

## What is not yet production-calibrated

- RFMO stock-assessment posterior draws.
- GFW spatial effort grids and observation-error model.
- Actual EM/observer task sensitivities and reporting error.
- Country/fleet-specific vessel accounts and debt data.
- Buyer-specific premium/offtake demand curves.
- Lender-specific credit, insurance and default models.
- Blue-finance application/approval/collateral constraints.

Do not use raw numerical outputs as policy forecasts until these are calibrated and hindcast validation gates are met.
