"""
API Conformance Gym Environment Implementation.

This environment trains RL agents to design robust, secure, and compliant REST API schemas.
Agents receive natural language business requirements and must produce valid OpenAPI 3.0/3.1 schemas.
Through iterative feedback from a multi-stage validation pipeline, agents learn to incrementally
improve their API designs across multiple steps.
"""

import random
import time
from typing import Dict, List, Optional, Any
from uuid import uuid4

from openenv.core.env_server.interfaces import Environment
from openenv.core.env_server.types import State

try:
    from ..models import APIAction, APIObservation, APIState, ValidationResult
    from .validators import ValidationPipeline
    from .reward import RewardCalculator
    from .llm_reward import HybridRewardCalculator
    from .graders import TaskGradingSystem
except ImportError:
    # Handle both relative and absolute imports
    import sys
    import os

    # Add parent directory to path for absolute imports
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)

    try:
        from models import APIAction, APIObservation, APIState, ValidationResult
        from server.validators import ValidationPipeline
        from server.reward import RewardCalculator
        from server.llm_reward import HybridRewardCalculator
        from server.graders import TaskGradingSystem
    except ImportError:
        # Last resort - try direct imports
        from api_conformance_gym.models import (
            APIAction,
            APIObservation,
            APIState,
            ValidationResult,
        )
        from api_conformance_gym.server.validators import ValidationPipeline
        from api_conformance_gym.server.reward import RewardCalculator
        from api_conformance_gym.server.llm_reward import HybridRewardCalculator
        from api_conformance_gym.server.graders import TaskGradingSystem


class APIEnvironment(Environment):
    """
    API Conformance Gym Environment.

    This environment presents agents with natural language business requirements
    and expects them to produce valid OpenAPI 3.0/3.1 schemas. The environment
    provides structured feedback through a multi-stage validation pipeline and
    calculates rewards server-side to prevent reward hacking.

    Features:
    - Multi-turn schema improvement
    - Comprehensive validation pipeline (JSON, OpenAPI, Auth, Best Practices)
    - Server-side reward calculation: R = (V × 0.6) + (B × 0.4) - (E × 0.2)
    - Episode termination on max iterations or perfect schema
    - Complete state history tracking

    Example:
        >>> env = APIEnvironment()
        >>> state = env.reset()
        >>> print(state.business_requirement)  # "Design a library management API..."
        >>>
        >>> action = APIAction(schema_json='{"openapi": "3.0.0", ...}', iteration=1)
        >>> obs, reward, done, info = env.step(action)
        >>> print(f"Reward: {reward}, Errors: {obs.error_count}")
    """

    # Enable concurrent WebSocket sessions
    SUPPORTS_CONCURRENT_SESSIONS: bool = True

    # Environment configuration
    MAX_ITERATIONS = 10
    MAX_ERRORS = 20

    # Real-world business requirements pool
    BUSINESS_REQUIREMENTS = [
        "Design a library management API with user authentication, book search, borrowing system, and overdue notifications. Include endpoints for user registration, book catalog management, checkout/return operations, and fine calculations.",
        "Create an e-commerce checkout API with product catalog, shopping cart, payment processing, and order management. Include security for payment data, inventory tracking, user accounts, and order history.",
        "Build a user authentication system API with registration, login, password reset, and profile management. Include JWT token handling, role-based access control, email verification, and session management.",
        "Design a data analytics API for processing and querying large datasets. Include endpoints for data ingestion, query execution, result aggregation, and report generation with proper authentication and rate limiting.",
        "Create a scheduling system API for appointment booking with calendar integration, availability checking, and notification system. Include user management, resource booking, conflict resolution, and reminder services.",
        "Build a content moderation API for social media platforms with automated content analysis, user reporting, and admin review workflows. Include content classification, user management, and audit trails.",
        "Design a real estate listing API with property search, agent management, and inquiry handling. Include geolocation search, image management, contact forms, and market analytics.",
        "Create a healthcare appointment API with patient records, doctor scheduling, and prescription management. Include HIPAA compliance, secure data handling, and integration with medical systems.",
        "Build a financial transaction API with account management, transfer processing, and fraud detection. Include strong security, audit logging, compliance reporting, and real-time notifications.",
        "Design a project management API with task tracking, team collaboration, and progress reporting. Include user roles, project hierarchies, time tracking, and notification systems.",
    ]

    def __init__(self, use_llm_grading: bool = False, **llm_kwargs):
        """Initialize the API Conformance Gym environment.

        Args:
            use_llm_grading: Whether to use LLM-based reward grading via Ollama
            **llm_kwargs: Additional arguments for LLM reward calculator
        """
        self._state = State(episode_id=str(uuid4()), step_count=0)
        self._current_state: Optional[APIState] = None
        self._validation_pipeline = ValidationPipeline()

        # Choose reward calculator based on configuration
        if use_llm_grading:
            self._reward_calculator = HybridRewardCalculator(use_llm=True, **llm_kwargs)
            print("Using LLM-enhanced reward grading via Ollama")
        else:
            self._reward_calculator = RewardCalculator()
            print("Using rule-based reward calculation")

        self._reset_count = 0
        self._use_llm_grading = use_llm_grading
        self._task_grading = TaskGradingSystem()
        self._active_task_idx = 0
        self._previous_task_score = 0.0

    def reset(self, seed: Optional[int] = None) -> APIObservation:
        """
        Reset the environment with a new business requirement.

        Args:
            seed: Optional seed for deterministic requirement selection

        Returns:
            APIObservation with initial state and business requirement in episode_info
        """
        start_time = time.time()

        # Set seed for deterministic behavior
        if seed is not None:
            random.seed(seed)

        # Generate new episode ID and reset step count
        self._state = State(episode_id=str(uuid4()), step_count=0)
        self._reset_count += 1
        self._active_task_idx = (self._reset_count - 1) % len(self._task_grading.graders)
        self._previous_task_score = 0.0

        # Select business requirement
        business_requirement = random.choice(self.BUSINESS_REQUIREMENTS)

        # Initialize new APIState
        self._current_state = APIState(
            business_requirement=business_requirement,
            current_schema=None,
            validation_result=None,
            iteration_count=0,
            schema_history=[],
            error_history=[],
            episode_done=False,
            total_reward=0.0,
        )

        # Create initial observation with business requirement in episode_info
        observation = APIObservation(
            validation_errors=[],
            error_count=0,
            validity_score=0.0,
            best_practices_score=0.0,
            schema_feedback="New episode started. Please submit your OpenAPI schema design.",
            iteration=0,
            episode_info={
                "episode_id": self._state.episode_id,
                "step_count": 0,
                "iteration_count": 0,
                "max_iterations": self.MAX_ITERATIONS,
                "business_requirement": business_requirement,
                "task_name": self._task_grading.graders[self._active_task_idx].task_name,
                "task_difficulty": self._task_grading.graders[self._active_task_idx].difficulty,
            },
            episode_done=False,
        )

        # Ensure reset completes within 100ms
        elapsed = (time.time() - start_time) * 1000
        if elapsed > 100:
            print(f"Warning: reset() took {elapsed:.1f}ms (target: <100ms)")

        return observation

    def step(self, action: APIAction) -> APIObservation:
        """
        Execute a step by validating the submitted schema and calculating reward.

        Args:
            action: APIAction containing schema_json and metadata

        Returns:
            APIObservation with reward and done fields populated
        """
        start_time = time.time()

        if self._current_state is None:
            raise RuntimeError("Environment not initialized. Call reset() first.")

        # Increment step count and iteration
        self._state.step_count += 1
        self._current_state.iteration_count += 1

        # Validate the schema using the validation pipeline
        validation_result = self._validation_pipeline.validate(action.schema_json)

        # Grade active task (easy/medium/hard) with deterministic criteria.
        active_grader = self._task_grading.graders[self._active_task_idx]
        task_grade = active_grader.grade(action.schema_json, validation_result)
        task_score = task_grade.score
        progress_delta = max(0.0, task_score - self._previous_task_score)

        # Penalize clear undesirable behavior.
        repeated_schema = bool(self._current_state.schema_history) and (
            action.schema_json == self._current_state.schema_history[-1]
        )
        no_progress = self._current_state.iteration_count > 1 and progress_delta < 0.01
        penalty = 0.0
        if repeated_schema:
            penalty += 0.10
        if no_progress:
            penalty += 0.05

        # Calculate reward (enhanced with LLM if enabled)
        if self._use_llm_grading:
            llm_reward = self._reward_calculator.calculate(
                validation_result,
                business_requirement=self._current_state.business_requirement,
                schema_json=action.schema_json,
                iteration=self._current_state.iteration_count,
            )
            shaped_reward = RewardCalculator.calculate_shaped(
                validation_result=validation_result,
                task_score=task_score,
                progress_delta=progress_delta,
                penalty=penalty,
            )
            reward = max(0.0, min(1.0, (0.6 * shaped_reward) + (0.4 * llm_reward)))
        else:
            reward = self._reward_calculator.calculate_shaped(
                validation_result=validation_result,
                task_score=task_score,
                progress_delta=progress_delta,
                penalty=penalty,
            )

        self._previous_task_score = task_score

        # Update state
        self._current_state.current_schema = action.schema_json
        self._current_state.validation_result = validation_result
        self._current_state.schema_history.append(action.schema_json)
        self._current_state.error_history.append(validation_result.errors)
        self._current_state.total_reward += reward

        # Check termination conditions with stricter completion criteria.
        task_mastered = (
            task_score >= 0.90
            and validation_result.validity_score >= 0.90
            and validation_result.best_practices_score >= 0.85
        )
        episode_done = self._current_state.iteration_count >= self.MAX_ITERATIONS or task_mastered
        self._current_state.episode_done = episode_done

        # Generate human-readable feedback
        schema_feedback = self._generate_feedback(validation_result)

        # Create episode info
        episode_info = {
            "episode_id": self._state.episode_id,
            "step_count": self._state.step_count,
            "iteration_count": self._current_state.iteration_count,
            "max_iterations": self.MAX_ITERATIONS,
            "business_requirement": self._current_state.business_requirement,
            "task_name": active_grader.task_name,
            "task_difficulty": active_grader.difficulty,
            "task_score": task_score,
            "progress_delta": progress_delta,
            "penalty": penalty,
        }

        if episode_done:
            episode_info.update(
                {
                    "termination_reason": (
                        "max_iterations"
                        if self._current_state.iteration_count >= self.MAX_ITERATIONS
                        else "task_mastered"
                    ),
                    "final_validity_score": validation_result.validity_score,
                    "final_best_practices_score": validation_result.best_practices_score,
                    "total_reward": self._current_state.total_reward,
                    "final_task_score": task_score,
                }
            )

        # Create observation
        observation = APIObservation(
            validation_errors=validation_result.errors,
            error_count=len(validation_result.errors),
            validity_score=validation_result.validity_score,
            best_practices_score=validation_result.best_practices_score,
            schema_feedback=schema_feedback,
            iteration=self._current_state.iteration_count,
            episode_info=episode_info,
            episode_done=episode_done,
        )

        # Ensure step completes within 500ms
        elapsed = (time.time() - start_time) * 1000
        if elapsed > 500:
            print(f"Warning: step() took {elapsed:.1f}ms (target: <500ms)")

        observation.reward = reward
        observation.done = episode_done

        return observation

    @property
    def state(self) -> APIState:
        """
        Get the current environment state.

        Returns:
            Current APIState with complete history and metadata
        """
        if self._current_state is None:
            raise RuntimeError("Environment not initialized. Call reset() first.")

        return self._current_state

    def _generate_feedback(self, validation_result: ValidationResult) -> str:
        """
        Generate human-readable feedback from validation results.

        Args:
            validation_result: ValidationResult from pipeline

        Returns:
            Human-readable feedback string
        """
        if not validation_result.errors:
            return "Excellent! Your API schema is valid and follows best practices."

        critical_errors = [
            e for e in validation_result.errors if e.severity == "critical"
        ]
        warning_errors = [
            e for e in validation_result.errors if e.severity == "warning"
        ]
        info_errors = [e for e in validation_result.errors if e.severity == "info"]

        feedback_parts = []

        if critical_errors:
            feedback_parts.append(
                f"Critical issues ({len(critical_errors)}): {critical_errors[0].message}"
            )
            if len(critical_errors) > 1:
                feedback_parts.append(
                    f"Plus {len(critical_errors) - 1} more critical issues."
                )

        if warning_errors:
            feedback_parts.append(
                f"Warnings ({len(warning_errors)}): {warning_errors[0].message}"
            )

        if info_errors:
            feedback_parts.append(
                f"Suggestions ({len(info_errors)}): {info_errors[0].message}"
            )

        if validation_result.validity_score > 0.5:
            feedback_parts.append("Good progress on OpenAPI compliance!")

        if validation_result.best_practices_score > 0.7:
            feedback_parts.append("Following API design best practices well.")

        return " ".join(feedback_parts)


# Alias for backward compatibility
ApiConformanceGymEnvironment = APIEnvironment
