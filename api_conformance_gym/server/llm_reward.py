# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""
LLM-based reward calculation using Ollama for contextual API schema grading.

This module provides an enhanced reward system that uses a local LLM (via Ollama)
to evaluate API schemas with deeper contextual understanding, going beyond
rule-based validation to assess design quality, business alignment, and
architectural soundness.
"""

import json
import requests
import time
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass

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


@dataclass
class LLMGradingResult:
    """Result from LLM-based grading."""
    business_alignment_score: float  # How well does the API meet the business requirement?
    design_quality_score: float     # Overall API design quality
    completeness_score: float       # How complete is the implementation?
    innovation_score: float         # Creative/innovative aspects
    explanation: str                 # LLM's detailed explanation
    confidence: float               # LLM's confidence in the grading (0.0-1.0)


class OllamaRewardCalculator:
    """Enhanced reward calculator using Ollama LLM for contextual grading."""
    
    def __init__(self, 
                 ollama_url: str = "http://localhost:11434",
                 model_name: str = "llama3.1",
                 fallback_to_rule_based: bool = True,
                 timeout: float = 10.0):
        """Initialize the LLM reward calculator.
        
        Args:
            ollama_url: Base URL for Ollama API
            model_name: Name of the Ollama model to use
            fallback_to_rule_based: Whether to fall back to rule-based scoring on LLM failure
            timeout: Request timeout in seconds
        """
        self.ollama_url = ollama_url
        self.model_name = model_name
        self.fallback_to_rule_based = fallback_to_rule_based
        self.timeout = timeout
        
        # Import rule-based calculator for fallback
        if fallback_to_rule_based:
            from .reward import RewardCalculator
            self.rule_based_calculator = RewardCalculator()
    
    def calculate(self, 
                  validation_result: ValidationResult,
                  business_requirement: str,
                  schema_json: str,
                  iteration: int = 0) -> float:
        """Calculate reward using LLM grading with rule-based fallback.
        
        Args:
            validation_result: Rule-based validation results
            business_requirement: Original business requirement
            schema_json: The submitted OpenAPI schema
            iteration: Current iteration number
            
        Returns:
            Enhanced reward score (0.0-1.0)
        """
        try:
            # Get LLM grading
            llm_result = self._get_llm_grading(
                business_requirement, 
                schema_json, 
                validation_result,
                iteration
            )
            
            if llm_result is None:
                # Fall back to rule-based if LLM fails
                if self.fallback_to_rule_based:
                    return self.rule_based_calculator.calculate(validation_result)
                else:
                    return 0.0
            
            # Combine LLM grading with rule-based validation
            return self._combine_scores(validation_result, llm_result)
            
        except Exception as e:
            print(f"LLM reward calculation failed: {e}")
            if self.fallback_to_rule_based:
                return self.rule_based_calculator.calculate(validation_result)
            else:
                return 0.0
    
    def _get_llm_grading(self, 
                        business_requirement: str,
                        schema_json: str,
                        validation_result: ValidationResult,
                        iteration: int) -> Optional[LLMGradingResult]:
        """Get grading from Ollama LLM."""
        
        # Prepare validation context
        validation_context = self._format_validation_context(validation_result)
        
        # Create grading prompt
        prompt = self._create_grading_prompt(
            business_requirement,
            schema_json,
            validation_context,
            iteration
        )
        
        try:
            # Call Ollama API
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,  # Low temperature for consistent grading
                        "top_p": 0.9,
                        "num_predict": 500   # Limit response length
                    }
                },
                timeout=self.timeout
            )
            
            if response.status_code != 200:
                print(f"Ollama API error: {response.status_code}")
                return None
            
            llm_response = response.json().get("response", "")
            return self._parse_llm_response(llm_response)
            
        except requests.exceptions.RequestException as e:
            print(f"Ollama request failed: {e}")
            return None
    
    def _create_grading_prompt(self, 
                              business_requirement: str,
                              schema_json: str,
                              validation_context: str,
                              iteration: int) -> str:
        """Create a structured prompt for LLM grading."""
        
        return f"""You are an expert API architect evaluating an OpenAPI schema design. Grade this API schema based on how well it meets the business requirement.

BUSINESS REQUIREMENT:
{business_requirement}

SUBMITTED OPENAPI SCHEMA:
{schema_json}

TECHNICAL VALIDATION RESULTS:
{validation_context}

ITERATION: {iteration + 1}

Please evaluate this API schema on the following criteria and provide scores from 0.0 to 1.0:

1. BUSINESS_ALIGNMENT (0.0-1.0): How well does this API design fulfill the stated business requirement? Does it include all necessary endpoints, data models, and functionality?

2. DESIGN_QUALITY (0.0-1.0): Is this a well-designed API? Consider REST principles, resource modeling, HTTP method usage, response codes, and overall architecture.

3. COMPLETENESS (0.0-1.0): How complete is this implementation? Are there missing endpoints, incomplete data models, or gaps in functionality?

4. INNOVATION (0.0-1.0): Does this design show creative problem-solving, innovative approaches, or thoughtful architectural decisions?

5. CONFIDENCE (0.0-1.0): How confident are you in your assessment?

Respond in this exact JSON format:
{{
  "business_alignment_score": 0.0,
  "design_quality_score": 0.0,
  "completeness_score": 0.0,
  "innovation_score": 0.0,
  "confidence": 0.0,
  "explanation": "Detailed explanation of your grading rationale, highlighting strengths and areas for improvement."
}}

Focus on constructive feedback that would help improve the API design."""
    
    def _format_validation_context(self, validation_result: ValidationResult) -> str:
        """Format validation results for LLM context."""
        
        context_parts = [
            f"Overall Valid: {validation_result.is_valid}",
            f"Validity Score: {validation_result.validity_score:.2f}",
            f"Best Practices Score: {validation_result.best_practices_score:.2f}",
            f"Error Count: {len(validation_result.errors)}"
        ]
        
        if validation_result.errors:
            context_parts.append("\nValidation Errors:")
            for error in validation_result.errors[:5]:  # Limit to first 5 errors
                context_parts.append(f"- {error.severity.upper()}: {error.message}")
            
            if len(validation_result.errors) > 5:
                context_parts.append(f"... and {len(validation_result.errors) - 5} more errors")
        
        return "\n".join(context_parts)
    
    def _parse_llm_response(self, response: str) -> Optional[LLMGradingResult]:
        """Parse LLM response into structured grading result."""
        
        try:
            # Try to extract JSON from response
            response = response.strip()
            
            # Find JSON block
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            
            if start_idx == -1 or end_idx == 0:
                print("No JSON found in LLM response")
                return None
            
            json_str = response[start_idx:end_idx]
            grading_data = json.loads(json_str)
            
            # Validate required fields
            required_fields = [
                "business_alignment_score", "design_quality_score", 
                "completeness_score", "innovation_score", "confidence"
            ]
            
            for field in required_fields:
                if field not in grading_data:
                    print(f"Missing required field: {field}")
                    return None
                
                # Ensure scores are in valid range
                score = float(grading_data[field])
                if not (0.0 <= score <= 1.0):
                    print(f"Score {field} out of range: {score}")
                    grading_data[field] = max(0.0, min(1.0, score))
            
            return LLMGradingResult(
                business_alignment_score=grading_data["business_alignment_score"],
                design_quality_score=grading_data["design_quality_score"],
                completeness_score=grading_data["completeness_score"],
                innovation_score=grading_data["innovation_score"],
                confidence=grading_data["confidence"],
                explanation=grading_data.get("explanation", "No explanation provided")
            )
            
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            print(f"Failed to parse LLM response: {e}")
            return None
    
    def _combine_scores(self, 
                       validation_result: ValidationResult,
                       llm_result: LLMGradingResult) -> float:
        """Combine rule-based validation with LLM grading."""
        
        # Get rule-based score as baseline
        rule_based_score = self.rule_based_calculator.calculate(validation_result)
        
        # Calculate LLM composite score
        llm_composite = (
            llm_result.business_alignment_score * 0.35 +  # Business fit is most important
            llm_result.design_quality_score * 0.30 +     # Design quality
            llm_result.completeness_score * 0.25 +       # Completeness
            llm_result.innovation_score * 0.10           # Innovation bonus
        )
        
        # Weight combination based on LLM confidence
        confidence = llm_result.confidence
        
        # High confidence: favor LLM grading more
        # Low confidence: rely more on rule-based validation
        combined_score = (
            rule_based_score * (1.0 - confidence * 0.7) +
            llm_composite * (confidence * 0.7)
        )
        
        # Ensure critical validation errors still penalize heavily
        if validation_result.validity_score == 0.0:  # Critical errors present
            combined_score = min(combined_score, 0.4)  # Cap at 0.4 for critical issues
        
        # Ensure score is in valid range
        return max(0.0, min(1.0, combined_score))


class HybridRewardCalculator:
    """Hybrid calculator that can switch between rule-based and LLM-based grading."""
    
    def __init__(self, use_llm: bool = True, **ollama_kwargs):
        """Initialize hybrid calculator.
        
        Args:
            use_llm: Whether to use LLM grading (falls back to rule-based if LLM fails)
            **ollama_kwargs: Arguments passed to OllamaRewardCalculator
        """
        self.use_llm = use_llm
        
        if use_llm:
            self.llm_calculator = OllamaRewardCalculator(**ollama_kwargs)
        
        # Always have rule-based as fallback
        from .reward import RewardCalculator
        self.rule_based_calculator = RewardCalculator()
    
    def calculate(self, 
                  validation_result: ValidationResult,
                  business_requirement: str = "",
                  schema_json: str = "",
                  iteration: int = 0) -> float:
        """Calculate reward using the configured method."""
        
        if self.use_llm and business_requirement and schema_json:
            return self.llm_calculator.calculate(
                validation_result, business_requirement, schema_json, iteration
            )
        else:
            return self.rule_based_calculator.calculate(validation_result)