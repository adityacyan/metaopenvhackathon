# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""
Task Grading System for API Conformance Gym.

This module implements programmatic graders for evaluating agent performance
on real-world API design tasks. Each grader returns a score in [0.0, 1.0]
with clear, deterministic success/failure criteria.

The grading system evaluates three distinct tasks of increasing difficulty:
1. Basic API Structure (Easy) - OpenAPI compliance and basic endpoints
2. Security & Authentication (Medium) - Proper auth schemes and protected endpoints  
3. Advanced Best Practices (Hard) - Comprehensive documentation, error handling, versioning
"""

import json
import re
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass

try:
    from ..models import ValidationResult
except ImportError:
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from models import ValidationResult


@dataclass
class TaskGrade:
    """Represents the grade for a single task."""
    task_name: str
    score: float  # 0.0 to 1.0
    max_score: float  # Always 1.0
    passed: bool
    feedback: str
    details: Dict[str, Any]


class TaskGrader:
    """Base class for task graders."""
    
    def __init__(self, task_name: str, difficulty: str):
        self.task_name = task_name
        self.difficulty = difficulty
    
    def grade(self, schema_json: str, validation_result: ValidationResult) -> TaskGrade:
        """Grade the schema for this specific task."""
        raise NotImplementedError


class BasicAPIStructureGrader(TaskGrader):
    """
    Task 1: Basic API Structure (Easy)
    
    Evaluates fundamental OpenAPI compliance and basic endpoint structure.
    Success criteria:
    - Valid JSON structure
    - Required OpenAPI fields present (openapi, info, paths)
    - At least 2 endpoints defined
    - Basic HTTP methods used correctly
    """
    
    def __init__(self):
        super().__init__("Basic API Structure", "Easy")
    
    def grade(self, schema_json: str, validation_result: ValidationResult) -> TaskGrade:
        """Grade basic API structure compliance."""
        score = 0.0
        details = {}
        feedback_parts = []
        
        try:
            schema_dict = json.loads(schema_json)
        except json.JSONDecodeError:
            return TaskGrade(
                task_name=self.task_name,
                score=0.0,
                max_score=1.0,
                passed=False,
                feedback="Invalid JSON structure",
                details={"error": "json_parse_failed"}
            )
        
        # Check required fields (30 points)
        required_fields = ["openapi", "info", "paths"]
        present_fields = [field for field in required_fields if field in schema_dict]
        field_score = len(present_fields) / len(required_fields) * 0.3
        score += field_score
        details["required_fields"] = {
            "present": present_fields,
            "missing": [f for f in required_fields if f not in present_fields],
            "score": field_score
        }
        
        if len(present_fields) == len(required_fields):
            feedback_parts.append("✓ All required fields present")
        else:
            feedback_parts.append(f"✗ Missing fields: {', '.join([f for f in required_fields if f not in present_fields])}")
        
        # Check endpoint count (25 points)
        paths = schema_dict.get("paths", {})
        endpoint_count = len(paths)
        endpoint_score = min(endpoint_count / 2, 1.0) * 0.25  # Full points for 2+ endpoints
        score += endpoint_score
        details["endpoints"] = {
            "count": endpoint_count,
            "score": endpoint_score,
            "paths": list(paths.keys())
        }
        
        if endpoint_count >= 2:
            feedback_parts.append(f"✓ Good endpoint coverage ({endpoint_count} endpoints)")
        else:
            feedback_parts.append(f"✗ Need more endpoints (found {endpoint_count}, need 2+)")
        
        # Check HTTP methods (25 points)
        method_score = 0.0
        total_operations = 0
        correct_methods = 0
        
        for path_name, path_item in paths.items():
            if not isinstance(path_item, dict):
                continue
            
            for method in ["get", "post", "put", "patch", "delete"]:
                if method in path_item:
                    total_operations += 1
                    operation = path_item[method]
                    
                    # Simple heuristic: GET should not modify, POST should create
                    if method == "get":
                        # GET operations should not have requestBody
                        if "requestBody" not in operation:
                            correct_methods += 1
                    elif method == "post":
                        # POST operations often have requestBody for creation
                        correct_methods += 1  # Give benefit of doubt for POST
                    else:
                        correct_methods += 1  # PUT, PATCH, DELETE are generally correct if present
        
        if total_operations > 0:
            method_score = (correct_methods / total_operations) * 0.25
        
        score += method_score
        details["http_methods"] = {
            "total_operations": total_operations,
            "correct_methods": correct_methods,
            "score": method_score
        }
        
        if total_operations > 0:
            feedback_parts.append(f"✓ HTTP methods: {correct_methods}/{total_operations} correct")
        else:
            feedback_parts.append("✗ No HTTP operations defined")
        
        # Check basic validation (20 points)
        critical_errors = [e for e in validation_result.errors if e.severity == "critical"]
        validation_score = (1.0 - min(len(critical_errors) / 5, 1.0)) * 0.2
        score += validation_score
        details["validation"] = {
            "critical_errors": len(critical_errors),
            "score": validation_score
        }
        
        if len(critical_errors) == 0:
            feedback_parts.append("✓ No critical validation errors")
        else:
            feedback_parts.append(f"✗ {len(critical_errors)} critical errors need fixing")
        
        # Determine pass/fail (threshold: 0.6)
        passed = score >= 0.6
        feedback = f"Basic API Structure: {score:.1%} | " + " | ".join(feedback_parts)
        
        return TaskGrade(
            task_name=self.task_name,
            score=score,
            max_score=1.0,
            passed=passed,
            feedback=feedback,
            details=details
        )


class SecurityAuthenticationGrader(TaskGrader):
    """
    Task 2: Security & Authentication (Medium)
    
    Evaluates security schemes and endpoint protection.
    Success criteria:
    - Security schemes defined in components
    - All endpoints properly protected
    - Valid authentication types used
    - Proper security requirements applied
    """
    
    def __init__(self):
        super().__init__("Security & Authentication", "Medium")
    
    def grade(self, schema_json: str, validation_result: ValidationResult) -> TaskGrade:
        """Grade security and authentication implementation."""
        score = 0.0
        details = {}
        feedback_parts = []
        
        try:
            schema_dict = json.loads(schema_json)
        except json.JSONDecodeError:
            return TaskGrade(
                task_name=self.task_name,
                score=0.0,
                max_score=1.0,
                passed=False,
                feedback="Invalid JSON structure",
                details={"error": "json_parse_failed"}
            )
        
        # Check security schemes defined (40 points)
        components = schema_dict.get("components", {})
        security_schemes = components.get("securitySchemes", {})
        
        if security_schemes:
            scheme_score = 0.4
            feedback_parts.append(f"✓ Security schemes defined ({len(security_schemes)} schemes)")
        else:
            scheme_score = 0.0
            feedback_parts.append("✗ No security schemes defined")
        
        score += scheme_score
        details["security_schemes"] = {
            "count": len(security_schemes),
            "schemes": list(security_schemes.keys()),
            "score": scheme_score
        }
        
        # Check valid security scheme types (20 points)
        valid_types = {"apiKey", "http", "oauth2", "openIdConnect"}
        valid_schemes = 0
        
        for scheme_name, scheme_def in security_schemes.items():
            if isinstance(scheme_def, dict) and scheme_def.get("type") in valid_types:
                valid_schemes += 1
        
        if security_schemes:
            type_score = (valid_schemes / len(security_schemes)) * 0.2
        else:
            type_score = 0.0
        
        score += type_score
        details["scheme_types"] = {
            "valid_schemes": valid_schemes,
            "total_schemes": len(security_schemes),
            "score": type_score
        }
        
        if valid_schemes == len(security_schemes) and security_schemes:
            feedback_parts.append("✓ All security scheme types are valid")
        elif security_schemes:
            feedback_parts.append(f"✗ {len(security_schemes) - valid_schemes} invalid scheme types")
        
        # Check endpoint protection (40 points)
        paths = schema_dict.get("paths", {})
        global_security = schema_dict.get("security", [])
        
        total_operations = 0
        protected_operations = 0
        
        for path_name, path_item in paths.items():
            if not isinstance(path_item, dict):
                continue
            
            for method in ["get", "post", "put", "patch", "delete"]:
                if method in path_item:
                    total_operations += 1
                    operation = path_item[method]
                    
                    if isinstance(operation, dict):
                        # Check if operation has security or global security is defined
                        operation_security = operation.get("security")
                        has_security = operation_security is not None or global_security
                        
                        if has_security:
                            protected_operations += 1
        
        if total_operations > 0:
            protection_score = (protected_operations / total_operations) * 0.4
        else:
            protection_score = 0.0
        
        score += protection_score
        details["endpoint_protection"] = {
            "total_operations": total_operations,
            "protected_operations": protected_operations,
            "score": protection_score
        }
        
        if protected_operations == total_operations and total_operations > 0:
            feedback_parts.append("✓ All endpoints properly protected")
        elif total_operations > 0:
            feedback_parts.append(f"✗ {total_operations - protected_operations} unprotected endpoints")
        else:
            feedback_parts.append("✗ No operations to protect")
        
        # Determine pass/fail (threshold: 0.7)
        passed = score >= 0.7
        feedback = f"Security & Authentication: {score:.1%} | " + " | ".join(feedback_parts)
        
        return TaskGrade(
            task_name=self.task_name,
            score=score,
            max_score=1.0,
            passed=passed,
            feedback=feedback,
            details=details
        )


class AdvancedBestPracticesGrader(TaskGrader):
    """
    Task 3: Advanced Best Practices (Hard)
    
    Evaluates comprehensive API design best practices.
    Success criteria:
    - Complete operation documentation
    - Proper error response definitions
    - API versioning strategy
    - Request/response schemas
    - Consistent naming conventions
    """
    
    def __init__(self):
        super().__init__("Advanced Best Practices", "Hard")
    
    def grade(self, schema_json: str, validation_result: ValidationResult) -> TaskGrade:
        """Grade advanced best practices compliance."""
        score = 0.0
        details = {}
        feedback_parts = []
        
        try:
            schema_dict = json.loads(schema_json)
        except json.JSONDecodeError:
            return TaskGrade(
                task_name=self.task_name,
                score=0.0,
                max_score=1.0,
                passed=False,
                feedback="Invalid JSON structure",
                details={"error": "json_parse_failed"}
            )
        
        # Check documentation completeness (25 points)
        paths = schema_dict.get("paths", {})
        total_operations = 0
        documented_operations = 0
        
        for path_name, path_item in paths.items():
            if not isinstance(path_item, dict):
                continue
            
            for method in ["get", "post", "put", "patch", "delete"]:
                if method in path_item:
                    total_operations += 1
                    operation = path_item[method]
                    
                    if isinstance(operation, dict):
                        has_summary = bool(operation.get("summary"))
                        has_description = bool(operation.get("description"))
                        
                        if has_summary or has_description:
                            documented_operations += 1
        
        if total_operations > 0:
            doc_score = (documented_operations / total_operations) * 0.25
        else:
            doc_score = 0.0
        
        score += doc_score
        details["documentation"] = {
            "total_operations": total_operations,
            "documented_operations": documented_operations,
            "score": doc_score
        }
        
        if documented_operations == total_operations and total_operations > 0:
            feedback_parts.append("✓ All operations documented")
        elif total_operations > 0:
            feedback_parts.append(f"✗ {total_operations - documented_operations} operations lack documentation")
        
        # Check error responses (25 points)
        operations_with_errors = 0
        
        for path_name, path_item in paths.items():
            if not isinstance(path_item, dict):
                continue
            
            for method in ["get", "post", "put", "patch", "delete"]:
                if method in path_item:
                    operation = path_item[method]
                    
                    if isinstance(operation, dict):
                        responses = operation.get("responses", {})
                        error_responses = [code for code in responses.keys() if code.startswith(('4', '5'))]
                        
                        if error_responses:
                            operations_with_errors += 1
        
        if total_operations > 0:
            error_score = (operations_with_errors / total_operations) * 0.25
        else:
            error_score = 0.0
        
        score += error_score
        details["error_responses"] = {
            "operations_with_errors": operations_with_errors,
            "total_operations": total_operations,
            "score": error_score
        }
        
        if operations_with_errors == total_operations and total_operations > 0:
            feedback_parts.append("✓ All operations define error responses")
        elif total_operations > 0:
            feedback_parts.append(f"✗ {total_operations - operations_with_errors} operations missing error responses")
        
        # Check API versioning (20 points)
        info = schema_dict.get("info", {})
        version = info.get("version")
        paths_str = str(paths.keys())
        
        has_version_info = bool(version)
        has_version_path = "/v" in paths_str or "/api/v" in paths_str
        has_versioning = has_version_info or has_version_path
        
        version_score = 0.2 if has_versioning else 0.0
        score += version_score
        
        details["versioning"] = {
            "has_version_info": has_version_info,
            "has_version_path": has_version_path,
            "score": version_score
        }
        
        if has_versioning:
            feedback_parts.append("✓ API versioning implemented")
        else:
            feedback_parts.append("✗ No API versioning strategy")
        
        # Check schemas and components (15 points)
        components = schema_dict.get("components", {})
        schemas = components.get("schemas", {})
        
        schema_score = min(len(schemas) / 3, 1.0) * 0.15  # Full points for 3+ schemas
        score += schema_score
        
        details["schemas"] = {
            "count": len(schemas),
            "score": schema_score
        }
        
        if len(schemas) >= 3:
            feedback_parts.append(f"✓ Good schema definitions ({len(schemas)} schemas)")
        else:
            feedback_parts.append(f"✗ Need more schema definitions (found {len(schemas)}, recommended 3+)")
        
        # Check naming conventions (15 points)
        naming_score = 0.0
        path_naming_good = True
        
        for path_name in paths.keys():
            # Check if path uses lowercase and proper separators
            if path_name != path_name.lower() or " " in path_name:
                path_naming_good = False
                break
        
        if path_naming_good and paths:
            naming_score = 0.15
            feedback_parts.append("✓ Good naming conventions")
        elif paths:
            feedback_parts.append("✗ Naming convention issues")
        
        score += naming_score
        details["naming"] = {
            "path_naming_good": path_naming_good,
            "score": naming_score
        }
        
        # Determine pass/fail (threshold: 0.8)
        passed = score >= 0.8
        feedback = f"Advanced Best Practices: {score:.1%} | " + " | ".join(feedback_parts)
        
        return TaskGrade(
            task_name=self.task_name,
            score=score,
            max_score=1.0,
            passed=passed,
            feedback=feedback,
            details=details
        )


class TaskGradingSystem:
    """
    Main grading system that evaluates schemas across all tasks.
    
    Provides aggregate scoring and detailed feedback for hackathon evaluation.
    """
    
    def __init__(self):
        self.graders = [
            BasicAPIStructureGrader(),
            SecurityAuthenticationGrader(),
            AdvancedBestPracticesGrader()
        ]
    
    def grade_all_tasks(self, schema_json: str, validation_result: ValidationResult) -> Dict[str, Any]:
        """
        Grade the schema across all tasks.
        
        Args:
            schema_json: JSON-stringified OpenAPI schema
            validation_result: ValidationResult from the validation pipeline
            
        Returns:
            Dictionary with individual task grades and aggregate metrics
        """
        task_grades = []
        total_score = 0.0
        tasks_passed = 0
        
        for grader in self.graders:
            grade = grader.grade(schema_json, validation_result)
            task_grades.append(grade)
            total_score += grade.score
            if grade.passed:
                tasks_passed += 1
        
        # Calculate aggregate metrics
        average_score = total_score / len(self.graders)
        all_tasks_passed = tasks_passed == len(self.graders)
        
        return {
            "task_grades": [
                {
                    "task_name": grade.task_name,
                    "difficulty": self.graders[i].difficulty,
                    "score": grade.score,
                    "passed": grade.passed,
                    "feedback": grade.feedback,
                    "details": grade.details
                }
                for i, grade in enumerate(task_grades)
            ],
            "aggregate": {
                "total_tasks": len(self.graders),
                "tasks_passed": tasks_passed,
                "all_tasks_passed": all_tasks_passed,
                "average_score": average_score,
                "total_score": total_score,
                "max_total_score": len(self.graders),
                "success_rate": tasks_passed / len(self.graders)
            },
            "summary": f"Passed {tasks_passed}/{len(self.graders)} tasks (avg score: {average_score:.1%})"
        }
    
    def get_task_descriptions(self) -> List[Dict[str, str]]:
        """Get descriptions of all available tasks."""
        return [
            {
                "task_name": grader.task_name,
                "difficulty": grader.difficulty,
                "description": grader.__doc__.strip().split('\n')[0] if grader.__doc__ else ""
            }
            for grader in self.graders
        ]