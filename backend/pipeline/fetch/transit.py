"""Fetch BART ridership data and define station locations for transit accessibility."""

import logging
import os
from pathlib import Path

import pandas as pd
import requests

logger = logging.getLogger(__name__)

RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"

# BART ridership data URL (monthly average exits by station)
BART_RIDERSHIP_URL = (
    "https://www.bart.gov/sites/default/files/docs/FY%20Avg%20Weekday%20Exits.xlsx"
)

# BART station locations (lat, lon) - all active stations as of 2023
BART_STATIONS = {
    "12TH": {"name": "12th St. Oakland City Center", "lat": 37.8032, "lon": -122.2711},
    "16TH": {"name": "16th St. Mission", "lat": 37.7650, "lon": -122.4195},
    "19TH": {"name": "19th St. Oakland", "lat": 37.8083, "lon": -122.2686},
    "24TH": {"name": "24th St. Mission", "lat": 37.7523, "lon": -122.4183},
    "ANTC": {"name": "Antioch", "lat": 37.9956, "lon": -121.7831},
    "BALB": {"name": "Balboa Park", "lat": 37.7210, "lon": -122.4474},
    "BAYF": {"name": "Bay Fair", "lat": 37.6976, "lon": -122.1266},
    "BERY": {"name": "Berryessa/North San Jose", "lat": 37.3685, "lon": -121.8748},
    "CAST": {"name": "Castro Valley", "lat": 37.6908, "lon": -122.0758},
    "CIVC": {"name": "Civic Center/UN Plaza", "lat": 37.7797, "lon": -122.4138},
    "COLM": {"name": "Colma", "lat": 37.6846, "lon": -122.4669},
    "COLS": {"name": "Coliseum", "lat": 37.7536, "lon": -122.1968},
    "CONC": {"name": "Concord", "lat": 37.9740, "lon": -122.0290},
    "DALY": {"name": "Daly City", "lat": 37.7062, "lon": -122.4692},
    "DBRK": {"name": "Downtown Berkeley", "lat": 37.8700, "lon": -122.2681},
    "DUBL": {"name": "Dublin/Pleasanton", "lat": 37.7017, "lon": -121.8992},
    "EMBR": {"name": "Embarcadero", "lat": 37.7930, "lon": -122.3969},
    "FRMT": {"name": "Fremont", "lat": 37.5574, "lon": -121.9764},
    "FTVL": {"name": "Fruitvale", "lat": 37.7749, "lon": -122.2243},
    "GLEN": {"name": "Glen Park", "lat": 37.7330, "lon": -122.4340},
    "HAYW": {"name": "Hayward", "lat": 37.6700, "lon": -122.0870},
    "LAFY": {"name": "Lafayette", "lat": 37.8933, "lon": -122.1248},
    "LAKE": {"name": "Lake Merritt", "lat": 37.7979, "lon": -122.2658},
    "MCAR": {"name": "MacArthur", "lat": 37.8284, "lon": -122.2672},
    "MILB": {"name": "Milpitas", "lat": 37.4104, "lon": -121.8910},
    "MLBR": {"name": "Millbrae", "lat": 37.5997, "lon": -122.3866},
    "MONT": {"name": "Montgomery St.", "lat": 37.7894, "lon": -122.4018},
    "NBRK": {"name": "North Berkeley", "lat": 37.8740, "lon": -122.2830},
    "NCON": {"name": "North Concord/Martinez", "lat": 38.0032, "lon": -122.0251},
    "OAKL": {"name": "Oakland Int'l Airport", "lat": 37.7133, "lon": -122.2127},
    "ORIN": {"name": "Orinda", "lat": 37.8784, "lon": -122.1837},
    "PCTR": {"name": "Pittsburg Center", "lat": 38.0169, "lon": -121.8897},
    "PHIL": {"name": "Pleasant Hill/Contra Costa Centre", "lat": 37.9286, "lon": -122.0569},
    "PITT": {"name": "Pittsburg/Bay Point", "lat": 38.0189, "lon": -121.9453},
    "PLZA": {"name": "El Cerrito Plaza", "lat": 37.9030, "lon": -122.2990},
    "POWL": {"name": "Powell St.", "lat": 37.7845, "lon": -122.4081},
    "RICH": {"name": "Richmond", "lat": 37.9370, "lon": -122.3537},
    "ROCK": {"name": "Rockridge", "lat": 37.8443, "lon": -122.2517},
    "SANL": {"name": "San Leandro", "lat": 37.7227, "lon": -122.1609},
    "SBRN": {"name": "San Bruno", "lat": 37.6375, "lon": -122.4159},
    "SFIA": {"name": "San Francisco Int'l Airport", "lat": 37.6161, "lon": -122.3922},
    "SHAY": {"name": "South Hayward", "lat": 37.6348, "lon": -122.0575},
    "SSAN": {"name": "South San Francisco", "lat": 37.6640, "lon": -122.4440},
    "UCTY": {"name": "Union City", "lat": 37.5910, "lon": -122.0172},
    "WARM": {"name": "Warm Springs/South Fremont", "lat": 37.5025, "lon": -121.9395},
    "WCRK": {"name": "Walnut Creek", "lat": 37.9056, "lon": -122.0672},
    "WDUB": {"name": "West Dublin/Pleasanton", "lat": 37.6996, "lon": -121.9281},
    "WOAK": {"name": "West Oakland", "lat": 37.8047, "lon": -122.2945},
    "ELNR": {"name": "El Cerrito del Norte", "lat": 37.9252, "lon": -122.3172},
}

# Default ridership data (average weekday exits, approximate 2023 values)
DEFAULT_RIDERSHIP = {
    "EMBR": 14200, "MONT": 12800, "POWL": 10500, "CIVC": 8900,
    "16TH": 7200, "24TH": 6100, "BALB": 4800, "GLEN": 3200,
    "DALY": 5100, "COLM": 3400, "SBRN": 2800, "SSAN": 2500,
    "MLBR": 4200, "SFIA": 6500,
    "12TH": 6800, "19TH": 5900, "LAKE": 4100, "FTVL": 4600,
    "COLS": 3800, "SANL": 3200, "BAYF": 4500, "HAYW": 3100,
    "SHAY": 2400, "UCTY": 2900, "FRMT": 4800, "WARM": 3600,
    "MILB": 3200, "BERY": 2800,
    "MCAR": 4200, "ROCK": 3500, "ORIN": 2100, "LAFY": 2800,
    "WCRK": 3900, "PHIL": 3100, "CONC": 3600, "NCON": 1800,
    "PITT": 2900, "PCTR": 1600, "ANTC": 1200,
    "WOAK": 5400, "OAKL": 1900,
    "DBRK": 4600, "NBRK": 2100, "PLZA": 2600, "ELNR": 3400,
    "RICH": 3100,
    "CAST": 2200, "WDUB": 1500, "DUBL": 3400,
}


def _download_bart_ridership(output_dir: Path) -> Path:
    """Download BART ridership data. Falls back to default data if download fails."""
    output_file = output_dir / "bart_ridership.csv"

    if output_file.exists():
        logger.info("BART ridership data already cached at %s, skipping", output_file)
        return output_file

    try:
        logger.info("Downloading BART ridership data from %s", BART_RIDERSHIP_URL)
        response = requests.get(BART_RIDERSHIP_URL, timeout=30)
        response.raise_for_status()

        # Try to parse the Excel file
        df = pd.read_excel(
            response.content,
            engine="openpyxl",
        )
        # Save as CSV
        df.to_csv(output_file, index=False)
        logger.info("Downloaded BART ridership data: %d rows", len(df))
        return output_file
    except Exception:
        logger.warning("Failed to download BART ridership data, using defaults")
        # Fall back to hardcoded defaults
        records = []
        for station_code, exits in DEFAULT_RIDERSHIP.items():
            station_info = BART_STATIONS.get(station_code, {})
            records.append({
                "station_code": station_code,
                "station_name": station_info.get("name", station_code),
                "lat": station_info.get("lat", 0.0),
                "lon": station_info.get("lon", 0.0),
                "avg_weekday_exits": exits,
            })
        df = pd.DataFrame(records)
        df.to_csv(output_file, index=False)
        logger.info("Saved default BART ridership data for %d stations", len(df))
        return output_file


def _save_station_locations(output_dir: Path) -> Path:
    """Save BART station locations as a CSV."""
    output_file = output_dir / "bart_stations.csv"

    if output_file.exists():
        logger.info("BART station locations already cached at %s", output_file)
        return output_file

    records = []
    for code, info in BART_STATIONS.items():
        records.append({
            "station_code": code,
            "station_name": info["name"],
            "lat": info["lat"],
            "lon": info["lon"],
            "avg_weekday_exits": DEFAULT_RIDERSHIP.get(code, 0),
        })

    df = pd.DataFrame(records)
    df.to_csv(output_file, index=False)
    logger.info("Saved %d BART station locations to %s", len(df), output_file)
    return output_file


def fetch() -> dict[str, Path]:
    """Fetch BART ridership data and save station locations.

    Returns:
        Dict with paths to ridership and station files.
    """
    output_dir = RAW_DIR / "transit"
    output_dir.mkdir(parents=True, exist_ok=True)

    ridership_path = _download_bart_ridership(output_dir)
    stations_path = _save_station_locations(output_dir)

    return {
        "ridership": ridership_path,
        "stations": stations_path,
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    fetch()
