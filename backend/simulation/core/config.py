"""Policy configuration and simulation parameters."""

from dataclasses import dataclass, field
from typing import Optional


# 9 Bay Area county FIPS codes (state=06)
BAY_AREA_COUNTIES = {
    "001": "Alameda",
    "013": "Contra Costa",
    "041": "Marin",
    "055": "Napa",
    "075": "San Francisco",
    "081": "San Mateo",
    "085": "Santa Clara",
    "095": "Solano",
    "097": "Sonoma",
}

STATE_FIPS = "06"

# Simulation constants
TOTAL_TIMESTEPS = 260  # 10 years of fortnightly steps
TIMESTEP_DAYS = 14
STEPS_PER_YEAR = 26

# Default model parameters (calibrated)
DEFAULT_PARAMS = {
    "housing_demand_elasticity": -0.7,
    "housing_supply_elasticity": 0.8,
    "construction_cost_per_sqft": 1000.0,
    "construction_lag_steps": 52,  # ~2 years
    "depreciation_rate": 0.005,  # per step
    "fare_elasticity": -0.3,
    "service_elasticity": 0.6,
    "property_tax_rate": 0.0115,
    "displacement_coefficient": 0.7,
    "dealer_exit_rate": 0.3,
    "treatment_entry_rate": 0.2,
    "rent_burden_threshold": 0.5,
    "developer_profit_threshold": 0.15,
    "business_crime_penalty": -0.02,
    "migration_sensitivity": 0.3,
}


@dataclass
class PolicyConfiguration:
    """Structured policy parameters extracted from natural language input."""

    # Housing/Zoning
    density_multiplier: float = 1.0  # 1-5x, applied to target tracts
    target_tract_ids: list[str] = field(default_factory=list)

    # Enforcement
    enforcement_budget_multiplier: float = 1.0  # relative to current
    enforcement_target_tracts: list[str] = field(default_factory=list)
    treatment_beds_added: int = 0

    # Fiscal
    budget_reduction_pct: float = 0.0  # 0-50%
    protected_departments: list[str] = field(default_factory=list)

    # Transit
    fare_multiplier: float = 1.0  # 0=free, 1=current, 2=double
    service_frequency_multiplier: float = 1.0

    # Permits
    permit_timeline_reduction_pct: float = 0.0  # 0-100%
    permit_target_types: list[str] = field(default_factory=lambda: ["residential"])

    # Metadata
    description: str = ""
    name: str = ""

    def validate(self) -> list[str]:
        """Return list of validation errors, empty if valid."""
        errors = []
        if not 1.0 <= self.density_multiplier <= 5.0:
            errors.append(f"density_multiplier must be 1-5, got {self.density_multiplier}")
        if self.budget_reduction_pct < 0 or self.budget_reduction_pct > 50:
            errors.append(f"budget_reduction_pct must be 0-50, got {self.budget_reduction_pct}")
        if self.fare_multiplier < 0:
            errors.append(f"fare_multiplier must be >= 0, got {self.fare_multiplier}")
        if self.permit_timeline_reduction_pct < 0 or self.permit_timeline_reduction_pct > 100:
            errors.append(f"permit_timeline_reduction_pct must be 0-100, got {self.permit_timeline_reduction_pct}")
        return errors

    def clamp(self) -> "PolicyConfiguration":
        """Clamp all values to valid ranges."""
        self.density_multiplier = max(1.0, min(5.0, self.density_multiplier))
        self.budget_reduction_pct = max(0.0, min(50.0, self.budget_reduction_pct))
        self.fare_multiplier = max(0.0, self.fare_multiplier)
        self.permit_timeline_reduction_pct = max(0.0, min(100.0, self.permit_timeline_reduction_pct))
        return self


@dataclass
class SimulationConfig:
    """Full simulation configuration."""

    policy: PolicyConfiguration = field(default_factory=PolicyConfiguration)
    params: dict = field(default_factory=lambda: dict(DEFAULT_PARAMS))
    total_steps: int = TOTAL_TIMESTEPS
    random_seed: int = 42
