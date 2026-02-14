"""Scenario: Double enforcement in Tenderloin + 500 treatment beds.

Simulates a combined enforcement and harm-reduction approach targeting
the Tenderloin neighborhood's open drug market.
"""

from simulation.core.config import PolicyConfiguration, SimulationConfig, DEFAULT_PARAMS


# Census tract IDs for the Tenderloin (SF county FIPS 075)
TENDERLOIN_TRACTS: list[str] = [
    "06075012400",  # Tenderloin core
    "06075012300",  # Tenderloin north
    "06075012500",  # Tenderloin south / Civic Center
    "06075012200",  # Lower Nob Hill / Tenderloin edge
    "06075012600",  # Mid-Market / 6th St corridor
]


def build_drug_enforcement_config() -> SimulationConfig:
    """Build a SimulationConfig for the Tenderloin enforcement + treatment scenario.

    Returns
    -------
    SimulationConfig
        Configuration with 2x enforcement in Tenderloin tracts and 500 treatment beds.
    """
    policy = PolicyConfiguration(
        enforcement_budget_multiplier=2.0,
        enforcement_target_tracts=list(TENDERLOIN_TRACTS),
        treatment_beds_added=500,
        name="Tenderloin Enforcement + Treatment",
        description=(
            "Double police enforcement in Tenderloin tracts while adding 500 "
            "treatment beds. Tests dealer displacement, user treatment uptake, "
            "and spillover effects on neighboring areas."
        ),
    )
    return SimulationConfig(
        policy=policy,
        params=dict(DEFAULT_PARAMS),
    )

# Alias for script compatibility
get_config = build_drug_enforcement_config
