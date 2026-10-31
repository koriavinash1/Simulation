# Blurgs Global Fisheries Digital Twin

A Streamlit multi-agent bioeconomic/ecosystem simulator for exploring how Electronic Monitoring (EM), government MPA policy, vessel reallocation, persistent non-compliance, climate variability, fisheries management, fish populations and economic outcomes interact in global tuna longline fisheries.

## Package management

This project uses **uv** as the canonical Python package and environment manager. Dependencies are declared in `pyproject.toml`. Run `uv lock` once in a networked environment to create the reproducible `uv.lock`, then commit that lockfile. Use `uv` for installation, execution, testing, and dependency updates.

Common commands:

```bash
uv lock                         # resolve dependencies and create/update uv.lock
uv sync                         # create/update .venv from uv.lock
uv run streamlit run app.py     # launch the app
uv run python run_cli.py        # run CLI simulation
uv run pytest -q                # run tests
```

For development dependencies, `uv sync` installs the default `dev` dependency group containing pytest.

## Master Technical & Socio-Economic Report

For the complete mathematical specification, simulation philosophy, bioeconomic J-curve valuation, crew livelihood analysis, and World Bank macroeconomic growth benchmarking, refer to:

👉 **[`docs/COMPREHENSIVE_MODEL_REPORT.md`](docs/COMPREHENSIVE_MODEL_REPORT.md)**

## Core positioning

EM is **not** modeled as perfect surveillance. Its primary behavioral mechanism is awareness/transparency: adopting vessels draw a heterogeneous reduction in latent non-compliance propensity, while a non-zero residual illegal-entry probability always remains. Government MPA expansion, management, enforcement/norm pressure and reallocation support are independent policy mechanisms.

The model runs paired BAU and EM worlds with the same starting fleet and stochastic climate process.

## Run

```bash
uv lock
uv sync
uv run streamlit run app.py
```

Or use the included launcher:

```bash
./run_app.sh
```

## Main controls

The user only controls high-level scenario/extremity variables:

- maximum EM adoption (%)
- maximum EM awareness effect (%)
- maximum premium (%)
- maximum government MPA expansion/redesign push (%)
- maximum reallocation support (%)
- maximum general compliance push (%)
- maximum climate extremity (%)
- simulation horizon / random seed / representative-agent count

Most other parameters are reference priors in `sim/global_config.py` and are documented in `docs/PARAMETER_REFERENCES.md`.

## Single global canvas

The Global Animation tab displays:

- synthetic longliner agents moving collectively across global pelagic fishing cells
- EM-enabled vs non-EM agents
- simulated non-compliant MPA entries
- coarse MPA exposure cells (or a locally installed current MPA polygon data pack)
- species-abundance indicator layer
- animated monthly time control

Additional tabs show species depletion/recovery, landed value, profit, MPA policy, management quality and agent-level outcome distributions.

## Data-pack design

The repository runs without external downloads using clearly-labelled fallback priors. Publication/production use should install a calibrated open-data pack:

- GFW: longline effort/behavioral priors
- WCPFC/IOTC/ICCAT/IATTC/CCSBT: catch, effort, species composition, CPUE
- OBIS/GBIF: species occurrence/suitability indicators
- Protected Planet/WDPCA: all current marine protected/conserved-area polygons
- Copernicus/NOAA: SST/productivity/heat-wave inputs
- FAO/GLOBEFISH + public port/trade sources: species/region ex-vessel prices
- RFMO observer/bycatch sources: shark/turtle/seabird encounter distributions

This repository does not redistribute datasets whose terms may require registration, API tokens or commercial permission. Use `data_pipeline/build_open_data_pack.py` to normalize authorised local exports.

## Tests

```bash
uv run pytest -q
```

Current suite: 6 tests.

## Important interpretation

All illegal/non-compliance events in the simulator are synthetic latent behavior. The application must not be used to accuse a named real vessel based on AIS gaps or apparent fishing activity alone.
