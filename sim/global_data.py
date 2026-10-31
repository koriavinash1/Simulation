from __future__ import annotations
import math
from pathlib import Path
import numpy as np
import pandas as pd

# Coarse ocean-basin priors used only when a preprocessed open-data pack is not present.
# They are deliberately labelled as fallback priors in the app/documentation.
BASINS = [
    ("WCPFC-West", 145, 5, 1.30, 0.09),
    ("WCPFC-East", -165, 2, 1.05, 0.08),
    ("IATTC", -120, 5, 1.00, 0.07),
    ("IOTC-West", 55, -8, 0.95, 0.10),
    ("IOTC-East", 90, -12, 1.00, 0.09),
    ("Atlantic-N", -40, 22, 0.78, 0.08),
    ("Atlantic-S", -25, -20, 0.72, 0.07),
    ("Southern", 80, -38, 0.56, 0.05),
]

SPECIES_CENTERS = {
    # 1. YFT (Yellowfin Tuna, Thunnus albacares): Strictly tropical and warm-subtropical epipelagic predator
    # Confined to tropical ocean basins across WCPFC, IATTC, IOTC, and ICCAT (|lat| <= 35°, 0.0 at |lat| >= 36°)
    "YFT": [
        (155, 4, 34, 14, 1.00),     # WCPFC: Western & Central Pacific Warm Pool (Coral Sea, Micronesia, PNG)
        (-115, 2, 30, 12, 0.85),    # IATTC: Eastern Tropical Pacific Upwelling (Costa Rica Dome, Galapagos Front)
        (58, -4, 25, 14, 0.90),     # IOTC: Western Indian Ocean (Seychelles Bank, Somali Current, Mozambique)
        (92, -6, 22, 12, 0.75),     # IOTC: Eastern Indian Ocean (Bay of Bengal, Sumatra upwelling)
        (-25, 2, 26, 13, 0.70),     # ICCAT: Tropical Atlantic (Gulf of Guinea, North Equatorial Countercurrent)
        (148, -14, 28, 12, 0.80),   # Southwestern Pacific / Coral Sea (Queensland pelagic shelf)
    ],
    # 2. BET (Bigeye Tuna, Thunnus obesus): Mesopelagic deep diver foraging beneath thermocline (|lat| <= 40°)
    # Feeds in cold, low-oxygen waters (13°-22°C down to 500m) by day, ascending to surface at night
    "BET": [
        (160, 2, 36, 16, 0.95),     # WCPFC: Central/Western Equatorial Pacific (Line Islands, Kiribati)
        (-105, 0, 32, 15, 0.90),    # IATTC: Eastern Equatorial Cold Tongue (Galapagos to 110°W equatorial front)
        (75, -5, 32, 16, 0.85),     # IOTC: Central Equatorial Indian Ocean (Chagos Archipelago / Maldives ridge)
        (-28, 0, 30, 15, 0.80),     # ICCAT: Equatorial Atlantic (Mid-Atlantic Ridge, Romanche Fracture Zone)
        (165, 28, 32, 12, 0.65),    # North Pacific Subtropical Front (Kuroshio Extension / Hawaii grounds)
        (-120, -18, 30, 12, 0.60),  # Southeastern Pacific Subtropical Transition (French Polynesia / Peru offshore)
    ],
    # 3. ALB (Albacore Tuna, Thunnus alalunga): Temperate and subtropical gyres (10° <= |lat| <= 50°)
    # Actively avoids warm equatorial surface waters (SST > 28°C); partitioned into distinct, non-mixing stocks
    "ALB": [
        (165, -28, 38, 12, 1.00),   # South Pacific Subtropical Gyre (New Caledonia, Fiji, Tonga, Cook Islands)
        (165, 34, 38, 12, 0.85),    # North Pacific Transition Zone (Kuroshio Extension to Midway / Hawaii)
        (-135, 42, 30, 10, 0.75),   # Northeast Pacific Subarctic Front (California Current to Oregon / Washington / BC)
        (75, -30, 36, 12, 0.80),    # Southern Indian Ocean Subtropical Gyre (Madagascar to Western Australia)
        (-35, 38, 32, 12, 0.75),    # North Atlantic (Bay of Biscay, Azores, Canary Current, Grand Banks)
        (-25, -28, 30, 12, 0.70),   # South Atlantic Subtropical Gyre (Brazil-Malvinas confluence to Benguela)
        (15, 38, 15, 6, 0.65),      # Mediterranean Sea (Western & Central Mediterranean isolated resident stock)
    ],
    # 4. SWO (Swordfish, Xiphias gladius): Cosmopolitan apex predator associated with fronts and seamounts (|lat| <= 45°)
    # Wide diel vertical migrations down to 650m; concentrated along major oceanic boundary currents
    "SWO": [
        (155, 32, 38, 15, 0.85),    # Northwest Pacific Frontal Zone (Kuroshio-Oyashio confluence)
        (-85, -18, 28, 16, 0.80),   # Eastern South Pacific (Humboldt Current upwelling, northern Chile / Peru)
        (-65, 36, 30, 14, 0.80),    # Northwest Atlantic (Gulf Stream thermal wall, Charleston Bump, Grand Banks)
        (48, -25, 30, 15, 0.75),    # Southwest Indian Ocean (Madagascar Ridge, Mozambique Channel, Agulhas retroflection)
        (158, -28, 30, 14, 0.75),   # Southwest Pacific (East Australian Current, Lord Howe Rise, northern Tasman Sea)
        (18, 36, 16, 8, 0.70),      # Mediterranean Sea (Strait of Sicily, Ionian Sea, Tyrrhenian Sea)
        (-30, 12, 32, 16, 0.70),    # Central Tropical Atlantic (North Equatorial Current / Mid-Atlantic Ridge)
    ],
    # 5. SHK (Pelagic Sharks): Circumglobal pelagic in tropical and warm-temperate waters (|lat| <= 45°)
    # Silky and oceanic whitetip sharks in tropics; blue and shortfin mako sharks along temperate oceanic fronts
    "SHK": [
        (160, 6, 42, 18, 0.85),     # Central Pacific Longline Bycatch Corridor (Palmyra, Kiribati, Line Islands)
        (-95, 4, 32, 16, 0.85),     # Eastern Tropical Pacific Marine Corridor (Cocos-Galapagos-Malpelo swimway)
        (55, -4, 35, 18, 0.80),     # Western Indian Ocean (Seychelles, Mascarene Plateau, Mozambique Channel)
        (-40, 32, 36, 16, 0.75),    # North Atlantic Pelagic Convergence (Azores / Sargasso Sea blue shark nursery)
        (-22, -14, 32, 16, 0.70),   # South Atlantic Tropical Belt (Ascension Island, Mid-Atlantic Ridge)
        (95, -12, 30, 16, 0.70),    # Eastern Indian Ocean (Java Trench, Cocos-Keeling basin)
        (150, -22, 35, 16, 0.70),   # Coral Sea & Southwestern Pacific longline grounds
    ],
    # 6. TUR (Marine Turtles): Strictly tropical and warm-subtropical nesting and foraging belts (|lat| <= 35°)
    # Leatherback, loggerhead, and olive ridley trans-oceanic migration corridors and nesting nodes
    "TUR": [
        (140, 2, 32, 14, 0.85),     # Western Pacific / Coral Triangle Swimway (Bird's Head Papua, Solomon Sea, PNG)
        (-92, 4, 28, 12, 0.85),     # Eastern Pacific Leatherback Corridor (Las Baulas Costa Rica, Galapagos, Michoacán)
        (76, 6, 30, 14, 0.75),      # Northern Indian Ocean (Sri Lanka, Maldives, Andaman Sea foraging grounds)
        (40, -16, 26, 12, 0.70),    # Southwest Indian Ocean (Mozambique Channel, Tongaland nesting coast)
        (-48, 6, 28, 12, 0.75),     # Western Atlantic Leatherback Belt (French Guiana, Suriname, Trinidad)
        (8, -1, 24, 12, 0.70),      # Eastern Atlantic Nesting Hub (Gabon, Equatorial Guinea, Gulf of Guinea)
        (160, 26, 30, 12, 0.65),    # North Pacific Loggerhead Kuroshio Highway (Japan nesting to Baja California)
    ],
    # 7. SEA (Seabirds, e.g. Albatrosses & Petrels): High-latitude Southern Ocean Roaring Forties & North Pacific
    # Sub-Antarctic island breeding colonies and foraging grounds (35°S-60°S); completely absent in tropics (|lat| <= 16°)
    "SEA": [
        (-40, -52, 38, 10, 0.95),   # Southwest Atlantic / South Georgia & Falklands (wandering & black-browed albatrosses)
        (65, -48, 40, 10, 0.90),    # Southern Indian Ocean / Crozet & Kerguelen Islands (major petrel & albatross foraging)
        (168, -48, 38, 10, 0.90),   # Southwest Pacific / Campbell, Auckland & Antipodes (New Zealand sub-Antarctic colonies)
        (-12, -40, 32, 10, 0.85),   # South Atlantic / Tristan da Cunha & Gough Island (Tristan albatross, Atlantic yellow-nosed)
        (175, 38, 35, 10, 0.75),    # North Pacific Central Transition / NWHI (Laysan & Black-footed albatrosses)
        (148, 42, 30, 10, 0.70),    # Northwest Pacific / Kuroshio-Oyashio boundary (Short-tailed & Black-footed albatrosses)
    ],
}


def _wrap_lon_diff(a, b):
    d = abs(a - b)
    return min(d, 360 - d)


def _suitability(lon, lat, code):
    alat = abs(lat)
    # 1. Strict Latitudinal Cutoffs per Species Physiology
    if code == "YFT" and alat >= 36.0:
        return 0.0
    if code == "TUR" and alat >= 36.0:
        return 0.0
    if code == "BET" and alat >= 42.0:
        return 0.0
    if code == "ALB" and (alat >= 50.0 or alat <= 8.0):
        return 0.0
    if code == "SEA" and (alat <= 16.0 or alat >= 62.0):
        return 0.0
    if code == "SWO" and alat >= 48.0:
        return 0.0
    if code == "SHK" and alat >= 46.0:
        return 0.0

    # 2. Kernel Suitability Summation across Oceanographic Centers
    v = 0.0
    for cl, ct, slon, slat, w in SPECIES_CENTERS.get(code, []):
        dl = _wrap_lon_diff(lon, cl) / max(slon, 1)
        da = abs(lat - ct) / max(slat, 1)
        v += w * math.exp(-0.5 * (dl * dl + da * da))

    # 3. Species-Specific Biological Attenuation & Thermal Niche Shaping
    if code == "YFT":
        v *= math.exp(-0.5 * (max(0.0, alat - 24.0) / 4.5)**2)
    elif code == "TUR":
        v *= math.exp(-0.5 * (max(0.0, alat - 22.0) / 4.5)**2)
    elif code == "BET":
        v *= math.exp(-0.5 * (max(0.0, alat - 28.0) / 5.5)**2)
    elif code == "ALB":
        v *= (1.0 - math.exp(-0.5 * (alat / 7.0)**2))  # Smooth equatorial depression
    elif code == "SWO":
        v *= math.exp(-0.5 * (max(0.0, alat - 35.0) / 5.0)**2)  # Temperate tapering
    elif code == "SHK":
        v *= math.exp(-0.5 * (max(0.0, alat - 32.0) / 6.0)**2)  # Subtropical tapering
    elif code == "SEA":
        # Peaks strongly in the Roaring Forties (40°-55°S) and North Pacific (35°-50°N)
        v *= (1.0 - math.exp(-0.5 * (max(0.0, alat - 16.0) / 6.0)**2))

    return min(v, 1.0) if v > 0.015 else 0.0


def generate_fallback_world(grid_deg=10):
    # Ocean-like coarse cells: strictly exclude landmasses using Natural Earth geometry if available
    land_path = Path(__file__).resolve().parents[1] / "data" / "ne_110m_land.geojson"
    prep_land = None
    if land_path.exists():
        try:
            import json
            from shapely.geometry import shape, Point
            from shapely.ops import unary_union
            from shapely.prepared import prep
            with open(land_path, "r", encoding="utf-8") as f:
                geo = json.load(f)
            prep_land = prep(unary_union([shape(feat["geometry"]) for feat in geo["features"]]))
        except Exception:
            prep_land = None

    rows=[]
    for lat in np.arange(-55, 56, grid_deg):
        for lon in np.arange(-175, 176, grid_deg):
            if prep_land and prep_land.contains(Point(lon, lat)):
                continue
            basin_score=0.0
            basin_name="Other"
            for name, blon, blat, effort, mpa in BASINS:
                dl=_wrap_lon_diff(lon, blon)/50
                da=abs(lat-blat)/25
                s=effort*math.exp(-0.5*(dl*dl+da*da))
                if s>basin_score:
                    basin_score=s; basin_name=name
            if basin_score < 0.12:
                continue
            row={"cell_id":len(rows),"lon":float(lon),"lat":float(lat),"basin":basin_name,
                 "effort_prior":float(basin_score),"mpa_share":float(min(0.42,0.02+0.08*basin_score))}
            for code in SPECIES_CENTERS:
                row[f"suit_{code}"]=_suitability(lon,lat,code)
            rows.append(row)
    df=pd.DataFrame(rows)
    df["effort_prior"] /= df["effort_prior"].sum()
    return df


def load_world(data_dir: Path, grid_deg=10):
    p = data_dir / "processed" / "world_cells.parquet"
    if p.exists():
        return pd.read_parquet(p), "verified open-data pack (GFW/WDPA/Natural Earth)"
    return generate_fallback_world(grid_deg), "documented fallback priors"


def load_mpas(data_dir: Path):
    # Optional real polygon layer. The app works without geopandas; if present it is read by the UI.
    for name in ["marine_mpas.geojson", "marine_mpas.json"]:
        p=data_dir/"processed"/name
        if p.exists():
            return p
    return None


def get_frame_mpas(features, fr, total_months, clim_val, is_em, push_pct, prep_land=None, vessels_lon=None, vessels_lat=None):
    try:
        from shapely.geometry import Point
    except ImportError:
        Point = None

    prog = fr / max(total_months - 1, 1)

    all_lons, all_lats, line_hovers = [], [], []
    cent_lons, cent_lats, cent_hovers = [], [], []

    for k, feat in enumerate(features):
        geom_data = feat.get("geometry", {})
        props = feat.get("properties", {})
        name = props.get("name", "MPA")
        country = props.get("country", "N/A")
        desig = props.get("designation", "Marine Reserve")
        base_area = props.get("area_km2", 0)

        polys = geom_data.get("coordinates", []) if geom_data.get("type") == "MultiPolygon" else [geom_data.get("coordinates", [])]
        raw_pts = [pt for poly in polys if poly and poly[0] for pt in poly[0]]
        if not raw_pts:
            continue
        c_lon = float(np.mean([p[0] for p in raw_pts]))
        c_lat = float(np.mean([p[1] for p in raw_pts]))

        # Check local fisher presence if vessel coordinates are provided
        has_local_fishers = True
        n_near = 0
        if vessels_lon is not None and len(vessels_lon) > 0 and vessels_lat is not None:
            v_dists = np.hypot(((vessels_lon - c_lon + 180) % 360) - 180, vessels_lat - c_lat)
            n_near = int(np.sum(v_dists <= 18.0))
            has_local_fishers = (n_near > 0)

        if is_em and has_local_fishers:
            threat_scale = min(1.0, max(n_near / 4.0, 0.25)) if vessels_lon is not None else 1.0
            exp = 1.0 + (push_pct / 100.0) * prog * 0.45 * threat_scale
            lat_dir = 1.0 if c_lat >= 0 else -1.0
            dlat = lat_dir * (clim_val * 6.5) * (0.25 + 0.75 * prog) * threat_scale
            dlon = float(np.sin(prog * np.pi + k) * 1.8 * prog * threat_scale)
            status_txt = "🟢 Dynamic Climate-Smart MPA"
            cent_txt = f"{c_lat + dlat:.1f}°, {c_lon + dlon:.1f}°"
        else:
            exp = 1.0
            dlat, dlon = 0.0, 0.0
            status_txt = "⚪ Static (No Local Fishing Threat)" if is_em else "⚪ Static Protected Area"
            cent_txt = f"{c_lat:.1f}°, {c_lon:.1f}° (baseline)"

        curr_area = int(base_area * (exp ** 2))
        dyn_ht = f"<b>{name}</b><br>Country: {country}<br>Status: {status_txt}<br>Area: {curr_area:,} km² ({'+' if exp>1 else ''}{(exp**2 - 1)*100:.1f}%)<br>Centroid: {cent_txt}"

        lons_feat, lats_feat = [], []
        for poly in polys:
            if not poly or not poly[0]:
                continue
            ext_ring = poly[0]
            for pt in ext_ring:
                nx = c_lon + dlon + (pt[0] - c_lon) * exp
                ny = c_lat + dlat + (pt[1] - c_lat) * exp
                nx = ((nx + 180) % 360) - 180
                ny = float(np.clip(ny, -60, 60))
                if prep_land and Point is not None and prep_land.contains(Point(nx, ny)):
                    nx = c_lon + 0.6 * (nx - c_lon)
                    ny = c_lat + 0.6 * (ny - c_lat)
                all_lons.append(nx)
                all_lats.append(ny)
                line_hovers.append(dyn_ht)
                lons_feat.append(nx)
                lats_feat.append(ny)
            all_lons.append(None)
            all_lats.append(None)
            line_hovers.append("")

        if lons_feat and lats_feat:
            cent_lons.append(float(np.mean(lons_feat)))
            cent_lats.append(float(np.mean(lats_feat)))
            cent_hovers.append(dyn_ht)

    return all_lons, all_lats, line_hovers, cent_lons, cent_lats, cent_hovers
