"""DiPasquale-Wheaton housing model per census tract.

Implements rent adjustment, price capitalization, construction pipeline,
and depreciation dynamics at the tract level.
"""

import numpy as np

from simulation.core.config import PolicyConfiguration, SimulationConfig
from simulation.core.state import SimulationState, TractState


# Natural vacancy rate benchmark
NATURAL_VACANCY_RATE: float = 0.065

# Capitalization rate for price = rent * 12 / cap_rate
BASE_CAP_RATE: float = 0.04

# Rent adjustment speed per timestep
RENT_ADJUSTMENT_SPEED: float = 0.02

# Depreciation applied each timestep (fraction of stock lost)
DEPRECIATION_RATE_PER_STEP: float = 0.0001


def update_housing(
    state: SimulationState,
    config: SimulationConfig,
    params: dict,
) -> None:
    """Advance the housing system-dynamics model by one timestep.

    Steps:
        1. Adjust rents based on vacancy vs. natural vacancy rate.
        2. Capitalize rents into home prices.
        3. Advance the construction pipeline (completions and new starts).
        4. Apply depreciation to existing housing stock.
        5. Recalculate vacancy rates.

    All mutations happen in-place on *state.tracts*.
    """
    policy: PolicyConfiguration = config.policy
    demand_elasticity: float = params.get("housing_demand_elasticity", -0.7)
    supply_elasticity: float = params.get("housing_supply_elasticity", 0.8)
    construction_lag: int = int(params.get("construction_lag_steps", 52))
    cost_per_sqft: float = params.get("construction_cost_per_sqft", 1000.0)
    profit_threshold: float = params.get("developer_profit_threshold", 0.15)
    depreciation: float = params.get("depreciation_rate", 0.005)

    target_tracts: set[str] = set(policy.target_tract_ids)
    density_mult: float = policy.density_multiplier

    for tid, tract in state.tracts.items():
        # ----- 1. Rent adjustment -----
        vacancy_gap: float = tract.vacancy_rate - NATURAL_VACANCY_RATE
        # Negative gap (tight market) → rent increase; positive gap → decrease
        rent_change_pct: float = -vacancy_gap * abs(demand_elasticity) * RENT_ADJUSTMENT_SPEED * 100.0
        tract.median_rent = max(500.0, tract.median_rent * (1.0 + rent_change_pct))

        # ----- 2. Price capitalization -----
        cap_rate: float = BASE_CAP_RATE
        tract.median_home_price = tract.median_rent * 12.0 / cap_rate

        # ----- 3. Construction pipeline -----
        # Apply density policy to target tracts
        effective_max_density: float = tract.max_density_units
        if tid in target_tracts:
            effective_max_density *= density_mult

        # Room to build?
        room_to_build: float = max(0.0, effective_max_density - tract.housing_units - tract.construction_pipeline)

        if room_to_build > 0:
            # Developer profitability check
            avg_sqft: float = 850.0  # assumed average unit size
            expected_revenue_per_unit: float = tract.median_home_price
            cost_per_unit: float = cost_per_sqft * avg_sqft
            margin: float = (expected_revenue_per_unit - cost_per_unit) / max(cost_per_unit, 1.0)

            if margin > profit_threshold:
                # New starts proportional to margin and supply elasticity
                starts: float = room_to_build * supply_elasticity * min(margin, 0.5) * 0.01
                starts = max(0.0, min(starts, room_to_build))
                tract.construction_pipeline += starts

        # Pipeline completion: fraction completes each step based on lag
        if tract.construction_pipeline > 0 and construction_lag > 0:
            completions: float = tract.construction_pipeline / construction_lag
            tract.housing_units += completions
            tract.construction_pipeline = max(0.0, tract.construction_pipeline - completions)

        # ----- 4. Depreciation -----
        lost_units: float = tract.housing_units * depreciation * (1.0 / 260.0)
        tract.housing_units = max(0.0, tract.housing_units - lost_units)

        # ----- 5. Vacancy recalculation -----
        occupied: float = tract.households
        if tract.housing_units > 0:
            tract.vacancy_rate = max(0.0, min(1.0, 1.0 - occupied / tract.housing_units))
        else:
            tract.vacancy_rate = 0.0

        # ----- 6. Property-tax revenue (used by fiscal module) -----
        tax_rate: float = params.get("property_tax_rate", 0.0115)
        tract.property_tax_revenue = (
            tract.median_home_price
            * tract.housing_units
            * (1.0 - tract.vacancy_rate)
            * tax_rate
            / 26.0  # per-step share of annual tax
        )
