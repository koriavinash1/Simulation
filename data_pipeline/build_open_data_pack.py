"""Build a local simulation-ready open-data pack.

This script intentionally does not scrape or redistribute datasets whose terms may require
registration, tokens or commercial permission. It normalises authorised local exports.

Examples:
  python data_pipeline/build_open_data_pack.py --world-cells my_world_cells.csv
  python data_pipeline/build_open_data_pack.py --mpa-geojson WDPA_marine.geojson

Required world-cell columns: lon, lat, effort_prior, mpa_share and suit_YFT/BET/ALB/SWO/SHK/TUR/SEA.
"""
from pathlib import Path
import argparse, shutil
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"data"/"processed"; OUT.mkdir(parents=True,exist_ok=True)

p=argparse.ArgumentParser(description="Build or fetch simulation-ready open-data pack.")
p.add_argument("--world-cells", help="Path to local world cells CSV/Parquet")
p.add_argument("--mpa-geojson", help="Path to local MPA GeoJSON")
p.add_argument("--fetch-realistic", action="store_true", help="Compile authoritative GFW/WDPA/Natural Earth data pack")
a=p.parse_args()

if a.fetch_realistic:
    import sys
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from data_pipeline.fetch_and_build_data_pack import build_data_pack
    build_data_pack()
elif a.world_cells:
    src=Path(a.world_cells)
    df=pd.read_csv(src) if src.suffix.lower()==".csv" else pd.read_parquet(src)
    required={"lon","lat","effort_prior","mpa_share","suit_YFT","suit_BET","suit_ALB","suit_SWO","suit_SHK","suit_TUR","suit_SEA"}
    missing=required-set(df.columns)
    if missing: raise SystemExit(f"Missing columns: {sorted(missing)}")
    df.reset_index(drop=True,inplace=True); df["cell_id"]=range(len(df))
    df.to_parquet(OUT/"world_cells.parquet",index=False)
    print("Wrote",OUT/"world_cells.parquet")
if a.mpa_geojson:
    shutil.copy2(a.mpa_geojson,OUT/"marine_mpas.geojson")
    print("Wrote",OUT/"marine_mpas.geojson")
if not a.world_cells and not a.mpa_geojson and not a.fetch_realistic:
    p.print_help()
