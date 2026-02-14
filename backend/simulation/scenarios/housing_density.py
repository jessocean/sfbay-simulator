"""Scenario: 5x housing density in Mission/SoMa tracts.

Simulates the effect of dramatically upzoning the Mission District and
South of Market (SoMa) neighborhoods in San Francisco.
"""

from simulation.core.config import PolicyConfiguration, SimulationConfig, DEFAULT_PARAMS


# Census tract IDs for Mission District and SoMa (SF county FIPS 075)
# These are representative tracts; a full implementation would use
# a complete tract-to-neighborhood mapping.
MISSION_SOMA_TRACTS: list[str] = [
    "06075017700",  # Mission - 24th St corridor
    "06075017601",  # Mission - Valencia/Mission
    "06075017602",  # Mission - 16th St area
    "06075017800",  # Inner Mission
    "06075017900",  # Mission Dolores
    "06075017500",  # Mission - Cesar Chavez
    "06075060200",  # SoMa - 2nd/3rd St
    "06075060100",  # SoMa - Howard/Folsom
    "06075060400",  # SoMa - Brannan area
    "06075060300",  # SoMa - Townsend
]


def build_housing_density_config() -> SimulationConfig:
    """Build a SimulationConfig for the 5x Mission/SoMa density scenario.

    Returns
    -------
    SimulationConfig
        Configuration with density_multiplier=5.0 for Mission and SoMa tracts.
    """
    policy = PolicyConfiguration(
        density_multiplier=5.0,
        target_tract_ids=list(MISSION_SOMA_TRACTS),
        name="5x Density in Mission/SoMa",
        description=(
            "Upzone Mission District and SoMa to allow 5x current density. "
            "Tests effects on housing supply, rents, displacement, and transit demand."
        ),
    )
    return SimulationConfig(
        policy=policy,
        params=dict(DEFAULT_PARAMS),
    )

# Alias for script compatibility
get_config = build_housing_density_config
