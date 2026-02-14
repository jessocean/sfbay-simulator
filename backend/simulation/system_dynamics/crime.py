"""Crime system dynamics module.

Models enforcement-displacement at the district level and crime's
effect on business climate.
"""

import numpy as np

from simulation.core.config import SimulationConfig
from simulation.core.state import SimulationState, TractState


# Baseline crime decay per step absent any changes
CRIME_DECAY_RATE: float = 0.005

# How much enforcement reduces local crime per unit of enforcement
ENFORCEMENT_EFFECTIVENESS: float = 0.03

# Fraction of suppressed crime that displaces to neighboring tracts
DISPLACEMENT_FRACTION: float = 0.4


def _get_neighbor_tracts(
    tract: TractState,
    all_tracts: dict[str, TractState],
    radius_deg: float = 0.02,
) -> list[str]:
    """Return tract IDs within *radius_deg* of *tract* centroid (simple proximity)."""
    neighbors: list[str] = []
    lat, lon = tract.centroid_lat, tract.centroid_lon
    for tid, other in all_tracts.items():
        if tid == tract.tract_id:
            continue
        dist = np.sqrt((other.centroid_lat - lat) ** 2 + (other.centroid_lon - lon) ** 2)
        if dist <= radius_deg:
            neighbors.append(tid)
    return neighbors


def update_crime(
    state: SimulationState,
    config: SimulationConfig,
    params: dict,
) -> None:
    """Advance crime dynamics by one timestep.

    Steps:
        1. For each tract, compute enforcement-driven suppression.
        2. Displace a fraction of suppressed crime to neighbors.
        3. Apply natural crime decay.
        4. Compute crime penalty on business climate (stored for business module).

    Mutations are in-place on *state.tracts*.
    """
    displacement_coeff: float = params.get("displacement_coefficient", 0.7)
    crime_penalty: float = params.get("business_crime_penalty", -0.02)

    tracts: dict[str, TractState] = state.tracts

    # Collect displacement spillovers to apply after the sweep
    spillover: dict[str, float] = {tid: 0.0 for tid in tracts}

    for tid, tract in tracts.items():
        # ----- 1. Enforcement suppression -----
        enforcement_effect: float = (tract.enforcement_level - 1.0) * ENFORCEMENT_EFFECTIVENESS
        suppressed: float = tract.crime_incidents * max(0.0, enforcement_effect)
        tract.crime_incidents = max(0.0, tract.crime_incidents - suppressed)

        # ----- 2. Displacement -----
        displaced: float = suppressed * DISPLACEMENT_FRACTION * displacement_coeff
        neighbors: list[str] = _get_neighbor_tracts(tract, tracts)
        if neighbors and displaced > 0:
            per_neighbor: float = displaced / len(neighbors)
            for nid in neighbors:
                spillover[nid] += per_neighbor

    # Apply spillovers
    for tid, extra_crime in spillover.items():
        tracts[tid].crime_incidents = max(0.0, tracts[tid].crime_incidents + extra_crime)

    # ----- 3. Natural decay -----
    for tract in tracts.values():
        tract.crime_incidents = max(0.0, tract.crime_incidents * (1.0 - CRIME_DECAY_RATE))
