"""Routes for natural language policy parsing."""

from dataclasses import asdict

from fastapi import APIRouter, HTTPException

from api.models import (
    PolicyParseRequest,
    PolicyParseResponse,
    PolicyRefineRequest,
)
from nlp.parser import PolicyParser
from nlp.validator import PolicyValidator
from simulation.core.config import PolicyConfiguration

router = APIRouter(prefix="/parse", tags=["parse"])

# Lazy-init to avoid crashing at import time if ANTHROPIC_API_KEY isn't loaded yet
_parser: PolicyParser | None = None
validator = PolicyValidator()


def _get_parser() -> PolicyParser:
    global _parser
    if _parser is None:
        _parser = PolicyParser()
    return _parser


def _collect_affected_tracts(config: PolicyConfiguration) -> list[str]:
    """Collect all unique tract IDs affected by a policy configuration."""
    tracts: set[str] = set()
    tracts.update(config.target_tract_ids)
    tracts.update(config.enforcement_target_tracts)
    return sorted(tracts)


@router.post("", response_model=PolicyParseResponse)
async def parse_policy(request: PolicyParseRequest) -> PolicyParseResponse:
    """Parse natural language text into a structured policy configuration.

    Sends the text to Claude for NLP parsing, then validates and clamps
    the resulting configuration.
    """
    try:
        config, summary = await _get_parser().parse(request.text)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to parse policy: {str(e)}"
        )

    config, warnings, errors = validator.validate(config)
    if errors:
        raise HTTPException(status_code=422, detail="; ".join(errors))

    # Generate a richer summary from the validator
    summary = validator.generate_summary(config)
    affected_tracts = _collect_affected_tracts(config)

    return PolicyParseResponse(
        config=asdict(config),
        summary=summary,
        warnings=warnings,
        affected_tracts=affected_tracts,
    )


@router.post("/refine", response_model=PolicyParseResponse)
async def refine_policy(request: PolicyRefineRequest) -> PolicyParseResponse:
    """Refine an existing policy configuration based on follow-up instructions.

    Takes the current config and a natural language modification, returns
    the updated configuration.
    """
    # Reconstruct PolicyConfiguration from the dict
    try:
        current_config = PolicyConfiguration(**request.current_config)
    except (TypeError, ValueError) as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid current_config: {str(e)}",
        )

    try:
        config, summary = await _get_parser().refine(request.text, current_config)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to refine policy: {str(e)}"
        )

    config, warnings, errors = validator.validate(config)
    if errors:
        raise HTTPException(status_code=422, detail="; ".join(errors))

    summary = validator.generate_summary(config)
    affected_tracts = _collect_affected_tracts(config)

    return PolicyParseResponse(
        config=asdict(config),
        summary=summary,
        warnings=warnings,
        affected_tracts=affected_tracts,
    )
