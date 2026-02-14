"""Household agent module.

Models individual household rent-burden evaluation, relocation decisions
via multinomial logit, and commute mode updates.
"""

import numpy as np
import pandas as pd

from simulation.core.config import SimulationConfig
from simulation.core.state import SimulationState, TractState


# Multinomial logit coefficients for tract utility
LOGIT_RENT_COEFF: float = -2.0
LOGIT_INCOME_MATCH_COEFF: float = 1.0
LOGIT_TRANSIT_COEFF: float = 0.8
LOGIT_CRIME_COEFF: float = -1.5

# Maximum fraction of households that can move in a single step
MAX_MOVE_FRACTION: float = 0.05


def _compute_tract_utilities(
    tracts: dict[str, TractState],
    income: float,
) -> dict[str, float]:
    """Compute destination utility for every tract given a household income."""
    utilities: dict[str, float] = {}
    for tid, t in tracts.items():
        rent_share: float = (t.median_rent * 12.0) / max(income, 1.0)
        income_match: float = 1.0 - abs(t.median_income - income) / max(t.median_income, 1.0)
        crime_norm: float = t.crime_incidents / 1000.0  # rough normalization

        utility: float = (
            LOGIT_RENT_COEFF * rent_share
            + LOGIT_INCOME_MATCH_COEFF * income_match
            + LOGIT_TRANSIT_COEFF * t.transit_accessibility
            + LOGIT_CRIME_COEFF * crime_norm
        )
        utilities[tid] = utility
    return utilities


def update_households(
    state: SimulationState,
    config: SimulationConfig,
    params: dict,
    rng: np.random.Generator,
) -> None:
    """Advance household agents by one timestep.

    Steps:
        1. Recalculate rent_share for each household.
        2. Flag households where rent_share > threshold as wanting to move.
        3. Relocate flagged households via multinomial logit.
        4. Update commute_mode based on destination tract accessibility.

    Mutations are in-place on *state.agents.households*.
    """
    hh: pd.DataFrame = state.agents.households
    if hh is None or hh.empty:
        return

    threshold: float = params.get("rent_burden_threshold", 0.5)
    tracts: dict[str, TractState] = state.tracts

    # Build tract lookup for rent
    tract_rent: dict[str, float] = {tid: t.median_rent for tid, t in tracts.items()}
    tract_ids: list[str] = list(tracts.keys())

    # ----- 1. Rent share recalculation -----
    hh["rent_share"] = hh.apply(
        lambda row: min(
            1.0,
            tract_rent.get(row["tract_id"], 2500.0) * 12.0 / max(row["income"], 1.0),
        ),
        axis=1,
    )

    # ----- 2. Flag movers -----
    hh["wants_to_move"] = hh["rent_share"] > threshold

    movers: pd.DataFrame = hh[hh["wants_to_move"]]
    if movers.empty:
        return

    # Cap the number of movers per step
    max_movers: int = int(len(hh) * MAX_MOVE_FRACTION)
    if len(movers) > max_movers:
        movers = movers.sample(n=max_movers, random_state=int(rng.integers(0, 2**31)))

    # ----- 3. Multinomial logit relocation -----
    # Precompute utility for a representative income (median of movers) for speed
    # then add household-specific rent-share adjustment
    if len(tract_ids) == 0:
        return

    for idx in movers.index:
        income: float = hh.at[idx, "income"]
        utilities: dict[str, float] = _compute_tract_utilities(tracts, income)

        # Convert to probabilities via softmax
        util_arr: np.ndarray = np.array([utilities[tid] for tid in tract_ids])
        # Numerical stability
        util_arr = util_arr - util_arr.max()
        exp_util: np.ndarray = np.exp(util_arr)
        probs: np.ndarray = exp_util / exp_util.sum()

        # Draw destination
        dest_idx: int = int(rng.choice(len(tract_ids), p=probs))
        new_tract: str = tract_ids[dest_idx]
        hh.at[idx, "tract_id"] = new_tract
        hh.at[idx, "wants_to_move"] = False

        # ----- 4. Update commute mode -----
        dest_tract: TractState = tracts[new_tract]
        mode_probs: np.ndarray = np.array([
            dest_tract.commute_mode_car,
            dest_tract.commute_mode_transit,
            dest_tract.commute_mode_other,
        ])
        mode_probs = mode_probs / mode_probs.sum()
        mode_choice: str = rng.choice(["car", "transit", "other"], p=mode_probs)
        hh.at[idx, "commute_mode"] = mode_choice

    # Recalculate rent share after move
    hh["rent_share"] = hh.apply(
        lambda row: min(
            1.0,
            tract_rent.get(row["tract_id"], 2500.0) * 12.0 / max(row["income"], 1.0),
        ),
        axis=1,
    )
