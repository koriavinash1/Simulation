"""Shared extraction accounting for the spatial and regional models."""
from __future__ import annotations

import numpy as np


def allocate_removals(amount, region, weights, biomass, tonnes_per_index):
    """Cap catch at available stock; use the same catch for sales and removals."""
    requested = np.bincount(region, weights=amount * weights, minlength=len(biomass))
    available = biomass * tonnes_per_index
    fraction = np.minimum(1.0, np.divide(available, requested,
                         out=np.ones_like(available), where=requested > 0))
    realized = amount * fraction[region]
    removed = np.bincount(region, weights=realized * weights, minlength=len(biomass))
    return realized, np.divide(removed, tonnes_per_index,
                              out=np.zeros_like(removed), where=tonnes_per_index > 0)


def conservative_exchange(biomass, capacity, tonnes_per_index, edges, rate):
    """Move physical biomass along habitat edges without creating fish.

    Flux follows B/K differences. Rate is a monthly fraction, limited so a
    donor cannot export more than its available physical stock.
    """
    if not len(edges) or rate <= 0:
        return np.zeros_like(biomass)
    i, j = edges.T
    density = np.divide(biomass, capacity, out=np.zeros_like(biomass), where=capacity > 0)
    physical_capacity = capacity * tonnes_per_index
    flux = rate * (density[i] - density[j]) * np.minimum(physical_capacity[i], physical_capacity[j])
    donor = np.where(flux >= 0, i, j)
    receiver = np.where(flux >= 0, j, i)
    outgoing = np.bincount(donor, weights=np.abs(flux), minlength=len(biomass))
    factor = np.minimum(1.0, np.divide(biomass * tonnes_per_index, outgoing,
                        out=np.ones_like(outgoing), where=outgoing > 0))
    transfer = np.abs(flux) * factor[donor]
    incoming = np.bincount(receiver, weights=transfer, minlength=len(biomass))
    room = np.maximum(capacity - biomass, 0) * tonnes_per_index
    receiver_factor = np.minimum(1.0, np.divide(room, incoming,
                                 out=np.ones_like(room), where=incoming > 0))
    transfer *= receiver_factor[receiver]
    delta = (np.bincount(receiver, weights=transfer, minlength=len(biomass)) -
             np.bincount(donor, weights=transfer, minlength=len(biomass)))
    return np.divide(delta, tonnes_per_index, out=np.zeros_like(delta), where=tonnes_per_index > 0)


def monthly_stock_step(biomass, capacity, removals, growth_rate, exchange, climate_loss, noise):
    """Explicit monthly balance. Zero is absorbing without incoming migration."""
    growth = (growth_rate / 12) * biomass * (1 - np.divide(
        biomass, capacity, out=np.zeros_like(biomass), where=capacity > 0))
    updated = biomass + growth - removals + exchange - climate_loss + noise
    return np.where(capacity > 0, np.clip(updated, 0, capacity), 0)
