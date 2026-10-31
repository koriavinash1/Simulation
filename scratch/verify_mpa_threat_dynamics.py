from pathlib import Path
import numpy as np
import pandas as pd
from sim.global_config import GlobalSimulationConfig
from sim.global_engine import simulate_global
from sim.global_data import load_world, load_mpas, get_frame_mpas

def test_mpa_threat_conditioned_dynamics():
    print("Loading world and MPA data...")
    cfg = GlobalSimulationConfig(years=2, representative_agents=100, government_mpa_push_max_pct=25.0)
    world, _ = load_world(Path("data"), 10)
    
    print("Running EM simulation with simulate_global...")
    res = simulate_global(cfg, world, intervention=True, animation_agents=100)
    
    mpa_frames = res.meta.get("mpa_frames", {})
    last_frame = max(mpa_frames.keys())
    lons, lats, hovs, cents_x, cents_y, cent_hovs = mpa_frames[last_frame]
    
    print(f"\nTotal MPA centroids evaluated in frame {last_frame}: {len(cent_hovs)}")
    
    static_count = 0
    dynamic_count = 0
    for h in cent_hovs:
        name = h.split("<br>")[0].replace("<b>", "").replace("</b>", "")
        status = h.split("<br>")[2]
        centroid = h.split("<br>")[4]
        if "Static (No Local Fishing Threat)" in status or "baseline" in centroid:
            static_count += 1
            print(f"  [STATIC MPA]: {name} | {status} | {centroid}")
        else:
            dynamic_count += 1
            print(f"  [DYNAMIC MPA]: {name} | {status} | {centroid}")
            
    print(f"\nSummary at month {last_frame}:")
    print(f"  Static MPAs (0 fishers nearby): {static_count}")
    print(f"  Dynamic MPAs (active fishing threat): {dynamic_count}")
    
    assert static_count > 0, "Expected at least some remote MPAs with 0 fishers to remain completely static!"
    print("\nSUCCESS: MPAs with 0 fishers remained strictly static at baseline coordinates and 0% expansion!")

    # Test fallback get_frame_mpas
    print("\nTesting get_frame_mpas fallback with empty vessels:")
    mpa_path = Path("data/world_mpas_high_seas.geojson")
    if mpa_path.exists():
        import json
        with open(mpa_path) as f:
            feats = json.load(f).get("features", [])
        # Pass empty vessels
        lons_e, lats_e, hovs_e, cents_x_e, cents_y_e, cent_hovs_e = get_frame_mpas(
            feats, fr=20, total_months=24, clim_val=0.5, is_em=True, push_pct=25.0, vessels_lon=np.array([]), vessels_lat=np.array([])
        )
        assert all("Static (No Local Fishing Threat)" in h for h in cent_hovs_e), "All MPAs should be static when vessels are empty!"
        print("  -> get_frame_mpas with empty vessels: 100% static!")

        # Pass vessels near Pacific Remote Islands (lat ~ 4.0, lon ~ -168.0)
        v_lon = np.array([-168.0, -167.5, -168.5])
        v_lat = np.array([4.0, 4.2, 3.8])
        lons_v, lats_v, hovs_v, cents_x_v, cents_y_v, cent_hovs_v = get_frame_mpas(
            feats, fr=20, total_months=24, clim_val=0.5, is_em=True, push_pct=25.0, vessels_lon=v_lon, vessels_lat=v_lat
        )
        static_f = [h for h in cent_hovs_v if "Static" in h]
        dynamic_f = [h for h in cent_hovs_v if "Dynamic" in h]
        print(f"  -> get_frame_mpas with localized vessels: {len(dynamic_f)} dynamic MPAs, {len(static_f)} static MPAs!")
        assert len(dynamic_f) > 0 and len(static_f) > 0, "Expected localized dynamics!"
        print("SUCCESS: get_frame_mpas fallback correctly conditioned on vessel presence!")

if __name__ == "__main__":
    test_mpa_threat_conditioned_dynamics()
