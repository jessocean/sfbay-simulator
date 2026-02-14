"""Pydantic models for API request/response schemas."""

from pydantic import BaseModel, Field


class PolicyParseRequest(BaseModel):
    """Request to parse natural language into a policy configuration."""

    text: str = Field(..., description="Natural language policy description")


class PolicyParseResponse(BaseModel):
    """Response containing parsed policy configuration."""

    config: dict = Field(..., description="Parsed PolicyConfiguration as a dictionary")
    summary: str = Field(..., description="Human-readable summary of the policy")
    warnings: list[str] = Field(
        default_factory=list, description="Non-fatal validation warnings"
    )
    affected_tracts: list[str] = Field(
        default_factory=list,
        description="All census tract IDs affected by this policy",
    )


class PolicyRefineRequest(BaseModel):
    """Request to refine an existing policy configuration."""

    text: str = Field(..., description="Natural language refinement instruction")
    current_config: dict = Field(
        ..., description="Current PolicyConfiguration as a dictionary"
    )


class SimulationRunRequest(BaseModel):
    """Request to start a simulation run."""

    config: dict = Field(..., description="PolicyConfiguration as a dictionary")
    name: str = Field(default="", description="Optional name for the simulation run")


class SimulationStatus(BaseModel):
    """Status of a running or completed simulation."""

    run_id: str = Field(..., description="Unique identifier for the simulation run")
    status: str = Field(
        ..., description="Current status: pending, running, completed, failed"
    )
    progress: float = Field(
        ..., description="Progress from 0.0 to 1.0", ge=0.0, le=1.0
    )
    current_step: int = Field(..., description="Current simulation timestep")
    total_steps: int = Field(..., description="Total number of timesteps")


class TractResult(BaseModel):
    """Simulation results for a single census tract."""

    tract_id: str = Field(..., description="Census tract ID")
    values: dict = Field(
        ...,
        description="Metric values for this tract (e.g., population, rent, crime_index)",
    )


class MetricsResult(BaseModel):
    """Aggregate simulation metrics for a single timestep."""

    timestep: int = Field(..., description="Simulation timestep number")
    metrics: dict = Field(
        ...,
        description="Aggregate metric values (e.g., total_population, avg_rent, budget_balance)",
    )


class TimeseriesPoint(BaseModel):
    """A single data point in a time series."""

    timestep: int = Field(..., description="Simulation timestep number")
    value: float = Field(..., description="Metric value at this timestep")


class PredefinedScenario(BaseModel):
    """A predefined policy scenario with a natural language description."""

    id: str = Field(..., description="Unique scenario identifier")
    name: str = Field(..., description="Short display name")
    description: str = Field(..., description="Natural language description of the policy")
    config: dict = Field(..., description="PolicyConfiguration as a dictionary")
