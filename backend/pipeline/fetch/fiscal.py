"""Define SF city budget data by department (from public budget documents).

The City and County of San Francisco FY2023-2024 budget is approximately $15.9 billion.
Data sourced from the SF Controller's Office and Mayor's Budget documents.
"""

import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"

# SF city budget by department (FY2023-2024, in millions USD)
# Source: SF Mayor's Office proposed budget / Controller's Office
SF_BUDGET_DEPARTMENTS = [
    {
        "department": "Public Health",
        "code": "DPH",
        "budget_millions": 3020,
        "category": "Health & Human Services",
        "employees_approx": 9200,
        "description": "SF Department of Public Health - hospitals, clinics, behavioral health",
    },
    {
        "department": "Human Services Agency",
        "code": "HSA",
        "budget_millions": 1280,
        "category": "Health & Human Services",
        "employees_approx": 2100,
        "description": "CalWORKs, CalFresh, Medi-Cal, County Adult Assistance Programs",
    },
    {
        "department": "Homelessness & Supportive Housing",
        "code": "HSH",
        "budget_millions": 672,
        "category": "Health & Human Services",
        "employees_approx": 400,
        "description": "Homeless shelters, supportive housing, outreach",
    },
    {
        "department": "Municipal Transportation Agency",
        "code": "SFMTA",
        "budget_millions": 1460,
        "category": "Infrastructure & Transportation",
        "employees_approx": 6100,
        "description": "Muni transit, parking, traffic engineering, taxis",
    },
    {
        "department": "Public Works",
        "code": "DPW",
        "budget_millions": 480,
        "category": "Infrastructure & Transportation",
        "employees_approx": 1700,
        "description": "Street cleaning, paving, urban forestry, building design",
    },
    {
        "department": "SF International Airport",
        "code": "SFO",
        "budget_millions": 1350,
        "category": "Infrastructure & Transportation",
        "employees_approx": 1800,
        "description": "Airport operations, capital improvements",
    },
    {
        "department": "Public Utilities Commission",
        "code": "SFPUC",
        "budget_millions": 1620,
        "category": "Infrastructure & Transportation",
        "employees_approx": 2300,
        "description": "Water, wastewater, power (Hetch Hetchy, CleanPowerSF)",
    },
    {
        "department": "Police Department",
        "code": "SFPD",
        "budget_millions": 780,
        "category": "Public Safety",
        "employees_approx": 2900,
        "description": "Law enforcement, investigations, community policing",
    },
    {
        "department": "Fire Department",
        "code": "SFFD",
        "budget_millions": 470,
        "category": "Public Safety",
        "employees_approx": 1700,
        "description": "Fire suppression, EMS, prevention, airport rescue",
    },
    {
        "department": "Sheriff's Department",
        "code": "SHF",
        "budget_millions": 310,
        "category": "Public Safety",
        "employees_approx": 1050,
        "description": "County jails, court security, civil process",
    },
    {
        "department": "District Attorney",
        "code": "DAT",
        "budget_millions": 78,
        "category": "Public Safety",
        "employees_approx": 350,
        "description": "Criminal prosecution",
    },
    {
        "department": "Public Defender",
        "code": "PDR",
        "budget_millions": 60,
        "category": "Public Safety",
        "employees_approx": 240,
        "description": "Criminal defense for indigent clients",
    },
    {
        "department": "Mayor's Office of Housing & Community Development",
        "code": "MOHCD",
        "budget_millions": 410,
        "category": "Housing & Community Development",
        "employees_approx": 160,
        "description": "Affordable housing, community development, first-time homebuyer",
    },
    {
        "department": "Planning Department",
        "code": "CPC",
        "budget_millions": 72,
        "category": "Housing & Community Development",
        "employees_approx": 280,
        "description": "Land use planning, zoning, environmental review",
    },
    {
        "department": "Building Inspection",
        "code": "DBI",
        "budget_millions": 86,
        "category": "Housing & Community Development",
        "employees_approx": 340,
        "description": "Building permits, inspections, code enforcement",
    },
    {
        "department": "Recreation & Parks",
        "code": "RPD",
        "budget_millions": 290,
        "category": "Community Services",
        "employees_approx": 1200,
        "description": "Parks, recreation centers, pools, playgrounds",
    },
    {
        "department": "Library",
        "code": "LIB",
        "budget_millions": 178,
        "category": "Community Services",
        "employees_approx": 650,
        "description": "Main library, 27 branch libraries",
    },
    {
        "department": "Children, Youth & Their Families",
        "code": "DCYF",
        "budget_millions": 230,
        "category": "Community Services",
        "employees_approx": 80,
        "description": "Youth programs, childcare, after-school",
    },
    {
        "department": "Controller's Office",
        "code": "CON",
        "budget_millions": 68,
        "category": "General Government",
        "employees_approx": 250,
        "description": "Financial oversight, auditing, payroll",
    },
    {
        "department": "Technology",
        "code": "DT",
        "budget_millions": 145,
        "category": "General Government",
        "employees_approx": 500,
        "description": "City IT infrastructure, digital services, 311",
    },
    {
        "department": "Other Departments & Reserves",
        "code": "OTHER",
        "budget_millions": 2740,
        "category": "Other",
        "employees_approx": 4000,
        "description": "All other departments, reserves, debt service, capital projects",
    },
]

# Revenue sources (approximate, in millions USD)
SF_REVENUE_SOURCES = [
    {"source": "Property Tax", "amount_millions": 3800, "category": "Tax Revenue"},
    {"source": "Business Tax (Homelessness Gross Receipts)", "amount_millions": 1150, "category": "Tax Revenue"},
    {"source": "Sales Tax", "amount_millions": 420, "category": "Tax Revenue"},
    {"source": "Hotel Tax (TOT)", "amount_millions": 520, "category": "Tax Revenue"},
    {"source": "Transfer Tax", "amount_millions": 380, "category": "Tax Revenue"},
    {"source": "Utility Users Tax", "amount_millions": 110, "category": "Tax Revenue"},
    {"source": "Parking Tax", "amount_millions": 95, "category": "Tax Revenue"},
    {"source": "Other Taxes", "amount_millions": 350, "category": "Tax Revenue"},
    {"source": "Federal Grants", "amount_millions": 1600, "category": "Intergovernmental"},
    {"source": "State Grants", "amount_millions": 1800, "category": "Intergovernmental"},
    {"source": "Charges for Services", "amount_millions": 2400, "category": "Fees & Charges"},
    {"source": "Enterprise Revenue (Airport, PUC)", "amount_millions": 2850, "category": "Enterprise"},
    {"source": "Other Revenue", "amount_millions": 425, "category": "Other"},
]


def fetch() -> dict[str, Path]:
    """Save SF fiscal data to CSV files.

    Returns:
        Dict with paths to budget and revenue files.
    """
    output_dir = RAW_DIR / "fiscal"
    output_dir.mkdir(parents=True, exist_ok=True)

    budget_file = output_dir / "sf_budget_departments.csv"
    revenue_file = output_dir / "sf_revenue_sources.csv"

    # Save department budgets
    if not budget_file.exists():
        df_budget = pd.DataFrame(SF_BUDGET_DEPARTMENTS)
        df_budget.to_csv(budget_file, index=False)
        total = df_budget["budget_millions"].sum()
        logger.info(
            "Saved SF budget data: %d departments, total $%.1fB to %s",
            len(df_budget), total / 1000, budget_file,
        )
    else:
        logger.info("SF budget data already cached at %s", budget_file)

    # Save revenue sources
    if not revenue_file.exists():
        df_revenue = pd.DataFrame(SF_REVENUE_SOURCES)
        df_revenue.to_csv(revenue_file, index=False)
        total = df_revenue["amount_millions"].sum()
        logger.info(
            "Saved SF revenue data: %d sources, total $%.1fB to %s",
            len(df_revenue), total / 1000, revenue_file,
        )
    else:
        logger.info("SF revenue data already cached at %s", revenue_file)

    return {
        "budget": budget_file,
        "revenue": revenue_file,
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    fetch()
