#!/usr/bin/env python3
"""
Test script for LLM-enhanced reward grading using Ollama.

This script demonstrates how to use the enhanced reward system that combines
rule-based validation with LLM contextual grading for more nuanced evaluation.
"""

import json
import sys
import os

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_llm_grading():
    """Test LLM-enhanced grading system."""
    print("Testing LLM-Enhanced Reward Grading")
    print("=" * 50)
    
    from server.api_conformance_gym_environment import APIEnvironment
    from models import APIAction
    
    # Test with LLM grading enabled
    print("Initializing environment with LLM grading...")
    try:
        env = APIEnvironment(
            use_llm_grading=True,
            model_name="llama3.1",  # Change to your preferred Ollama model
            timeout=15.0
        )
        print("LLM grading enabled successfully")
    except Exception as e:
        print(f"LLM grading failed to initialize: {e}")
        print("Falling back to rule-based grading...")
        env = APIEnvironment(use_llm_grading=False)
    
    # Reset environment
    print("\nResetting environment...")
    state = env.reset(seed=42)  # Use seed for reproducible testing
    print(f"Business Requirement: {state.business_requirement[:100]}...")
    
    # Test 1: Minimal schema (should get low scores)
    print("\nTest 1: Minimal Schema")
    minimal_schema = {
        "openapi": "3.0.0",
        "info": {"title": "Minimal API", "version": "1.0.0"},
        "paths": {}
    }
    
    action1 = APIAction(schema_json=json.dumps(minimal_schema), iteration=1)
    obs1, reward1, done1, info1 = env.step(action1)
    
    print(f"   Reward: {reward1:.3f}")
    print(f"   Validity: {obs1.validity_score:.3f}")
    print(f"   Best Practices: {obs1.best_practices_score:.3f}")
    print(f"   Errors: {obs1.error_count}")
    print(f"   Feedback: {obs1.schema_feedback[:100]}...")
    
    # Test 2: Better schema (should get higher scores)
    print("\nTest 2: Improved Schema")
    improved_schema = {
        "openapi": "3.0.0",
        "info": {
            "title": "Library Management API",
            "version": "1.0.0",
            "description": "A comprehensive library management system API"
        },
        "paths": {
            "/books": {
                "get": {
                    "summary": "List all books",
                    "description": "Retrieve a paginated list of all books in the library",
                    "parameters": [
                        {
                            "name": "page",
                            "in": "query",
                            "description": "Page number for pagination",
                            "schema": {"type": "integer", "minimum": 1}
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/BookList"}
                                }
                            }
                        },
                        "400": {"description": "Bad request"},
                        "401": {"description": "Unauthorized"}
                    }
                },
                "post": {
                    "summary": "Add a new book",
                    "description": "Create a new book entry in the library system",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Book"}
                            }
                        }
                    },
                    "responses": {
                        "201": {"description": "Book created successfully"},
                        "400": {"description": "Invalid input"},
                        "401": {"description": "Unauthorized"}
                    }
                }
            },
            "/users": {
                "post": {
                    "summary": "Register new user",
                    "description": "Register a new library user",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/User"}
                            }
                        }
                    },
                    "responses": {
                        "201": {"description": "User registered successfully"},
                        "400": {"description": "Invalid input"}
                    }
                }
            }
        },
        "components": {
            "securitySchemes": {
                "bearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT"
                }
            },
            "schemas": {
                "Book": {
                    "type": "object",
                    "required": ["title", "author", "isbn"],
                    "properties": {
                        "id": {"type": "integer"},
                        "title": {"type": "string"},
                        "author": {"type": "string"},
                        "isbn": {"type": "string"},
                        "available": {"type": "boolean", "default": True}
                    }
                },
                "BookList": {
                    "type": "object",
                    "properties": {
                        "books": {
                            "type": "array",
                            "items": {"$ref": "#/components/schemas/Book"}
                        },
                        "total": {"type": "integer"},
                        "page": {"type": "integer"}
                    }
                },
                "User": {
                    "type": "object",
                    "required": ["name", "email"],
                    "properties": {
                        "id": {"type": "integer"},
                        "name": {"type": "string"},
                        "email": {"type": "string", "format": "email"},
                        "membershipType": {"type": "string", "enum": ["basic", "premium"]}
                    }
                }
            }
        },
        "security": [{"bearerAuth": []}]
    }
    
    action2 = APIAction(schema_json=json.dumps(improved_schema), iteration=2)
    obs2, reward2, done2, info2 = env.step(action2)
    
    print(f"   Reward: {reward2:.3f}")
    print(f"   Validity: {obs2.validity_score:.3f}")
    print(f"   Best Practices: {obs2.best_practices_score:.3f}")
    print(f"   Errors: {obs2.error_count}")
    print(f"   Feedback: {obs2.schema_feedback[:100]}...")
    
    # Compare improvements
    print(f"\nImprovement Analysis:")
    print(f"   Reward improvement: {reward2 - reward1:+.3f}")
    print(f"   Error reduction: {obs1.error_count - obs2.error_count}")
    
    if reward2 > reward1:
        print("   LLM grading detected improvement!")
    else:
        print("   No improvement detected")
    
    print(f"\nFinal State:")
    print(f"   Episode done: {done2}")
    print(f"   Total iterations: {env.state.iteration_count}")
    print(f"   Total reward: {env.state.total_reward:.3f}")


def test_ollama_connection():
    """Test connection to Ollama API."""
    print("Testing Ollama Connection")
    print("=" * 30)
    
    import requests
    
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get("models", [])
            print(f"Ollama is running with {len(models)} models:")
            for model in models[:3]:  # Show first 3 models
                print(f"   - {model['name']}")
            if len(models) > 3:
                print(f"   ... and {len(models) - 3} more")
            return True
        else:
            print(f"Ollama API returned status {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"Cannot connect to Ollama: {e}")
        print("Make sure Ollama is running: ollama serve")
        return False


def main():
    """Run LLM grading tests."""
    print("API Conformance Gym - LLM Grading Test")
    print("=" * 50)
    
    # Test Ollama connection first
    if not test_ollama_connection():
        print("\nOllama not available - testing will use rule-based fallback")
    
    print()
    
    try:
        test_llm_grading()
        
        print("\nLLM grading test completed!")
        print("\nUsage Tips:")
        print("1. Ensure Ollama is running: ollama serve")
        print("2. Pull a model: ollama pull llama3.1")
        print("3. Adjust model_name in APIEnvironment() constructor")
        print("4. LLM grading provides more contextual feedback than rule-based validation")
        
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())