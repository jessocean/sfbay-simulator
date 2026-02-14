"""Transit system dynamics module.

Models fare/ridership elasticity, service frequency effects on accessibility,
and commute mode share updates at the tract level.
"""

import numpy as np

from simulation.core.config import PolicyConfiguration, SimulationConfig
from simulation.core.state import SimulationState, TractState


def update_transit(
    state: SimulationState,
    config: SimulationConfig,
    params: dict,
) -> None:
    """Advance transit dynamics by one timestep.

    Steps:
        1. Update transit accessibility based on service frequency multiplier.
        2. Update ridership based on fare changes (fare elasticity).
        3. Adjust commute mode shares toward new equilibrium.

    Mutations are in-place on *state.tracts*.
    """
    policy: PolicyConfiguration = config.policy
    fare_elasticity: float = params.get("fare_elasticity", -0.3)
    service_elasticity: float = params.get("service_elasticity", 0.6)

    fare_mult: float = policy.fare_multiplier
    service_mult: float = policy.service_frequency_multiplier

    # Fare change relative to baseline (1.0)
    fare_change_pct: float = fare_mult - 1.0  # e.g. 0 → free = -1.0

    for _tid, tract in state.tracts.items():
        # ----- 1. Accessibility -----
        # Accessibility improves with more frequent service
        base_access: float = tract.transit_accessibility
        new_access: float = base_access * (1.0 + (service_mult - 1.0) * service_elasticity)
        tract.transit_accessibility = float(np.clip(new_access, 0.0, 1.0))

        # ----- 2. Ridership -----
        # Ridership responds to fare via constant elasticity
        ridership_change: float = fare_change_pct * fare_elasticity
        tract.transit_ridership = max(
            0.0,
            tract.transit_ridership * (1.0 + ridership_change * 0.01),
        )

        # Ridership also responds positively to higher service frequency
        service_ridership_boost: float = (service_mult - 1.0) * service_elasticity * 0.01
        tract.transit_ridership = max(
            0.0,
            tract.transit_ridership * (1.0 + service_ridership_boost),
        )

        # ----- 3. Commute mode shares -----
        # Transit share shifts based on accessibility change and fare effect
        access_effect: float = (tract.transit_accessibility - base_access) * 0.5
        fare_effect: float = fare_change_pct * fare_elasticity * 0.02

        delta_transit: float = access_effect + fare_effect
        new_transit_share: float = tract.commute_mode_transit + delta_transit
        new_transit_share = float(np.clip(new_transit_share, 0.0, 0.8))

        # Rebalance: shift comes from / goes to car mode
        delta_actual: float = new_transit_share - tract.commute_mode_transit
        tract.commute_mode_transit = new_transit_share
        tract.commute_mode_car = float(np.clip(tract.commute_mode_car - delta_actual, 0.05, 1.0))

        # Normalize to sum to 1
        total: float = tract.commute_mode_car + tract.commute_mode_transit + tract.commute_mode_other
        if total > 0:
            tract.commute_mode_car /= total
            tract.commute_mode_transit /= total
            tract.commute_mode_other /= total
