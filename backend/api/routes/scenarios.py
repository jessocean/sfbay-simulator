"""Routes for predefined policy scenarios."""

from dataclasses import asdict

from fastapi import APIRouter

from api.models import PredefinedScenario
from simulation.core.config import PolicyConfiguration

router = APIRouter(prefix="/scenarios", tags=["scenarios"])


def _build_predefined_scenarios() -> list[PredefinedScenario]:
    """Build the list of predefined scenarios."""
    scenarios = [
        PredefinedScenario(
            id="upzone-mission-soma",
            name="Upzone Mission and SoMa",
            description="Upzone Mission and SoMa to 5x density",
            config=asdict(PolicyConfiguration(
                density_multiplier=5.0,
                target_tract_ids=[
                    "017700", "017800", "017900", "018000", "018100", "018200",
                    "018300", "020700", "020800", "020900", "021000",
                    "017600", "017601", "017602", "017603", "017604", "017605",
                    "017606",
                ],
                name="Upzone Mission and SoMa",
                description="Increase zoning density to 5x in Mission and SoMa neighborhoods.",
            )),
        ),
        PredefinedScenario(
            id="tenderloin-enforcement",
            name="Tenderloin Enforcement + Treatment",
            description="Double police presence in Tenderloin + 500 treatment beds",
            config=asdict(PolicyConfiguration(
                enforcement_budget_multiplier=2.0,
                enforcement_target_tracts=[
                    "012400", "012500", "012600", "012700", "012800", "012900",
                ],
                treatment_beds_added=500,
                name="Tenderloin enforcement + treatment",
                description="Double enforcement budget in Tenderloin and add 500 treatment beds.",
            )),
        ),
        PredefinedScenario(
            id="budget-cut-40",
            name="40% Budget Cut",
            description="Cut city budget by 40%, protecting fire and police",
            config=asdict(PolicyConfiguration(
                budget_reduction_pct=40.0,
                protected_departments=["fire", "police"],
                name="40% budget cut (fire/police protected)",
                description="Reduce city budget by 40%, shielding fire and police departments from cuts.",
            )),
        ),
        PredefinedScenario(
            id="free-muni",
            name="Free Muni + Frequency Boost",
            description="Make Muni free and increase frequency 50%",
            config=asdict(PolicyConfiguration(
                fare_multiplier=0.0,
                service_frequency_multiplier=1.5,
                name="Free Muni + 50% more service",
                description="Eliminate transit fares and increase Muni service frequency by 50%.",
            )),
        ),
        PredefinedScenario(
            id="fast-permits",
            name="Fast-Track Residential Permits",
            description="Reduce permit approval to 90 days for residential",
            config=asdict(PolicyConfiguration(
                permit_timeline_reduction_pct=50.0,
                permit_target_types=["residential"],
                name="Fast-track residential permits",
                description="Reduce residential permit approval timeline by 50% (approx. 90 days).",
            )),
        ),
    ]
    return scenarios


PREDEFINED_SCENARIOS = _build_predefined_scenarios()


@router.get("/predefined", response_model=list[PredefinedScenario])
async def get_predefined_scenarios() -> list[PredefinedScenario]:
    """Return the list of predefined policy scenarios.

    These serve as starting points and examples for users to understand
    what kinds of policies the simulator supports.
    """
    return PREDEFINED_SCENARIOS
