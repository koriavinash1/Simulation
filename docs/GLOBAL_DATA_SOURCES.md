# Open-data sources and intended use

The application separates **data calibration** from **simulation mechanics**. Do not infer illegal activity from a named real vessel. GFW activity/gaps are behavioural observations and coverage artefacts can exist.

## Installed Realistic Open-Data Pack

The simulator bundles an active, verified open-data pack under `data/processed/` generated via `data_pipeline/fetch_and_build_data_pack.py`:

1. **Natural Earth 110m Physical Land:** Official global land boundaries used for strict polygon-intersection masking. No simulated vessel or world cell is ever located on land.
2. **Global Fishing Watch (GFW) & RFMO Effort Priors:** 316 ocean cells calibrated against high-seas drifting longliner effort densities across WCPFC, IATTC, IOTC, and ICCAT convention areas.
3. **World Database on Protected Areas (WDPA / MPAtlas / UNEP-WCMC):** 15 major pelagic marine reserves with verified spatial boundaries (e.g., Papahānaumokuākea, Pacific Remote Islands, PIPA, Galápagos, Coral Sea, Marae Moana, Chagos, Tristan da Cunha). Spatial intersection between reserve boundaries and 10° ocean cells endogenously calculates `mpa_share`.
4. **World Bank & FAO Fisheries Statistics:** Landed value calibration anchor of $6.0B based on FAO The State of World Fisheries and Aquaculture (SOFIA) pelagic longline landing valuations and World Bank Commodity Markets (Pink Sheet) fuel and market indices.

## Vessel activity and fishing effort

**Global Fishing Watch (GFW):** calibrate drifting-longline spatial effort, ground persistence, voyage structure, seasonal activity, encounter/gap patterns and MPA exposure. The standard GFW data licence must be checked for commercial use before embedding data in a Blurgs production product.

## Catch and effort

**WCPFC, IOTC, ICCAT, IATTC, CCSBT:** monthly/grid/flag/gear catch and effort where public. Use these datasets for CPUE, species composition and hooks/effort calibration rather than treating GFW apparent fishing hours as catch.

## Species distribution

**OBIS / GBIF marine occurrence products:** rough global occurrence/suitability indicators. For tuna, refine with RFMO catch distributions and stock-assessment spatial products.

## Protected areas

**Protected Planet / WDPA / MPAtlas:** 15 real pelagic marine protected area polygons loaded from `data/processed/marine_mpas.geojson`. You can recompile or add custom reserves with `uv run python data_pipeline/build_open_data_pack.py --fetch-realistic`.

## Ocean/climate

**Copernicus Marine / NOAA:** SST, chlorophyll/productivity and marine heat-wave indicators for a calibrated climate/habitat model. The default simulator generates a stochastic climate index bounded by the user's extremity ceiling.

## Economics

**FAO/GLOBEFISH, RFMO/port studies, trade unit values, World Bank/energy series:** reconstruct ex-vessel prices, fuel costs and landed value. The default landed value baseline anchor ($6.0B) is calibrated to FAO SOFIA and World Bank series.

## Bycatch

RFMO observer datasets/summaries plus species-specific public studies calibrate shark, turtle and seabird encounter/mortality distributions.
