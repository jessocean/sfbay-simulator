"""Scenario: Free Muni + 50% frequency increase.

Simulates the combined effect of eliminating Muni fares and increasing
service frequency by 50% on ridership, mode share, housing demand,
and fiscal balance.
"""

from simulation.core.config import PolicyConfiguration, SimulationConfig, DEFAULT_PARAMS


def build_transit_subsidy_config() -> SimulationConfig:
    """Build a SimulationConfig for the free transit + frequency boost scenario.

    Returns
    -------
    SimulationConfig
        Configuration with fare_multiplier=0 and service_frequency_multiplier=1.5.
    """
    policy = PolicyConfiguration(
        fare_multiplier=0.0,  # free transit
        service_frequency_multiplier=1.5,  # 50% more frequent service
        name="Free Muni + 50% Frequency Increase",
        description=(
            "Eliminate Muni fares entirely and increase service frequency by 50%. "
            "Tests ridership response, transit mode share gains, housing demand "
            "shifts near transit, and fiscal implications of fare revenue loss."
        ),
    )
    return SimulationConfig(
        policy=policy,
        params=dict(DEFAULT_PARAMS),
    )

# Alias for script compatibility
get_config = build_transit_subsidy_config
