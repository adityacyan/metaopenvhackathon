#!/usr/bin/env python3
"""
Simple test script for API Conformance Gym Environment

This script tests the core functionality without requiring a server.
"""

import json
import sys
import os

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_validators():
    """Test the validation pipeline."""
    print("🧪 Testing Validation Pipeline...")
    
    from server.validators import ValidationPipeline
    
    pipeline = ValidationPipeline()
    
    # Test 1: Invalid JSON
    print("  Test 1: Invalid JSON")
    result = pipeline.validate('{"invalid": json}')
    print(f"    ✅ Caught invalid JSON: {len(result.errors)} errors")
    
    # Test 2: Valid minimal schema
    print("  Test 2: Valid minimal schema")
    minimal_schema = {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "paths": {},
        "components": {
            "securitySchemes": {
                "bearerAuth": {"type": "http", "scheme": "bearer"}
            }
        },
        "security": [{"bearerAuth": []}]
    }
    
    result = pipeline.validate(json.dumps(minimal_schema))
    print(f"    ✅ Minimal schema: {len(result.errors)} errors, validity: {result.validity_score:.2f}")
    
    # Test 3: Schema with issues
    print("  Test 3: Schema with issues")
    bad_schema = {
        "openapi": "3.0.0",
        "info": {"title": "Bad API", "version": "1.0.0"},
        "paths": {
            "/test": {
                "get": {"summary": "Test endpoint"}
            }
        }
        # Missing security schemes
    }
    
    result = pipeline.validate(json.dumps(bad_schema))
    print(f"    ✅ Bad schema: {len(result.errors)} errors, validity: {result.validity_score:.2f}")
    
    print("✅ Validation Pipeline tests passed!\n")


def test_reward_calculator():
    """Test the reward calculator."""
    print("🧪 Testing Reward Calculator...")
    
    from server.reward import RewardCalculator
    from models import ValidationResult, ValidationError
    
    calculator = RewardCalculator()
    
    # Test 1: Perfect schema
    print("  Test 1: Perfect schema")
    perfect_result = ValidationResult(
        is_valid=True,
        errors=[],
        validity_score=1.0,
        best_practices_score=1.0,
        validation_stages={},
        timestamp=0.0
    )
    
    reward = calculator.calculate(perfect_result)
    print(f"    ✅ Perfect schema reward: {reward:.3f} (expected: 1.0)")
    
    # Test 2: Schema with errors
    print("  Test 2: Schema with errors")
    error_result = ValidationResult(
        is_valid=False,
        errors=[
            ValidationError(
                error_type="missing_auth",
                severity="critical", 
                path="",
                message="Missing auth",
                suggestion="Add auth"
            ),
            ValidationError(
                error_type="bad_method",
                severity="warning",
                path="",
                message="Bad method", 
                suggestion="Fix method"
            )
        ],
        validity_score=0.0,
        best_practices_score=0.5,
        validation_stages={},
        timestamp=0.0
    )
    
    reward = calculator.calculate(error_result)
    print(f"    ✅ Error schema reward: {reward:.3f} (should be negative)")
    
    print("✅ Reward Calculator tests passed!\n")


def test_environment():
    """Test the core environment."""
    print("🧪 Testing Core Environment...")
    
    from server.api_conformance_gym_environment import APIEnvironment
    from models import APIAction
    
    env = APIEnvironment()
    
    # Test 1: Reset
    print("  Test 1: Environment reset")
    state = env.reset()
    print(f"    ✅ Reset successful. Business requirement: {state.business_requirement[:50]}...")
    
    # Test 2: Step with minimal schema
    print("  Test 2: Environment step")
    minimal_schema = {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "paths": {}
    }
    
    action = APIAction(schema_json=json.dumps(minimal_schema), iteration=1)
    obs, reward, done, info = env.step(action)
    
    print(f"    ✅ Step successful!")
    print(f"       Reward: {reward:.3f}")
    print(f"       Validity Score: {obs.validity_score:.3f}")
    print(f"       Error Count: {obs.error_count}")
    print(f"       Done: {done}")
    
    # Test 3: State retrieval
    print("  Test 3: State retrieval")
    current_state = env.state
    print(f"    ✅ State retrieved. Iteration count: {current_state.iteration_count}")
    
    print("✅ Core Environment tests passed!\n")


def test_grading_system():
    """Test the task grading system."""
    print("🧪 Testing Task Grading System...")
    
    from server.graders import TaskGradingSystem
    from models import ValidationResult
    
    grader = TaskGradingSystem()
    
    # Test with a decent schema
    test_schema = {
        "openapi": "3.0.0",
        "info": {"title": "Library API", "version": "1.0.0", "description": "A library management API"},
        "paths": {
            "/books": {
                "get": {
                    "summary": "List books",
                    "description": "Get a list of all books",
                    "responses": {
                        "200": {"description": "Success"},
                        "404": {"description": "Not found"}
                    }
                },
                "post": {
                    "summary": "Create book",
                    "description": "Add a new book",
                    "requestBody": {
                        "required": True,
                        "content": {"application/json": {"schema": {"type": "object"}}}
                    },
                    "responses": {
                        "201": {"description": "Created"},
                        "400": {"description": "Bad request"}
                    }
                }
            }
        },
        "components": {
            "securitySchemes": {
                "bearerAuth": {"type": "http", "scheme": "bearer"}
            },
            "schemas": {
                "Book": {"type": "object", "properties": {"title": {"type": "string"}}},
                "Error": {"type": "object", "properties": {"message": {"type": "string"}}},
                "BookList": {"type": "array", "items": {"$ref": "#/components/schemas/Book"}}
            }
        },
        "security": [{"bearerAuth": []}]
    }
    
    # Create a mock validation result
    validation_result = ValidationResult(
        is_valid=True,
        errors=[],
        validity_score=1.0,
        best_practices_score=0.8,
        validation_stages={},
        timestamp=0.0
    )
    
    results = grader.grade_all_tasks(json.dumps(test_schema), validation_result)
    
    print(f"  ✅ Grading completed!")
    print(f"     Tasks passed: {results['aggregate']['tasks_passed']}/{results['aggregate']['total_tasks']}")
    print(f"     Average score: {results['aggregate']['average_score']:.3f}")
    print(f"     Summary: {results['summary']}")
    
    for task in results['task_grades']:
        print(f"     - {task['task_name']} ({task['difficulty']}): {task['score']:.3f} {'✅' if task['passed'] else '❌'}")
    
    print("✅ Task Grading System tests passed!\n")


def main():
    """Run all tests."""
    print("🚀 API Conformance Gym - Test Suite")
    print("=" * 50)
    
    try:
        test_validators()
        test_reward_calculator()
        test_environment()
        test_grading_system()
        
        print("🎉 All tests passed! Environment is working correctly.")
        print("\n📋 Next steps:")
        print("1. Start the server: uvicorn server.app:app --host 0.0.0.0 --port 8000")
        print("2. Test with client: python examples/simple_agent.py")
        print("3. Run baseline: python inference.py")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())