"""Scenario: 40% budget cut protecting fire and police.

Simulates the effect of severe austerity with essential-service protections
on city services, enforcement, and downstream economic outcomes.
"""

from simulation.core.config import PolicyConfiguration, SimulationConfig, DEFAULT_PARAMS


def build_budget_reduction_config() -> SimulationConfig:
    """Build a SimulationConfig for the 40% budget reduction scenario.

    Returns
    -------
    SimulationConfig
        Configuration with 40% budget cut, fire and police departments protected.
    """
    policy = PolicyConfiguration(
        budget_reduction_pct=40.0,
        protected_departments=["fire", "police"],
        name="40% Budget Cut (Fire/Police Protected)",
        description=(
            "Reduce the city budget by 40% while protecting fire and police "
            "departments at current funding levels. All other departments absorb "
            "proportionally larger cuts. Tests impacts on transit, housing services, "
            "health programs, and business climate."
        ),
    )
    return SimulationConfig(
        policy=policy,
        params=dict(DEFAULT_PARAMS),
    )

# Alias for script compatibility
get_config = build_budget_reduction_config
