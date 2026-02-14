"""Main simulation engine.

Orchestrates the three-phase simulation loop:
    Phase A: System dynamics updates (housing, transit, fiscal, crime, business)
    Phase B: Agent-based model updates (households, drug market, businesses,
             decision makers, developers)
    Phase C: Integration (ABM->SD aggregation, SD->ABM push, cross-system linkages)
"""

from typing import Optional

import numpy as np
import pandas as pd

from simulation.core.config import SimulationConfig, TOTAL_TIMESTEPS
from simulation.core.state import SimulationState

# System dynamics modules
from simulation.system_dynamics.housing import update_housing
from simulation.system_dynamics.transit import update_transit
from simulation.system_dynamics.fiscal import update_fiscal
from simulation.system_dynamics.crime import update_crime
from simulation.system_dynamics.business import update_business

# Agent modules
from simulation.agents.households import update_households
from simulation.agents.drug_market import update_drug_market
from simulation.agents.businesses import update_business_agents
from simulation.agents.decision_makers import update_decision_makers
from simulation.agents.developers import update_developers

# Integration modules
from simulation.integration.linkages import compute_cross_system_linkages
from simulation.integration.sd_to_abm import update_agents_from_sd
from simulation.integration.abm_to_sd import update_sd_from_agents


# Default snapshot interval (every 2 steps = monthly)
DEFAULT_SNAPSHOT_INTERVAL: int = 2


def initialize_state(
    baseline_df: pd.DataFrame,
    config: SimulationConfig,
) -> tuple[SimulationState, np.random.Generator]:
    """Initialize simulation state from baseline tract data.

    Parameters
    ----------
    baseline_df : pd.DataFrame
        Tract-level baseline data with columns matching TractState fields.
        Must contain at least 'tract_id' and 'county_fips'.
    config : SimulationConfig
        Full simulation configuration including policy and parameters.

    Returns
    -------
    tuple[SimulationState, np.random.Generator]
        Initialized state and seeded RNG.
    """
    rng: np.random.Generator = np.random.default_rng(config.random_seed)
    state = SimulationState()
    state.initialize_from_data(baseline_df, rng)
    return state, rng


def run_phase_a(
    state: SimulationState,
    config: SimulationConfig,
    params: dict,
) -> None:
    """Phase A: System dynamics updates.

    Order matters for dependency flow:
        1. Housing (rents, prices, construction)
        2. Transit (accessibility, ridership, mode shares)
        3. Fiscal (revenue, budgets, enforcement level)
        4. Crime (enforcement-displacement, decay)
        5. Business (formation, closure, counts)
    """
    update_housing(state, config, params)
    update_transit(state, config, params)
    update_fiscal(state, config, params)
    update_crime(state, config, params)
    update_business(state, config, params)


def run_phase_b(
    state: SimulationState,
    config: SimulationConfig,
    params: dict,
    rng: np.random.Generator,
) -> None:
    """Phase B: Agent-based model updates.

    Order:
        1. Households (rent burden, relocation, commute)
        2. Drug market (dealer displacement, treatment entry)
        3. Businesses (revenue, closures, spawns)
        4. Decision makers (annual voting)
        5. Developers (construction starts)
    """
    update_households(state, config, params, rng)
    update_drug_market(state, config, params, rng)
    update_business_agents(state, config, params, rng)
    update_decision_makers(state, config, params, rng)
    update_developers(state, config, params, rng)


def run_phase_c(
    state: SimulationState,
    config: SimulationConfig,
    params: dict,
) -> None:
    """Phase C: Integration and cross-system linkages.

    Order:
        1. Aggregate agents -> SD variables
        2. Push SD variables -> agent context
        3. Compute cross-system feedback linkages
    """
    update_sd_from_agents(state)
    update_agents_from_sd(state)
    compute_cross_system_linkages(state, config, params)


def run_simulation(
    baseline_df: pd.DataFrame,
    config: Optional[SimulationConfig] = None,
    snapshot_interval: int = DEFAULT_SNAPSHOT_INTERVAL,
    progress_callback: Optional[callable] = None,
) -> list[dict]:
    """Run the full simulation and return snapshots.

    Parameters
    ----------
    baseline_df : pd.DataFrame
        Tract-level baseline data.
    config : SimulationConfig, optional
        Simulation configuration. Uses defaults if not provided.
    snapshot_interval : int
        Save a state snapshot every N timesteps.
    progress_callback : callable, optional
        Called with (current_step, total_steps) for progress reporting.

    Returns
    -------
    list[dict]
        List of state snapshots, each produced by SimulationState.snapshot().
    """
    if config is None:
        config = SimulationConfig()

    params: dict = config.params
    total_steps: int = config.total_steps

    # Initialize
    state, rng = initialize_state(baseline_df, config)

    # Take initial snapshot
    snapshots: list[dict] = [state.snapshot()]

    # Main loop
    for step in range(1, total_steps + 1):
        state.timestep = step

        # Phase A: System dynamics
        run_phase_a(state, config, params)

        # Phase B: Agent-based updates
        run_phase_b(state, config, params, rng)

        # Phase C: Integration
        run_phase_c(state, config, params)

        # Snapshot
        if step % snapshot_interval == 0 or step == total_steps:
            snapshots.append(state.snapshot())

        # Progress
        if progress_callback is not None:
            progress_callback(step, total_steps)

    return snapshots
