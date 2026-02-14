"""Transform raw TIGER shapefiles into processed tract geometries.

Loads raw shapefiles, filters to Bay Area, simplifies geometries,
computes centroids and areas, and outputs tracts.geojson.
"""

import logging
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"
PROCESSED_DIR = Path(__file__).resolve().parents[2] / "data" / "processed"

STATE_FIPS = "06"
BAY_AREA_COUNTY_FIPS = {"001", "013", "041", "055", "075", "081", "085", "095", "097"}

# Square meters to square miles conversion
SQ_METERS_TO_SQ_MILES = 3.861e-7


def _load_raw_tracts() -> gpd.GeoDataFrame:
    """Load raw tract geometries from TIGER GeoJSON or shapefiles."""
    geojson_path = RAW_DIR / "tiger" / "bay_area_tracts_raw.geojson"

    if geojson_path.exists():
        logger.info("Loading raw tracts from GeoJSON: %s", geojson_path)
        gdf = gpd.read_file(geojson_path)
        return gdf

    # Fallback: try loading individual county shapefiles
    tiger_dir = RAW_DIR / "tiger"
    all_gdfs = []

    for county_fips in BAY_AREA_COUNTY_FIPS:
        county_dir = tiger_dir / f"tiger_{STATE_FIPS}{county_fips}"
        if not county_dir.exists():
            continue
        shp_files = list(county_dir.glob("*.shp"))
        if shp_files:
            gdf = gpd.read_file(shp_files[0])
            gdf["county_fips"] = county_fips
            all_gdfs.append(gdf)

    if not all_gdfs:
        raise FileNotFoundError(
            f"No TIGER data found in {tiger_dir}. Run the tiger fetch step first."
        )

    combined = gpd.GeoDataFrame(pd.concat(all_gdfs, ignore_index=True))
    return combined


def _filter_bay_area(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Filter to only Bay Area county tracts."""
    if "COUNTYFP" in gdf.columns:
        mask = gdf["COUNTYFP"].isin(BAY_AREA_COUNTY_FIPS)
        filtered = gdf[mask].copy()
    elif "county_fips" in gdf.columns:
        mask = gdf["county_fips"].isin(BAY_AREA_COUNTY_FIPS)
        filtered = gdf[mask].copy()
    else:
        logger.warning("No county FIPS column found; using all tracts")
        filtered = gdf.copy()

    logger.info("Filtered to %d Bay Area tracts", len(filtered))
    return filtered


def _ensure_wgs84(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Ensure CRS is WGS84 (EPSG:4326)."""
    if gdf.crs is None:
        logger.warning("No CRS set; assuming WGS84")
        gdf = gdf.set_crs(epsg=4326)
    elif gdf.crs.to_epsg() != 4326:
        logger.info("Reprojecting from %s to EPSG:4326", gdf.crs)
        gdf = gdf.to_crs(epsg=4326)
    return gdf


def _simplify_geometries(gdf: gpd.GeoDataFrame, tolerance: float = 0.0001) -> gpd.GeoDataFrame:
    """Simplify geometries for web rendering.

    Args:
        gdf: GeoDataFrame with tract geometries.
        tolerance: Simplification tolerance in degrees (~11m at Bay Area latitude).

    Returns:
        GeoDataFrame with simplified geometries.
    """
    logger.info("Simplifying %d geometries (tolerance=%.5f degrees)", len(gdf), tolerance)
    gdf = gdf.copy()
    gdf["geometry"] = gdf["geometry"].simplify(tolerance, preserve_topology=True)

    # Remove any empty geometries
    empty_mask = gdf["geometry"].is_empty | gdf["geometry"].isna()
    if empty_mask.any():
        logger.warning("Dropping %d tracts with empty geometries", empty_mask.sum())
        gdf = gdf[~empty_mask]

    return gdf


def _compute_centroids_and_areas(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Compute centroid lat/lon and area in square miles."""
    gdf = gdf.copy()

    # Compute centroids in WGS84
    centroids = gdf["geometry"].centroid
    gdf["centroid_lat"] = centroids.y
    gdf["centroid_lon"] = centroids.x

    # Compute area: use ALAND if available, otherwise project and compute
    if "ALAND" in gdf.columns:
        gdf["area_sqmi"] = pd.to_numeric(gdf["ALAND"], errors="coerce") * SQ_METERS_TO_SQ_MILES
    else:
        # Project to a suitable CRS for area calculation (UTM Zone 10N for Bay Area)
        gdf_projected = gdf.to_crs(epsg=32610)
        gdf["area_sqmi"] = gdf_projected["geometry"].area * SQ_METERS_TO_SQ_MILES

    # Fill any NaN areas with a small default
    gdf["area_sqmi"] = gdf["area_sqmi"].fillna(0.1)

    logger.info(
        "Computed centroids and areas: lat range [%.3f, %.3f], area range [%.3f, %.3f] sqmi",
        gdf["centroid_lat"].min(), gdf["centroid_lat"].max(),
        gdf["area_sqmi"].min(), gdf["area_sqmi"].max(),
    )

    return gdf


def _standardize_columns(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Standardize column names for downstream use."""
    gdf = gdf.copy()

    # Create tract_id from GEOID if available
    if "GEOID" in gdf.columns:
        gdf["tract_id"] = gdf["GEOID"].astype(str)
    elif "tract_id" not in gdf.columns:
        # Try to construct from component fields
        if all(c in gdf.columns for c in ["STATEFP", "COUNTYFP", "TRACTCE"]):
            gdf["tract_id"] = gdf["STATEFP"] + gdf["COUNTYFP"] + gdf["TRACTCE"]
        else:
            gdf["tract_id"] = gdf.index.astype(str)

    # Standardize county_fips
    if "COUNTYFP" in gdf.columns and "county_fips" not in gdf.columns:
        gdf["county_fips"] = gdf["COUNTYFP"]

    # Select output columns
    output_cols = [
        "tract_id", "county_fips", "centroid_lat", "centroid_lon",
        "area_sqmi", "geometry",
    ]
    # Add county_name if available
    if "county_name" in gdf.columns:
        output_cols.insert(2, "county_name")

    existing = [c for c in output_cols if c in gdf.columns]
    return gdf[existing]


def transform() -> Path:
    """Run the full geometry transform pipeline.

    Reads raw TIGER data, filters, simplifies, computes derived fields,
    and writes tracts.geojson.

    Returns:
        Path to the output tracts.geojson file.
    """
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    output_file = PROCESSED_DIR / "tracts.geojson"

    if output_file.exists():
        logger.info("tracts.geojson already exists at %s, skipping", output_file)
        return output_file

    # Load
    gdf = _load_raw_tracts()
    logger.info("Loaded %d raw tracts", len(gdf))

    # Filter
    gdf = _filter_bay_area(gdf)

    # Ensure WGS84
    gdf = _ensure_wgs84(gdf)

    # Simplify
    gdf = _simplify_geometries(gdf, tolerance=0.0001)

    # Compute centroids and areas
    gdf = _compute_centroids_and_areas(gdf)

    # Standardize columns
    gdf = _standardize_columns(gdf)

    # Save
    gdf.to_file(output_file, driver="GeoJSON")
    logger.info("Saved %d processed tracts to %s", len(gdf), output_file)

    return output_file


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    transform()
