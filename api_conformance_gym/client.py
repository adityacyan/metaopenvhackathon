# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""API Conformance Gym Environment Client."""

from typing import Dict

from openenv.core import EnvClient
from openenv.core.client_types import StepResult

try:
    from .models import APIAction, APIObservation, APIState
except ImportError:
    # Handle both relative and absolute imports
    import sys
    import os
    
    # Add current directory to path for absolute imports
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)
    
    try:
        from models import APIAction, APIObservation, APIState
    except ImportError:
        # Last resort - try direct import
        from api_conformance_gym.models import APIAction, APIObservation, APIState


class APIEnvClient(EnvClient[APIAction, APIObservation, APIState]):
    """
    Client for the API Conformance Gym Environment.

    This client maintains a persistent WebSocket connection to the environment server,
    enabling efficient multi-step interactions for training RL agents to design
    robust REST API schemas.

    The client handles:
    - WebSocket connection management with automatic reconnection
    - Serialization/deserialization of APIAction, APIObservation, and APIState
    - Error handling and connection recovery
    - Session isolation for concurrent training

    Example:
        >>> # Connect to a running server
        >>> with APIEnvClient(base_url="http://localhost:8000") as client:
        ...     result = client.reset()
        ...     print(result.observation.business_requirement)
        ...
        ...     action = APIAction(schema_json='{"openapi": "3.0.0", ...}', iteration=1)
        ...     result = client.step(action)
        ...     print(f"Reward: {result.reward}, Errors: {result.observation.error_count}")

    Example with Docker:
        >>> # Automatically start container and connect
        >>> client = APIEnvClient.from_docker_image("api_conformance_gym-env:latest")
        >>> try:
        ...     result = client.reset()
        ...     action = APIAction(schema_json='{"openapi": "3.0.0", ...}')
        ...     result = client.step(action)
        ... finally:
        ...     client.close()
    """

    def _step_payload(self, action: APIAction) -> Dict:
        """
        Convert APIAction to JSON payload for step message.

        Args:
            action: APIAction instance with schema_json and metadata

        Returns:
            Dictionary representation suitable for JSON encoding
        """
        return {
            "schema_json": action.schema_json,
            "iteration": action.iteration,
            "metadata": action.metadata,
        }

    def _parse_result(self, payload: Dict) -> StepResult[APIObservation]:
        """
        Parse server response into StepResult[APIObservation].

        Args:
            payload: JSON response data from server

        Returns:
            StepResult with APIObservation containing validation feedback
        """
        obs_data = payload.get("observation", {})
        
        # Parse validation errors
        validation_errors = []
        for error_data in obs_data.get("validation_errors", []):
            try:
                from .models import ValidationError
            except ImportError:
                from models import ValidationError
            validation_errors.append(ValidationError(
                error_type=error_data.get("error_type", ""),
                severity=error_data.get("severity", "info"),
                path=error_data.get("path", ""),
                message=error_data.get("message", ""),
                suggestion=error_data.get("suggestion", "")
            ))
        
        observation = APIObservation(
            validation_errors=validation_errors,
            error_count=obs_data.get("error_count", 0),
            validity_score=obs_data.get("validity_score", 0.0),
            best_practices_score=obs_data.get("best_practices_score", 0.0),
            schema_feedback=obs_data.get("schema_feedback", ""),
            iteration=obs_data.get("iteration", 0),
            episode_info=obs_data.get("episode_info", {}),
            episode_done=obs_data.get("episode_done", False)
        )

        return StepResult(
            observation=observation,
            reward=payload.get("reward"),
            done=payload.get("done", False),
        )

    def _parse_state(self, payload: Dict) -> APIState:
        """
        Parse server response into APIState object.

        Args:
            payload: JSON response from state request

        Returns:
            APIState object with complete environment state and history
        """
        try:
            from .models import ValidationResult, ValidationError
        except ImportError:
            from models import ValidationResult, ValidationError
        
        # Parse validation result if present
        validation_result = None
        if "validation_result" in payload and payload["validation_result"]:
            vr_data = payload["validation_result"]
            
            # Parse validation errors
            errors = []
            for error_data in vr_data.get("errors", []):
                errors.append(ValidationError(
                    error_type=error_data.get("error_type", ""),
                    severity=error_data.get("severity", "info"),
                    path=error_data.get("path", ""),
                    message=error_data.get("message", ""),
                    suggestion=error_data.get("suggestion", "")
                ))
            
            validation_result = ValidationResult(
                is_valid=vr_data.get("is_valid", False),
                errors=errors,
                validity_score=vr_data.get("validity_score", 0.0),
                best_practices_score=vr_data.get("best_practices_score", 0.0),
                validation_stages=vr_data.get("validation_stages", {}),
                timestamp=vr_data.get("timestamp", 0.0)
            )
        
        # Parse error history
        error_history = []
        for error_list_data in payload.get("error_history", []):
            error_list = []
            for error_data in error_list_data:
                error_list.append(ValidationError(
                    error_type=error_data.get("error_type", ""),
                    severity=error_data.get("severity", "info"),
                    path=error_data.get("path", ""),
                    message=error_data.get("message", ""),
                    suggestion=error_data.get("suggestion", "")
                ))
            error_history.append(error_list)
        
        return APIState(
            business_requirement=payload.get("business_requirement", ""),
            current_schema=payload.get("current_schema"),
            validation_result=validation_result,
            iteration_count=payload.get("iteration_count", 0),
            schema_history=payload.get("schema_history", []),
            error_history=error_history,
            episode_done=payload.get("episode_done", False),
            total_reward=payload.get("total_reward", 0.0)
        )


# Alias for backward compatibility
ApiConformanceGymEnv = APIEnvClient
