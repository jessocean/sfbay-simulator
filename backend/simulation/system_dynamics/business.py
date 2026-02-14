"""Business system dynamics module.

Models aggregate business formation and closure rates at the tract level
based on population, income, transit access, rent costs, and crime.
"""

import numpy as np

from simulation.core.config import PolicyConfiguration, SimulationConfig
from simulation.core.state import SimulationState, TractState


# Baseline formation rate per 1,000 population per step
BASE_FORMATION_PER_1K: float = 0.02

# Baseline closure rate per step (fraction of existing businesses)
BASE_CLOSURE_RATE: float = 0.005


def update_business(
    state: SimulationState,
    config: SimulationConfig,
    params: dict,
) -> None:
    """Advance business system dynamics by one timestep.

    Steps:
        1. Compute formation rate from population, income, transit access, permits.
        2. Compute closure rate from rent, crime, customer base.
        3. Update tract business counts.

    Mutations are in-place on *state.tracts*.
    """
    policy: PolicyConfiguration = config.policy
    crime_penalty: float = params.get("business_crime_penalty", -0.02)
    permit_reduction: float = policy.permit_timeline_reduction_pct / 100.0

    for _tid, tract in state.tracts.items():
        # ----- 1. Formation -----
        pop_factor: float = tract.population / 1000.0 if tract.population > 0 else 0.0
        income_factor: float = tract.median_income / 80000.0  # normalized to Bay Area median
        transit_factor: float = 0.8 + 0.4 * tract.transit_accessibility  # 0.8 - 1.2 range

        # Faster permits → more formation
        permit_boost: float = 1.0 + permit_reduction * 0.5  # up to 1.5x with 100% reduction

        formation_rate: float = (
            BASE_FORMATION_PER_1K
            * pop_factor
            * income_factor
            * transit_factor
            * permit_boost
        )
        tract.business_formation_rate = max(0.0, formation_rate)

        # ----- 2. Closure -----
        # High rent relative to income hurts businesses
        if tract.median_income > 0:
            rent_pressure: float = tract.median_rent / tract.median_income
        else:
            rent_pressure = 1.0
        rent_closure_factor: float = 1.0 + max(0.0, rent_pressure - 0.03) * 2.0

        # Crime penalty on survival
        crime_closure_factor: float = 1.0 + tract.crime_incidents * abs(crime_penalty) * 0.001

        # Low population reduces customer base
        customer_factor: float = max(0.5, min(1.5, tract.population / 5000.0))
        customer_closure_factor: float = 1.5 - customer_factor * 0.5  # fewer customers → higher closure

        closure_rate: float = (
            BASE_CLOSURE_RATE
            * rent_closure_factor
            * crime_closure_factor
            * customer_closure_factor
        )
        tract.business_closure_rate = max(0.0, min(1.0, closure_rate))

        # ----- 3. Update count -----
        new_businesses: float = formation_rate
        closed_businesses: float = tract.businesses_count * closure_rate
        tract.businesses_count = max(
            0.0,
            tract.businesses_count + new_businesses - closed_businesses,
        )
