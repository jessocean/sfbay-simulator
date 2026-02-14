"""Fetch SF OpenData via Socrata (sodapy) for crime, permits, and businesses."""

import logging
import os
from pathlib import Path

import pandas as pd
from sodapy import Socrata

logger = logging.getLogger(__name__)

RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"

# SF OpenData datasets
SF_DOMAIN = "data.sfgov.org"
DATASETS = {
    "crime_incidents": {
        "id": "wg3w-h783",
        "description": "Police Department Incident Reports (2018-present)",
        "filename": "sf_crime_incidents.csv",
    },
    "building_permits": {
        "id": "i98e-djp9",
        "description": "Building Permits",
        "filename": "sf_building_permits.csv",
    },
    "registered_businesses": {
        "id": "g8m3-pdis",
        "description": "Registered Business Locations",
        "filename": "sf_registered_businesses.csv",
    },
}

PAGE_SIZE = 50000  # Records per request
MAX_RECORDS = 500000  # Safety cap per dataset


def _get_socrata_client() -> Socrata:
    """Create Socrata client, optionally with app token."""
    app_token = os.environ.get("SOCRATA_APP_TOKEN", None)
    client = Socrata(SF_DOMAIN, app_token, timeout=60)
    return client


def _fetch_dataset(client: Socrata, dataset_id: str, output_file: Path) -> Path:
    """Fetch a full Socrata dataset using pagination.

    Args:
        client: Socrata client instance.
        dataset_id: Socrata dataset identifier.
        output_file: Path to save the CSV.

    Returns:
        Path to the saved CSV file.
    """
    if output_file.exists():
        logger.info("Dataset %s already cached at %s, skipping", dataset_id, output_file)
        return output_file

    all_records = []
    offset = 0

    while offset < MAX_RECORDS:
        logger.info("Fetching dataset %s: offset=%d, limit=%d", dataset_id, offset, PAGE_SIZE)
        try:
            results = client.get(dataset_id, limit=PAGE_SIZE, offset=offset)
        except Exception:
            logger.exception("Error fetching dataset %s at offset %d", dataset_id, offset)
            break

        if not results:
            break

        all_records.extend(results)
        offset += PAGE_SIZE

        if len(results) < PAGE_SIZE:
            break

    if not all_records:
        logger.warning("No records fetched for dataset %s", dataset_id)
        return output_file

    df = pd.DataFrame(all_records)
    df.to_csv(output_file, index=False)
    logger.info("Saved %d records for dataset %s to %s", len(df), dataset_id, output_file)

    return output_file


def fetch() -> dict[str, Path]:
    """Fetch all SF OpenData datasets.

    Returns:
        Dict mapping dataset name to saved file path.
    """
    output_dir = RAW_DIR / "socrata"
    output_dir.mkdir(parents=True, exist_ok=True)

    client = _get_socrata_client()
    results = {}

    for name, config in DATASETS.items():
        output_file = output_dir / config["filename"]
        logger.info("Fetching %s: %s", name, config["description"])
        try:
            path = _fetch_dataset(client, config["id"], output_file)
            results[name] = path
        except Exception:
            logger.exception("Failed to fetch dataset %s", name)

    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    fetch()
