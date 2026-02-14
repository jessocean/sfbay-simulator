"""Fetch ACS 5-year data via Census API for 9 Bay Area counties."""

import logging
import os
from pathlib import Path

import pandas as pd
import requests

logger = logging.getLogger(__name__)

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

# ACS 5-year variables to fetch
ACS_VARIABLES = {
    "B01003_001E": "population",
    "B19013_001E": "median_income",
    "B25001_001E": "housing_units",
    "B25002_003E": "vacant_units",
    "B25064_001E": "median_rent",
    "B25077_001E": "median_home_value",
    "B08301_001E": "total_commuters",
    "B08301_010E": "transit_commuters",
}

RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"
ACS_YEAR = 2022  # Most recent available ACS 5-year
BASE_URL = f"https://api.census.gov/data/{ACS_YEAR}/acs/acs5"


def _fetch_county_data(county_fips: str, api_key: str = "") -> list[dict]:
    """Fetch ACS data at tract level for a single county using requests."""
    variable_codes = ",".join(ACS_VARIABLES.keys())
    params = {
        "get": f"NAME,{variable_codes}",
        "for": "tract:*",
        "in": f"state:{STATE_FIPS} county:{county_fips}",
    }
    if api_key:
        params["key"] = api_key

    try:
        resp = requests.get(BASE_URL, params=params, timeout=60)
        resp.raise_for_status()
        data = resp.json()

        # First row is header
        headers = data[0]
        records = []
        for row in data[1:]:
            records.append(dict(zip(headers, row)))

        logger.info(
            "Fetched %d tracts for county %s (%s)",
            len(records), county_fips, BAY_AREA_COUNTIES.get(county_fips, ""),
        )
        return records
    except Exception:
        logger.exception("Failed to fetch ACS data for county %s", county_fips)
        return []


def fetch() -> Path:
    """Fetch ACS 5-year data for all 9 Bay Area counties at tract level.

    Returns:
        Path to the saved CSV file.
    """
    output_dir = RAW_DIR / "census"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "acs_5year_tracts.csv"

    if output_file.exists():
        logger.info("ACS data already cached at %s, skipping", output_file)
        return output_file

    api_key = os.environ.get("CENSUS_API_KEY", "")
    if not api_key:
        logger.warning(
            "CENSUS_API_KEY not set. Requests may be rate-limited. "
            "Get a free key at https://api.census.gov/data/key_signup.html"
        )

    all_records = []
    for county_fips in BAY_AREA_COUNTIES:
        records = _fetch_county_data(county_fips, api_key)
        all_records.extend(records)

    if not all_records:
        raise RuntimeError("Failed to fetch any ACS data")

    df = pd.DataFrame(all_records)

    # Construct GEOID (state + county + tract)
    df["tract_id"] = df["state"] + df["county"] + df["tract"]

    # Rename ACS variables to friendly names
    rename_map = {code: name for code, name in ACS_VARIABLES.items()}
    df = df.rename(columns=rename_map)

    # Convert numeric columns
    numeric_cols = list(ACS_VARIABLES.values())
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Replace negative values (Census uses negative for missing/suppressed)
    for col in numeric_cols:
        if col in df.columns:
            df.loc[df[col] < 0, col] = pd.NA

    df.to_csv(output_file, index=False)
    logger.info("Saved ACS data for %d tracts to %s", len(df), output_file)

    return output_file


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    fetch()
