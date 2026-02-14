#!/usr/bin/env python3
"""Run the full data pipeline: fetch all sources → transform → output baseline files."""

import sys
import os
import logging
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "backend", ".env"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("pipeline")


def main():
    from pipeline.orchestrator import run_pipeline

    start = time.time()
    logger.info("Starting full data pipeline...")

    results = run_pipeline(force=("--force" in sys.argv))

    elapsed = time.time() - start
    logger.info(f"Pipeline completed in {elapsed:.1f}s")

    for name, info in results.items():
        if isinstance(info, dict):
            status = "OK" if info.get("success") else "FAILED"
            logger.info(f"  {name}: {status} ({info.get('elapsed_seconds', 0)}s)")
        else:
            logger.info(f"  {name}: {info}")


if __name__ == "__main__":
    main()
