# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""
Data models for the API Conformance Gym Environment.

This module defines the core data structures for the api-conformance-gym OpenEnv environment,
which trains RL agents to design robust, secure, and compliant REST API schemas.
"""

import warnings
from typing import Any, Dict, List, Optional

from openenv.core.env_server.types import Action, Observation, State
from pydantic import BaseModel, Field, validator

# APIAction intentionally mirrors OpenEnv payload key `schema_json`.
# Silence the specific class construction warning to keep runtime output clean.
warnings.filterwarnings(
    "ignore",
    message=r'Field name "schema_json" in "APIAction" shadows an attribute in parent "Action"',
    category=UserWarning,
)


class ValidationError(BaseModel):
    """Represents a single validation error with actionable feedback.

    Attributes:
        error_type: Category of error (e.g., "missing_auth", "invalid_method")
        severity: Error severity level ("critical", "warning", or "info")
        path: JSON path to error location (e.g., "paths./users.get")
        message: Human-readable error description
        suggestion: Actionable fix suggestion
    """

    error_type: str
    severity: str = Field(..., pattern="^(critical|warning|info)$")
    path: str
    message: str = Field(..., min_length=1)
    suggestion: str = Field(..., min_length=1)


class ValidationResult(BaseModel):
    """Aggregated validation results from the entire pipeline.

    Attributes:
        is_valid: Overall validity flag (True only if errors list is empty)
        errors: List of all validation errors found
        validity_score: Percentage of OpenAPI spec checks passed (0.0-1.0)
        best_practices_score: Compliance with API design best practices (0.0-1.0)
        validation_stages: Per-stage results from validation pipeline
        timestamp: Unix timestamp when validation occurred
    """

    is_valid: bool
    errors: List[ValidationError] = Field(default_factory=list)
    validity_score: float = Field(..., ge=0.0, le=1.0)
    best_practices_score: float = Field(..., ge=0.0, le=1.0)
    validation_stages: Dict[str, Any] = Field(default_factory=dict)
    timestamp: float

    @validator("is_valid")
    def validate_is_valid(cls, v, values):
        """Ensure is_valid is False if errors exist."""
        errors = values.get("errors", [])
        if v and len(errors) > 0:
            raise ValueError("is_valid must be False if errors list is not empty")
        return v


class APIAction(Action):
    """Represents an agent's action - submitting an OpenAPI schema design.

    Attributes:
        schema_json: JSON-stringified OpenAPI 3.0/3.1 schema
        iteration: Current iteration number for tracking
        metadata: Optional metadata (agent_id, timestamp, etc.)
    """

    schema_json: str = Field(..., description="JSON-stringified OpenAPI schema")
    iteration: int = Field(default=0, description="Current iteration number")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Optional metadata"
    )

    @validator("schema_json")
    def validate_schema_json(cls, v):
        """Ensure schema_json is non-empty."""
        if not v or not isinstance(v, str):
            raise ValueError("schema_json must be a non-empty string")
        return v

    @validator("iteration")
    def validate_iteration(cls, v):
        """Ensure iteration is non-negative."""
        if v < 0:
            raise ValueError("iteration must be non-negative")
        return v


class APIObservation(Observation):
    """Environment feedback to agent after action submission.

    Attributes:
        validation_errors: Structured list of validation errors
        error_count: Total number of errors
        validity_score: OpenAPI spec compliance (0.0-1.0)
        best_practices_score: API design best practices compliance (0.0-1.0)
        schema_feedback: Human-readable feedback summary
        iteration: Current iteration number
        episode_info: Additional episode metadata
        episode_done: Whether episode is complete
        reward: Step reward (for OpenEnv compatibility)
        done: Episode done flag (for OpenEnv compatibility)
    """

    validation_errors: List[ValidationError] = Field(default_factory=list)
    error_count: int = Field(default=0)
    validity_score: float = Field(default=0.0, ge=0.0, le=1.0)
    best_practices_score: float = Field(default=0.0, ge=0.0, le=1.0)
    schema_feedback: str = Field(default="")
    iteration: int = Field(default=0, ge=0)
    episode_info: Dict[str, Any] = Field(default_factory=dict)
    episode_done: bool = Field(default=False)

    # OpenEnv compatibility fields
    reward: float = Field(default=0.0, description="Step reward")
    done: bool = Field(default=False, description="Episode done flag")

    @validator("error_count")
    def validate_error_count(cls, v, values):
        """Ensure error_count matches validation_errors length."""
        validation_errors = values.get("validation_errors", [])
        if v != len(validation_errors):
            raise ValueError("error_count must equal length of validation_errors")
        if v < 0:
            raise ValueError("error_count must be non-negative")
        return v


class APIState(State):
    """Complete environment state at any point in time.

    Attributes:
        business_requirement: Original natural language requirement
        current_schema: Current OpenAPI schema (JSON string) or None
        validation_result: Latest validation result
        iteration_count: Number of steps taken
        schema_history: All previously submitted schemas
        error_history: Error progression across iterations
        episode_done: Whether episode is complete
        total_reward: Cumulative reward across all steps
        reward: Current step reward (for OpenEnv compatibility)
        done: Episode done flag (for OpenEnv compatibility)
    """

    business_requirement: str = Field(..., min_length=1)
    current_schema: Optional[str] = None
    validation_result: Optional[ValidationResult] = None
    iteration_count: int = Field(default=0, ge=0)
    schema_history: List[str] = Field(default_factory=list)
    error_history: List[List[ValidationError]] = Field(default_factory=list)
    episode_done: bool = False
    total_reward: float = 0.0

    # OpenEnv compatibility fields
    reward: float = Field(default=0.0, description="Current step reward")
    done: bool = Field(default=False, description="Episode done flag")

    @validator("schema_history")
    def validate_schema_history(cls, v, values):
        """Ensure schema_history length matches iteration_count."""
        iteration_count = values.get("iteration_count", 0)
        if len(v) != iteration_count:
            raise ValueError("schema_history length must equal iteration_count")
        return v

    @validator("error_history")
    def validate_error_history(cls, v, values):
        """Ensure error_history length matches iteration_count."""
        iteration_count = values.get("iteration_count", 0)
        if len(v) != iteration_count:
            raise ValueError("error_history length must equal iteration_count")
        return v
