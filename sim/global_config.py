"""Backward-compatibility module re-exporting merged configurations from sim.config."""
from __future__ import annotations
from .config import (
    SpeciesConfig,
    DEFAULT_SPECIES,
    GlobalSimulationConfig,
    FleetClass,
    DEFAULT_FLEET_CLASSES,
    SimulationConfig,
    DEFAULT_NOMINAL_PRICE_GROWTH,
    DEFAULT_INFLATION_RATE,
)

__all__ = [
    "SpeciesConfig",
    "DEFAULT_SPECIES",
    "GlobalSimulationConfig",
    "FleetClass",
    "DEFAULT_FLEET_CLASSES",
    "SimulationConfig",
    "DEFAULT_NOMINAL_PRICE_GROWTH",
    "DEFAULT_INFLATION_RATE",
]
