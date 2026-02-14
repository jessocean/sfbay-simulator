"""Pipeline orchestrator: coordinates full data pipeline from fetch to transform.

Runs all fetch steps, then all transform steps, producing final output files:
  - tracts.geojson         (tract geometries)
  - tract_baseline.parquet (demographics + derived metrics)
  - agent_populations.parquet (agent index with per-type parquet files)

Includes caching: checks if output files already exist and skips steps
that have fresh results.
"""

import logging
import os
import time
from pathlib import Path

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"

# Maximum age of cached files before re-fetching (in seconds)
# Default: 7 days
CACHE_MAX_AGE_SECONDS = int(os.environ.get("PIPELINE_CACHE_MAX_AGE", 7 * 24 * 3600))


def _is_fresh(path: Path, max_age: int = CACHE_MAX_AGE_SECONDS) -> bool:
    """Check if a file exists and is fresh (not older than max_age seconds)."""
    if not path.exists():
        return False
    age = time.time() - path.stat().st_mtime
    return age < max_age


def _ensure_dirs():
    """Ensure all data directories exist."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Fetch steps
# ---------------------------------------------------------------------------

def _fetch_tiger(force: bool = False) -> bool:
    """Fetch TIGER/Line shapefiles."""
    output = RAW_DIR / "tiger" / "bay_area_tracts_raw.geojson"
    if not force and _is_fresh(output):
        logger.info("[SKIP] TIGER data is fresh")
        return True

    try:
        from pipeline.fetch.tiger import fetch
        fetch()
        logger.info("[OK] TIGER fetch complete")
        return True
    except Exception:
        logger.exception("[FAIL] TIGER fetch failed")
        return False


def _fetch_census(force: bool = False) -> bool:
    """Fetch ACS Census data."""
    output = RAW_DIR / "census" / "acs_5year_tracts.csv"
    if not force and _is_fresh(output):
        logger.info("[SKIP] Census ACS data is fresh")
        return True

    try:
        from pipeline.fetch.census import fetch
        fetch()
        logger.info("[OK] Census fetch complete")
        return True
    except Exception:
        logger.exception("[FAIL] Census fetch failed")
        return False


def _fetch_socrata(force: bool = False) -> bool:
    """Fetch SF OpenData via Socrata."""
    output = RAW_DIR / "socrata" / "sf_crime_incidents.csv"
    if not force and _is_fresh(output):
        logger.info("[SKIP] Socrata data is fresh")
        return True

    try:
        from pipeline.fetch.socrata import fetch
        fetch()
        logger.info("[OK] Socrata fetch complete")
        return True
    except Exception:
        logger.exception("[FAIL] Socrata fetch failed")
        return False


def _fetch_transit(force: bool = False) -> bool:
    """Fetch BART transit data."""
    output = RAW_DIR / "transit" / "bart_stations.csv"
    if not force and _is_fresh(output):
        logger.info("[SKIP] Transit data is fresh")
        return True

    try:
        from pipeline.fetch.transit import fetch
        fetch()
        logger.info("[OK] Transit fetch complete")
        return True
    except Exception:
        logger.exception("[FAIL] Transit fetch failed")
        return False


def _fetch_fiscal(force: bool = False) -> bool:
    """Save SF fiscal/budget data."""
    output = RAW_DIR / "fiscal" / "sf_budget_departments.csv"
    if not force and _is_fresh(output):
        logger.info("[SKIP] Fiscal data is fresh")
        return True

    try:
        from pipeline.fetch.fiscal import fetch
        fetch()
        logger.info("[OK] Fiscal data saved")
        return True
    except Exception:
        logger.exception("[FAIL] Fiscal data save failed")
        return False


def _fetch_political(force: bool = False) -> bool:
    """Save SF political data."""
    output = RAW_DIR / "political" / "sf_supervisors.csv"
    if not force and _is_fresh(output):
        logger.info("[SKIP] Political data is fresh")
        return True

    try:
        from pipeline.fetch.political import fetch
        fetch()
        logger.info("[OK] Political data saved")
        return True
    except Exception:
        logger.exception("[FAIL] Political data save failed")
        return False


# ---------------------------------------------------------------------------
# Transform steps
# ---------------------------------------------------------------------------

def _transform_geometries(force: bool = False) -> bool:
    """Transform raw TIGER data into tracts.geojson."""
    output = PROCESSED_DIR / "tracts.geojson"
    if not force and _is_fresh(output):
        logger.info("[SKIP] tracts.geojson is fresh")
        return True

    try:
        from pipeline.transform.geometries import transform
        transform()
        logger.info("[OK] Geometries transform complete")
        return True
    except Exception:
        logger.exception("[FAIL] Geometries transform failed")
        return False


def _transform_demographics(force: bool = False) -> bool:
    """Transform Census data into tract_baseline.parquet."""
    output = PROCESSED_DIR / "tract_baseline.parquet"
    if not force and _is_fresh(output):
        logger.info("[SKIP] tract_baseline.parquet is fresh")
        return True

    try:
        from pipeline.transform.demographics import transform
        transform()
        logger.info("[OK] Demographics transform complete")
        return True
    except Exception:
        logger.exception("[FAIL] Demographics transform failed")
        return False


def _transform_housing_stock(force: bool = False) -> bool:
    """Transform building permits into housing_stock.parquet."""
    output = PROCESSED_DIR / "housing_stock.parquet"
    if not force and _is_fresh(output):
        logger.info("[SKIP] housing_stock.parquet is fresh")
        return True

    try:
        from pipeline.transform.housing_stock import transform
        transform()
        logger.info("[OK] Housing stock transform complete")
        return True
    except Exception:
        logger.exception("[FAIL] Housing stock transform failed")
        return False


def _transform_crime_data(force: bool = False) -> bool:
    """Transform crime incidents into crime_data.parquet."""
    output = PROCESSED_DIR / "crime_data.parquet"
    if not force and _is_fresh(output):
        logger.info("[SKIP] crime_data.parquet is fresh")
        return True

    try:
        from pipeline.transform.crime_data import transform
        transform()
        logger.info("[OK] Crime data transform complete")
        return True
    except Exception:
        logger.exception("[FAIL] Crime data transform failed")
        return False


def _transform_agents(force: bool = False) -> bool:
    """Initialize agent populations from baseline data."""
    output = PROCESSED_DIR / "agent_populations.parquet"
    if not force and _is_fresh(output):
        logger.info("[SKIP] agent_populations.parquet is fresh")
        return True

    try:
        from pipeline.transform.agent_initialization import transform
        transform()
        logger.info("[OK] Agent initialization complete")
        return True
    except Exception:
        logger.exception("[FAIL] Agent initialization failed")
        return False


# ---------------------------------------------------------------------------
# Main orchestration
# ---------------------------------------------------------------------------

def run_pipeline(force: bool = False, skip_fetch: bool = False, skip_transform: bool = False) -> dict:
    """Run the full data pipeline.

    Args:
        force: If True, re-run all steps regardless of cache freshness.
        skip_fetch: If True, skip all fetch steps (use existing raw data).
        skip_transform: If True, skip all transform steps.

    Returns:
        Dict with status of each step.
    """
    _ensure_dirs()
    start_time = time.time()
    results = {}

    logger.info("=" * 60)
    logger.info("SF Bay Area Policy Simulator - Data Pipeline")
    logger.info("=" * 60)

    # ---- FETCH PHASE ----
    if not skip_fetch:
        logger.info("")
        logger.info("--- FETCH PHASE ---")

        fetch_steps = [
            ("tiger", _fetch_tiger),
            ("census", _fetch_census),
            ("socrata", _fetch_socrata),
            ("transit", _fetch_transit),
            ("fiscal", _fetch_fiscal),
            ("political", _fetch_political),
        ]

        for name, func in fetch_steps:
            step_start = time.time()
            success = func(force=force)
            elapsed = time.time() - step_start
            results[f"fetch_{name}"] = {"success": success, "elapsed_seconds": round(elapsed, 1)}
            logger.info("  %s: %s (%.1fs)", name, "OK" if success else "FAILED", elapsed)
    else:
        logger.info("[SKIP] Entire fetch phase skipped")

    # ---- TRANSFORM PHASE ----
    if not skip_transform:
        logger.info("")
        logger.info("--- TRANSFORM PHASE ---")

        # Transform steps must run in order (dependencies)
        transform_steps = [
            ("geometries", _transform_geometries),       # Must be first (others depend on tracts.geojson)
            ("demographics", _transform_demographics),     # Depends on geometries + census
            ("housing_stock", _transform_housing_stock),   # Depends on geometries + socrata
            ("crime_data", _transform_crime_data),         # Depends on geometries + socrata
            ("agents", _transform_agents),                 # Depends on demographics + crime + housing
        ]

        for name, func in transform_steps:
            step_start = time.time()
            success = func(force=force)
            elapsed = time.time() - step_start
            results[f"transform_{name}"] = {"success": success, "elapsed_seconds": round(elapsed, 1)}
            logger.info("  %s: %s (%.1fs)", name, "OK" if success else "FAILED", elapsed)
    else:
        logger.info("[SKIP] Entire transform phase skipped")

    # ---- SUMMARY ----
    total_elapsed = time.time() - start_time
    n_success = sum(1 for v in results.values() if v["success"])
    n_total = len(results)

    logger.info("")
    logger.info("=" * 60)
    logger.info("Pipeline complete: %d/%d steps succeeded (%.1fs total)", n_success, n_total, total_elapsed)
    logger.info("=" * 60)

    # List output files
    output_files = [
        PROCESSED_DIR / "tracts.geojson",
        PROCESSED_DIR / "tract_baseline.parquet",
        PROCESSED_DIR / "agent_populations.parquet",
        PROCESSED_DIR / "housing_stock.parquet",
        PROCESSED_DIR / "crime_data.parquet",
    ]
    logger.info("")
    logger.info("Output files:")
    for f in output_files:
        status = "EXISTS" if f.exists() else "MISSING"
        size = f"""{f.stat().st_size / 1024:.0f} KB""" if f.exists() else "N/A"
        logger.info("  [%s] %s (%s)", status, f.name, size)

    results["total_elapsed_seconds"] = round(total_elapsed, 1)
    return results


def run_fetch_only(force: bool = False) -> dict:
    """Run only the fetch phase of the pipeline."""
    return run_pipeline(force=force, skip_transform=True)


def run_transform_only(force: bool = False) -> dict:
    """Run only the transform phase of the pipeline."""
    return run_pipeline(force=force, skip_fetch=True)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="SF Bay Area Data Pipeline Orchestrator")
    parser.add_argument("--force", action="store_true", help="Force re-run all steps")
    parser.add_argument("--fetch-only", action="store_true", help="Run only fetch steps")
    parser.add_argument("--transform-only", action="store_true", help="Run only transform steps")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    if args.fetch_only:
        run_fetch_only(force=args.force)
    elif args.transform_only:
        run_transform_only(force=args.force)
    else:
        run_pipeline(force=args.force)
