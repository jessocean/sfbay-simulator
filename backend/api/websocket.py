"""WebSocket endpoint for live simulation progress updates."""

import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from api.routes.simulations import simulation_runs

router = APIRouter()


@router.websocket("/ws/simulation/{run_id}")
async def simulation_progress_ws(websocket: WebSocket, run_id: str) -> None:
    """WebSocket endpoint for streaming simulation progress.

    Clients connect to /ws/simulation/{run_id} and receive JSON messages
    with status updates until the simulation completes or fails.

    Message format:
    {
        "run_id": "...",
        "status": "running",
        "progress": 0.45,
        "current_step": 117,
        "total_steps": 260
    }

    On completion, sends a final message with status "completed" or "failed",
    then closes the connection.
    """
    await websocket.accept()

    if run_id not in simulation_runs:
        await websocket.send_json({
            "error": f"Simulation run '{run_id}' not found",
        })
        await websocket.close(code=4004)
        return

    try:
        last_step = -1
        while True:
            run = simulation_runs.get(run_id)
            if run is None:
                await websocket.send_json({
                    "error": f"Simulation run '{run_id}' was removed",
                })
                break

            current_step = run["current_step"]

            # Only send updates when progress changes
            if current_step != last_step:
                last_step = current_step
                await websocket.send_json({
                    "run_id": run["run_id"],
                    "status": run["status"],
                    "progress": run["progress"],
                    "current_step": run["current_step"],
                    "total_steps": run["total_steps"],
                })

            # Stop polling when simulation is done
            if run["status"] in ("completed", "failed"):
                break

            await asyncio.sleep(0.5)

    except WebSocketDisconnect:
        pass
    except Exception:
        try:
            await websocket.close(code=1011)
        except Exception:
            pass
