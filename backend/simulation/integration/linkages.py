"""Cross-system linkage computation.

Implements the feedback loops between housing, crime, transit, and density
that connect the system-dynamics and agent-based layers.
"""

import numpy as np

from simulation.core.config import SimulationConfig
from simulation.core.state import SimulationState, TractState


# Linkage strength parameters
HOUSING_MIGRATION_SENSITIVITY: float = 0.3
CRIME_BUSINESS_PENALTY: float = 0.02
TRANSIT_HOUSING_DEMAND_BOOST: float = 0.05
DENSITY_SERVICE_DEMAND_FACTOR: float = 0.001


def compute_cross_system_linkages(
    state: SimulationState,
    config: SimulationConfig,
    params: dict,
) -> None:
    """Compute and apply cross-system feedback linkages.

    Linkages:
        1. Housing price -> migration pressure: high prices push out low-income
           households by increasing rent_share and flagging wants_to_move.
        2. Crime -> business location: high crime reduces business survival
           via increased closure rate.
        3. Transit -> housing demand: good transit increases housing demand,
           putting upward pressure on rents/prices.
        4. Density -> service demand: more population requires more transit
           and public services.

    Mutations are in-place on *state.tracts*.
    """
    migration_sens: float = params.get("migration_sensitivity", HOUSING_MIGRATION_SENSITIVITY)
    crime_penalty: float = params.get("business_crime_penalty", -CRIME_BUSINESS_PENALTY)
    tracts: dict[str, TractState] = state.tracts

    # Compute Bay Area medians for relative comparisons
    rents: list[float] = [t.median_rent for t in tracts.values()]
    median_rent_bay: float = float(np.median(rents)) if rents else 2500.0

    populations: list[float] = [t.population for t in tracts.values()]
    median_pop_bay: float = float(np.median(populations)) if populations else 5000.0

    for tid, tract in tracts.items():
        # ----- 1. Housing price -> migration pressure -----
        rent_ratio: float = tract.median_rent / max(median_rent_bay, 1.0)
        if rent_ratio > 1.2:
            # Above-median rent tracts see population pressure downward
            pressure: float = (rent_ratio - 1.2) * migration_sens * 0.01
            tract.population = max(0.0, tract.population * (1.0 - pressure))
            tract.households = max(0.0, tract.households * (1.0 - pressure))

        # ----- 2. Crime -> business climate -----
        if tract.crime_incidents > 50:
            crime_impact: float = tract.crime_incidents * abs(crime_penalty) * 0.0001
            tract.business_closure_rate = min(
                1.0,
                tract.business_closure_rate + crime_impact,
            )

        # ----- 3. Transit -> housing demand -----
        if tract.transit_accessibility > 0.7:
            transit_premium: float = (
                (tract.transit_accessibility - 0.7)
                * TRANSIT_HOUSING_DEMAND_BOOST
            )
            tract.median_rent *= 1.0 + transit_premium
            tract.median_home_price *= 1.0 + transit_premium

        # ----- 4. Density -> service demand -----
        pop_ratio: float = tract.population / max(median_pop_bay, 1.0)
        if pop_ratio > 1.5:
            # High density tracts need more transit service (signal for policy)
            service_gap: float = (pop_ratio - 1.5) * DENSITY_SERVICE_DEMAND_FACTOR
            # Reduce accessibility slightly if service hasn't kept up
            tract.transit_accessibility = float(np.clip(
                tract.transit_accessibility - service_gap,
                0.0,
                1.0,
            ))
