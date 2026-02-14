"""Fiscal system dynamics module.

Models city/county revenue, budget allocation, and enforcement-level
derivation from police budget shares.
"""

import numpy as np

from simulation.core.config import PolicyConfiguration, SimulationConfig
from simulation.core.state import SimulationState


# Default department budget shares (fraction of total)
DEFAULT_DEPARTMENT_SHARES: dict[str, float] = {
    "police": 0.28,
    "fire": 0.12,
    "transit": 0.15,
    "public_works": 0.10,
    "health": 0.12,
    "housing": 0.08,
    "parks": 0.05,
    "admin": 0.10,
}

# Business tax revenue per business per step (rough proxy)
BUSINESS_TAX_PER_BUSINESS_STEP: float = 200.0


def update_fiscal(
    state: SimulationState,
    config: SimulationConfig,
    params: dict,
) -> None:
    """Advance fiscal dynamics by one timestep.

    Steps:
        1. Compute total revenue from property taxes and business taxes.
        2. Apply budget reduction if policy dictates.
        3. Allocate to departments, respecting protected-department floors.
        4. Derive enforcement_level from police budget ratio.

    Results are stored on the state for downstream modules.
    """
    policy: PolicyConfiguration = config.policy
    tax_rate: float = params.get("property_tax_rate", 0.0115)

    # ----- 1. Revenue -----
    total_property_tax: float = sum(
        t.property_tax_revenue for t in state.tracts.values()
    )
    total_businesses: float = sum(
        t.businesses_count for t in state.tracts.values()
    )
    business_tax: float = total_businesses * BUSINESS_TAX_PER_BUSINESS_STEP
    total_revenue: float = total_property_tax + business_tax

    # ----- 2. Budget reduction -----
    reduction_pct: float = policy.budget_reduction_pct / 100.0
    available_budget: float = total_revenue * (1.0 - reduction_pct)

    # ----- 3. Department allocation -----
    protected: set[str] = set(policy.protected_departments)
    shares: dict[str, float] = dict(DEFAULT_DEPARTMENT_SHARES)

    # Protected departments keep their full share of the *original* budget
    protected_total: float = sum(
        shares[d] * total_revenue for d in protected if d in shares
    )
    remaining_budget: float = max(0.0, available_budget - protected_total)

    unprotected_share_total: float = sum(
        v for k, v in shares.items() if k not in protected
    )

    department_budgets: dict[str, float] = {}
    for dept, share in shares.items():
        if dept in protected:
            department_budgets[dept] = share * total_revenue
        else:
            if unprotected_share_total > 0:
                dept_fraction: float = share / unprotected_share_total
                department_budgets[dept] = remaining_budget * dept_fraction
            else:
                department_budgets[dept] = 0.0

    # ----- 4. Enforcement level -----
    baseline_police_budget: float = DEFAULT_DEPARTMENT_SHARES["police"] * total_revenue
    actual_police_budget: float = department_budgets.get("police", 0.0)

    # Enforcement multiplier also incorporates policy multiplier
    if baseline_police_budget > 0:
        budget_ratio: float = actual_police_budget / baseline_police_budget
    else:
        budget_ratio = 1.0

    enforcement_base: float = budget_ratio * policy.enforcement_budget_multiplier

    # Apply enforcement to tracts (targeted or uniform)
    enforcement_targets: set[str] = set(policy.enforcement_target_tracts)
    for tid, tract in state.tracts.items():
        if enforcement_targets and tid in enforcement_targets:
            tract.enforcement_level = enforcement_base * 1.5  # focused boost
        elif enforcement_targets:
            # Non-target tracts get slightly reduced enforcement (resource shift)
            tract.enforcement_level = enforcement_base * 0.9
        else:
            tract.enforcement_level = enforcement_base

    # Store department budgets on state for inspection
    if not hasattr(state, "department_budgets"):
        state.department_budgets = {}  # type: ignore[attr-defined]
    state.department_budgets = department_budgets  # type: ignore[attr-defined]
    if not hasattr(state, "total_revenue"):
        state.total_revenue = 0.0  # type: ignore[attr-defined]
    state.total_revenue = total_revenue  # type: ignore[attr-defined]
