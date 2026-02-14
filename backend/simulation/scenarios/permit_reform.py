"""Scenario: Reduce permit timeline to 90 days for residential.

Simulates the effect of streamlining the permitting process for
residential construction projects across San Francisco.
"""

from simulation.core.config import PolicyConfiguration, SimulationConfig, DEFAULT_PARAMS


# Current average SF residential permit timeline is ~400 days.
# Reducing to 90 days is a ~77.5% reduction.
PERMIT_REDUCTION_PCT: float = 77.5


def build_permit_reform_config() -> SimulationConfig:
    """Build a SimulationConfig for the permit reform scenario.

    Returns
    -------
    SimulationConfig
        Configuration with 77.5% permit timeline reduction for residential projects.
    """
    policy = PolicyConfiguration(
        permit_timeline_reduction_pct=PERMIT_REDUCTION_PCT,
        permit_target_types=["residential"],
        name="90-Day Residential Permits",
        description=(
            "Reduce the average residential permit timeline from ~400 days to "
            "90 days (77.5% reduction). Tests effects on housing construction "
            "starts, supply growth, and downstream rent impacts."
        ),
    )
    return SimulationConfig(
        policy=policy,
        params=dict(DEFAULT_PARAMS),
    )

# Alias for script compatibility
get_config = build_permit_reform_config
