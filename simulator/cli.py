from __future__ import annotations

import argparse
import json
from pathlib import Path

from .config import BlueFinanceConfig, SimulationConfig
from .engine import run_paired_simulation
from .reporting import build_horizon_table


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Run the tuna fisheries Monte Carlo simulator")
    p.add_argument("--years", type=int, default=30)
    p.add_argument("--replicates", type=int, default=100)
    p.add_argument("--vessels", type=int, default=7000)
    p.add_argument("--seed", type=int, default=20261107)
    p.add_argument("--em-adoption", type=float, default=0.30)
    p.add_argument("--premium", type=float, default=0.05)
    p.add_argument("--awareness", type=float, default=0.55)
    p.add_argument("--bond-size", type=float, default=15.0, help="Blue-finance pool, US$m")
    p.add_argument("--no-blue-finance", action="store_true")
    p.add_argument("--output", default="outputs/cli_run")
    return p


def main() -> None:
    args = parser().parse_args()
    blue = BlueFinanceConfig(enabled=not args.no_blue_finance, bond_size_musd=args.bond_size)
    cfg = SimulationConfig(
        years=args.years,
        n_replicates=args.replicates,
        n_vessels=args.vessels,
        seed=args.seed,
        initial_em_adoption=args.em_adoption,
        max_verified_premium=args.premium,
        awareness_campaign_strength=args.awareness,
        blue_finance=blue,
    )
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    result = run_paired_simulation(cfg)
    result["summary"].to_csv(out / "summary_timeseries.csv", index=False)
    result["final"].to_csv(out / "final_comparison.csv", index=False)
    build_horizon_table(result).to_csv(out / "horizon_outcomes.csv", index=False)
    (out / "config.json").write_text(json.dumps(result["config"], indent=2), encoding="utf-8")
    print(f"Wrote outputs to {out}")


if __name__ == "__main__":
    main()
