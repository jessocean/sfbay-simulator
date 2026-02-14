#!/usr/bin/env python3
"""Run Bayesian optimization to calibrate simulation parameters against empirical targets."""

import sys
import os
import logging
import json
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("calibration")


def main():
    from simulation.calibration.optimizer import run_calibration

    start = time.time()
    n_calls = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    logger.info(f"Starting calibration with {n_calls} iterations...")

    result = run_calibration(n_calls=n_calls)

    elapsed = time.time() - start
    logger.info(f"Calibration completed in {elapsed:.1f}s")
    logger.info(f"Best RMSE: {result['best_rmse']:.4f}")
    logger.info(f"Best parameters:")
    for k, v in result["best_params"].items():
        logger.info(f"  {k}: {v:.4f}")

    # Save results
    output_path = os.path.join(
        os.path.dirname(__file__), "..", "backend", "data", "processed", "calibrated_params.json"
    )
    with open(output_path, "w") as f:
        json.dump(result["best_params"], f, indent=2)
    logger.info(f"Saved calibrated parameters to {output_path}")


if __name__ == "__main__":
    main()
