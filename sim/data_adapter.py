from __future__ import annotations
import numpy as np
import pandas as pd

REQUIRED_COLUMNS = {"region", "month", "fishing_hours", "mpa_exposure", "cpue_index"}


def demo_empirical_priors(n_regions: int = 8) -> pd.DataFrame:
    """Synthetic calibration priors shaped like GFW/RFMO inputs.

    IMPORTANT: these are demonstrative priors, not Global Fishing Watch observations.
    They intentionally encode concentrated effort, seasonality, heterogeneous MPA exposure,
    and heterogeneous CPUE so the simulator is usable before real datasets are loaded.
    """
    rows = []
    region_weights = np.array([0.30, 0.22, 0.16, 0.11, 0.08, 0.06, 0.04, 0.03])[:n_regions]
    region_weights = region_weights / region_weights.sum()
    base_cpue = np.linspace(1.18, 0.78, n_regions)
    mpa = np.array([0.03, 0.07, 0.12, 0.18, 0.05, 0.10, 0.20, 0.08])[:n_regions]
    for r in range(n_regions):
        for month in range(1, 13):
            seasonal = 1.0 + 0.18*np.sin((month-1)/12*2*np.pi + r*0.6)
            rows.append({
                "region": f"Region {r+1}",
                "month": month,
                "fishing_hours": 100000 * region_weights[r] * seasonal,
                "mpa_exposure": float(mpa[r]),
                "cpue_index": float(base_cpue[r] * (1 + 0.10*np.cos((month-1)/12*2*np.pi-r*0.35))),
            })
    return pd.DataFrame(rows)


def validate_priors(df: pd.DataFrame) -> tuple[bool, str]:
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        return False, f"Missing required columns: {', '.join(sorted(missing))}"
    if not df["month"].between(1, 12).all():
        return False, "month must be in 1..12"
    if (df[["fishing_hours", "mpa_exposure", "cpue_index"]] < 0).any().any():
        return False, "fishing_hours, mpa_exposure and cpue_index must be non-negative"
    return True, "OK"


def priors_to_arrays(df: pd.DataFrame, n_regions: int):
    regions = [f"Region {i+1}" for i in range(n_regions)]
    full = pd.MultiIndex.from_product([regions, range(1,13)], names=["region", "month"]).to_frame(index=False)
    x = full.merge(df, on=["region", "month"], how="left")
    x["fishing_hours"] = x["fishing_hours"].fillna(0.0)
    x["mpa_exposure"] = x.groupby("region")["mpa_exposure"].transform(lambda s: s.fillna(s.mean())).fillna(0.0)
    x["cpue_index"] = x.groupby("region")["cpue_index"].transform(lambda s: s.fillna(s.mean())).fillna(1.0)

    effort = x.pivot(index="month", columns="region", values="fishing_hours").reindex(columns=regions).values
    effort = np.maximum(effort, 1e-9)
    effort = effort / effort.sum(axis=1, keepdims=True)
    mpa = x.groupby("region")["mpa_exposure"].mean().reindex(regions).fillna(0).values
    cpue = x.pivot(index="month", columns="region", values="cpue_index").reindex(columns=regions).fillna(1.0).values
    return effort, mpa, cpue
