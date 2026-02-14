"""Routes for retrieving simulation results."""

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

from api.models import MetricsResult, TimeseriesPoint, TractResult
from api.routes.simulations import simulation_runs, RESULTS_DIR

router = APIRouter(prefix="/results", tags=["results"])


def _load_snapshot(run_id: str, timestep: int) -> dict:
    """Load a simulation snapshot from disk.

    Args:
        run_id: The simulation run ID.
        timestep: The timestep to load.

    Returns:
        Snapshot dictionary.

    Raises:
        HTTPException: If the run or snapshot is not found.
    """
    if run_id not in simulation_runs:
        raise HTTPException(status_code=404, detail=f"Simulation run '{run_id}' not found")

    run_dir = RESULTS_DIR / run_id
    if not run_dir.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Results directory for run '{run_id}' not found",
        )

    # Find the closest available snapshot
    snapshot_path = run_dir / f"step_{timestep:04d}.json"
    if not snapshot_path.exists():
        # Try to find the nearest available snapshot
        available = sorted(run_dir.glob("step_*.json"))
        if not available:
            raise HTTPException(
                status_code=404,
                detail=f"No snapshots available for run '{run_id}'",
            )

        # Find the closest snapshot by timestep number
        target = timestep
        best = available[0]
        best_diff = abs(int(best.stem.split("_")[1]) - target)
        for path in available:
            step_num = int(path.stem.split("_")[1])
            diff = abs(step_num - target)
            if diff < best_diff:
                best = path
                best_diff = diff
        snapshot_path = best

    with open(snapshot_path) as f:
        return json.load(f)


def _list_all_snapshots(run_id: str) -> list[Path]:
    """List all snapshot files for a given run, sorted by timestep.

    Args:
        run_id: The simulation run ID.

    Returns:
        Sorted list of snapshot file paths.
    """
    run_dir = RESULTS_DIR / run_id
    if not run_dir.exists():
        return []
    return sorted(run_dir.glob("step_*.json"))


@router.get("/{run_id}/tracts", response_model=list[TractResult])
async def get_tract_results(
    run_id: str,
    timestep: int = Query(default=260, description="Simulation timestep to retrieve"),
) -> list[TractResult]:
    """Get tract-level results for a specific timestep.

    Returns per-tract metric values suitable for map visualization.
    """
    snapshot = _load_snapshot(run_id, timestep)

    tracts_data = snapshot.get("tracts", {})
    results = [
        TractResult(tract_id=tract_id, values=values)
        for tract_id, values in tracts_data.items()
    ]

    return results


@router.get("/{run_id}/metrics")
async def get_aggregate_metrics(
    run_id: str,
    timestep: int = Query(default=260, description="Simulation timestep to retrieve"),
) -> dict:
    """Get aggregate simulation metrics for a specific timestep.

    Returns dict keyed by metric name with current, baseline, delta, delta_pct.
    """
    snapshot = _load_snapshot(run_id, timestep)
    metrics = snapshot.get("metrics", {})

    # Load baseline (step 0 or first available snapshot)
    snapshots = _list_all_snapshots(run_id)
    baseline_metrics = {}
    if snapshots:
        with open(snapshots[0]) as f:
            baseline_metrics = json.load(f).get("metrics", {})

    result = {}
    for key, current_val in metrics.items():
        current = float(current_val)
        baseline = float(baseline_metrics.get(key, current))
        delta = current - baseline
        delta_pct = (delta / baseline * 100) if baseline != 0 else 0.0
        result[key] = {
            "current": current,
            "baseline": baseline,
            "delta": delta,
            "delta_pct": delta_pct,
        }

    return result


@router.get("/{run_id}/timeseries", response_model=list[TimeseriesPoint])
async def get_timeseries(
    run_id: str,
    metric: str = Query(..., description="Metric name (e.g., 'total_population', 'avg_rent')"),
) -> list[TimeseriesPoint]:
    """Get a time series of a specific metric across all available timesteps.

    Reads all snapshot files for the run and extracts the requested metric.
    """
    if run_id not in simulation_runs:
        raise HTTPException(status_code=404, detail=f"Simulation run '{run_id}' not found")

    snapshots = _list_all_snapshots(run_id)
    if not snapshots:
        raise HTTPException(
            status_code=404,
            detail=f"No results available for run '{run_id}'",
        )

    points: list[TimeseriesPoint] = []
    for snapshot_path in snapshots:
        with open(snapshot_path) as f:
            data = json.load(f)

        metrics = data.get("metrics", {})
        if metric in metrics:
            points.append(
                TimeseriesPoint(
                    timestep=data.get("timestep", 0),
                    value=float(metrics[metric]),
                )
            )

    if not points:
        raise HTTPException(
            status_code=404,
            detail=f"Metric '{metric}' not found in results for run '{run_id}'",
        )

    return points
