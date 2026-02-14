"""Empirical calibration targets for the SF Bay Area simulation.

Each target represents an observable metric that the simulation should
reproduce at steady state (or at specific time horizons).
"""

from dataclasses import dataclass


@dataclass
class CalibrationTarget:
    """A single empirical target for calibration."""

    name: str
    value: float
    unit: str
    weight: float = 1.0  # relative importance in RMSE computation
    tolerance_pct: float = 10.0  # acceptable deviation in percent
    source: str = ""
    description: str = ""


# Empirical targets for the SF Bay Area (circa 2023-2024)
CALIBRATION_TARGETS: list[CalibrationTarget] = [
    CalibrationTarget(
        name="sf_median_rent",
        value=3500.0,
        unit="USD/month",
        weight=2.0,
        tolerance_pct=10.0,
        source="Zillow/Census ACS 2023",
        description="San Francisco county median asking rent",
    ),
    CalibrationTarget(
        name="bay_area_vacancy_rate",
        value=0.065,
        unit="fraction",
        weight=1.5,
        tolerance_pct=15.0,
        source="Census ACS 2023",
        description="Bay Area average residential vacancy rate",
    ),
    CalibrationTarget(
        name="sf_transit_mode_share",
        value=0.34,
        unit="fraction",
        weight=1.5,
        tolerance_pct=10.0,
        source="ACS Commuting Data 2023",
        description="SF transit commute mode share",
    ),
    CalibrationTarget(
        name="bay_area_median_home_price",
        value=1200000.0,
        unit="USD",
        weight=1.0,
        tolerance_pct=15.0,
        source="Redfin/Zillow 2024",
        description="Bay Area median single-family home price",
    ),
    CalibrationTarget(
        name="sf_crime_rate_per_1k",
        value=55.0,
        unit="incidents/1000 pop",
        weight=1.0,
        tolerance_pct=20.0,
        source="SFPD CompStat 2023",
        description="SF annual crime rate per 1,000 population",
    ),
    CalibrationTarget(
        name="bay_area_business_count",
        value=250000.0,
        unit="businesses",
        weight=0.5,
        tolerance_pct=20.0,
        source="Census County Business Patterns 2022",
        description="Total business establishments across 9 Bay Area counties",
    ),
    CalibrationTarget(
        name="sf_property_tax_revenue_annual",
        value=3_800_000_000.0,
        unit="USD/year",
        weight=0.5,
        tolerance_pct=15.0,
        source="SF Controller's Office FY2023",
        description="Annual property tax revenue for San Francisco",
    ),
    CalibrationTarget(
        name="muni_annual_ridership",
        value=150_000_000.0,
        unit="rides/year",
        weight=1.0,
        tolerance_pct=20.0,
        source="SFMTA 2023",
        description="Annual Muni transit ridership",
    ),
    CalibrationTarget(
        name="sf_housing_units",
        value=400000.0,
        unit="units",
        weight=1.0,
        tolerance_pct=5.0,
        source="Census ACS 2023",
        description="Total housing units in San Francisco",
    ),
    CalibrationTarget(
        name="bay_area_population",
        value=7_750_000.0,
        unit="people",
        weight=0.5,
        tolerance_pct=5.0,
        source="Census 2023 estimate",
        description="Total 9-county Bay Area population",
    ),
]


def get_target_dict() -> dict[str, float]:
    """Return mapping of target name to target value."""
    return {t.name: t.value for t in CALIBRATION_TARGETS}


def get_weight_dict() -> dict[str, float]:
    """Return mapping of target name to calibration weight."""
    return {t.name: t.weight for t in CALIBRATION_TARGETS}
