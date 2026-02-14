"""Geocode SF crime incidents to tracts, compute per-tract crime rates and drug market scores.

Reads SF crime incident data from Socrata, assigns incidents to census tracts
via spatial join, and computes per-tract crime rates and drug market activity scores.
"""

import logging
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import Point

logger = logging.getLogger(__name__)

RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"
PROCESSED_DIR = Path(__file__).resolve().parents[2] / "data" / "processed"

# Drug-related incident categories (SF PD classification)
DRUG_CATEGORIES = [
    "drug offense",
    "drug violation",
    "drug/narcotic",
    "drug paraphernalia",
    "under influence of drugs",
    "possession of narcotics",
    "sale of narcotics",
    "narcotics",
]

# Violent crime categories for weighting
VIOLENT_CATEGORIES = [
    "assault",
    "robbery",
    "homicide",
    "rape",
    "weapons offense",
    "weapons carrying",
]

# Property crime categories
PROPERTY_CATEGORIES = [
    "burglary",
    "larceny theft",
    "motor vehicle theft",
    "stolen property",
    "vandalism",
    "arson",
]


def _load_crime_data() -> pd.DataFrame:
    """Load raw SF crime incident data."""
    crime_path = RAW_DIR / "socrata" / "sf_crime_incidents.csv"

    if not crime_path.exists():
        logger.warning("Crime data not found at %s", crime_path)
        return pd.DataFrame()

    df = pd.read_csv(crime_path, low_memory=False)
    logger.info("Loaded %d crime incidents", len(df))
    return df


def _load_tract_geometries() -> gpd.GeoDataFrame:
    """Load processed tract geometries for spatial joining."""
    geojson_path = PROCESSED_DIR / "tracts.geojson"

    if not geojson_path.exists():
        raise FileNotFoundError(
            f"Tract geometries not found at {geojson_path}. Run geometries transform first."
        )

    gdf = gpd.read_file(geojson_path)
    gdf["tract_id"] = gdf["tract_id"].astype(str)
    return gdf


def _standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Standardize column names from Socrata crime data."""
    if df.empty:
        return df

    df = df.copy()

    # Map common Socrata column names to standard names
    col_map = {}
    for col in df.columns:
        lower = col.lower().replace(" ", "_")
        col_map[col] = lower
    df = df.rename(columns=col_map)

    return df


def _geocode_incidents_to_tracts(crime_df: pd.DataFrame, tracts_gdf: gpd.GeoDataFrame) -> pd.DataFrame:
    """Assign each crime incident to a census tract via spatial join."""
    if crime_df.empty:
        return pd.DataFrame(columns=["tract_id", "incident_category", "incident_date"])

    # Find lat/lon columns
    lat_col = lon_col = None
    for candidate in ["latitude", "lat", "point_y", "y"]:
        if candidate in crime_df.columns:
            lat_col = candidate
            break
    for candidate in ["longitude", "lon", "lng", "point_x", "x"]:
        if candidate in crime_df.columns:
            lon_col = candidate
            break

    if lat_col is None or lon_col is None:
        logger.warning("No lat/lon columns found in crime data; cannot geocode to tracts")
        return pd.DataFrame(columns=["tract_id", "incident_category", "incident_date"])

    crime_df = crime_df.copy()
    crime_df[lat_col] = pd.to_numeric(crime_df[lat_col], errors="coerce")
    crime_df[lon_col] = pd.to_numeric(crime_df[lon_col], errors="coerce")

    # Filter valid coordinates (San Francisco bounding box)
    valid_mask = (
        crime_df[lat_col].notna()
        & crime_df[lon_col].notna()
        & (crime_df[lat_col] > 37.6)
        & (crime_df[lat_col] < 37.85)
        & (crime_df[lon_col] > -122.55)
        & (crime_df[lon_col] < -122.35)
    )
    crime_df = crime_df[valid_mask].copy()
    logger.info("Valid geocoded incidents: %d", len(crime_df))

    if crime_df.empty:
        return pd.DataFrame(columns=["tract_id", "incident_category", "incident_date"])

    # Create GeoDataFrame
    geometry = [Point(xy) for xy in zip(crime_df[lon_col], crime_df[lat_col])]
    crime_gdf = gpd.GeoDataFrame(crime_df, geometry=geometry, crs="EPSG:4326")

    # Spatial join - only keep SF tracts (county_fips == "075")
    sf_tracts = tracts_gdf[tracts_gdf["county_fips"] == "075"][["tract_id", "geometry"]].copy()
    if sf_tracts.empty:
        # If no county_fips filter works, try using all tracts
        sf_tracts = tracts_gdf[["tract_id", "geometry"]].copy()

    joined = gpd.sjoin(crime_gdf, sf_tracts, how="left", predicate="within")
    logger.info("Geocoded %d incidents to tracts", joined["tract_id"].notna().sum())

    # Extract key fields
    result = pd.DataFrame()
    result["tract_id"] = joined["tract_id"]

    # Find incident category column
    for candidate in ["incident_category", "category", "incident_subcategory", "offense_description"]:
        if candidate in joined.columns:
            result["incident_category"] = joined[candidate].str.lower().fillna("unknown")
            break
    else:
        result["incident_category"] = "unknown"

    # Find date column
    for candidate in ["incident_date", "date", "incident_datetime", "report_datetime"]:
        if candidate in joined.columns:
            result["incident_date"] = pd.to_datetime(joined[candidate], errors="coerce")
            break
    else:
        result["incident_date"] = pd.NaT

    return result


def _compute_tract_crime_metrics(incidents_df: pd.DataFrame) -> pd.DataFrame:
    """Compute per-tract crime rates and drug market activity scores."""
    if incidents_df.empty or "tract_id" not in incidents_df.columns:
        return pd.DataFrame(columns=[
            "tract_id", "total_incidents", "violent_incidents", "property_incidents",
            "drug_incidents", "crime_rate_normalized", "drug_market_activity",
        ])

    df = incidents_df.dropna(subset=["tract_id"]).copy()

    # Total incidents per tract
    total = df.groupby("tract_id").size().reset_index(name="total_incidents")

    # Categorize incidents
    df["is_violent"] = df["incident_category"].str.contains(
        "|".join(VIOLENT_CATEGORIES), na=False
    )
    df["is_property"] = df["incident_category"].str.contains(
        "|".join(PROPERTY_CATEGORIES), na=False
    )
    df["is_drug"] = df["incident_category"].str.contains(
        "|".join(DRUG_CATEGORIES), na=False
    )

    violent = df.groupby("tract_id")["is_violent"].sum().reset_index(name="violent_incidents")
    prop = df.groupby("tract_id")["is_property"].sum().reset_index(name="property_incidents")
    drug = df.groupby("tract_id")["is_drug"].sum().reset_index(name="drug_incidents")

    # Merge all
    result = total.merge(violent, on="tract_id", how="left")
    result = result.merge(prop, on="tract_id", how="left")
    result = result.merge(drug, on="tract_id", how="left")

    result = result.fillna(0)

    # Normalize crime rate (0-1 scale, relative to max tract)
    max_incidents = result["total_incidents"].max()
    if max_incidents > 0:
        result["crime_rate_normalized"] = result["total_incidents"] / max_incidents
    else:
        result["crime_rate_normalized"] = 0.0

    # Drug market activity score (0-10 scale)
    max_drug = result["drug_incidents"].max()
    if max_drug > 0:
        result["drug_market_activity"] = (result["drug_incidents"] / max_drug) * 10.0
    else:
        result["drug_market_activity"] = 0.0

    logger.info(
        "Crime metrics: %d tracts, %.0f total incidents, %.0f drug incidents",
        len(result), result["total_incidents"].sum(), result["drug_incidents"].sum(),
    )

    return result


def transform() -> Path:
    """Run crime data transform pipeline.

    Returns:
        Path to the output crime_data.parquet file.
    """
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    output_file = PROCESSED_DIR / "crime_data.parquet"

    if output_file.exists():
        logger.info("crime_data.parquet already exists at %s, skipping", output_file)
        return output_file

    # Load data
    crime_df = _load_crime_data()
    tracts_gdf = _load_tract_geometries()

    # Standardize columns
    crime_df = _standardize_columns(crime_df)

    # Geocode to tracts
    geocoded = _geocode_incidents_to_tracts(crime_df, tracts_gdf)

    # Compute metrics
    metrics = _compute_tract_crime_metrics(geocoded)

    # Ensure all SF tracts are present
    sf_tracts = tracts_gdf[tracts_gdf["county_fips"] == "075"][["tract_id"]].copy()
    if sf_tracts.empty:
        sf_tracts = tracts_gdf[["tract_id"]].copy()

    result = sf_tracts.merge(metrics, on="tract_id", how="left")

    # Fill missing with zeros
    fill_cols = [
        "total_incidents", "violent_incidents", "property_incidents",
        "drug_incidents", "crime_rate_normalized", "drug_market_activity",
    ]
    for col in fill_cols:
        if col in result.columns:
            result[col] = result[col].fillna(0)

    result.to_parquet(output_file, index=False)
    logger.info("Saved crime data: %d tracts to %s", len(result), output_file)

    return output_file


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    transform()
