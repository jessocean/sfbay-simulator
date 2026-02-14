"""Merge Census ACS data with tract geometries, compute derived fields.

Produces a tract-level baseline dataset with demographics, housing,
transit, and derived metrics (vacancy rate, transit mode share, etc.).
"""

import logging
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"
PROCESSED_DIR = Path(__file__).resolve().parents[2] / "data" / "processed"


def _load_census_data() -> pd.DataFrame:
    """Load ACS 5-year data from raw CSV."""
    csv_path = RAW_DIR / "census" / "acs_5year_tracts.csv"

    if not csv_path.exists():
        raise FileNotFoundError(
            f"ACS data not found at {csv_path}. Run the census fetch step first."
        )

    df = pd.read_csv(csv_path, dtype={"tract_id": str, "state": str, "county": str, "tract": str})
    logger.info("Loaded ACS data: %d tracts", len(df))
    return df


def _load_tract_geometries() -> gpd.GeoDataFrame:
    """Load processed tract geometries."""
    geojson_path = PROCESSED_DIR / "tracts.geojson"

    if not geojson_path.exists():
        raise FileNotFoundError(
            f"Tract geometries not found at {geojson_path}. Run the geometries transform first."
        )

    gdf = gpd.read_file(geojson_path)
    gdf["tract_id"] = gdf["tract_id"].astype(str)
    logger.info("Loaded tract geometries: %d tracts", len(gdf))
    return gdf


def _compute_derived_fields(df: pd.DataFrame) -> pd.DataFrame:
    """Compute derived fields from raw ACS variables."""
    df = df.copy()

    # Vacancy rate
    df["vacancy_rate"] = np.where(
        df["housing_units"] > 0,
        df["vacant_units"] / df["housing_units"],
        0.065,  # Bay Area default
    )
    df["vacancy_rate"] = df["vacancy_rate"].clip(0, 1).fillna(0.065)

    # Transit mode share
    df["transit_mode_share"] = np.where(
        df["total_commuters"] > 0,
        df["transit_commuters"] / df["total_commuters"],
        0.15,  # Bay Area default
    )
    df["transit_mode_share"] = df["transit_mode_share"].clip(0, 1).fillna(0.15)

    # Commute mode breakdown (estimated from transit share)
    df["commute_mode_transit"] = df["transit_mode_share"]
    df["commute_mode_car"] = np.where(
        df["transit_mode_share"] > 0,
        (1 - df["transit_mode_share"]) * 0.75,  # ~75% of non-transit is car
        0.60,
    )
    df["commute_mode_other"] = 1.0 - df["commute_mode_car"] - df["commute_mode_transit"]
    df["commute_mode_other"] = df["commute_mode_other"].clip(0, 1)

    # Households (estimated as housing_units * (1 - vacancy_rate))
    df["households"] = (df["housing_units"] * (1 - df["vacancy_rate"])).round(0)
    df["households"] = df["households"].fillna(0).clip(lower=0)

    # Population density (per sq mi)
    df["pop_density"] = np.where(
        df["area_sqmi"] > 0,
        df["population"] / df["area_sqmi"],
        0,
    )

    # Median home price (use median_home_value directly)
    df["median_home_price"] = df.get("median_home_value", pd.Series(dtype=float))
    if "median_home_value" in df.columns:
        df["median_home_price"] = df["median_home_value"]
    else:
        df["median_home_price"] = 800000  # Bay Area default

    # Estimated property tax revenue per tract (1.1% of assessed value, rough approximation)
    df["property_tax_revenue"] = (
        df["median_home_price"].fillna(800000)
        * df["housing_units"].fillna(0)
        * 0.011  # approximate effective tax rate
        * 0.5    # assessed value is often below market value (Prop 13)
    )

    # Permit timeline (rough default, varies by jurisdiction)
    df["permit_timeline_days"] = 400  # days, default

    # Max density (rough estimate: current units * 2 as zoning cap)
    df["max_density_units"] = df["housing_units"].fillna(0) * 2.0

    logger.info("Computed derived fields for %d tracts", len(df))
    return df


def _fill_missing_values(df: pd.DataFrame) -> pd.DataFrame:
    """Fill missing values with reasonable Bay Area defaults."""
    defaults = {
        "population": 4000,
        "median_income": 80000,
        "housing_units": 1500,
        "vacant_units": 100,
        "median_rent": 2500,
        "median_home_value": 800000,
        "median_home_price": 800000,
        "total_commuters": 2000,
        "transit_commuters": 300,
    }

    for col, default in defaults.items():
        if col in df.columns:
            n_missing = df[col].isna().sum()
            if n_missing > 0:
                logger.info("Filling %d missing values in '%s' with default %s", n_missing, col, default)
                df[col] = df[col].fillna(default)

    return df


def transform() -> Path:
    """Merge Census data with geometries and compute demographics baseline.

    Returns:
        Path to the output tract_baseline.parquet file.
    """
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    output_file = PROCESSED_DIR / "tract_baseline.parquet"

    if output_file.exists():
        logger.info("tract_baseline.parquet already exists at %s, skipping", output_file)
        return output_file

    # Load data
    census_df = _load_census_data()
    tracts_gdf = _load_tract_geometries()

    # Merge census data onto tract geometries
    merged = tracts_gdf.merge(census_df, on="tract_id", how="left")
    logger.info("Merged: %d tracts (%d with census data)", len(merged), merged["population"].notna().sum())

    # Fill missing values
    merged = _fill_missing_values(merged)

    # Compute derived fields
    merged = _compute_derived_fields(merged)

    # Select output columns (drop geometry for parquet)
    output_cols = [
        "tract_id", "county_fips",
        "centroid_lat", "centroid_lon", "area_sqmi",
        "population", "households", "median_income", "pop_density",
        "housing_units", "vacant_units", "vacancy_rate",
        "median_rent", "median_home_value", "median_home_price",
        "total_commuters", "transit_commuters", "transit_mode_share",
        "commute_mode_car", "commute_mode_transit", "commute_mode_other",
        "property_tax_revenue", "permit_timeline_days", "max_density_units",
    ]
    existing_cols = [c for c in output_cols if c in merged.columns]
    df_out = pd.DataFrame(merged[existing_cols])

    # Save as parquet
    df_out.to_parquet(output_file, index=False)
    logger.info("Saved tract baseline: %d tracts, %d columns to %s", len(df_out), len(existing_cols), output_file)

    return output_file


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    transform()
