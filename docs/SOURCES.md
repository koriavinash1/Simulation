# Data sources and calibration plan

The packaged application is runnable without downloading external data. Its built-in calibration table is **synthetic demonstration data**, not a reproduction of any proprietary or licensed dataset. For evidence-grade use, replace those priors with data assembled from the sources below.

## Global Fishing Watch (GFW)

**Use in the model:** apparent fishing effort, vessel behavior, seasonal/spatial fishing-ground attractiveness, MPA exposure, trip and event patterns.

- Apparent Fishing Activity: https://globalfishingwatch.org/detailed-apparent-fishing-activity/
- Dataset/code overview: https://globalfishingwatch.org/dataset-and-code-fishing-activity/
- API documentation: https://api-doc.globalfishingwatch.org/our-apis/documentation/

Important interpretation: GFW describes *apparent fishing activity*, not confirmed gear deployment or catch. The current 2026 documentation states that the model uses AIS/VMS movement and track context and can contain false positives or vessel/gear classification errors.

**Licensing:** GFW's standard site/services/data are described as CC BY-NC 4.0/non-commercial. A commercial Blurgs deployment should obtain appropriate permission/licensing before embedding GFW data or APIs. The simulator therefore accepts an uploaded calibration CSV rather than redistributing GFW records.

## WCPFC

**Use:** longline catch/effort, monthly seasonality, 5°×5° catch/effort surfaces and flag-specific strata.

Public-domain page: https://www.wcpfc.int/index.php/sustainability/scientific-data/wcpfc-public-domain-aggregated-catcheffort-data-download-page

As of the 30 April 2026 update, WCPFC lists longline catch/effort at 5°×5° by year/month through 2024, plus flag/year/month variants. Public-domain filtering is applied for confidentiality.

## IOTC

**Use:** Indian Ocean longline catches, effort and CPUE priors by month/species/gear/flag/spatial stratum.

- Catch-effort reference: https://iotc.org/documents/ce-reference
- All CE files: https://iotc.org/documents/all-ce-files

The 2026 IOTC metadata says longline data are generally monthly and up to 5°×5°, with effort commonly in hooks and catches in weight and/or numbers. Data completeness varies and some records are samples rather than raised totals. The latest all-CE metadata found during app preparation covers data through 2025.

## ICCAT

**Use:** Atlantic catch/effort and size-frequency calibration.

Database access: https://www.iccat.int/en/accesingdb.html

ICCAT Task 2 catch/effort provides species, gear, flag and month by small area; longlines are generally 5°×5°. The public database page was updated 30 January 2026.

## IATTC

**Use:** Eastern Pacific longline catch/effort.

Public-domain data: https://www.iattc.org/en-US/Data/Public-domain

The March 2026 public longline tuna/billfish file is aggregated by year, month, flag and 5°×5° area.

## World Bank / FAO bioeconomic context

World Bank, *The Sunken Billions Revisited*: https://www.worldbank.org/content/dam/Worldbank/Topics/Environment/Sunken%20Billions%20Revisited-web-2.pdf

The report estimates that global marine fisheries in 2012 generated about US$83B less annual net economic benefit than under an economically optimal management scenario, with a stated uncertainty range of roughly US$51B–105B. This is **context only** and must not be attributed to tuna longliners or to EM. It motivates testing whether better management can reduce economic inefficiency.

## Recommended empirical calibration table

The app accepts a CSV with:

- `region`: simulator region label;
- `month`: 1–12;
- `fishing_hours`: GFW-derived apparent fishing effort or a normalized equivalent;
- `mpa_exposure`: fraction/proxy for interaction with protected space;
- `cpue_index`: RFMO-derived catch-per-unit-effort index normalized around 1.

For a production model, extend the adapter to retain real RFMO, 5°×5° cell, flag, species, hooks, catch number/weight and uncertainty fields rather than collapsing them into eight synthetic regions.
