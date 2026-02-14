"""Validation and post-processing for parsed PolicyConfiguration objects."""

from dataclasses import asdict

from simulation.core.config import PolicyConfiguration

# Neighborhood name to tract ID mapping for resolving string references
NEIGHBORHOOD_TRACTS: dict[str, list[str]] = {
    "tenderloin": ["012400", "012500", "012600", "012700", "012800", "012900"],
    "mission": [
        "017700", "017800", "017900", "018000", "018100", "018200", "018300",
        "020700", "020800", "020900", "021000",
    ],
    "soma": [
        "017600", "017601", "017602", "017603", "017604", "017605", "017606",
    ],
    "south of market": [
        "017600", "017601", "017602", "017603", "017604", "017605", "017606",
    ],
    "castro": ["020200", "020300", "020400"],
    "haight": ["016800", "016900", "017000"],
    "haight-ashbury": ["016800", "016900", "017000"],
    "richmond": [
        "047600", "047700", "047800", "047900", "048000", "048100",
        "048200", "048300", "048400", "048500", "048600", "048700",
    ],
    "sunset": [
        "033100", "033200", "033300", "033400", "033500", "033600",
        "033700", "033800", "033900", "034000", "035100", "035200",
    ],
    "marina": ["013100", "013200", "013300", "013400"],
    "north beach": ["010600", "010700", "010800"],
    "chinatown": ["011300", "011400", "011500", "011600"],
    "financial district": ["011000", "011100", "011200", "061100"],
    "nob hill": ["011700", "011800", "011900", "012000"],
    "pacific heights": ["013500", "013600", "013700"],
    "bayview": [
        "023100", "023200", "023300", "023400", "023500", "023600",
        "026001", "026002",
    ],
    "hunters point": [
        "023100", "023200", "023300", "023400", "023500", "023600",
        "026001", "026002",
    ],
    "excelsior": ["026100", "026200", "026300", "026400"],
    "visitacion valley": ["026000", "025900"],
    "potrero hill": ["022600", "022700", "022800"],
    "dogpatch": ["022500"],
    "noe valley": ["020500", "020600"],
    "glen park": ["025400", "025500"],
    "bernal heights": ["025200", "025300"],
    "western addition": ["015400", "015500", "015600", "015700"],
    "japantown": ["015800"],
}

# Reverse lookup: tract ID -> neighborhood name
TRACT_TO_NEIGHBORHOOD: dict[str, str] = {}
for _name, _tracts in NEIGHBORHOOD_TRACTS.items():
    for _tract in _tracts:
        if _tract not in TRACT_TO_NEIGHBORHOOD:
            TRACT_TO_NEIGHBORHOOD[_tract] = _name

VALID_DEPARTMENTS = {"fire", "police", "transit", "health", "parks", "education"}
VALID_PERMIT_TYPES = {"residential", "commercial", "industrial", "mixed_use"}


class PolicyValidator:
    """Validates and post-processes PolicyConfiguration objects."""

    def validate(
        self, config: PolicyConfiguration
    ) -> tuple[PolicyConfiguration, list[str], list[str]]:
        """Validate and clamp a PolicyConfiguration.

        Args:
            config: The PolicyConfiguration to validate.

        Returns:
            Tuple of (clamped_config, warnings, errors).
            - clamped_config has all values within valid ranges.
            - warnings are non-fatal issues (e.g., clamped values, conflicts).
            - errors are fatal issues that may require user attention.
        """
        warnings: list[str] = []
        errors: list[str] = []

        # Resolve any neighborhood names that ended up in tract ID lists
        config.target_tract_ids = self._resolve_tract_ids(
            config.target_tract_ids, warnings
        )
        config.enforcement_target_tracts = self._resolve_tract_ids(
            config.enforcement_target_tracts, warnings
        )

        # Clamp density_multiplier (1.0 - 5.0)
        if config.density_multiplier < 1.0:
            warnings.append(
                f"density_multiplier clamped from {config.density_multiplier} to 1.0"
            )
            config.density_multiplier = 1.0
        elif config.density_multiplier > 5.0:
            warnings.append(
                f"density_multiplier clamped from {config.density_multiplier} to 5.0"
            )
            config.density_multiplier = 5.0

        # Clamp enforcement_budget_multiplier (0.0 - 10.0)
        if config.enforcement_budget_multiplier < 0.0:
            warnings.append(
                f"enforcement_budget_multiplier clamped from "
                f"{config.enforcement_budget_multiplier} to 0.0"
            )
            config.enforcement_budget_multiplier = 0.0
        elif config.enforcement_budget_multiplier > 10.0:
            warnings.append(
                f"enforcement_budget_multiplier clamped from "
                f"{config.enforcement_budget_multiplier} to 10.0"
            )
            config.enforcement_budget_multiplier = 10.0

        # Clamp treatment_beds_added (0 - 5000)
        if config.treatment_beds_added < 0:
            warnings.append(
                f"treatment_beds_added clamped from {config.treatment_beds_added} to 0"
            )
            config.treatment_beds_added = 0
        elif config.treatment_beds_added > 5000:
            warnings.append(
                f"treatment_beds_added clamped from {config.treatment_beds_added} to 5000"
            )
            config.treatment_beds_added = 5000

        # Clamp budget_reduction_pct (0.0 - 50.0)
        if config.budget_reduction_pct < 0.0:
            warnings.append(
                f"budget_reduction_pct clamped from {config.budget_reduction_pct} to 0.0"
            )
            config.budget_reduction_pct = 0.0
        elif config.budget_reduction_pct > 50.0:
            warnings.append(
                f"budget_reduction_pct clamped from {config.budget_reduction_pct} to 50.0"
            )
            config.budget_reduction_pct = 50.0

        # Clamp fare_multiplier (0.0+)
        if config.fare_multiplier < 0.0:
            warnings.append(
                f"fare_multiplier clamped from {config.fare_multiplier} to 0.0"
            )
            config.fare_multiplier = 0.0

        # Clamp service_frequency_multiplier (0.1 - 5.0)
        if config.service_frequency_multiplier < 0.1:
            warnings.append(
                f"service_frequency_multiplier clamped from "
                f"{config.service_frequency_multiplier} to 0.1"
            )
            config.service_frequency_multiplier = 0.1
        elif config.service_frequency_multiplier > 5.0:
            warnings.append(
                f"service_frequency_multiplier clamped from "
                f"{config.service_frequency_multiplier} to 5.0"
            )
            config.service_frequency_multiplier = 5.0

        # Clamp permit_timeline_reduction_pct (0.0 - 100.0)
        if config.permit_timeline_reduction_pct < 0.0:
            warnings.append(
                f"permit_timeline_reduction_pct clamped from "
                f"{config.permit_timeline_reduction_pct} to 0.0"
            )
            config.permit_timeline_reduction_pct = 0.0
        elif config.permit_timeline_reduction_pct > 100.0:
            warnings.append(
                f"permit_timeline_reduction_pct clamped from "
                f"{config.permit_timeline_reduction_pct} to 100.0"
            )
            config.permit_timeline_reduction_pct = 100.0

        # Validate protected_departments
        invalid_depts = [
            d for d in config.protected_departments if d.lower() not in VALID_DEPARTMENTS
        ]
        if invalid_depts:
            warnings.append(
                f"Unrecognized departments removed: {invalid_depts}. "
                f"Valid: {sorted(VALID_DEPARTMENTS)}"
            )
            config.protected_departments = [
                d for d in config.protected_departments
                if d.lower() in VALID_DEPARTMENTS
            ]

        # Validate permit_target_types
        invalid_types = [
            t for t in config.permit_target_types if t.lower() not in VALID_PERMIT_TYPES
        ]
        if invalid_types:
            warnings.append(
                f"Unrecognized permit types removed: {invalid_types}. "
                f"Valid: {sorted(VALID_PERMIT_TYPES)}"
            )
            config.permit_target_types = [
                t for t in config.permit_target_types
                if t.lower() in VALID_PERMIT_TYPES
            ]

        # Detect policy conflicts
        conflicts = self._detect_conflicts(config)
        warnings.extend(conflicts)

        # Check for empty tract lists when density/enforcement is set
        if config.density_multiplier > 1.0 and not config.target_tract_ids:
            warnings.append(
                "density_multiplier is set but no target_tract_ids specified. "
                "The density change will have no geographic target."
            )

        if (
            config.enforcement_budget_multiplier != 1.0
            and not config.enforcement_target_tracts
        ):
            warnings.append(
                "enforcement_budget_multiplier is changed but no "
                "enforcement_target_tracts specified. Enforcement change "
                "will apply city-wide."
            )

        return config, warnings, errors

    def generate_summary(self, config: PolicyConfiguration) -> str:
        """Generate a human-readable summary of the policy configuration.

        Args:
            config: The PolicyConfiguration to summarize.

        Returns:
            Human-readable summary string.
        """
        parts: list[str] = []

        if config.density_multiplier > 1.0 and config.target_tract_ids:
            neighborhoods = self._tracts_to_neighborhoods(config.target_tract_ids)
            area_desc = ", ".join(neighborhoods) if neighborhoods else f"{len(config.target_tract_ids)} tracts"
            parts.append(
                f"Upzone {len(config.target_tract_ids)} tracts in {area_desc} "
                f"to {config.density_multiplier}x density"
            )

        if config.enforcement_budget_multiplier != 1.0:
            if config.enforcement_target_tracts:
                neighborhoods = self._tracts_to_neighborhoods(
                    config.enforcement_target_tracts
                )
                area_desc = ", ".join(neighborhoods) if neighborhoods else "targeted areas"
            else:
                area_desc = "city-wide"
            parts.append(
                f"{config.enforcement_budget_multiplier}x enforcement budget in {area_desc}"
            )

        if config.treatment_beds_added > 0:
            parts.append(f"Add {config.treatment_beds_added} treatment beds")

        if config.budget_reduction_pct > 0:
            protected = ""
            if config.protected_departments:
                protected = f" (protecting {', '.join(config.protected_departments)})"
            parts.append(
                f"Cut city budget by {config.budget_reduction_pct}%{protected}"
            )

        if config.fare_multiplier != 1.0:
            if config.fare_multiplier == 0.0:
                parts.append("Make transit free")
            else:
                parts.append(f"Set transit fare to {config.fare_multiplier}x current")

        if config.service_frequency_multiplier != 1.0:
            pct_change = (config.service_frequency_multiplier - 1.0) * 100
            direction = "increase" if pct_change > 0 else "decrease"
            parts.append(
                f"{direction.capitalize()} transit frequency by {abs(pct_change):.0f}%"
            )

        if config.permit_timeline_reduction_pct > 0:
            types_desc = ", ".join(config.permit_target_types) if config.permit_target_types else "all"
            parts.append(
                f"Reduce {types_desc} permit timelines by "
                f"{config.permit_timeline_reduction_pct}%"
            )

        if not parts:
            return "No policy changes (baseline scenario)."

        return "; ".join(parts) + "."

    def _resolve_tract_ids(
        self, tract_ids: list[str], warnings: list[str]
    ) -> list[str]:
        """Resolve any neighborhood names mixed into tract ID lists.

        Args:
            tract_ids: List that may contain tract IDs or neighborhood names.
            warnings: Mutable list to append warnings to.

        Returns:
            List of resolved tract IDs.
        """
        resolved: list[str] = []
        for item in tract_ids:
            item_lower = item.lower().strip()
            if item_lower in NEIGHBORHOOD_TRACTS:
                neighborhood_tracts = NEIGHBORHOOD_TRACTS[item_lower]
                warnings.append(
                    f"Resolved neighborhood '{item}' to {len(neighborhood_tracts)} tract IDs."
                )
                resolved.extend(neighborhood_tracts)
            else:
                resolved.append(item)
        # Deduplicate while preserving order
        seen: set[str] = set()
        deduped: list[str] = []
        for t in resolved:
            if t not in seen:
                seen.add(t)
                deduped.append(t)
        return deduped

    def _tracts_to_neighborhoods(self, tract_ids: list[str]) -> list[str]:
        """Map a list of tract IDs back to neighborhood names.

        Args:
            tract_ids: List of census tract IDs.

        Returns:
            Sorted list of unique neighborhood names found.
        """
        neighborhoods: set[str] = set()
        for tract_id in tract_ids:
            if tract_id in TRACT_TO_NEIGHBORHOOD:
                neighborhoods.add(TRACT_TO_NEIGHBORHOOD[tract_id].title())
        return sorted(neighborhoods)

    def _detect_conflicts(self, config: PolicyConfiguration) -> list[str]:
        """Detect conflicting policy settings.

        Args:
            config: The PolicyConfiguration to check.

        Returns:
            List of conflict warning strings.
        """
        conflicts: list[str] = []

        # Conflict: cutting police budget while increasing enforcement
        if (
            config.budget_reduction_pct > 0
            and "police" not in [d.lower() for d in config.protected_departments]
            and config.enforcement_budget_multiplier > 1.0
        ):
            conflicts.append(
                "CONFLICT: Increasing enforcement budget while cutting city budget "
                "without protecting police department. The enforcement increase may "
                "be offset by budget cuts."
            )

        # Conflict: free transit with reduced frequency
        if config.fare_multiplier == 0.0 and config.service_frequency_multiplier < 1.0:
            conflicts.append(
                "CONFLICT: Making transit free while reducing service frequency. "
                "Free fares will increase demand, but reduced frequency will worsen service."
            )

        # Conflict: high density without permit streamlining
        if config.density_multiplier >= 3.0 and config.permit_timeline_reduction_pct == 0.0:
            conflicts.append(
                "NOTE: High density upzoning without permit streamlining. "
                "Construction may be bottlenecked by slow permit approvals."
            )

        return conflicts
