"""Offline historical context; this is not a fitted longline price series.

Values are rounded nominal global capture first-sale values, not seafood exports
or capture-plus-aquaculture totals. Cross-edition revisions and coverage differ.
See docs/MODEL_CORRECTIONS.md for sources and limitations.
"""

CAPTURE_VALUE_HISTORY = (
    (2018, 151.0, "https://doi.org/10.4060/ca9229en"),
    (2020, 141.0, "https://www.fao.org/4/cc0461en/online/sofia/2022/world-fisheries-aquaculture.html"),
    (2022, 159.0, "https://doi.org/10.4060/cd0683en"),
)

# Endpoint CAGR avoids extrapolating the pandemic rebound alone. Used as a
# provisional nominal price prior under approximately stable reference volume.
HISTORICAL_NOMINAL_VALUE_CAGR = (CAPTURE_VALUE_HISTORY[-1][1] / CAPTURE_VALUE_HISTORY[0][1]) ** (
    1 / (CAPTURE_VALUE_HISTORY[-1][0] - CAPTURE_VALUE_HISTORY[0][0])) - 1


def nominal_price_growth(real_growth: float, inflation: float) -> float:
    """Compose a planning assumption in real terms with its nominal deflator."""
    if real_growth <= -1 or inflation <= -1:
        raise ValueError("Real growth and inflation must exceed -100%")
    return (1 + real_growth) * (1 + inflation) - 1


# User-requested positive-real-growth planning scenario, independent of the
# historical nominal proxy above. This is an assumption, not an empirical fit.
DEFAULT_REAL_PRICE_GROWTH = 0.015
DEFAULT_INFLATION_RATE = 0.022
DEFAULT_NOMINAL_PRICE_GROWTH = nominal_price_growth(DEFAULT_REAL_PRICE_GROWTH, DEFAULT_INFLATION_RATE)
