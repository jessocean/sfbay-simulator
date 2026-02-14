"""Create agent_populations.parquet by sampling from tract baseline data.

Uses the AgentPopulation class from simulation.core.state to generate
household, business, drug market, decision maker, and developer agents.
"""

import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Add project root to path so we can import simulation modules
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

PROCESSED_DIR = Path(__file__).resolve().parents[2] / "data" / "processed"

# Default random seed for reproducibility
DEFAULT_SEED = 42


def _load_baseline() -> pd.DataFrame:
    """Load tract baseline data."""
    baseline_path = PROCESSED_DIR / "tract_baseline.parquet"

    if not baseline_path.exists():
        raise FileNotFoundError(
            f"Tract baseline not found at {baseline_path}. Run demographics transform first."
        )

    df = pd.read_parquet(baseline_path)
    df["tract_id"] = df["tract_id"].astype(str)
    logger.info("Loaded tract baseline: %d tracts", len(df))
    return df


def _load_supplementary_data(baseline_df: pd.DataFrame) -> pd.DataFrame:
    """Merge supplementary data (crime, housing stock, transit) into baseline."""
    df = baseline_df.copy()

    # Merge crime data
    crime_path = PROCESSED_DIR / "crime_data.parquet"
    if crime_path.exists():
        crime_df = pd.read_parquet(crime_path)
        crime_df["tract_id"] = crime_df["tract_id"].astype(str)
        df = df.merge(
            crime_df[["tract_id", "total_incidents", "drug_market_activity"]],
            on="tract_id", how="left",
        )
        df["crime_incidents"] = df["total_incidents"].fillna(0)
        df["drug_market_activity"] = df["drug_market_activity"].fillna(0)
        df = df.drop(columns=["total_incidents"], errors="ignore")
        logger.info("Merged crime data")
    else:
        df["crime_incidents"] = 0
        df["drug_market_activity"] = 0
        logger.warning("No crime data found; using defaults")

    # Merge housing stock data
    housing_path = PROCESSED_DIR / "housing_stock.parquet"
    if housing_path.exists():
        housing_df = pd.read_parquet(housing_path)
        housing_df["tract_id"] = housing_df["tract_id"].astype(str)
        df = df.merge(
            housing_df[["tract_id", "annual_construction_rate", "new_units_proposed"]],
            on="tract_id", how="left",
        )
        df["construction_pipeline"] = df["new_units_proposed"].fillna(0) / 5.0  # approximate annual
        df = df.drop(columns=["new_units_proposed"], errors="ignore")
        df["annual_construction_rate"] = df["annual_construction_rate"].fillna(0)
        logger.info("Merged housing stock data")
    else:
        df["construction_pipeline"] = 0
        df["annual_construction_rate"] = 0
        logger.warning("No housing stock data found; using defaults")

    # Transit accessibility (compute from BART station proximity if available)
    # Default to a basic score based on transit mode share
    if "transit_accessibility" not in df.columns:
        if "transit_mode_share" in df.columns:
            # Rough proxy: higher transit commute share = better accessibility
            df["transit_accessibility"] = (df["transit_mode_share"] / df["transit_mode_share"].max()).clip(0, 1)
        else:
            df["transit_accessibility"] = 0.5

    # Business count (estimate from registered businesses if available)
    businesses_path = RAW_DIR / "socrata" / "sf_registered_businesses.csv"
    if "businesses_count" not in df.columns:
        df["businesses_count"] = 10  # default

    return df


# Need RAW_DIR for business data path
RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"


def _initialize_agents(baseline_df: pd.DataFrame, seed: int = DEFAULT_SEED) -> dict[str, pd.DataFrame]:
    """Initialize all agent populations from baseline data.

    Uses the AgentPopulation class from simulation.core.state.

    Returns:
        Dict mapping agent type to DataFrame.
    """
    try:
        from simulation.core.state import AgentPopulation
    except ImportError:
        try:
            from simulation.core.state import AgentPopulation
        except ImportError:
            logger.warning("Could not import AgentPopulation; using inline initialization")
            return _initialize_agents_inline(baseline_df, seed)

    rng = np.random.default_rng(seed)

    population = AgentPopulation()
    population.initialize_from_baseline(baseline_df, rng)

    result = {}
    if population.households is not None and not population.households.empty:
        result["households"] = population.households
        logger.info("Initialized %d household agents", len(population.households))

    if population.businesses is not None and not population.businesses.empty:
        result["businesses"] = population.businesses
        logger.info("Initialized %d business agents", len(population.businesses))

    if population.drug_market is not None and not population.drug_market.empty:
        result["drug_market"] = population.drug_market
        logger.info("Initialized %d drug market agents", len(population.drug_market))

    if population.decision_makers is not None and not population.decision_makers.empty:
        result["decision_makers"] = population.decision_makers
        logger.info("Initialized %d decision maker agents", len(population.decision_makers))

    if population.developers is not None and not population.developers.empty:
        result["developers"] = population.developers
        logger.info("Initialized %d developer agents", len(population.developers))

    return result


def _initialize_agents_inline(baseline_df: pd.DataFrame, seed: int = DEFAULT_SEED) -> dict[str, pd.DataFrame]:
    """Fallback: initialize agents without importing AgentPopulation.

    Mirrors the logic in simulation.core.state.AgentPopulation.
    """
    rng = np.random.default_rng(seed)
    result = {}

    # Households (~10% sample)
    household_records = []
    sample_rate = 0.1
    for _, row in baseline_df.iterrows():
        n = max(1, int(row.get("households", 100) * sample_rate))
        for _ in range(n):
            income = max(10000, rng.normal(
                row.get("median_income", 80000),
                row.get("median_income", 80000) * 0.4,
            ))
            car_pct = row.get("commute_mode_car", 0.6)
            transit_pct = row.get("commute_mode_transit", 0.25)
            other_pct = max(0, 1.0 - car_pct - transit_pct)
            # Normalize
            total = car_pct + transit_pct + other_pct
            if total > 0:
                car_pct /= total
                transit_pct /= total
                other_pct /= total
            else:
                car_pct, transit_pct, other_pct = 0.6, 0.25, 0.15

            household_records.append({
                "tract_id": row["tract_id"],
                "income": income,
                "rent_share": min(1.0, row.get("median_rent", 2500) * 12 / max(income, 1)),
                "commute_mode": rng.choice(
                    ["car", "transit", "other"],
                    p=[car_pct, transit_pct, other_pct],
                ),
                "wants_to_move": False,
            })
    result["households"] = pd.DataFrame(household_records)
    logger.info("Initialized %d household agents (inline)", len(result["households"]))

    # Businesses (20% sample)
    business_records = []
    for _, row in baseline_df.iterrows():
        n = max(0, int(row.get("businesses_count", 10) * 0.2))
        for _ in range(n):
            business_records.append({
                "tract_id": row["tract_id"],
                "revenue": max(10000, rng.lognormal(11.5, 1.0)),
                "employees": max(1, int(rng.lognormal(1.5, 1.0))),
                "is_open": True,
            })
    result["businesses"] = pd.DataFrame(business_records) if business_records else pd.DataFrame(
        columns=["tract_id", "revenue", "employees", "is_open"]
    )
    logger.info("Initialized %d business agents (inline)", len(result["businesses"]))

    # Drug market agents
    drug_records = []
    for _, row in baseline_df.iterrows():
        activity = row.get("drug_market_activity", 0.0)
        n_dealers = int(activity * 5)
        n_users = int(activity * 20)
        for _ in range(n_dealers):
            drug_records.append({
                "tract_id": row["tract_id"],
                "role": "dealer",
                "active": True,
            })
        for _ in range(n_users):
            drug_records.append({
                "tract_id": row["tract_id"],
                "role": "user",
                "in_treatment": False,
                "active": True,
            })
    result["drug_market"] = pd.DataFrame(drug_records) if drug_records else pd.DataFrame(
        columns=["tract_id", "role", "active"]
    )
    logger.info("Initialized %d drug market agents (inline)", len(result["drug_market"]))

    # Decision makers (11 SF supervisors)
    result["decision_makers"] = pd.DataFrame([
        {"district": i + 1, "ideology_score": score, "name": f"Supervisor D{i+1}"}
        for i, score in enumerate([
            -0.8, -0.6, -0.3, 0.1, -0.2,
            -0.7, 0.2, -0.1, 0.3, -0.4, 0.0,
        ])
    ])
    logger.info("Initialized %d decision maker agents (inline)", len(result["decision_makers"]))

    # Developers (50 agents)
    dev_records = []
    county_choices = list(baseline_df["county_fips"].unique()) if "county_fips" in baseline_df.columns else ["075"]
    for i in range(50):
        dev_records.append({
            "id": i,
            "capital": rng.lognormal(16, 1.0),
            "risk_threshold": 0.10 + rng.uniform(0, 0.15),
            "active_projects": 0,
            "preferred_county": rng.choice(county_choices),
        })
    result["developers"] = pd.DataFrame(dev_records)
    logger.info("Initialized %d developer agents (inline)", len(result["developers"]))

    return result


def transform(seed: int = DEFAULT_SEED) -> Path:
    """Run agent initialization pipeline.

    Returns:
        Path to the output agent_populations.parquet file.
    """
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    output_file = PROCESSED_DIR / "agent_populations.parquet"

    if output_file.exists():
        logger.info("agent_populations.parquet already exists at %s, skipping", output_file)
        return output_file

    # Load and enrich baseline
    baseline = _load_baseline()
    baseline = _load_supplementary_data(baseline)

    # Initialize agents
    agents = _initialize_agents(baseline, seed=seed)

    # Save each agent type as a separate parquet file, plus a combined index
    agent_dir = PROCESSED_DIR / "agents"
    agent_dir.mkdir(parents=True, exist_ok=True)

    index_records = []
    for agent_type, df in agents.items():
        agent_file = agent_dir / f"{agent_type}.parquet"
        df.to_parquet(agent_file, index=False)
        index_records.append({
            "agent_type": agent_type,
            "file": str(agent_file),
            "count": len(df),
        })
        logger.info("Saved %d %s agents to %s", len(df), agent_type, agent_file)

    # Save index
    index_df = pd.DataFrame(index_records)
    index_df.to_parquet(output_file, index=False)
    logger.info("Saved agent population index to %s", output_file)

    return output_file


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    transform()
