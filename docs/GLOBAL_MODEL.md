# Global fisheries model: current coupled specification

Updated 2 November 2026. [MODEL_CORRECTIONS.md](MODEL_CORRECTIONS.md) records historical sources, reference runs, limitations and test coverage. Earlier real-growth guarantees, Gaussian reserve boundaries and normalized extraction equations are superseded.

## 1. Paired scenarios

BAU and EM share the starting fleet, reference catch calibration, climate, market shocks and biological random draws. EM adoption, awareness, verified premium, government MPA redesign, enforcement and reallocation support are distinct controls. With all six zero, outputs are exactly identical apart from labels. Climate is shared regardless of its ceiling.

Each scenario advances monthly; management updates annually. Climate is exogenous, not bidirectionally coupled. Dedicated random streams and fixed elapsed-time policy ramps preserve earlier results when the horizon is extended.

## 2. Fleet, habitat and protected access

Fleet traits include capacity, fishing hours, catchability, fuel intensity, monthly fixed/crew costs and latent non-compliance. Synthetic vessels target one of four commercial species. Ground choice combines historical preferences, current species biomass, persistence, legal aversion and exploration, restricted to resident habitat.

A displayed coordinate is the monthly operating cell used for all catch, enforcement and protection calculations. Relocation distance contributes to fuel costs; routes between cells are not simulated. Fishing effort uses mean-one lognormal variability, depletion-related effort creep and a management cap responding to stock shortfalls. Fishing days cannot exceed average calendar days per month.

Installed reserve polygons use a single dateline-aware transform for rendering and exact fishing-cell point membership, including holes. Polygon expansion and centroid adaptation require government MPA push and enabled redesign. Coarse protection fractions are used explicitly when no polygons are installed. Membership at cell centers is an approximation to fine-scale fishing access.

Encounter and latent violation determine illegal entry. Awareness and government enforcement reduce violation probability, retaining a nonzero configured residual propensity. Compliant encounters reduce access before catch; illegal vessels can extract within reserves and incur fines. Recorded catch is never discounted again in the stock update.

## 3. Catch and stocks

Vessel catch depends on effective effort, capacity, catchability, local stock raised to the CPUE elasticity, suitability, crowding, climate availability and mean-one catch noise. Eligible EM gear mitigation reduces incidental bycatch.

A pre-policy reference year sets the same fixed scale in both worlds to the configured first-year landed-value anchor. This includes actual catch randomness and access. It is not recalibrated in later years. Cell-specific physical stock conversions are inferred from equilibrium surplus production under reference catch, not measured biomass.

For requested cell catch `H`, stock index `B` and physical units per index `u`:

```
fraction = min(1, u*B/H)        # 1 when H=0
realized vessel catch = requested vessel catch * fraction[cell]
stock removal = sum(realized catch * fleet weight) / u
B_next = clip(B + (r/12)*B*(1-B/K) - removal + exchange - climate_loss + noise, 0, K)
```

The same realized catch drives revenue. Increasing extraction increases removal until stocks constrain it. Protection does not create unaccounted refuge benefits. Target stock-removal tonnes equal landed catch tonnes in the monthly ledger; bycatch uses separately labeled synthetic units.

Spatial exchange transfers physical stock between neighboring resident cells along differences in `B/K`, conserving every donor debit and receiver credit and limiting availability and receiver space. The regional engine uses conservative all-region mixing as an explicit approximation. Initial stocks lie below carrying capacity; zeros do not receive a positive floor. Growth rates are net surplus-production parameters; the retained `natural_mortality` field is informational.

## 4. Climate

Climate follows a bounded AR(1) anomaly process with occasional extreme jumps. It modifies catch availability within a fixed habitat envelope. Extra stock mortality is `max(abs(climate)-0.20,0)^2 * species_sensitivity * B / 12`. Proportional stock noise has zero mean before bounds. These response coefficients remain scenario priors. The model does not dynamically move carrying-capacity maps or simulate ocean currents.

## 5. Management and EM

EM installation phases in over 36 months and realized fleet share cannot exceed the selected ceiling. Adoption improves observability; awareness separately reduces latent non-compliance. Observability can reduce wasted search fuel and moderate effort on depleted grounds. Government norms and redesign phase in over a fixed 60 months, independently of the run length. Premium realization matures over 24 months. The package does not identify the causal effect of monitoring alone.

## 6. Economics and historical context

The default planning assumption is 1.5% annual real price growth. Nominal price growth composes with the 2.2% inflation assumption as `(1.015*1.022)-1 = 3.733%`. This assumption is shared by both worlds; annual variation is mean-one lognormal. The historical comparison instead uses `(159/151)^(1/4)-1`, approximately 1.30% nominal growth per year. Rounded FAO global capture first-sale observations are $151B in 2018, $141B in 2020 and $159B in 2022. These are broad, cross-edition historical proxies used only in the comparison scenario, not a fitted longline price series or evidence for the positive-real-growth planning default. Sources and scope differences are detailed in [MODEL_CORRECTIONS.md](MODEL_CORRECTIONS.md) and stored in `sim/market.py`.

Prices respond to current catch relative to a fixed reference supply, so persistent scarcity has a persistent price effect. There is no automatic BAU trade penalty. Premium eligibility respects EM and compliance requirements. Revenue remains endogenous: catches and stock quality can offset or exceed price growth.

```
revenue = realized catch * nominal species price * quality * eligible premium * supply adjustment
profit = revenue - fuel - monthly fixed costs - monthly crew costs - variable costs - EM costs - fines
real_landed_value = nominal_landed_value / (1+inflation)^(year-1)
```

Monthly cost priors are charged monthly, with nominal inflation applied to nonfuel costs and EM service fees. Nominal values do not receive inflation a second time. The $6B anchor is a scenario input. Current fleet costs can imply operating losses; subsidies and fleet exit/entry are not modeled. Revenue calibration is not profit validation.

## 7. Habitat reference

### Regional Biogeography & Thermal Envelopes
Fish species are **not globally ubiquitous**; their biogeographical ranges are strictly governed by sea surface temperatures (SST), thermoclines, dissolved oxygen thresholds, and Regional Fisheries Management Organization (RFMO) ocean basins:

| Species | Scientific Name | Thermal Range (Optimal) | Vertical Zone | Latitudinal Bounds | Key Global Basins & Stocks | RFMO Jurisdiction |
|:---|:---|:---|:---|:---|:---|:---|
| **Yellowfin Tuna** (YFT) | *Thunnus albacares* | 18°C – 31°C (22°C–28°C) | Epipelagic (0–100m) | $35^\circ\text{S} \le \text{lat} \le 35^\circ\text{N}$ ($0$ at $|\text{lat}| \ge 36^\circ$) | Western Pacific Warm Pool, Coral Sea, ETP, W. Indian, Gulf of Guinea | WCPFC, IATTC, IOTC, ICCAT |
| **Bigeye Tuna** (BET) | *Thunnus obesus* | 13°C – 29°C (17°C–22°C) | Mesopelagic (0–500m) | $40^\circ\text{S} \le \text{lat} \le 40^\circ\text{N}$ ($0$ at $|\text{lat}| \ge 42^\circ$) | Central/Eastern Equatorial Pacific, Equatorial Indian, Tropical Atlantic | WCPFC, IATTC, IOTC, ICCAT |
| **Albacore Tuna** (ALB) | *Thunnus alalunga* | 10°C – 25°C (15°C–19°C) | Subsurface / Epipelagic | $10^\circ \le |\text{lat}| \le 48^\circ$ ($0$ in equator $\le 8^\circ$ & polar $\ge 50^\circ$) | North/South Pacific Gyres, North/South Atlantic, Med Sea, Southern Indian | WCPFC, IATTC, IOTC, ICCAT |
| **Swordfish** (SWO) | *Xiphias gladius* | 5°C – 27°C (18°C–22°C) | Epipelagic to Mesopelagic | $45^\circ\text{S} \le \text{lat} \le 45^\circ\text{N}$ ($0$ at $|\text{lat}| \ge 48^\circ$) | Global fronts, Kuroshio, Humboldt, Gulf Stream, Agulhas Current | All RFMOs |
| **Silky / Blue Sharks** (SHK) | *Carcharhinus falciformis* | 18°C – 28°C | Pelagic (0–500m) | $40^\circ\text{S} \le \text{lat} \le 40^\circ\text{N}$ | Circumglobal pelagic drift | All RFMOs |
| **Marine Turtles** (TUR) | *Dermochelys coriacea*, etc. | > 15°C | Epipelagic / Coastal | $35^\circ\text{S} \le \text{lat} \le 35^\circ\text{N}$ | Tropical nesting beaches and equatorial foraging corridors | All RFMOs |
| **Seabirds** (SEA) | *Diomedeidae* (Albatrosses) | Subpolar / Cold temperate | Surface scavengers | $20^\circ \le |\text{lat}| \le 58^\circ$ ($0$ in equator $\le 16^\circ$) | Southern Ocean "Roaring Forties", Sub-Antarctic, North Pacific Rim | CCSBT, WCPFC, ICCAT |

#### Detailed Anatomy of Albacore Tuna (*Thunnus alalunga*) Distribution
Unlike tropical tunas (Yellowfin, Skipjack) that thrive in the equatorial warm pool, Albacore is a **temperate and subtropical species**. It actively avoids warm equatorial surface waters where SST exceeds 28°C, creating a bimodal global distribution separated by the equatorial doldrums:
1. **North Pacific Stock (20°N – 50°N):** Extends from the Kuroshio Extension off Japan eastward across the North Pacific Transition Zone to the California Current (US West Coast and British Columbia). Seasonally migrates with the 15°C–19°C SST front.
2. **South Pacific Stock (10°S – 45°S):** Inhabits the South Pacific Subtropical Gyre across Australia's eastern seaboard, New Caledonia, Fiji, Tonga, Cook Islands, French Polynesia, and down to New Zealand's Subtropical Convergence Zone (STCZ).
3. **North Atlantic Stock (30°N – 55°N):** Centered in the Bay of Biscay, Celtic Sea, Azores, Madeira, Canary Islands, and the western Atlantic margins (Grand Banks).
4. **South Atlantic Stock (10°S – 45°S):** Encompasses the southern subtropical gyre between Brazil/Uruguay and the Benguela/Agulhas current boundary off South Africa.
5. **Mediterranean Stock:** A discrete, genetically differentiated self-sustaining population resident throughout the Western and Central Mediterranean Sea.
6. **Indian Ocean Stock (10°S – 40°S):** Exclusively temperate Southern Indian Ocean from Madagascar east to southwestern Australia.

#### Calibrated Geographic Centers Matrix (All 7 Modeled Species)
The digital twin parameterizes regional environmental suitability $S_{sg}$ as a multi-modal Gaussian mixture model centered on oceanographically verified hotspots:

| Species | Code | Center Coords $(\text{Lon}, \text{Lat})$ | Dispersion $(\sigma_{\text{lon}}, \sigma_{\text{lat}})$ | Weight $w$ | Oceanographic Feature & Fishing Ground |
|:---|:---|:---|:---|:---|:---|
| **Yellowfin Tuna** | `YFT` | $(155^\circ, 4^\circ)$ | $(34^\circ, 14^\circ)$ | 1.00 | WCPFC: Western Pacific Warm Pool (Micronesia, PNG, Coral Sea) |
| | | $(-115^\circ, 2^\circ)$ | $(30^\circ, 12^\circ)$ | 0.85 | IATTC: Eastern Tropical Pacific Upwelling (Costa Rica Dome, Galapagos) |
| | | $(58^\circ, -4^\circ)$ | $(25^\circ, 14^\circ)$ | 0.90 | IOTC: Western Indian Ocean (Seychelles, Somali Current, Mozambique) |
| | | $(92^\circ, -6^\circ)$ | $(22^\circ, 12^\circ)$ | 0.75 | IOTC: Eastern Indian Ocean (Bay of Bengal, Sumatra upwelling) |
| | | $(-25^\circ, 2^\circ)$ | $(26^\circ, 13^\circ)$ | 0.70 | ICCAT: Tropical Atlantic (Gulf of Guinea, Equatorial Current) |
| | | $(148^\circ, -14^\circ)$ | $(28^\circ, 12^\circ)$ | 0.80 | Southwestern Pacific / Coral Sea (Queensland pelagic margin) |
| **Bigeye Tuna** | `BET` | $(160^\circ, 2^\circ)$ | $(36^\circ, 16^\circ)$ | 0.95 | WCPFC: Central/Western Equatorial Pacific (Line Islands, Kiribati) |
| | | $(-105^\circ, 0^\circ)$ | $(32^\circ, 15^\circ)$ | 0.90 | IATTC: Eastern Equatorial Cold Tongue (Galapagos to 110°W front) |
| | | $(75^\circ, -5^\circ)$ | $(32^\circ, 16^\circ)$ | 0.85 | IOTC: Central Equatorial Indian Ocean (Chagos Archipelago ridge) |
| | | $(-28^\circ, 0^\circ)$ | $(30^\circ, 15^\circ)$ | 0.80 | ICCAT: Equatorial Atlantic (Mid-Atlantic Ridge, Romanche Fracture) |
| | | $(165^\circ, 28^\circ)$ | $(32^\circ, 12^\circ)$ | 0.65 | North Pacific Subtropical Front (Kuroshio Extension / Hawaii grounds) |
| | | $(-120^\circ, -18^\circ)$ | $(30^\circ, 12^\circ)$ | 0.60 | Southeastern Pacific Subtropical Transition (French Polynesia / Peru) |
| **Albacore Tuna** | `ALB` | $(165^\circ, -28^\circ)$ | $(38^\circ, 12^\circ)$ | 1.00 | South Pacific Subtropical Gyre (New Caledonia, Fiji, Tonga, Cook Islands) |
| | | $(165^\circ, 34^\circ)$ | $(38^\circ, 12^\circ)$ | 0.85 | North Pacific Transition Zone (Kuroshio Extension to Midway / Hawaii) |
| | | $(-135^\circ, 42^\circ)$ | $(30^\circ, 10^\circ)$ | 0.75 | Northeast Pacific Subarctic Front (California Current to Oregon/WA/BC) |
| | | $(75^\circ, -30^\circ)$ | $(36^\circ, 12^\circ)$ | 0.80 | Southern Indian Ocean Subtropical Gyre (Madagascar to W. Australia) |
| | | $(-35^\circ, 38^\circ)$ | $(32^\circ, 12^\circ)$ | 0.75 | North Atlantic (Bay of Biscay, Azores, Canary Current, Grand Banks) |
| | | $(-25^\circ, -28^\circ)$ | $(30^\circ, 12^\circ)$ | 0.70 | South Atlantic Subtropical Gyre (Brazil-Malvinas confluence to Benguela) |
| | | $(15^\circ, 38^\circ)$ | $(15^\circ, 6^\circ)$ | 0.65 | Mediterranean Sea (Western & Central Mediterranean isolated stock) |
| **Swordfish** | `SWO` | $(155^\circ, 32^\circ)$ | $(38^\circ, 15^\circ)$ | 0.85 | Northwest Pacific Frontal Zone (Kuroshio-Oyashio confluence) |
| | | $(-85^\circ, -18^\circ)$ | $(28^\circ, 16^\circ)$ | 0.80 | Eastern South Pacific (Humboldt Current upwelling, northern Chile/Peru) |
| | | $(-65^\circ, 36^\circ)$ | $(30^\circ, 14^\circ)$ | 0.80 | Northwest Atlantic (Gulf Stream thermal wall, Charleston Bump) |
| | | $(48^\circ, -25^\circ)$ | $(30^\circ, 15^\circ)$ | 0.75 | Southwest Indian Ocean (Madagascar Ridge, Mozambique, Agulhas) |
| | | $(158^\circ, -28^\circ)$ | $(30^\circ, 14^\circ)$ | 0.75 | Southwest Pacific (East Australian Current, Lord Howe Rise, Tasman Sea) |
| | | $(18^\circ, 36^\circ)$ | $(16^\circ, 8^\circ)$ | 0.70 | Mediterranean Sea (Strait of Sicily, Ionian Sea, Tyrrhenian Sea) |
| | | $(-30^\circ, 12^\circ)$ | $(32^\circ, 16^\circ)$ | 0.70 | Central Tropical Atlantic (North Equatorial Current / MAR) |
| **Pelagic Sharks** | `SHK` | $(160^\circ, 6^\circ)$ | $(42^\circ, 18^\circ)$ | 0.85 | Central Pacific Longline Bycatch Corridor (Palmyra, Kiribati) |
| | | $(-95^\circ, 4^\circ)$ | $(32^\circ, 16^\circ)$ | 0.85 | Eastern Tropical Pacific Marine Corridor (Cocos-Galapagos swimway) |
| | | $(55^\circ, -4^\circ)$ | $(35^\circ, 18^\circ)$ | 0.80 | Western Indian Ocean (Seychelles, Mascarene Plateau, Mozambique) |
| | | $(-40^\circ, 32^\circ)$ | $(36^\circ, 16^\circ)$ | 0.75 | North Atlantic Pelagic Convergence (Azores / Sargasso Sea nursery) |
| | | $(-22^\circ, -14^\circ)$ | $(32^\circ, 16^\circ)$ | 0.70 | South Atlantic Tropical Belt (Ascension Island, Mid-Atlantic Ridge) |
| | | $(95^\circ, -12^\circ)$ | $(30^\circ, 16^\circ)$ | 0.70 | Eastern Indian Ocean (Java Trench, Cocos-Keeling basin) |
| | | $(150^\circ, -22^\circ)$ | $(35^\circ, 16^\circ)$ | 0.70 | Coral Sea & Southwestern Pacific longline grounds |
| **Marine Turtles** | `TUR` | $(140^\circ, 2^\circ)$ | $(32^\circ, 14^\circ)$ | 0.85 | Western Pacific / Coral Triangle Swimway (Bird's Head Papua, PNG) |
| | | $(-92^\circ, 4^\circ)$ | $(28^\circ, 12^\circ)$ | 0.85 | Eastern Pacific Leatherback Corridor (Costa Rica, Galapagos, Michoacán) |
| | | $(76^\circ, 6^\circ)$ | $(30^\circ, 14^\circ)$ | 0.75 | Northern Indian Ocean (Sri Lanka, Maldives, Andaman Sea foraging) |
| | | $(40^\circ, -16^\circ)$ | $(26^\circ, 12^\circ)$ | 0.70 | Southwest Indian Ocean (Mozambique Channel, Tongaland nesting) |
| | | $(-48^\circ, 6^\circ)$ | $(28^\circ, 12^\circ)$ | 0.75 | Western Atlantic Leatherback Belt (French Guiana, Suriname, Trinidad) |
| | | $(8^\circ, -1^\circ)$ | $(24^\circ, 12^\circ)$ | 0.70 | Eastern Atlantic Nesting Hub (Gabon, Equatorial Guinea, Gulf of Guinea) |
| | | $(160^\circ, 26^\circ)$ | $(30^\circ, 12^\circ)$ | 0.65 | North Pacific Loggerhead Kuroshio Highway (Japan to Baja California) |
| **Seabirds** | `SEA` | $(-40^\circ, -52^\circ)$ | $(38^\circ, 10^\circ)$ | 0.95 | Southwest Atlantic / South Georgia & Falklands (wandering albatross) |
| | | $(65^\circ, -48^\circ)$ | $(40^\circ, 10^\circ)$ | 0.90 | Southern Indian Ocean / Crozet & Kerguelen Islands (major petrels) |
| | | $(168^\circ, -48^\circ)$ | $(38^\circ, 10^\circ)$ | 0.90 | Southwest Pacific / Campbell, Auckland & Antipodes (NZ sub-Antarctic) |
| | | $(-12^\circ, -40^\circ)$ | $(32^\circ, 10^\circ)$ | 0.85 | South Atlantic / Tristan da Cunha & Gough Island (Tristan albatross) |
| | | $(175^\circ, 38^\circ)$ | $(35^\circ, 10^\circ)$ | 0.75 | North Pacific Central Transition / NWHI (Laysan & Black-footed) |
| | | $(148^\circ, 42^\circ)$ | $(30^\circ, 10^\circ)$ | 0.70 | Northwest Pacific / Kuroshio-Oyashio front (Short-tailed albatross) |

For each species $s$ and cell $g$, environmental carrying capacity scales strictly with regional suitability:

$$
K_{sg} = K_{0, s} \cdot S_{sg}
$$

For cells outside resident habitat ($S_{sg} \le 0.015$), $K_{sg} = 0.0$, initial virgin biomass $B_{sg0} = 0.0$, catch share is $0.0$, and biomass remains strictly $0.0$.

