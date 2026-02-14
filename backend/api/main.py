"""FastAPI application for the SF Bay Area Policy Simulator."""

import json
import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from api.routes import parse, scenarios, simulations, results
from api import websocket

# Tract geometry cache (loaded at startup for affected-tract highlighting)
_tract_geometry: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: load resources on startup, clean up on shutdown."""
    # Load tract geometry if available
    geometry_path = (
        Path(__file__).resolve().parent.parent / "data" / "tract_geometry.geojson"
    )
    if geometry_path.exists():
        with open(geometry_path) as f:
            data = json.load(f)
            for feature in data.get("features", []):
                tract_id = feature.get("properties", {}).get("TRACTCE", "")
                if tract_id:
                    _tract_geometry[tract_id] = feature

    # Ensure results directory exists
    results_dir = Path(__file__).resolve().parent.parent / "data" / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    yield

    # Cleanup (if needed in the future)
    _tract_geometry.clear()


app = FastAPI(
    title="SF Bay Area Policy Simulator",
    description=(
        "API for simulating the effects of policy changes on the San Francisco "
        "Bay Area. Accepts natural language policy descriptions, converts them "
        "to structured configurations, runs simulations, and returns results."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware - allow localhost origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8080",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8080",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include REST API routers
app.include_router(parse.router, prefix="/api")
app.include_router(scenarios.router, prefix="/api")
app.include_router(simulations.router, prefix="/api")
app.include_router(results.router, prefix="/api")

# Include WebSocket router
app.include_router(websocket.router)


@app.get("/api/health")
async def health_check() -> dict:
    """Health check endpoint."""
    return {
        "status": "ok",
        "tracts_loaded": len(_tract_geometry),
    }


_tracts_with_baseline: dict | None = None


@app.get("/api/tracts/geojson")
async def get_tracts_geojson():
    """Serve tracts GeoJSON with baseline demographics merged in."""
    global _tracts_with_baseline
    if _tracts_with_baseline is not None:
        return _tracts_with_baseline

    data_dir = Path(__file__).resolve().parent.parent / "data" / "processed"
    geojson_path = data_dir / "tracts.geojson"
    baseline_path = data_dir / "tract_baseline.parquet"

    if not geojson_path.exists():
        return {"error": "tracts.geojson not found"}

    with open(geojson_path) as f:
        geojson = json.load(f)

    # Merge baseline data if available
    if baseline_path.exists():
        import pandas as pd
        df = pd.read_parquet(baseline_path)
        baseline_map = {}
        for _, row in df.iterrows():
            baseline_map[row["tract_id"]] = row.to_dict()

        for feature in geojson.get("features", []):
            props = feature.get("properties", {})
            tract_id = props.get("tract_id", "")
            if tract_id in baseline_map:
                bl = baseline_map[tract_id]
                for k, v in bl.items():
                    if k not in ("tract_id", "county_fips"):
                        props[k] = None if pd.isna(v) else v

    _tracts_with_baseline = geojson
    return geojson


@app.get("/api/tracts/geometry/{tract_id}")
async def get_tract_geometry(tract_id: str) -> dict:
    """Get GeoJSON geometry for a specific tract.

    Useful for highlighting affected tracts on the map.
    """
    if tract_id in _tract_geometry:
        return _tract_geometry[tract_id]
    return {"error": f"Tract '{tract_id}' not found", "tract_id": tract_id}
