"""Agent-based model to system-dynamics bridge.

Aggregates agent-level data back into tract-level system-dynamics
variables so that the SD modules reflect agent behavior.
"""

import pandas as pd

from simulation.core.state import SimulationState, TractState


def update_sd_from_agents(state: SimulationState) -> None:
    """Aggregate agent populations back to tract-level SD variables.

    Updates:
        - Tract population and households from household agent locations.
        - Tract businesses_count from active business agents.
        - Tract drug_market_activity from active drug market agents.
        - Tract commute mode shares from household commute modes.

    Mutations are in-place on *state.tracts*.
    """
    tracts: dict[str, TractState] = state.tracts

    # ----- 1. Household locations -> tract population / households -----
    hh: pd.DataFrame | None = state.agents.households
    if hh is not None and not hh.empty:
        hh_counts: pd.Series = hh.groupby("tract_id").size()
        # Estimate population from household count (avg household size ~2.5)
        avg_hh_size: float = 2.5
        # Account for sampling rate (agents represent 10% of actual)
        scale_factor: float = 10.0

        for tid in tracts:
            agent_hh: float = float(hh_counts.get(tid, 0.0))
            tracts[tid].households = agent_hh * scale_factor
            tracts[tid].population = agent_hh * scale_factor * avg_hh_size

        # ----- Commute mode shares -----
        tract_hh: pd.DataFrame = hh.groupby("tract_id")
        for tid, group in tract_hh:
            if tid not in tracts:
                continue
            n: int = len(group)
            if n == 0:
                continue
            mode_counts = group["commute_mode"].value_counts()
            tracts[tid].commute_mode_car = float(mode_counts.get("car", 0)) / n
            tracts[tid].commute_mode_transit = float(mode_counts.get("transit", 0)) / n
            tracts[tid].commute_mode_other = float(mode_counts.get("other", 0)) / n

    # ----- 2. Business agents -> tract businesses_count -----
    biz: pd.DataFrame | None = state.agents.businesses
    if biz is not None and not biz.empty:
        open_biz: pd.DataFrame = biz[biz["is_open"] == True]
        biz_counts: pd.Series = open_biz.groupby("tract_id").size()
        # Scale factor: agents represent ~20% of actual businesses
        biz_scale: float = 5.0
        for tid in tracts:
            tracts[tid].businesses_count = float(biz_counts.get(tid, 0.0)) * biz_scale

    # ----- 3. Drug market agents -> tract drug_market_activity -----
    dm: pd.DataFrame | None = state.agents.drug_market
    if dm is not None and not dm.empty:
        active_dm: pd.DataFrame = dm[dm["active"] == True]
        dm_counts: pd.Series = active_dm.groupby("tract_id").size()
        for tid in tracts:
            tracts[tid].drug_market_activity = float(dm_counts.get(tid, 0.0))
