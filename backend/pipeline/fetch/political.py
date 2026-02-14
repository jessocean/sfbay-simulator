"""Fetch/define SF Board of Supervisors data, district-to-tract mappings, and ideology scores."""

import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"

# SF Board of Supervisors districts and their characteristics
# Ideology scores: -1.0 (very progressive) to +1.0 (moderate/conservative)
# Based on public voting records and political positioning as of 2024
SF_SUPERVISORS = [
    {
        "district": 1,
        "supervisor": "Connie Chan",
        "ideology_score": -0.75,
        "area_description": "Richmond District, Inner Richmond, Lone Mountain, USF area",
        "key_tracts_prefix": "06075012",  # approximate tract prefix
    },
    {
        "district": 2,
        "supervisor": "Catherine Stefani",
        "ideology_score": -0.20,
        "area_description": "Marina, Pacific Heights, Cow Hollow, Presidio Heights",
        "key_tracts_prefix": "06075011",
    },
    {
        "district": 3,
        "supervisor": "Aaron Peskin",
        "ideology_score": -0.70,
        "area_description": "North Beach, Chinatown, Financial District, Nob Hill, Telegraph Hill",
        "key_tracts_prefix": "06075010",
    },
    {
        "district": 4,
        "supervisor": "Joel Engardio",
        "ideology_score": 0.15,
        "area_description": "Sunset District, Parkside, West Portal",
        "key_tracts_prefix": "06075035",
    },
    {
        "district": 5,
        "supervisor": "Dean Preston",
        "ideology_score": -0.90,
        "area_description": "Haight-Ashbury, Western Addition, Fillmore, Hayes Valley, Tenderloin",
        "key_tracts_prefix": "06075015",
    },
    {
        "district": 6,
        "supervisor": "Matt Dorsey",
        "ideology_score": -0.10,
        "area_description": "SoMa, Mission Bay, Treasure Island, South Beach",
        "key_tracts_prefix": "06075017",
    },
    {
        "district": 7,
        "supervisor": "Myrna Melgar",
        "ideology_score": -0.40,
        "area_description": "West Twin Peaks, Inner Sunset, Golden Gate Heights, Miraloma Park",
        "key_tracts_prefix": "06075030",
    },
    {
        "district": 8,
        "supervisor": "Rafael Mandelman",
        "ideology_score": -0.35,
        "area_description": "Castro, Noe Valley, Diamond Heights, Glen Park",
        "key_tracts_prefix": "06075020",
    },
    {
        "district": 9,
        "supervisor": "Hillary Ronen",
        "ideology_score": -0.85,
        "area_description": "Mission, Bernal Heights, Portola",
        "key_tracts_prefix": "06075022",
    },
    {
        "district": 10,
        "supervisor": "Shamann Walton",
        "ideology_score": -0.60,
        "area_description": "Bayview-Hunters Point, Potrero Hill, Dogpatch, Visitacion Valley",
        "key_tracts_prefix": "06075023",
    },
    {
        "district": 11,
        "supervisor": "Ahsha Safai",
        "ideology_score": 0.05,
        "area_description": "Excelsior, Outer Mission, Ingleside, Oceanview",
        "key_tracts_prefix": "06075026",
    },
]

# Mapping of SF supervisor districts to approximate census tract GEOIDs
# These are approximate — real mapping would come from the City's redistricting data
DISTRICT_TRACT_MAPPING = {
    1: [
        "06075012600", "06075012700", "06075012800", "06075012900",
        "06075013100", "06075013200", "06075047600", "06075047700",
        "06075047800", "06075047900", "06075060100", "06075060200",
        "06075060300", "06075060400", "06075060500",
    ],
    2: [
        "06075011100", "06075011200", "06075011300", "06075011400",
        "06075011500", "06075011600", "06075011700", "06075011800",
        "06075012100", "06075012200", "06075012300", "06075012400",
        "06075012500", "06075010100",
    ],
    3: [
        "06075010200", "06075010300", "06075010400", "06075010500",
        "06075010600", "06075010700", "06075010800", "06075010900",
        "06075011000", "06075010100", "06075061200", "06075061300",
    ],
    4: [
        "06075035100", "06075035200", "06075035300", "06075035400",
        "06075035500", "06075035600", "06075035700", "06075035800",
        "06075032600", "06075032700", "06075032800", "06075032900",
        "06075033000", "06075033100",
    ],
    5: [
        "06075015400", "06075015500", "06075015600", "06075015700",
        "06075015800", "06075015900", "06075016000", "06075016100",
        "06075016200", "06075016300", "06075016400", "06075016500",
        "06075012000", "06075016800",
    ],
    6: [
        "06075017600", "06075017700", "06075017800", "06075017900",
        "06075017601", "06075017602", "06075017603", "06075017604",
        "06075017605", "06075060900", "06075061000", "06075061100",
        "06075980100", "06075980200",
    ],
    7: [
        "06075030100", "06075030200", "06075030300", "06075030400",
        "06075030500", "06075030600", "06075030700", "06075031400",
        "06075031500", "06075033200", "06075033300", "06075033400",
    ],
    8: [
        "06075020100", "06075020200", "06075020300", "06075020400",
        "06075020500", "06075020600", "06075020700", "06075020800",
        "06075020900", "06075021000", "06075021100", "06075021200",
    ],
    9: [
        "06075022800", "06075022900", "06075020700", "06075020800",
        "06075022600", "06075022700", "06075022100", "06075022200",
        "06075022300", "06075022400", "06075022500", "06075025200",
        "06075025300", "06075025400",
    ],
    10: [
        "06075023100", "06075023200", "06075023300", "06075023400",
        "06075023500", "06075023600", "06075023700", "06075023800",
        "06075023900", "06075024000", "06075024100", "06075060700",
        "06075060800", "06075025700",
    ],
    11: [
        "06075026300", "06075026400", "06075026500", "06075026600",
        "06075026700", "06075026800", "06075026900", "06075027000",
        "06075027100", "06075027200", "06075027300", "06075027400",
        "06075027500", "06075027600",
    ],
}


def fetch() -> dict[str, Path]:
    """Save SF political data (supervisors, district-tract mappings).

    Returns:
        Dict with paths to supervisors and mapping files.
    """
    output_dir = RAW_DIR / "political"
    output_dir.mkdir(parents=True, exist_ok=True)

    supervisors_file = output_dir / "sf_supervisors.csv"
    mapping_file = output_dir / "district_tract_mapping.csv"

    # Save supervisor data
    if not supervisors_file.exists():
        df_sup = pd.DataFrame(SF_SUPERVISORS)
        df_sup.to_csv(supervisors_file, index=False)
        logger.info("Saved %d supervisor records to %s", len(df_sup), supervisors_file)
    else:
        logger.info("Supervisor data already cached at %s", supervisors_file)

    # Save district-to-tract mapping
    if not mapping_file.exists():
        records = []
        for district, tracts in DISTRICT_TRACT_MAPPING.items():
            for tract_id in tracts:
                records.append({
                    "district": district,
                    "tract_id": tract_id,
                })
        df_map = pd.DataFrame(records)
        df_map.to_csv(mapping_file, index=False)
        logger.info("Saved %d district-tract mappings to %s", len(df_map), mapping_file)
    else:
        logger.info("District-tract mapping already cached at %s", mapping_file)

    return {
        "supervisors": supervisors_file,
        "mapping": mapping_file,
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    fetch()
