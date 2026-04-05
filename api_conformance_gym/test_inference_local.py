#!/usr/bin/env python3
"""
Local inference test for API Conformance Gym Environment

This script tests the environment without requiring external API keys.
It uses a simple rule-based agent to demonstrate the environment functionality.
"""

import asyncio
import json
import sys
import os

# Add current directory to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from client import APIEnvClient
from models import APIAction

# Simple rule-based agent templates
SIMPLE_TEMPLATES = [
    # Template 1: Basic API with auth
    {
        "openapi": "3.0.0",
        "info": {"title": "Basic API", "version": "1.0.0"},
        "paths": {
            "/items": {
                "get": {"summary": "List items", "responses": {"200": {"description": "Success"}}},
                "post": {"summary": "Create item", "responses": {"201": {"description": "Created"}}}
            }
        },
        "components": {
            "securitySchemes": {"bearerAuth": {"type": "http", "scheme": "bearer"}}
        },
        "security": [{"bearerAuth": []}]
    },
    
    # Template 2: More complete API
    {
        "openapi": "3.0.0",
        "info": {
            "title": "Library Management API",
            "version": "1.0.0",
            "description": "A comprehensive library management system"
        },
        "paths": {
            "/books": {
                "get": {
                    "summary": "List all books",
                    "description": "Retrieve a paginated list of books",
                    "responses": {
                        "200": {"description": "Successful response"},
                        "401": {"description": "Unauthorized"}
                    }
                },
                "post": {
                    "summary": "Add a new book",
                    "description": "Create a new book entry",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Book"}
                            }
                        }
                    },
                    "responses": {
                        "201": {"description": "Book created"},
                        "400": {"description": "Invalid input"},
                        "401": {"description": "Unauthorized"}
                    }
                }
            },
            "/users": {
                "post": {
                    "summary": "Register user",
                    "description": "Register a new library user",
                    "responses": {
                        "201": {"description": "User registered"},
                        "400": {"description": "Invalid input"}
                    }
                }
            }
        },
        "components": {
            "securitySchemes": {
                "bearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}
            },
            "schemas": {
                "Book": {
                    "type": "object",
                    "required": ["title", "author"],
                    "properties": {
                        "id": {"type": "integer"},
                        "title": {"type": "string"},
                        "author": {"type": "string"},
                        "isbn": {"type": "string"},
                        "available": {"type": "boolean", "default": True}
                    }
                }
            }
        },
        "security": [{"bearerAuth": []}]
    }
]


def simple_agent_response(business_requirement: str, step: int, feedback: str) -> str:
    """Simple rule-based agent that improves based on feedback."""
    
    # Start with basic template
    if step == 1:
        return json.dumps(SIMPLE_TEMPLATES[0])
    
    # If feedback mentions missing endpoints or incomplete, use more complete template
    if any(word in feedback.lower() for word in ["missing", "incomplete", "add", "endpoint"]):
        return json.dumps(SIMPLE_TEMPLATES[1])
    
    # If feedback mentions security issues, ensure auth is present
    if any(word in feedback.lower() for word in ["security", "auth", "unauthorized"]):
        schema = SIMPLE_TEMPLATES[1].copy()
        # Ensure security is properly configured
        if "security" not in schema:
            schema["security"] = [{"bearerAuth": []}]
        return json.dumps(schema)
    
    # Default: return the more complete template
    return json.dumps(SIMPLE_TEMPLATES[1])


async def test_local_inference():
    """Test the environment with a simple local agent."""
    print("API Conformance Gym - Local Inference Test")
    print("=" * 50)
    
    # Connect to local environment (assumes server is running)
    try:
        client = APIEnvClient(base_url="http://localhost:8000")
        print("Connected to local environment server")
    except Exception as e:
        print(f"Failed to connect to environment server: {e}")
        print("Make sure the server is running: uvicorn server.app:app --host 0.0.0.0 --port 8000")
        return False
    
    try:
        # Reset environment
        print("\nResetting environment...")
        result = await client.reset()
        # reset() returns StepResult with observation
        observation = result.observation
        business_requirement = observation.episode_info["business_requirement"]
        
        print(f"Business Requirement: {business_requirement[:100]}...")
        
        rewards = []
        last_feedback = "Starting new task"
        
        # Run for a few steps
        for step in range(1, 4):
            print(f"\nStep {step}:")
            
            # Get agent response
            schema_json = simple_agent_response(business_requirement, step, last_feedback)
            
            print(f"  Agent submitting schema (length: {len(schema_json)} chars)")
            
            # Create action and step
            action = APIAction(schema_json=schema_json, iteration=step)
            result = await client.step(action)
            
            observation = result.observation
            reward = result.reward or 0.0
            done = result.done
            
            rewards.append(reward)
            
            print(f"  Reward: {reward:.3f}")
            print(f"  Validity Score: {observation.validity_score:.3f}")
            print(f"  Best Practices Score: {observation.best_practices_score:.3f}")
            print(f"  Error Count: {observation.error_count}")
            print(f"  Feedback: {observation.schema_feedback[:100]}...")
            print(f"  Done: {done}")
            
            if done:
                print("  Episode completed!")
                break
            
            # Update feedback for next iteration
            last_feedback = observation.schema_feedback
        
        # Summary
        total_reward = sum(rewards)
        avg_reward = total_reward / len(rewards) if rewards else 0.0
        
        print(f"\nSummary:")
        print(f"  Steps taken: {len(rewards)}")
        print(f"  Total reward: {total_reward:.3f}")
        print(f"  Average reward: {avg_reward:.3f}")
        print(f"  Final validity: {observation.validity_score:.3f}")
        print(f"  Final best practices: {observation.best_practices_score:.3f}")
        
        return True
        
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        try:
            await client.close()
        except:
            pass


def main():
    """Main function."""
    print("Starting local inference test...")
    print("This test uses a simple rule-based agent (no API key required)")
    print()
    
    success = asyncio.run(test_local_inference())
    
    if success:
        print("\nLocal inference test completed successfully!")
        print("\nNext steps:")
        print("1. Set up API keys in .env file to test with real LLMs")
        print("2. Try: python inference.py")
        print("3. Test LLM grading: python test_llm_grading.py")
    else:
        print("\nLocal inference test failed!")
        print("Make sure the environment server is running:")
        print("  uvicorn server.app:app --host 0.0.0.0 --port 8000")
    
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())