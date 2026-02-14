"""Developer agent module.

Models developer decision-making for new construction projects,
scanning tracts for profitable opportunities and starting construction
when margins exceed risk thresholds.
"""

import numpy as np
import pandas as pd

from simulation.core.config import PolicyConfiguration, SimulationConfig
from simulation.core.state import SimulationState, TractState


# Average unit size in sqft for profit calculation
AVG_UNIT_SQFT: float = 850.0

# Maximum active projects per developer
MAX_ACTIVE_PROJECTS: int = 5

# Units per project (typical mid-rise)
UNITS_PER_PROJECT: float = 50.0


def update_developers(
    state: SimulationState,
    config: SimulationConfig,
    params: dict,
    rng: np.random.Generator,
) -> None:
    """Advance developer agents by one timestep.

    Steps:
        1. For each developer, scan tracts (preferring their preferred county).
        2. Evaluate profit margin for each candidate tract.
        3. Start construction if profit_margin > risk_threshold AND zoning allows.
        4. Update developer active_projects count.

    Mutations are in-place on *state.agents.developers* and *state.tracts*.
    """
    devs: pd.DataFrame = state.agents.developers
    if devs is None or devs.empty:
        return

    policy: PolicyConfiguration = config.policy
    cost_per_sqft: float = params.get("construction_cost_per_sqft", 1000.0)
    profit_threshold: float = params.get("developer_profit_threshold", 0.15)

    target_tracts: set[str] = set(policy.target_tract_ids)
    density_mult: float = policy.density_multiplier

    tracts: dict[str, TractState] = state.tracts
    tract_ids: list[str] = list(tracts.keys())

    for idx in devs.index:
        active: int = int(devs.at[idx, "active_projects"])
        if active >= MAX_ACTIVE_PROJECTS:
            continue

        risk_thresh: float = devs.at[idx, "risk_threshold"]
        preferred_county: str = devs.at[idx, "preferred_county"]
        capital: float = devs.at[idx, "capital"]

        # Scan candidate tracts (prefer same county, sample a few)
        preferred: list[str] = [
            tid for tid in tract_ids
            if tracts[tid].county_fips == preferred_county
        ]
        # Also consider some from other counties
        other: list[str] = [tid for tid in tract_ids if tid not in preferred]
        n_preferred: int = min(10, len(preferred))
        n_other: int = min(3, len(other))

        candidates: list[str] = []
        if preferred:
            candidates.extend(
                rng.choice(preferred, size=n_preferred, replace=False).tolist()
                if len(preferred) >= n_preferred
                else preferred
            )
        if other:
            candidates.extend(
                rng.choice(other, size=n_other, replace=False).tolist()
                if len(other) >= n_other
                else other[:n_other]
            )

        best_tract: str | None = None
        best_margin: float = -1.0

        for tid in candidates:
            tract: TractState = tracts[tid]

            # Effective max density with policy
            effective_max: float = tract.max_density_units
            if tid in target_tracts:
                effective_max *= density_mult

            # Room to build
            room: float = effective_max - tract.housing_units - tract.construction_pipeline
            if room < UNITS_PER_PROJECT:
                continue

            # Profit margin calculation
            expected_price: float = tract.median_home_price
            construction_cost: float = cost_per_sqft * AVG_UNIT_SQFT
            total_cost: float = construction_cost * UNITS_PER_PROJECT
            total_revenue: float = expected_price * UNITS_PER_PROJECT
            margin: float = (total_revenue - total_cost) / max(total_cost, 1.0)

            # Check capital sufficiency
            if total_cost > capital * 0.5:
                continue

            if margin > best_margin:
                best_margin = margin
                best_tract = tid

        # Start project if profitable enough
        if best_tract is not None and best_margin > max(risk_thresh, profit_threshold):
            tracts[best_tract].construction_pipeline += UNITS_PER_PROJECT
            devs.at[idx, "active_projects"] = active + 1

    # Decrement active projects slowly (projects complete over time)
    # Roughly: 1 project completes every ~52 steps (2 years)
    completion_prob: float = 1.0 / max(params.get("construction_lag_steps", 52), 1)
    for idx in devs.index:
        active_count: int = int(devs.at[idx, "active_projects"])
        if active_count > 0:
            completions: int = int(rng.binomial(active_count, completion_prob))
            devs.at[idx, "active_projects"] = max(0, active_count - completions)
