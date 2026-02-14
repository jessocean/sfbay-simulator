"""Routes for starting and monitoring simulation runs."""

import asyncio
import json
import os
import time
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException

from api.models import SimulationRunRequest, SimulationStatus
from simulation.core.config import (
    PolicyConfiguration,
    SimulationConfig,
    TOTAL_TIMESTEPS,
)

router = APIRouter(prefix="/simulations", tags=["simulations"])

# In-memory store for simulation run state
# Keys are run_id strings, values are dicts with status info
simulation_runs: dict[str, dict] = {}

# Background tasks keyed by run_id
_background_tasks: dict[str, asyncio.Task] = {}

RESULTS_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "results"


def _adapt_snapshot(raw_snapshot: dict) -> dict:
    """Adapt engine snapshot format to API format.

    Maps 'aggregate' → 'metrics' and renames fields to match frontend.
    """
    agg = raw_snapshot.get("aggregate", {})
    metrics = {
        "population": agg.get("total_population", 0),
        "median_rent": agg.get("avg_median_rent", 0),
        "housing_units": agg.get("total_housing_units", 0),
        "transit_share": agg.get("transit_mode_share", 0),
        "crime": agg.get("total_crime_incidents", 0),
        "vacancy": agg.get("avg_vacancy_rate", 0),
        "businesses": agg.get("total_businesses", 0),
        "drug_market_activity": 0,
    }
    return {
        "timestep": raw_snapshot.get("timestep", 0),
        "tracts": raw_snapshot.get("tracts", {}),
        "metrics": metrics,
    }


async def _run_simulation(run_id: str, sim_config: SimulationConfig) -> None:
    """Execute a simulation in the background.

    Updates simulation_runs[run_id] with progress as the simulation advances.
    Writes results to disk as JSON files in RESULTS_DIR/{run_id}/.
    """
    run_dir = RESULTS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    total_steps = sim_config.total_steps
    simulation_runs[run_id]["status"] = "running"

    try:
        import pandas as pd
        from simulation.core.engine import run_simulation as engine_run

        baseline_path = Path(__file__).resolve().parent.parent.parent / "data" / "processed" / "tract_baseline.parquet"
        baseline_df = pd.read_parquet(baseline_path)

        def progress_cb(step, total):
            simulation_runs[run_id].update({
                "current_step": step,
                "progress": step / total,
            })

        # Run in a thread to avoid blocking the event loop
        import concurrent.futures
        loop = asyncio.get_event_loop()

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            snapshots = await loop.run_in_executor(
                pool,
                lambda: engine_run(
                    baseline_df,
                    sim_config,
                    snapshot_interval=1,
                    progress_callback=progress_cb,
                ),
            )

        # Write snapshots to disk
        for snap in snapshots:
            adapted = _adapt_snapshot(snap)
            ts = adapted["timestep"]
            snapshot_path = run_dir / f"step_{ts:04d}.json"
            with open(snapshot_path, "w") as f:
                json.dump(adapted, f)

        # Save config
        from dataclasses import asdict
        config_path = run_dir / "config.json"
        with open(config_path, "w") as f:
            json.dump(asdict(sim_config.policy), f, indent=2)

        simulation_runs[run_id]["status"] = "completed"
        simulation_runs[run_id]["progress"] = 1.0
        simulation_runs[run_id]["current_step"] = total_steps

    except Exception as e:
        import traceback
        traceback.print_exc()
        simulation_runs[run_id]["status"] = "failed"
        simulation_runs[run_id]["error"] = str(e)


@router.post("/run", response_model=SimulationStatus)
async def start_simulation(request: SimulationRunRequest) -> SimulationStatus:
    """Start a new simulation run in the background.

    Returns immediately with a run_id that can be used to poll for status.
    """
    try:
        policy = PolicyConfiguration(**request.config)
    except (TypeError, ValueError) as e:
        raise HTTPException(
            status_code=400, detail=f"Invalid policy configuration: {str(e)}"
        )

    run_id = str(uuid.uuid4())
    # Use 26 steps (1 year) for interactive speed; full 260 available via config
    interactive_steps = 26
    sim_config = SimulationConfig(policy=policy, total_steps=interactive_steps)

    simulation_runs[run_id] = {
        "run_id": run_id,
        "status": "pending",
        "progress": 0.0,
        "current_step": 0,
        "total_steps": interactive_steps,
        "name": request.name,
        "started_at": time.time(),
    }

    task = asyncio.create_task(_run_simulation(run_id, sim_config))
    _background_tasks[run_id] = task

    return SimulationStatus(
        run_id=run_id,
        status="pending",
        progress=0.0,
        current_step=0,
        total_steps=TOTAL_TIMESTEPS,
    )


@router.get("/status/{run_id}", response_model=SimulationStatus)
async def get_simulation_status(run_id: str) -> SimulationStatus:
    """Get the current status and progress of a simulation run."""
    if run_id not in simulation_runs:
        raise HTTPException(status_code=404, detail=f"Simulation run '{run_id}' not found")

    run = simulation_runs[run_id]
    return SimulationStatus(
        run_id=run["run_id"],
        status=run["status"],
        progress=run["progress"],
        current_step=run["current_step"],
        total_steps=run["total_steps"],
    )
