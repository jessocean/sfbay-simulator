"""Decision-maker agent module.

Models the SF Board of Supervisors voting on policy changes,
using ideology-based alignment scoring with majority/veto rules.
"""

import numpy as np
import pandas as pd

from simulation.core.config import PolicyConfiguration, SimulationConfig, STEPS_PER_YEAR
from simulation.core.state import SimulationState


# Majority threshold: 6 of 11 supervisors
SIMPLE_MAJORITY: int = 6

# Veto override threshold: 8 of 11 supervisors
VETO_OVERRIDE: int = 8

# Policy ideology scores: negative = progressive, positive = moderate/conservative
POLICY_IDEOLOGY: dict[str, float] = {
    "density_increase": -0.3,       # progressive-leaning
    "enforcement_increase": 0.5,    # moderate/conservative-leaning
    "budget_reduction": 0.7,        # conservative-leaning
    "transit_subsidy": -0.6,        # progressive-leaning
    "permit_reform": 0.1,           # bipartisan
    "treatment_expansion": -0.4,    # progressive-leaning
}


def _compute_alignment(ideology_score: float, policy_ideology: float) -> float:
    """Compute alignment probability: how likely a supervisor supports a policy.

    Returns probability [0, 1]. Supervisors with similar ideology to the
    policy are more likely to vote yes.
    """
    distance: float = abs(ideology_score - policy_ideology)
    # Sigmoid-like: close ideology → high probability
    alignment: float = 1.0 / (1.0 + np.exp(3.0 * distance - 1.5))
    return float(alignment)


def _classify_policy(policy: PolicyConfiguration) -> list[str]:
    """Determine which policy categories are active."""
    categories: list[str] = []
    if policy.density_multiplier > 1.0:
        categories.append("density_increase")
    if policy.enforcement_budget_multiplier > 1.0:
        categories.append("enforcement_increase")
    if policy.budget_reduction_pct > 0:
        categories.append("budget_reduction")
    if policy.fare_multiplier < 1.0 or policy.service_frequency_multiplier > 1.0:
        categories.append("transit_subsidy")
    if policy.permit_timeline_reduction_pct > 0:
        categories.append("permit_reform")
    if policy.treatment_beds_added > 0:
        categories.append("treatment_expansion")
    return categories


def update_decision_makers(
    state: SimulationState,
    config: SimulationConfig,
    params: dict,
    rng: np.random.Generator,
) -> None:
    """Run annual Board of Supervisors vote (every 26 steps).

    Steps:
        1. Check if it is a voting step (every STEPS_PER_YEAR steps).
        2. Classify the current policy into categories.
        3. Each supervisor votes yes/no based on ideology alignment.
        4. If simple majority (6/11), policy continues; otherwise it may be modified.
        5. Veto override requires 8/11.

    Results stored as vote_result on state for logging.
    """
    dm: pd.DataFrame = state.agents.decision_makers
    if dm is None or dm.empty:
        return

    # Only vote annually
    if state.timestep == 0 or state.timestep % STEPS_PER_YEAR != 0:
        return

    policy: PolicyConfiguration = config.policy
    categories: list[str] = _classify_policy(policy)

    if not categories:
        return

    # Composite policy ideology = average of active policy category ideologies
    avg_policy_ideology: float = float(np.mean([
        POLICY_IDEOLOGY.get(c, 0.0) for c in categories
    ]))

    # Each supervisor votes
    votes: list[bool] = []
    for _, sup in dm.iterrows():
        ideology: float = sup["ideology_score"]
        prob_yes: float = _compute_alignment(ideology, avg_policy_ideology)
        vote: bool = bool(rng.random() < prob_yes)
        votes.append(vote)

    yes_count: int = sum(votes)
    has_majority: bool = yes_count >= SIMPLE_MAJORITY
    has_veto_override: bool = yes_count >= VETO_OVERRIDE

    # Store result for downstream inspection
    vote_result: dict = {
        "timestep": state.timestep,
        "categories": categories,
        "policy_ideology": avg_policy_ideology,
        "yes_votes": yes_count,
        "total_votes": len(votes),
        "passed": has_majority,
        "veto_override": has_veto_override,
        "votes_detail": votes,
    }

    if not hasattr(state, "vote_history"):
        state.vote_history = []  # type: ignore[attr-defined]
    state.vote_history.append(vote_result)  # type: ignore[attr-defined]

    # If policy fails, dampen its effects (reduce multipliers toward baseline)
    if not has_majority:
        policy.density_multiplier = max(1.0, policy.density_multiplier * 0.7)
        policy.enforcement_budget_multiplier = 1.0 + (policy.enforcement_budget_multiplier - 1.0) * 0.5
        policy.budget_reduction_pct *= 0.5
        policy.service_frequency_multiplier = 1.0 + (policy.service_frequency_multiplier - 1.0) * 0.5
        policy.fare_multiplier = 1.0 + (policy.fare_multiplier - 1.0) * 0.5
        policy.permit_timeline_reduction_pct *= 0.5
