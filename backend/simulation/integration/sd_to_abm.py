"""System-dynamics to agent-based model bridge.

Pushes SD-computed tract-level variables into agent decision contexts
so that agents react to the macro environment.
"""

import pandas as pd

from simulation.core.state import SimulationState, TractState


def update_agents_from_sd(state: SimulationState) -> None:
    """Push SD-computed rent, crime, and transit to agent decision context.

    Updates:
        - Household rent_share recalculated from current tract rents.
        - Business revenue context updated with current crime/transit.
        - Drug market enforcement context refreshed.

    Mutations are in-place on agent DataFrames.
    """
    tracts: dict[str, TractState] = state.tracts

    # Build lookup dicts for fast vectorized-style access
    tract_rent: dict[str, float] = {tid: t.median_rent for tid, t in tracts.items()}
    tract_enforcement: dict[str, float] = {tid: t.enforcement_level for tid, t in tracts.items()}
    tract_transit: dict[str, float] = {tid: t.transit_accessibility for tid, t in tracts.items()}
    tract_crime: dict[str, float] = {tid: t.crime_incidents for tid, t in tracts.items()}

    # ----- Households: update rent_share from current rents -----
    hh: pd.DataFrame | None = state.agents.households
    if hh is not None and not hh.empty:
        hh["rent_share"] = hh.apply(
            lambda row: min(
                1.0,
                tract_rent.get(row["tract_id"], 2500.0) * 12.0 / max(row["income"], 1.0),
            ),
            axis=1,
        )

    # ----- Businesses: no direct column to update, but context is -----
    # available in tract_data used by the business agent module.
    # This is a passthrough; the business agent reads tracts directly.

    # ----- Drug market: no direct column update needed -----
    # Enforcement level is read from tracts by the drug_market module.
