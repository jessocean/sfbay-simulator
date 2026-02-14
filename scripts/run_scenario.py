#!/usr/bin/env python3
"""Run a predefined scenario and output results."""

import sys
import os
import json
import logging
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("scenario")

SCENARIOS = {
    "housing_density": "simulation.scenarios.housing_density",
    "drug_enforcement": "simulation.scenarios.drug_enforcement",
    "budget_reduction": "simulation.scenarios.budget_reduction",
    "permit_reform": "simulation.scenarios.permit_reform",
    "transit_subsidy": "simulation.scenarios.transit_subsidy",
}


def main():
    import importlib
    import pandas as pd
    from simulation.core.engine import run_simulation
    from simulation.core.config import SimulationConfig

    if len(sys.argv) < 2 or sys.argv[1] not in SCENARIOS:
        print(f"Usage: python run_scenario.py <scenario_name>")
        print(f"Available scenarios: {', '.join(SCENARIOS.keys())}")
        sys.exit(1)

    scenario_name = sys.argv[1]
    logger.info(f"Running scenario: {scenario_name}")

    # Load scenario config
    module = importlib.import_module(SCENARIOS[scenario_name])
    # Each scenario module has a build_*_config() function
    build_fn_name = [n for n in dir(module) if n.startswith("build_") and n.endswith("_config")][0]
    config = getattr(module, build_fn_name)()

    # Load baseline data
    data_dir = os.path.join(os.path.dirname(__file__), "..", "backend", "data", "processed")
    baseline_path = os.path.join(data_dir, "tract_baseline.parquet")

    if not os.path.exists(baseline_path):
        logger.error(f"Baseline data not found at {baseline_path}. Run pipeline first.")
        sys.exit(1)

    baseline_df = pd.read_parquet(baseline_path)

    # Check for calibrated params
    params_path = os.path.join(data_dir, "calibrated_params.json")
    if os.path.exists(params_path):
        with open(params_path) as f:
            config.params.update(json.load(f))
        logger.info("Loaded calibrated parameters")

    # Run simulation
    start = time.time()
    results = run_simulation(
        baseline_df=baseline_df,
        config=config,
        progress_callback=lambda step, total: (
            logger.info(f"Step {step}/{total}") if step % 26 == 0 else None
        ),
    )

    elapsed = time.time() - start
    logger.info(f"Simulation completed in {elapsed:.1f}s ({len(results)} snapshots)")

    # Save results
    results_dir = os.path.join(data_dir, "..", "results", scenario_name)
    os.makedirs(results_dir, exist_ok=True)

    # Save aggregate timeseries
    aggregates = [r["aggregate"] for r in results]
    agg_df = pd.DataFrame(aggregates)
    agg_df.to_parquet(os.path.join(results_dir, "aggregates.parquet"))

    # Save final tract state
    final_tracts = results[-1]["tracts"]
    tracts_df = pd.DataFrame.from_dict(final_tracts, orient="index")
    tracts_df.to_parquet(os.path.join(results_dir, "final_tracts.parquet"))

    # Save full results as JSON
    with open(os.path.join(results_dir, "results.json"), "w") as f:
        json.dump(results, f)

    logger.info(f"Results saved to {results_dir}/")

    # Print summary
    first = results[0]["aggregate"]
    last = results[-1]["aggregate"]
    logger.info("=== Summary (baseline → final) ===")
    for key in first:
        v0 = first[key]
        v1 = last[key]
        if v0 != 0:
            pct = (v1 - v0) / v0 * 100
            logger.info(f"  {key}: {v0:.0f} → {v1:.0f} ({pct:+.1f}%)")
        else:
            logger.info(f"  {key}: {v0:.0f} → {v1:.0f}")


if __name__ == "__main__":
    main()
