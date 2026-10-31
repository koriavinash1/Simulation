# Biological Submodel & Regional Biogeography

## 1. Regional Biogeography vs. Global Ubiquity

In realistic pelagic fisheries oceanography, **fish species are not globally ubiquitous**. Highly migratory tuna and billfish species are strictly governed by:
1. **Physiological Thermal Envelopes:** Sea Surface Temperatures (SST) and thermocline structure.
2. **Ocean Basins & Regional Fisheries Management Organizations (RFMOs):**
   - **WCPFC (Western & Central Pacific Fisheries Commission):** The world's largest tuna fishery (~60% of global Yellowfin and Skipjack catch), centered on the Western Pacific Warm Pool and Coral Sea.
   - **IATTC (Inter-American Tropical Tuna Commission):** Eastern Tropical Pacific (ETP) upwelling zones, Costa Rica Dome, and Galápagos archipelago.
   - **IOTC (Indian Ocean Tuna Commission):** Western Indian Ocean (Seychelles, Mozambique Channel) and Eastern Indian Ocean upwelling.
   - **ICCAT (International Commission for the Conservation of Atlantic Tunas):** Gulf of Guinea equatorial belt, Caribbean, and central tropical Atlantic.
   - **CCSBT (Commission for the Conservation of Southern Bluefin Tuna):** High-latitude Southern Ocean temperate belts.

In the simulator, species habitat suitability $S_{sg} \in [0, 1]$ is calibrated using real coordinate centers, thermal drop-offs, and latitudinal boundaries. **Cells outside a species' physiological range have strictly $S_{sg} = 0.0$, carrying capacity $K_{sg} = 0.0$, initial biomass $B_{sg0} = 0.0$, and zero vessel catch.**

---

## 2. Calibrated Species Profiles & Latitudinal Bounds

| Species | Code | Role | Thermal & Latitudinal Range | Core RFMO Ocean Basins & Habitat Centroids |
|:---|:---:|:---:|:---|:---|
| **Yellowfin Tuna** (*Thunnus albacares*) | `YFT` | Target | **Strictly Tropical/Subtropical:** $|\text{lat}| \le 35^\circ$ ($0.0$ at $|\text{lat}| \ge 36^\circ$). Requires SST $> 18^\circ$C. | **WCPFC:** Warm Pool (155°E, 4°N) & Coral Sea (152°E, -16°S)<br>**IATTC:** Eastern Tropical Pacific (-115°W, 8°N)<br>**IOTC:** Western Indian Ocean (58°E, -4°S) & Eastern IO (92°E, 6°N)<br>**ICCAT:** Tropical Atlantic (-25°W, 2°N) & Gulf of Guinea (2°E, 1°S) |
| **Bigeye Tuna** (*Thunnus obesus*) | `BET` | Target | **Tropical/Subtropical Deep-Diver:** $|\text{lat}| \le 40^\circ$ ($0.0$ at $|\text{lat}| \ge 42^\circ$). Tolerates deep low-oxygen zones. | Central Pacific Warm Pool (165°W, 6°N & 175°E, -6°S), Eastern Pacific (-110°W, -4°S), Central Indian Ocean (75°E, -8°S), Equatorial Atlantic (-20°W, 0°N). |
| **Albacore Tuna** (*Thunnus alalunga*) | `ALB` | Target | **Temperate/Subtropical Gyres:** $10^\circ \le |\text{lat}| \le 48^\circ$ ($0.0$ at $|\text{lat}| \le 8^\circ$ and $|\text{lat}| \ge 50^\circ$). Avoids warm doldrums. | North Pacific Gyre (160°E, 32°N), South Pacific (170°W, -30°S), North Atlantic (-40°W, 35°N), South Atlantic (-15°W, -28°S), South Indian Ocean (80°E, -32°S). |
| **Swordfish** (*Xiphias gladius*) | `SWO` | Target | **Broad Pelagic Predator:** $|\text{lat}| \le 45^\circ$ ($0.0$ at $|\text{lat}| \ge 48^\circ$). Diel vertical migrant. | Subtropical frontal zones, Mediterranean, Kuroshio/California currents, Humboldt current (-85°W, -20°S), Agulhas current (35°E, -32°S). |
| **Silky & Pelagic Sharks** (*Carcharhinus falciformis*) | `SHK` | Bycatch | **Circumtropical Epipelagic:** $|\text{lat}| \le 42^\circ$ ($0.0$ at $|\text{lat}| \ge 45^\circ$). Frequents FADs and shelf edges. | Tropical Pacific (-140°W, 5°N & 150°E, 0°N), Indian Ocean (65°E, 2°S), Tropical Atlantic (-30°W, 8°N). |
| **Marine Turtles** (*Cheloniidae*) | `TUR` | Bycatch | **Tropical/Subtropical Coastal-Pelagic:** $|\text{lat}| \le 35^\circ$ ($0.0$ at $|\text{lat}| \ge 36^\circ$). Nesting beach corridors. | Indo-Pacific (145°E, -8°S & 110°E, 5°N), Costa Rica / ETP (-95°W, 10°N), Caribbean / Atlantic (-50°W, 14°N), Mozambique Channel (42°E, -18°S). |
| **Seabirds** (*Diomedeidae*) | `SEA` | Bycatch | **High-Latitude Wind Belts:** $20^\circ \le |\text{lat}| \le 58^\circ$ ($0.0$ in the equatorial belt $|\text{lat}| \le 16^\circ$). | Southern Ocean Roaring Forties (-120°W, -48°S; 40°E, -46°S; 140°E, -44°S) and North Pacific wind belts (170°E, 45°N; -150°W, 46°N). |

---

## 3. Mathematical Population Formulations

### Spatial Carrying Capacity
Carrying capacity scales strictly with regional suitability:

$$
K_{sg} = K_{0, s} \cdot S_{sg}
$$

For cells outside species habitat ($S_{sg} \le 0.015$), $K_{sg} = 0.0$ and standing biomass $B_{sgt} = 0.0$.

### Monthly Logistic Surplus Production
Within resident cells ($S_{sg} > 0.015$), surplus biological growth follows the Schaefer model:

$$
\text{Growth}_{sgt} = \frac{r_s}{12} B_{sgt} \left(1.0 - \frac{B_{sgt}}{\max(K_{sg}, 0.08)}\right)
$$

### Target Harvest & Bycatch Extractions
Vessel catch share is determined by local species abundance and regional suitability:

$$
\text{Share}_{sg} = \begin{cases} S_{sg} & \text{if } S_{sg} > 0.015 \\ 0.0 & \text{otherwise} \end{cases}
$$

$$
\text{Harvest}_{sgt} = \left(\frac{\text{scale}_{\text{harv}}}{12}\right) \cdot \left(\frac{\sum_{i \in g} C_{isgt} W_i}{\sum_h \sum_{i \in h} C_{isgt} W_i}\right) \cdot G \cdot \text{realized\_cell\_protection}(g, t)
$$

For incidental bycatch species (`SHK`, `TUR`, `SEA`), harvest is scaled by $0.45 \cdot \text{Harvest}_{sgt}$.

### Resident Basin Migration & Biological Spillover
- **Basin Equilibrium Pull:**
  $$
  \text{Migration}_{sgt} = \frac{m_s}{12} \left(\bar{B}_{s, \text{resident}} - B_{sgt}\right) \cdot S_{sg}
  $$
- **Sanctuary Spillover Export:**
  $$
  \text{SpillGain}_{sgt} = \frac{S_{\text{rate}}}{12} \cdot \text{Ring}(g) \cdot \max\left(0, \bar{B}_{s, \text{reserves}} - 0.85 \bar{B}_{s, \text{resident}}\right) \cdot S_{sg}
  $$
- **Sanctuary Biomass Export Loss:**
  $$
  \text{SpillLoss}_{sgt} = \frac{S_{\text{rate}}}{12} \cdot \text{effective\_mpa}(g, t) \cdot 0.35 \cdot B_{sgt}
  $$

---

## 4. Coupled Ecological Indicators

### Species Population Health Index
The annual species health ratio is averaged strictly across resident habitat cells ($S_{sg} > 0.015$):

$$
\text{Ratio}_s(y) = \frac{\sum_{g \in \text{resident}} B_{sg}(y)}{\sum_{g \in \text{resident}} B_{sg0}}
$$

Status categories:
- $\text{Ratio} \ge 0.80$: **Healthy**
- $0.50 \le \text{Ratio} < 0.80$: **Stressed**
- $\text{threshold}_{\text{dep}} \le \text{Ratio} < 0.50$: **Depleted**
- $\text{threshold}_{\text{ext}} \le \text{Ratio} < \text{threshold}_{\text{dep}}$: **Severely depleted**
- $\text{Ratio} < \text{threshold}_{\text{ext}}$: **Local functional extinction risk**
