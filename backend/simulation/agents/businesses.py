"""Business agent module.

Models individual business revenue dynamics, closures, and new spawns
driven by system-dynamics formation rates.
"""

import numpy as np
import pandas as pd

from simulation.core.config import SimulationConfig
from simulation.core.state import SimulationState, TractState


# Revenue multiplier from transit accessibility (0.5 accessibility → 1.0x, 1.0 → 1.3x)
TRANSIT_REVENUE_SLOPE: float = 0.6

# Revenue penalty per unit of crime incidents (normalized)
CRIME_REVENUE_PENALTY: float = 0.0005

# Minimum revenue to stay open (per step)
MIN_REVENUE_THRESHOLD: float = 5000.0


def update_business_agents(
    state: SimulationState,
    config: SimulationConfig,
    params: dict,
    rng: np.random.Generator,
) -> None:
    """Advance business agents by one timestep.

    Steps:
        1. Update each business's revenue based on local population, transit, crime.
        2. Close businesses that fall below the revenue threshold.
        3. Spawn new businesses based on SD-computed formation rates.

    Mutations are in-place on *state.agents.businesses*.
    """
    biz: pd.DataFrame = state.agents.businesses
    if biz is None or biz.empty:
        biz = pd.DataFrame(columns=["tract_id", "revenue", "employees", "is_open"])
        state.agents.businesses = biz

    tracts: dict[str, TractState] = state.tracts
    crime_penalty: float = params.get("business_crime_penalty", -0.02)

    # Build tract lookup
    tract_data: dict[str, dict] = {}
    for tid, t in tracts.items():
        tract_data[tid] = {
            "population": t.population,
            "transit": t.transit_accessibility,
            "crime": t.crime_incidents,
            "formation_rate": t.business_formation_rate,
        }

    # ----- 1. Revenue update for open businesses -----
    open_mask: pd.Series = biz["is_open"] == True
    for idx in biz.index[open_mask]:
        tid: str = biz.at[idx, "tract_id"]
        td: dict = tract_data.get(tid, {"population": 1000, "transit": 0.5, "crime": 0, "formation_rate": 0})

        # Population factor (more people → more customers)
        pop_factor: float = max(0.5, min(2.0, td["population"] / 5000.0))

        # Transit factor
        transit_factor: float = 1.0 + TRANSIT_REVENUE_SLOPE * (td["transit"] - 0.5)

        # Crime factor
        crime_factor: float = max(0.5, 1.0 + td["crime"] * CRIME_REVENUE_PENALTY * crime_penalty)

        # Random shock
        shock: float = rng.normal(1.0, 0.05)

        current_revenue: float = biz.at[idx, "revenue"]
        new_revenue: float = current_revenue * pop_factor * transit_factor * crime_factor * shock * 0.25
        # Blend: mostly keep existing revenue with gradual adjustment
        blended_revenue: float = 0.9 * current_revenue + 0.1 * new_revenue / 0.25
        biz.at[idx, "revenue"] = max(0.0, blended_revenue)

    # ----- 2. Closures -----
    open_biz: pd.DataFrame = biz[biz["is_open"] == True]
    close_mask: pd.Series = open_biz["revenue"] < MIN_REVENUE_THRESHOLD
    biz.loc[close_mask[close_mask].index, "is_open"] = False

    # ----- 3. Spawn new businesses -----
    new_records: list[dict] = []
    for tid, td in tract_data.items():
        formation: float = td["formation_rate"]
        # formation_rate is in businesses per step; use Poisson draw
        n_new: int = int(rng.poisson(max(0.0, formation)))
        for _ in range(n_new):
            new_records.append({
                "tract_id": tid,
                "revenue": max(10000.0, float(rng.lognormal(11.5, 1.0))),
                "employees": max(1, int(rng.lognormal(1.5, 1.0))),
                "is_open": True,
            })

    if new_records:
        new_df: pd.DataFrame = pd.DataFrame(new_records)
        state.agents.businesses = pd.concat([biz, new_df], ignore_index=True)
