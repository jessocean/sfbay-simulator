"""Process building permits data and compute per-tract housing construction metrics.

Reads SF building permits from Socrata data, geocodes to tracts, and
computes construction rates and existing stock summaries.
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

# Building permit types that represent new housing construction
NEW_CONSTRUCTION_TYPES = [
    "new construction",
    "new construction wood frame",
    "new construction condominium",
]

# Permit statuses that indicate active/completed construction
ACTIVE_STATUSES = [
    "issued", "complete", "approved",
]


def _load_building_permits() -> pd.DataFrame:
    """Load raw SF building permits data."""
    permits_path = RAW_DIR / "socrata" / "sf_building_permits.csv"

    if not permits_path.exists():
        logger.warning("Building permits data not found at %s", permits_path)
        return pd.DataFrame()

    df = pd.read_csv(permits_path, low_memory=False)
    logger.info("Loaded %d building permits", len(df))
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


def _filter_housing_permits(df: pd.DataFrame) -> pd.DataFrame:
    """Filter permits to housing-related construction."""
    if df.empty:
        return df

    df = df.copy()

    # Standardize column names (Socrata field names vary)
    col_mapping = {}
    for col in df.columns:
        lower = col.lower().replace(" ", "_")
        col_mapping[col] = lower
    df = df.rename(columns=col_mapping)

    # Filter to housing-related permits
    # Look for residential use type or new construction description
    type_col = None
    for candidate in ["permit_type_definition", "description", "proposed_use", "existing_use"]:
        if candidate in df.columns:
            type_col = candidate
            break

    if type_col:
        housing_mask = df[type_col].str.lower().str.contains(
            r"residential|apartment|dwelling|housing|condo|family",
            na=False,
        )
        df = df[housing_mask].copy()
        logger.info("Filtered to %d housing-related permits", len(df))

    # Filter to relevant statuses
    status_col = None
    for candidate in ["status", "current_status", "permit_status"]:
        if candidate in df.columns:
            status_col = candidate
            break

    if status_col:
        status_mask = df[status_col].str.lower().isin(ACTIVE_STATUSES)
        df = df[status_mask].copy()
        logger.info("Filtered to %d active/complete permits", len(df))

    return df


def _geocode_permits_to_tracts(permits_df: pd.DataFrame, tracts_gdf: gpd.GeoDataFrame) -> pd.DataFrame:
    """Assign each permit to a census tract via spatial join."""
    if permits_df.empty:
        return pd.DataFrame(columns=["tract_id", "units_proposed", "is_new_construction", "filed_date"])

    # Find lat/lon columns
    lat_col = lon_col = None
    for candidate in ["latitude", "lat", "location_lat"]:
        if candidate in permits_df.columns:
            lat_col = candidate
            break
    for candidate in ["longitude", "lon", "lng", "location_lng"]:
        if candidate in permits_df.columns:
            lon_col = candidate
            break

    if lat_col is None or lon_col is None:
        logger.warning("No lat/lon columns found in permits data; cannot geocode to tracts")
        return pd.DataFrame(columns=["tract_id", "units_proposed", "is_new_construction", "filed_date"])

    # Create GeoDataFrame from permits
    permits_df = permits_df.copy()
    permits_df[lat_col] = pd.to_numeric(permits_df[lat_col], errors="coerce")
    permits_df[lon_col] = pd.to_numeric(permits_df[lon_col], errors="coerce")

    # Drop rows without valid coordinates
    valid_mask = permits_df[lat_col].notna() & permits_df[lon_col].notna()
    permits_df = permits_df[valid_mask].copy()

    if permits_df.empty:
        logger.warning("No permits with valid coordinates")
        return pd.DataFrame(columns=["tract_id", "units_proposed", "is_new_construction", "filed_date"])

    geometry = [Point(xy) for xy in zip(permits_df[lon_col], permits_df[lat_col])]
    permits_gdf = gpd.GeoDataFrame(permits_df, geometry=geometry, crs="EPSG:4326")

    # Spatial join
    joined = gpd.sjoin(permits_gdf, tracts_gdf[["tract_id", "geometry"]], how="left", predicate="within")

    logger.info("Geocoded %d permits to tracts (%d matched)", len(joined), joined["tract_id"].notna().sum())

    # Extract useful fields
    result = pd.DataFrame()
    result["tract_id"] = joined["tract_id"]

    # Number of proposed units
    for candidate in ["proposed_units", "units_proposed", "number_of_proposed_stories",
                       "proposed_dwelling_units", "number_of_units"]:
        if candidate in joined.columns:
            result["units_proposed"] = pd.to_numeric(joined[candidate], errors="coerce").fillna(1)
            break
    else:
        result["units_proposed"] = 1

    # Identify new construction vs renovation
    desc_col = None
    for candidate in ["permit_type_definition", "description"]:
        if candidate in joined.columns:
            desc_col = candidate
            break
    if desc_col:
        result["is_new_construction"] = joined[desc_col].str.lower().str.contains(
            "new construction", na=False
        )
    else:
        result["is_new_construction"] = False

    # Filed date
    for candidate in ["filed_date", "permit_creation_date", "date_filed"]:
        if candidate in joined.columns:
            result["filed_date"] = pd.to_datetime(joined[candidate], errors="coerce")
            break
    else:
        result["filed_date"] = pd.NaT

    return result


def _compute_tract_housing_metrics(permits_df: pd.DataFrame) -> pd.DataFrame:
    """Compute per-tract housing construction metrics."""
    if permits_df.empty or "tract_id" not in permits_df.columns:
        return pd.DataFrame(columns=[
            "tract_id", "total_permits", "new_construction_permits",
            "total_units_proposed", "new_units_proposed",
            "annual_construction_rate",
        ])

    # Drop rows without tract assignment
    df = permits_df.dropna(subset=["tract_id"]).copy()

    grouped = df.groupby("tract_id").agg(
        total_permits=("tract_id", "size"),
        new_construction_permits=("is_new_construction", "sum"),
        total_units_proposed=("units_proposed", "sum"),
    ).reset_index()

    # New construction units
    new_only = df[df["is_new_construction"]].groupby("tract_id")["units_proposed"].sum().reset_index()
    new_only.columns = ["tract_id", "new_units_proposed"]
    grouped = grouped.merge(new_only, on="tract_id", how="left")
    grouped["new_units_proposed"] = grouped["new_units_proposed"].fillna(0)

    # Annual construction rate (rough: total over ~5 year window)
    grouped["annual_construction_rate"] = grouped["total_units_proposed"] / 5.0

    logger.info("Computed housing metrics for %d tracts", len(grouped))
    return grouped


def transform() -> Path:
    """Run housing stock transform pipeline.

    Returns:
        Path to the output housing_stock.parquet file.
    """
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    output_file = PROCESSED_DIR / "housing_stock.parquet"

    if output_file.exists():
        logger.info("housing_stock.parquet already exists at %s, skipping", output_file)
        return output_file

    # Load data
    permits_df = _load_building_permits()
    tracts_gdf = _load_tract_geometries()

    # Filter to housing permits
    housing_permits = _filter_housing_permits(permits_df)

    # Geocode to tracts
    geocoded = _geocode_permits_to_tracts(housing_permits, tracts_gdf)

    # Compute metrics
    metrics = _compute_tract_housing_metrics(geocoded)

    # Ensure all tracts are represented
    all_tracts = tracts_gdf[["tract_id"]].copy()
    result = all_tracts.merge(metrics, on="tract_id", how="left")

    # Fill missing with zeros
    fill_cols = [
        "total_permits", "new_construction_permits",
        "total_units_proposed", "new_units_proposed",
        "annual_construction_rate",
    ]
    for col in fill_cols:
        if col in result.columns:
            result[col] = result[col].fillna(0)

    result.to_parquet(output_file, index=False)
    logger.info("Saved housing stock data: %d tracts to %s", len(result), output_file)

    return output_file


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    transform()
