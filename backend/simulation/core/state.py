"""Simulation state data structures."""

from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd


@dataclass
class TractState:
    """State of a single census tract at a point in time."""

    tract_id: str
    county_fips: str

    # Housing
    housing_units: float = 0.0
    vacancy_rate: float = 0.065
    median_rent: float = 2500.0
    median_home_price: float = 800000.0
    construction_pipeline: float = 0.0  # units under construction
    max_density_units: float = 0.0  # zoning-allowed max

    # Population
    population: float = 0.0
    households: float = 0.0
    median_income: float = 80000.0

    # Business
    businesses_count: float = 0.0
    business_formation_rate: float = 0.0
    business_closure_rate: float = 0.0

    # Crime
    crime_incidents: float = 0.0
    drug_market_activity: float = 0.0
    enforcement_level: float = 1.0

    # Transit
    transit_accessibility: float = 0.5  # 0-1 score
    transit_ridership: float = 0.0
    commute_mode_car: float = 0.6
    commute_mode_transit: float = 0.25
    commute_mode_other: float = 0.15

    # Fiscal
    property_tax_revenue: float = 0.0
    permit_timeline_days: float = 400.0

    # Geography
    area_sqmi: float = 0.0
    centroid_lat: float = 0.0
    centroid_lon: float = 0.0


class AgentPopulation:
    """Container for all agent populations."""

    def __init__(self):
        self.households: Optional[pd.DataFrame] = None
        self.businesses: Optional[pd.DataFrame] = None
        self.drug_market: Optional[pd.DataFrame] = None
        self.decision_makers: Optional[pd.DataFrame] = None
        self.developers: Optional[pd.DataFrame] = None

    def initialize_from_baseline(self, baseline_df: pd.DataFrame, rng: np.random.Generator):
        """Sample agent populations from tract baseline data."""
        self._init_households(baseline_df, rng)
        self._init_businesses(baseline_df, rng)
        self._init_drug_market(baseline_df, rng)
        self._init_decision_makers()
        self._init_developers(baseline_df, rng)

    def _init_households(self, df: pd.DataFrame, rng: np.random.Generator):
        """Sample ~150K household agents from tract data."""
        records = []
        sample_rate = 0.1  # sample 10% of households
        for _, row in df.iterrows():
            n = max(1, int(row.get("households", 100) * sample_rate))
            for _ in range(n):
                income = max(10000, rng.normal(
                    row.get("median_income", 80000),
                    row.get("median_income", 80000) * 0.4
                ))
                records.append({
                    "tract_id": row["tract_id"],
                    "income": income,
                    "rent_share": min(1.0, row.get("median_rent", 2500) * 12 / max(income, 1)),
                    "commute_mode": rng.choice(
                        ["car", "transit", "other"],
                        p=[row.get("commute_mode_car", 0.6),
                           row.get("commute_mode_transit", 0.25),
                           row.get("commute_mode_other", 0.15)]
                    ),
                    "wants_to_move": False,
                })
        self.households = pd.DataFrame(records)

    def _init_businesses(self, df: pd.DataFrame, rng: np.random.Generator):
        """Initialize business agents."""
        records = []
        for _, row in df.iterrows():
            n = max(0, int(row.get("businesses_count", 10) * 0.2))
            for _ in range(n):
                records.append({
                    "tract_id": row["tract_id"],
                    "revenue": max(10000, rng.lognormal(11.5, 1.0)),
                    "employees": max(1, int(rng.lognormal(1.5, 1.0))),
                    "is_open": True,
                })
        self.businesses = pd.DataFrame(records) if records else pd.DataFrame(
            columns=["tract_id", "revenue", "employees", "is_open"]
        )

    def _init_drug_market(self, df: pd.DataFrame, rng: np.random.Generator):
        """Initialize drug market agents (dealers and users) in high-activity tracts."""
        records = []
        for _, row in df.iterrows():
            activity = row.get("drug_market_activity", 0.0)
            n_dealers = int(activity * 5)
            n_users = int(activity * 20)
            for _ in range(n_dealers):
                records.append({
                    "tract_id": row["tract_id"],
                    "role": "dealer",
                    "active": True,
                })
            for _ in range(n_users):
                records.append({
                    "tract_id": row["tract_id"],
                    "role": "user",
                    "in_treatment": False,
                    "active": True,
                })
        self.drug_market = pd.DataFrame(records) if records else pd.DataFrame(
            columns=["tract_id", "role", "active"]
        )

    def _init_decision_makers(self):
        """Initialize SF Board of Supervisors (11 members)."""
        # Ideology scores: -1 (progressive) to +1 (moderate/conservative)
        self.decision_makers = pd.DataFrame([
            {"district": i + 1, "ideology_score": score, "name": f"Supervisor D{i+1}"}
            for i, score in enumerate([
                -0.8, -0.6, -0.3, 0.1, -0.2,
                -0.7, 0.2, -0.1, 0.3, -0.4, 0.0
            ])
        ])

    def _init_developers(self, df: pd.DataFrame, rng: np.random.Generator):
        """Initialize developer agents."""
        records = []
        # ~50 developer agents with different risk appetites
        for i in range(50):
            records.append({
                "id": i,
                "capital": rng.lognormal(16, 1.0),  # varies widely
                "risk_threshold": 0.10 + rng.uniform(0, 0.15),
                "active_projects": 0,
                "preferred_county": rng.choice(list(df["county_fips"].unique())) if "county_fips" in df.columns else "075",
            })
        self.developers = pd.DataFrame(records)


class SimulationState:
    """Full simulation state at a point in time."""

    def __init__(self):
        self.timestep: int = 0
        self.tracts: dict[str, TractState] = {}
        self.agents: AgentPopulation = AgentPopulation()
        self.history: list[dict] = []  # snapshot per timestep

    def initialize_from_data(
        self,
        baseline_df: pd.DataFrame,
        rng: np.random.Generator,
    ):
        """Initialize state from baseline data."""
        for _, row in baseline_df.iterrows():
            tid = row["tract_id"]
            self.tracts[tid] = TractState(
                tract_id=tid,
                county_fips=row.get("county_fips", ""),
                housing_units=row.get("housing_units", 0),
                vacancy_rate=row.get("vacancy_rate", 0.065),
                median_rent=row.get("median_rent", 2500),
                median_home_price=row.get("median_home_price", 800000),
                max_density_units=row.get("max_density_units", row.get("housing_units", 0) * 2),
                population=row.get("population", 0),
                households=row.get("households", 0),
                median_income=row.get("median_income", 80000),
                businesses_count=row.get("businesses_count", 10),
                crime_incidents=row.get("crime_incidents", 0),
                drug_market_activity=row.get("drug_market_activity", 0),
                transit_accessibility=row.get("transit_accessibility", 0.5),
                commute_mode_car=row.get("commute_mode_car", 0.6),
                commute_mode_transit=row.get("commute_mode_transit", 0.25),
                commute_mode_other=row.get("commute_mode_other", 0.15),
                area_sqmi=row.get("area_sqmi", 0),
                centroid_lat=row.get("centroid_lat", 0),
                centroid_lon=row.get("centroid_lon", 0),
                permit_timeline_days=row.get("permit_timeline_days", 400),
            )
        self.agents.initialize_from_baseline(baseline_df, rng)

    def snapshot(self) -> dict:
        """Capture current state as a dict for history."""
        tract_data = {}
        for tid, ts in self.tracts.items():
            tract_data[tid] = {
                "housing_units": ts.housing_units,
                "vacancy_rate": ts.vacancy_rate,
                "median_rent": ts.median_rent,
                "median_home_price": ts.median_home_price,
                "population": ts.population,
                "businesses_count": ts.businesses_count,
                "crime_incidents": ts.crime_incidents,
                "drug_market_activity": ts.drug_market_activity,
                "transit_accessibility": ts.transit_accessibility,
                "commute_mode_transit": ts.commute_mode_transit,
                "property_tax_revenue": ts.property_tax_revenue,
            }
        return {
            "timestep": self.timestep,
            "tracts": tract_data,
            "aggregate": self._compute_aggregates(),
        }

    def _compute_aggregates(self) -> dict:
        """Compute Bay Area-wide aggregate metrics."""
        tracts = list(self.tracts.values())
        total_pop = sum(t.population for t in tracts)
        total_units = sum(t.housing_units for t in tracts)
        total_businesses = sum(t.businesses_count for t in tracts)
        total_crime = sum(t.crime_incidents for t in tracts)

        # Weighted averages
        if total_pop > 0:
            avg_rent = sum(t.median_rent * t.population for t in tracts) / total_pop
            transit_share = sum(t.commute_mode_transit * t.population for t in tracts) / total_pop
        else:
            avg_rent = 0
            transit_share = 0

        avg_vacancy = np.mean([t.vacancy_rate for t in tracts]) if tracts else 0

        return {
            "total_population": total_pop,
            "total_housing_units": total_units,
            "avg_median_rent": avg_rent,
            "avg_vacancy_rate": avg_vacancy,
            "transit_mode_share": transit_share,
            "total_businesses": total_businesses,
            "total_crime_incidents": total_crime,
        }
