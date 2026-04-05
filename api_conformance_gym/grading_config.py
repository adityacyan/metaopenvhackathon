# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""
Configuration for reward grading systems.

This module provides easy configuration switching between rule-based
and LLM-enhanced reward grading systems.
"""

from typing import Dict, Any
import os

# Default configuration
DEFAULT_CONFIG = {
    # Grading system selection
    "use_llm_grading": False,  # Set to True to enable LLM grading
    
    # Ollama configuration
    "ollama_url": "http://localhost:11434",
    "model_name": "llama3.1",  # Change to your preferred model
    "timeout": 15.0,
    "fallback_to_rule_based": True,
    
    # LLM grading weights (used in _combine_scores)
    "business_alignment_weight": 0.35,
    "design_quality_weight": 0.30,
    "completeness_weight": 0.25,
    "innovation_weight": 0.10,
    
    # Confidence-based blending
    "max_llm_influence": 0.7,  # Maximum influence of LLM vs rule-based (0.0-1.0)
    "critical_error_cap": 0.4,  # Max reward when critical validation errors exist
}

# Environment-specific overrides
ENV_OVERRIDES = {
    "development": {
        "use_llm_grading": True,
        "timeout": 20.0,  # Longer timeout for development
    },
    "production": {
        "use_llm_grading": False,  # Safer for production
        "timeout": 10.0,
    },
    "hackathon": {
        "use_llm_grading": True,
        "model_name": "llama3.1",
        "timeout": 15.0,
        "innovation_weight": 0.15,  # Higher innovation weight for hackathon
    }
}

def get_grading_config(environment: str = None) -> Dict[str, Any]:
    """Get grading configuration for specified environment.
    
    Args:
        environment: Environment name ("development", "production", "hackathon")
                    If None, uses DEFAULT_CONFIG
    
    Returns:
        Configuration dictionary
    """
    config = DEFAULT_CONFIG.copy()
    
    # Apply environment-specific overrides
    if environment and environment in ENV_OVERRIDES:
        config.update(ENV_OVERRIDES[environment])
    
    # Apply environment variable overrides
    if os.getenv("USE_LLM_GRADING"):
        config["use_llm_grading"] = os.getenv("USE_LLM_GRADING").lower() == "true"
    
    if os.getenv("OLLAMA_URL"):
        config["ollama_url"] = os.getenv("OLLAMA_URL")
    
    if os.getenv("OLLAMA_MODEL"):
        config["model_name"] = os.getenv("OLLAMA_MODEL")
    
    return config

def create_environment_with_config(environment: str = None, **override_kwargs):
    """Create APIEnvironment with specified configuration.
    
    Args:
        environment: Environment name for configuration
        **override_kwargs: Additional overrides for configuration
    
    Returns:
        Configured APIEnvironment instance
    """
    from server.api_conformance_gym_environment import APIEnvironment
    
    config = get_grading_config(environment)
    config.update(override_kwargs)
    
    # Extract LLM-specific config
    llm_config = {
        "ollama_url": config["ollama_url"],
        "model_name": config["model_name"],
        "timeout": config["timeout"],
        "fallback_to_rule_based": config["fallback_to_rule_based"],
    }
    
    return APIEnvironment(
        use_llm_grading=config["use_llm_grading"],
        **llm_config
    )

# Quick access functions
def create_development_env(**kwargs):
    """Create environment configured for development."""
    return create_environment_with_config("development", **kwargs)

def create_production_env(**kwargs):
    """Create environment configured for production."""
    return create_environment_with_config("production", **kwargs)

def create_hackathon_env(**kwargs):
    """Create environment configured for hackathon."""
    return create_environment_with_config("hackathon", **kwargs)