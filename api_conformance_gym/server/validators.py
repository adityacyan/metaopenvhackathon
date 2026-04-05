# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""
Validation pipeline for OpenAPI schemas.

This module implements a multi-stage validation pipeline that checks:
1. JSON syntax and structure
2. OpenAPI 3.0/3.1 specification compliance
3. Authentication and security configuration
4. API design best practices
"""

import json
import re
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
import time

try:
    from ..models import ValidationError, ValidationResult
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
        from models import ValidationError, ValidationResult
    except ImportError:
        # Last resort - try direct import
        from api_conformance_gym.models import ValidationError, ValidationResult


class JSONParser:
    """Validates JSON structure and syntax."""

    MAX_SCHEMA_SIZE = 100 * 1024  # 100KB

    @staticmethod
    def parse(schema_json: str) -> Union[Dict[str, Any], ValidationError]:
        """Parse and validate JSON structure.

        Args:
            schema_json: JSON string to parse

        Returns:
            Parsed dictionary on success, ValidationError on failure
        """
        # Check for empty string
        if not schema_json or not isinstance(schema_json, str):
            return ValidationError(
                error_type="empty_schema",
                severity="critical",
                path="",
                message="Schema cannot be empty",
                suggestion="Provide a valid OpenAPI schema JSON string",
            )

        # Check size limit
        if len(schema_json.encode("utf-8")) > JSONParser.MAX_SCHEMA_SIZE:
            return ValidationError(
                error_type="schema_too_large",
                severity="critical",
                path="",
                message=f"Schema exceeds maximum size of {JSONParser.MAX_SCHEMA_SIZE} bytes",
                suggestion="Reduce schema size or split into multiple files",
            )

        # Try to parse JSON
        try:
            parsed = json.loads(schema_json)
            return parsed
        except json.JSONDecodeError as e:
            # Extract line and column information
            msg = str(e)
            line_col = ""
            if hasattr(e, "lineno") and hasattr(e, "colno"):
                line_col = f" at line {e.lineno}, column {e.colno}"

            return ValidationError(
                error_type="invalid_json",
                severity="critical",
                path="",
                message=f"Invalid JSON syntax{line_col}: {msg}",
                suggestion="Check JSON syntax and ensure all quotes and brackets are properly closed",
            )


class OpenAPIValidator:
    """Validates OpenAPI 3.0/3.1 specification compliance."""

    REQUIRED_FIELDS = {"openapi", "info", "paths"}
    VALID_HTTP_METHODS = {
        "get",
        "post",
        "put",
        "patch",
        "delete",
        "head",
        "options",
        "trace",
    }

    @staticmethod
    def validate(schema_dict: Dict[str, Any]) -> List[ValidationError]:
        """Validate OpenAPI specification compliance.

        Args:
            schema_dict: Parsed OpenAPI schema dictionary

        Returns:
            List of ValidationError objects (empty if valid)
        """
        errors = []

        # Check required fields
        for field in OpenAPIValidator.REQUIRED_FIELDS:
            if field not in schema_dict:
                errors.append(
                    ValidationError(
                        error_type="missing_required_field",
                        severity="critical",
                        path=field,
                        message=f"Missing required field: {field}",
                        suggestion=f"Add '{field}' field to the root of the schema",
                    )
                )

        # Check openapi version format
        if "openapi" in schema_dict:
            openapi_version = schema_dict["openapi"]
            if not isinstance(openapi_version, str) or not re.match(
                r"^3\.[0-1]\.\d+$", openapi_version
            ):
                errors.append(
                    ValidationError(
                        error_type="invalid_field_value",
                        severity="critical",
                        path="openapi",
                        message=f"Invalid OpenAPI version: {openapi_version}",
                        suggestion="Use OpenAPI 3.0.x or 3.1.x format (e.g., '3.0.0' or '3.1.0')",
                    )
                )

        # Check paths
        if "paths" in schema_dict:
            paths = schema_dict["paths"]
            if not isinstance(paths, dict):
                errors.append(
                    ValidationError(
                        error_type="invalid_field_value",
                        severity="critical",
                        path="paths",
                        message="'paths' must be an object",
                        suggestion="Define paths as an object with path keys",
                    )
                )
            else:
                if len(paths) == 0:
                    errors.append(
                        ValidationError(
                            error_type="empty_paths",
                            severity="critical",
                            path="paths",
                            message="Schema has no API endpoints in 'paths'",
                            suggestion="Add endpoints under 'paths' with at least one operation",
                        )
                    )
                elif len(paths) < 2:
                    errors.append(
                        ValidationError(
                            error_type="insufficient_paths",
                            severity="warning",
                            path="paths",
                            message=f"Only {len(paths)} endpoint defined; expected 2+ for meaningful API design",
                            suggestion="Add more endpoints that reflect the business requirement",
                        )
                    )

                total_operations = 0
                for path_name, path_item in paths.items():
                    if not isinstance(path_item, dict):
                        continue

                    # Check for operations
                    operations = {
                        k: v
                        for k, v in path_item.items()
                        if k in OpenAPIValidator.VALID_HTTP_METHODS
                    }
                    total_operations += len(operations)

                    if not operations:
                        errors.append(
                            ValidationError(
                                error_type="empty_path",
                                severity="warning",
                                path=f"paths.{path_name}",
                                message=f"Path '{path_name}' has no operations defined",
                                suggestion=f"Add at least one HTTP method (get, post, put, patch, delete) to '{path_name}'",
                            )
                        )

                    # Check for invalid HTTP methods
                    for method in path_item.keys():
                        if (
                            method not in OpenAPIValidator.VALID_HTTP_METHODS
                            and not method.startswith("x-")
                        ):
                            errors.append(
                                ValidationError(
                                    error_type="invalid_http_method",
                                    severity="warning",
                                    path=f"paths.{path_name}.{method}",
                                    message=f"Invalid HTTP method: {method}",
                                    suggestion=f"Use valid HTTP methods: {', '.join(OpenAPIValidator.VALID_HTTP_METHODS)}",
                                )
                            )

                if total_operations == 0:
                    errors.append(
                        ValidationError(
                            error_type="no_operations",
                            severity="critical",
                            path="paths",
                            message="No HTTP operations defined across all paths",
                            suggestion="Define operations like GET/POST/PUT/DELETE under each path",
                        )
                    )

        return errors


class AuthValidator:
    """Validates authentication and security configuration."""

    VALID_SECURITY_SCHEMES = {"apiKey", "http", "oauth2", "openIdConnect"}

    @staticmethod
    def validate(schema_dict: Dict[str, Any]) -> List[ValidationError]:
        """Validate authentication and security schemes.

        Args:
            schema_dict: Parsed OpenAPI schema dictionary

        Returns:
            List of ValidationError objects (empty if valid)
        """
        errors = []

        # Check for securitySchemes
        components = schema_dict.get("components", {})
        security_schemes = components.get("securitySchemes", {})

        if not security_schemes:
            errors.append(
                ValidationError(
                    error_type="missing_auth_schemes",
                    severity="critical",
                    path="components.securitySchemes",
                    message="No security schemes defined",
                    suggestion="Define at least one security scheme (apiKey, http, oauth2, or openIdConnect) in components.securitySchemes",
                )
            )
            return errors

        # Validate security scheme types
        for scheme_name, scheme_def in security_schemes.items():
            if not isinstance(scheme_def, dict):
                continue

            scheme_type = scheme_def.get("type")
            if scheme_type not in AuthValidator.VALID_SECURITY_SCHEMES:
                errors.append(
                    ValidationError(
                        error_type="invalid_security_scheme",
                        severity="critical",
                        path=f"components.securitySchemes.{scheme_name}",
                        message=f"Invalid security scheme type: {scheme_type}",
                        suggestion=f"Use valid types: {', '.join(AuthValidator.VALID_SECURITY_SCHEMES)}",
                    )
                )

        # Check if endpoints are protected
        paths = schema_dict.get("paths", {})
        global_security = schema_dict.get("security", [])

        for path_name, path_item in paths.items():
            if not isinstance(path_item, dict):
                continue

            for method in ["get", "post", "put", "patch", "delete", "head", "options"]:
                if method not in path_item:
                    continue

                operation = path_item[method]
                if not isinstance(operation, dict):
                    continue

                # Check if operation has security or if global security is defined
                operation_security = operation.get("security")
                has_security = operation_security is not None or global_security

                if not has_security:
                    errors.append(
                        ValidationError(
                            error_type="unprotected_endpoint",
                            severity="critical",
                            path=f"paths.{path_name}.{method}",
                            message=f"Endpoint {method.upper()} {path_name} is not protected",
                            suggestion=f"Add security requirement to this operation or define global security",
                        )
                    )

        return errors


class BestPracticesChecker:
    """Validates API design best practices."""

    @staticmethod
    def validate(schema_dict: Dict[str, Any]) -> List[ValidationError]:
        """Check API design best practices.

        Args:
            schema_dict: Parsed OpenAPI schema dictionary

        Returns:
            List of ValidationError objects (empty if valid)
        """
        errors = []

        # Check HTTP method correctness
        paths = schema_dict.get("paths", {})
        for path_name, path_item in paths.items():
            if not isinstance(path_item, dict):
                continue

            for method, operation in path_item.items():
                if method not in ["get", "post", "put", "patch", "delete"]:
                    continue
                if not isinstance(operation, dict):
                    continue

                operation_id = operation.get("operationId", "").lower()
                summary = operation.get("summary", "").lower()
                description = operation.get("description", "").lower()

                # Check for incorrect HTTP method usage
                if method == "get" and any(
                    word in operation_id + summary + description
                    for word in ["create", "add", "new", "post"]
                ):
                    errors.append(
                        ValidationError(
                            error_type="incorrect_http_method",
                            severity="warning",
                            path=f"paths.{path_name}.{method}",
                            message=f"GET operation appears to be creating/modifying data",
                            suggestion="Use POST for creation, PUT/PATCH for updates, DELETE for deletion",
                        )
                    )

                if method in ["post", "put", "patch"] and any(
                    word in operation_id + summary + description
                    for word in ["list", "get", "retrieve", "fetch"]
                ):
                    errors.append(
                        ValidationError(
                            error_type="incorrect_http_method",
                            severity="warning",
                            path=f"paths.{path_name}.{method}",
                            message=f"{method.upper()} operation appears to be retrieving data",
                            suggestion="Use GET for retrieval operations",
                        )
                    )

                # Check for documentation
                if not operation.get("summary") and not operation.get("description"):
                    errors.append(
                        ValidationError(
                            error_type="incomplete_documentation",
                            severity="info",
                            path=f"paths.{path_name}.{method}",
                            message=f"Operation {method.upper()} {path_name} lacks description",
                            suggestion="Add 'summary' and/or 'description' field to document the operation",
                        )
                    )

                # Check parameters documentation
                parameters = operation.get("parameters", [])
                for param in parameters:
                    if isinstance(param, dict) and not param.get("description"):
                        errors.append(
                            ValidationError(
                                error_type="incomplete_documentation",
                                severity="info",
                                path=f"paths.{path_name}.{method}.parameters",
                                message=f"Parameter '{param.get('name')}' lacks description",
                                suggestion="Add 'description' field to all parameters",
                            )
                        )

        # Check naming conventions
        for path_name in paths.keys():
            # Paths should use lowercase with hyphens
            if path_name != path_name.lower():
                errors.append(
                    ValidationError(
                        error_type="naming_convention_violation",
                        severity="info",
                        path=f"paths.{path_name}",
                        message=f"Path '{path_name}' uses uppercase letters",
                        suggestion="Use lowercase letters and hyphens for path names (e.g., '/api/v1/user-profiles')",
                    )
                )

        # Check for API versioning
        info = schema_dict.get("info", {})
        version = info.get("version")
        paths_str = str(paths.keys())

        has_versioning = version or "/v" in paths_str or "/api/v" in paths_str
        if not has_versioning:
            errors.append(
                ValidationError(
                    error_type="missing_versioning",
                    severity="info",
                    path="info.version or paths",
                    message="API lacks version information",
                    suggestion="Add 'version' field to info section or include version in path (e.g., '/api/v1')",
                )
            )

        return errors


class ValidationPipeline:
    """Orchestrates multi-stage validation pipeline."""

    @staticmethod
    def validate(schema_json: str) -> ValidationResult:
        """Execute complete validation pipeline.

        Args:
            schema_json: JSON-stringified OpenAPI schema

        Returns:
            ValidationResult with aggregated errors and scores
        """
        timestamp = time.time()
        all_errors = []
        validation_stages = {}

        # Stage 1: JSON Parser
        parse_result = JSONParser.parse(schema_json)
        if isinstance(parse_result, ValidationError):
            all_errors.append(parse_result)
            validation_stages["json_parser"] = {
                "passed": False,
                "errors": [parse_result],
            }
            return ValidationResult(
                is_valid=False,
                errors=all_errors,
                validity_score=0.0,
                best_practices_score=0.0,
                validation_stages=validation_stages,
                timestamp=timestamp,
            )

        schema_dict = parse_result
        validation_stages["json_parser"] = {"passed": True, "errors": []}

        # Stage 2: OpenAPI Validator
        openapi_errors = OpenAPIValidator.validate(schema_dict)
        all_errors.extend(openapi_errors)
        validation_stages["openapi_validator"] = {
            "passed": len(openapi_errors) == 0,
            "errors": openapi_errors,
        }

        # Stage 3: Auth Validator
        auth_errors = AuthValidator.validate(schema_dict)
        all_errors.extend(auth_errors)
        validation_stages["auth_validator"] = {
            "passed": len(auth_errors) == 0,
            "errors": auth_errors,
        }

        # Stage 4: Best Practices Checker
        bp_errors = BestPracticesChecker.validate(schema_dict)
        all_errors.extend(bp_errors)
        validation_stages["best_practices_checker"] = {
            "passed": len(bp_errors) == 0,
            "errors": bp_errors,
        }

        # Calculate scores with a dense signal instead of binary pass/fail.
        critical_count = len([e for e in all_errors if e.severity == "critical"])
        warning_count = len([e for e in all_errors if e.severity == "warning"])
        info_count = len([e for e in all_errors if e.severity == "info"])

        # Validity emphasizes critical errors but still decays gradually.
        validity_score = max(
            0.0, 1.0 - (critical_count * 0.25) - (warning_count * 0.05)
        )

        # Best practices reflects non-critical quality issues and documentation gaps.
        best_practices_score = max(
            0.0, 1.0 - (warning_count * 0.08) - (info_count * 0.04)
        )

        return ValidationResult(
            is_valid=len(all_errors) == 0,
            errors=all_errors,
            validity_score=validity_score,
            best_practices_score=best_practices_score,
            validation_stages=validation_stages,
            timestamp=timestamp,
        )
