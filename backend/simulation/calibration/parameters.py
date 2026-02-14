"""Parameter space definition for calibration optimization.

Defines bounds and metadata for each calibratable parameter used
by the Bayesian optimizer.
"""

from dataclasses import dataclass


@dataclass
class ParameterBound:
    """Bounds for a single calibration parameter."""

    name: str
    lower: float
    upper: float
    default: float
    description: str = ""
    log_scale: bool = False  # whether to optimize in log-space


# Full parameter space for calibration
PARAMETER_SPACE: list[ParameterBound] = [
    ParameterBound(
        name="housing_demand_elasticity",
        lower=-1.2,
        upper=-0.3,
        default=-0.7,
        description="Price elasticity of housing demand",
    ),
    ParameterBound(
        name="housing_supply_elasticity",
        lower=0.3,
        upper=1.5,
        default=0.8,
        description="Price elasticity of housing supply (construction response)",
    ),
    ParameterBound(
        name="construction_cost_per_sqft",
        lower=600.0,
        upper=1500.0,
        default=1000.0,
        description="Construction cost per square foot in USD",
    ),
    ParameterBound(
        name="construction_lag_steps",
        lower=26,
        upper=78,
        default=52,
        description="Steps for construction pipeline completion (~1-3 years)",
    ),
    ParameterBound(
        name="depreciation_rate",
        lower=0.001,
        upper=0.01,
        default=0.005,
        description="Annual depreciation rate of housing stock",
    ),
    ParameterBound(
        name="fare_elasticity",
        lower=-0.6,
        upper=-0.1,
        default=-0.3,
        description="Transit ridership elasticity with respect to fare",
    ),
    ParameterBound(
        name="service_elasticity",
        lower=0.3,
        upper=1.0,
        default=0.6,
        description="Transit ridership elasticity with respect to service frequency",
    ),
    ParameterBound(
        name="property_tax_rate",
        lower=0.008,
        upper=0.015,
        default=0.0115,
        description="Effective property tax rate (annual)",
    ),
    ParameterBound(
        name="displacement_coefficient",
        lower=0.3,
        upper=1.0,
        default=0.7,
        description="Crime displacement coefficient under enforcement pressure",
    ),
    ParameterBound(
        name="dealer_exit_rate",
        lower=0.1,
        upper=0.5,
        default=0.3,
        description="Probability that a displaced dealer exits the market",
    ),
    ParameterBound(
        name="treatment_entry_rate",
        lower=0.05,
        upper=0.4,
        default=0.2,
        description="Base probability of drug user entering treatment per step",
    ),
    ParameterBound(
        name="rent_burden_threshold",
        lower=0.3,
        upper=0.7,
        default=0.5,
        description="Rent-to-income ratio above which households seek to move",
    ),
    ParameterBound(
        name="developer_profit_threshold",
        lower=0.05,
        upper=0.30,
        default=0.15,
        description="Minimum profit margin for developers to start construction",
    ),
    ParameterBound(
        name="business_crime_penalty",
        lower=-0.05,
        upper=-0.005,
        default=-0.02,
        description="Crime penalty coefficient on business survival",
    ),
    ParameterBound(
        name="migration_sensitivity",
        lower=0.1,
        upper=0.6,
        default=0.3,
        description="Sensitivity of migration to housing cost differentials",
    ),
]


def get_bounds() -> list[tuple[float, float]]:
    """Return list of (lower, upper) bounds for the optimizer."""
    return [(p.lower, p.upper) for p in PARAMETER_SPACE]


def get_default_point() -> list[float]:
    """Return the default parameter vector."""
    return [p.default for p in PARAMETER_SPACE]


def get_param_names() -> list[str]:
    """Return ordered list of parameter names."""
    return [p.name for p in PARAMETER_SPACE]


def vector_to_dict(x: list[float]) -> dict[str, float]:
    """Convert an optimizer parameter vector to a named dict."""
    names: list[str] = get_param_names()
    return {name: val for name, val in zip(names, x)}


def dict_to_vector(d: dict[str, float]) -> list[float]:
    """Convert a named param dict to an optimizer vector."""
    names: list[str] = get_param_names()
    return [d[name] for name in names]
