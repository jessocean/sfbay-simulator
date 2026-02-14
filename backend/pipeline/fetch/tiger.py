"""Fetch TIGER/Line tract shapefiles for 9 Bay Area counties from Census Bureau."""

import io
import logging
import zipfile
from pathlib import Path

import geopandas as gpd
import pandas as pd
import requests

logger = logging.getLogger(__name__)

# Bay Area county FIPS codes (state FIPS = 06)
STATE_FIPS = "06"
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

# TIGER files are organized by state, not county
TIGER_URL = "https://www2.census.gov/geo/tiger/TIGER2024/TRACT/tl_2024_06_tract.zip"
RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"


def _download_state_shapefile(output_dir: Path) -> Path:
    """Download and extract TIGER/Line shapefile for California.

    Returns the path to the extracted .shp file.
    """
    extract_dir = output_dir / "tiger_06"
    shp_files = list(extract_dir.glob("*.shp")) if extract_dir.exists() else []
    if shp_files:
        logger.info("TIGER shapefile already downloaded, skipping")
        return shp_files[0]

    logger.info("Downloading California TIGER/Line tract shapefile...")
    response = requests.get(TIGER_URL, timeout=300)
    response.raise_for_status()

    extract_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
        zf.extractall(extract_dir)

    shp_files = list(extract_dir.glob("*.shp"))
    if not shp_files:
        raise FileNotFoundError("No .shp file found in downloaded archive")

    logger.info("Extracted shapefile: %s", shp_files[0])
    return shp_files[0]


def _simplify_geometry(geom, tolerance: float = 0.0001):
    """Simplify a geometry for web rendering while preserving topology."""
    if geom is None or geom.is_empty:
        return geom
    return geom.simplify(tolerance, preserve_topology=True)


def fetch() -> Path:
    """Download TIGER/Line tract shapefiles, filter to Bay Area counties.

    Returns:
        Path to the Bay Area tracts GeoJSON file.
    """
    output_dir = RAW_DIR / "tiger"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "bay_area_tracts_raw.geojson"

    if output_file.exists():
        logger.info("Combined TIGER GeoJSON already exists at %s, skipping", output_file)
        return output_file

    # Download full California shapefile
    shp_path = _download_state_shapefile(output_dir)
    gdf = gpd.read_file(shp_path)

    # Filter to Bay Area counties
    bay_area_fips = [f"{STATE_FIPS}{c}" for c in BAY_AREA_COUNTIES.keys()]
    # COUNTYFP column has the 3-digit county code
    gdf = gdf[gdf["COUNTYFP"].isin(BAY_AREA_COUNTIES.keys())].copy()
    logger.info("Filtered to %d Bay Area tracts from %d total CA tracts", len(gdf), len(gpd.read_file(shp_path)))

    # Add county name
    gdf["county_fips"] = gdf["COUNTYFP"]
    gdf["county_name"] = gdf["COUNTYFP"].map(BAY_AREA_COUNTIES)

    # Ensure CRS is WGS84
    if gdf.crs is None or gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs(epsg=4326)

    # Simplify geometries for web rendering
    logger.info("Simplifying geometries (tolerance=0.0001 degrees)...")
    gdf["geometry"] = gdf["geometry"].apply(lambda g: _simplify_geometry(g, tolerance=0.0001))

    # Keep only essential columns
    keep_cols = ["GEOID", "STATEFP", "COUNTYFP", "TRACTCE", "ALAND", "AWATER",
                 "county_fips", "county_name", "geometry"]
    existing_cols = [c for c in keep_cols if c in gdf.columns]
    gdf = gdf[existing_cols]

    gdf.to_file(output_file, driver="GeoJSON")
    logger.info("Saved Bay Area TIGER GeoJSON with %d tracts to %s", len(gdf), output_file)

    return output_file


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    fetch()
