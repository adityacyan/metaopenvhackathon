# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""
Reward calculation for the API Conformance Gym environment.

Implements the reward formula: R = (V × 0.6) + (B × 0.4) - (E × 0.2)
where:
  V = Validity Score (0.0-1.0)
  B = Best Practices Score (0.0-1.0)
  E = Normalized Error Count (0.0-1.0)
"""

try:
    from ..models import ValidationResult
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
        from models import ValidationResult
    except ImportError:
        # Last resort - try direct import
        from api_conformance_gym.models import ValidationResult


class RewardCalculator:
    """Calculates rewards based on validation results."""

    MAX_ERRORS = 20  # Maximum errors before penalty is fully applied

    @staticmethod
    def calculate(validation_result: ValidationResult) -> float:
        """Calculate reward using the formula: R = (V × 0.6) + (B × 0.4) - (E × 0.2)

        Args:
            validation_result: ValidationResult from the validation pipeline

        Returns:
            Reward value in range [-0.2, 1.0]
        """
        # Extract scores from validation result
        validity_score = validation_result.validity_score
        best_practices_score = validation_result.best_practices_score
        error_count = len(validation_result.errors)

        # Normalize error count to [0.0, 1.0]
        normalized_error_count = min(1.0, error_count / RewardCalculator.MAX_ERRORS)

        # Apply reward formula
        reward = (
            (validity_score * 0.6)
            + (best_practices_score * 0.4)
            - (normalized_error_count * 0.2)
        )

        # Ensure reward is within bounds [-0.2, 1.0]
        reward = max(-0.2, min(1.0, reward))

        return reward

    @staticmethod
    def calculate_shaped(
        validation_result: ValidationResult,
        task_score: float,
        progress_delta: float,
        penalty: float = 0.0,
    ) -> float:
        """Calculate a trajectory-aware reward in [0.0, 1.0].

        Composition:
          - 45% global schema quality from validator scores
          - 35% active task grader score (easy/medium/hard)
          - 20% positive progress delta over previous step
          - subtract explicit behavior penalties
        """
        quality = (validation_result.validity_score * 0.55) + (
            validation_result.best_practices_score * 0.45
        )

        # Clamp external components for safety.
        task_score = max(0.0, min(1.0, task_score))
        progress_delta = max(0.0, min(1.0, progress_delta))
        penalty = max(0.0, min(0.5, penalty))

        reward = (
            (quality * 0.45) + (task_score * 0.35) + (progress_delta * 0.20) - penalty
        )
        return max(0.0, min(1.0, reward))
