from __future__ import annotations

import pandas as pd


def build_horizon_table(results: dict) -> pd.DataFrame:
    """Return compact BAU/intervention comparisons at short, medium and long horizons."""
    summary = results["summary"]
    max_year = int(summary["year"].max())
    horizons = sorted(set([min(3, max_year), min(10, max_year), max_year]))
    metrics = [
        "profit_musd",
        "cumulative_profit_musd",
        "biomass_ratio",
        "cpue_index",
        "catch_t",
        "iuu",
        "adoption",
        "household_resilience_index",
        "blue_finance_reach",
    ]
    rows: list[dict] = []
    for year in horizons:
        for metric in metrics:
            d = summary[(summary.year == year) & (summary.metric == metric)]
            if d.empty:
                continue
            vals = d.set_index("scenario")["median"]
            bau = float(vals.get("BAU", float("nan")))
            intervention = float(vals.get("INTERVENTION", float("nan")))
            rows.append(
                {
                    "year": year,
                    "metric": metric,
                    "bau_median": bau,
                    "intervention_median": intervention,
                    "delta": intervention - bau,
                }
            )
    return pd.DataFrame(rows)
