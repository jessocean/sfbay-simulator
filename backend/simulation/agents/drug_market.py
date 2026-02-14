"""Drug market agent module.

Models dealer displacement under enforcement, user treatment entry,
and updates tract-level drug_market_activity from agent counts.
"""

import numpy as np
import pandas as pd

from simulation.core.config import SimulationConfig
from simulation.core.state import SimulationState, TractState


def _get_adjacent_tracts(
    tract_id: str,
    tracts: dict[str, TractState],
    radius_deg: float = 0.02,
) -> list[str]:
    """Return IDs of tracts adjacent to *tract_id* by centroid proximity."""
    if tract_id not in tracts:
        return []
    src: TractState = tracts[tract_id]
    neighbors: list[str] = []
    for tid, t in tracts.items():
        if tid == tract_id:
            continue
        dist: float = np.sqrt(
            (t.centroid_lat - src.centroid_lat) ** 2
            + (t.centroid_lon - src.centroid_lon) ** 2
        )
        if dist <= radius_deg:
            neighbors.append(tid)
    return neighbors


def update_drug_market(
    state: SimulationState,
    config: SimulationConfig,
    params: dict,
    rng: np.random.Generator,
) -> None:
    """Advance drug-market agents by one timestep.

    Steps:
        1. Dealers: if enforcement_level is high, probability of displacement
           to adjacent lower-enforcement tracts or exit.
        2. Users: probability of entering treatment, boosted by treatment_beds_added.
        3. Aggregate agent counts back to tract drug_market_activity.

    Mutations are in-place on *state.agents.drug_market*.
    """
    dm: pd.DataFrame = state.agents.drug_market
    if dm is None or dm.empty:
        return

    displacement_coeff: float = params.get("displacement_coefficient", 0.7)
    dealer_exit_rate: float = params.get("dealer_exit_rate", 0.3)
    treatment_entry_rate: float = params.get("treatment_entry_rate", 0.2)
    treatment_beds: int = config.policy.treatment_beds_added

    tracts: dict[str, TractState] = state.tracts

    # Build enforcement lookup
    enforcement: dict[str, float] = {tid: t.enforcement_level for tid, t in tracts.items()}

    # ----- 1. Dealer displacement -----
    dealers_mask: pd.Series = (dm["role"] == "dealer") & (dm["active"] == True)
    dealer_indices: pd.Index = dm.index[dealers_mask]

    for idx in dealer_indices:
        tract_id: str = dm.at[idx, "tract_id"]
        enf: float = enforcement.get(tract_id, 1.0)

        # Higher enforcement → higher probability of displacement
        displacement_prob: float = min(1.0, max(0.0, (enf - 1.0) * displacement_coeff * 0.1))

        if rng.random() < displacement_prob:
            # Try to find lower-enforcement neighbor
            neighbors: list[str] = _get_adjacent_tracts(tract_id, tracts)
            lower_enf_neighbors: list[str] = [
                n for n in neighbors if enforcement.get(n, 1.0) < enf
            ]

            if lower_enf_neighbors and rng.random() > dealer_exit_rate:
                # Move to a random lower-enforcement neighbor
                dest: str = str(rng.choice(lower_enf_neighbors))
                dm.at[idx, "tract_id"] = dest
            else:
                # Exit the market
                dm.at[idx, "active"] = False

    # ----- 2. User treatment entry -----
    users_mask: pd.Series = (dm["role"] == "user") & (dm["active"] == True)
    user_indices: pd.Index = dm.index[users_mask]

    # Treatment beds boost entry rate
    beds_boost: float = min(1.0, treatment_beds / 1000.0) * 0.3  # up to +0.3
    effective_treatment_rate: float = min(1.0, treatment_entry_rate + beds_boost)

    for idx in user_indices:
        in_treatment: bool = dm.at[idx, "in_treatment"] if "in_treatment" in dm.columns else False
        if not in_treatment and rng.random() < effective_treatment_rate * 0.01:
            dm.at[idx, "in_treatment"] = True
            dm.at[idx, "active"] = False  # exits active drug market

    # ----- 3. Update tract drug_market_activity -----
    active_dm: pd.DataFrame = dm[dm["active"] == True]
    if not active_dm.empty:
        activity_counts: pd.Series = active_dm.groupby("tract_id").size()
        for tid in tracts:
            tracts[tid].drug_market_activity = float(activity_counts.get(tid, 0.0))
    else:
        for tid in tracts:
            tracts[tid].drug_market_activity = 0.0
