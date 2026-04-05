#!/usr/bin/env python3
"""
Quick test to verify all imports work correctly.
"""

import os
import sys

# Add current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

def test_imports():
    """Test all critical imports."""
    print("Testing imports...")
    
    try:
        print("  Testing models...")
        from models import APIAction, APIObservation, APIState, ValidationResult, ValidationError
        print("    ✓ Models imported successfully")
    except Exception as e:
        print(f"    ✗ Models import failed: {e}")
        return False
    
    try:
        print("  Testing server components...")
        from server.validators import ValidationPipeline
        from server.reward import RewardCalculator
        from server.api_conformance_gym_environment import APIEnvironment
        print("    ✓ Server components imported successfully")
    except Exception as e:
        print(f"    ✗ Server components import failed: {e}")
        return False
    
    try:
        print("  Testing client...")
        from client import APIEnvClient
        print("    ✓ Client imported successfully")
    except Exception as e:
        print(f"    ✗ Client import failed: {e}")
        return False
    
    try:
        print("  Testing server app...")
        from server.app import app
        print("    ✓ Server app imported successfully")
    except Exception as e:
        print(f"    ✗ Server app import failed: {e}")
        return False
    
    return True

def test_basic_functionality():
    """Test basic environment functionality."""
    print("\nTesting basic functionality...")
    
    try:
        from server.api_conformance_gym_environment import APIEnvironment
        from models import APIAction
        import json
        
        # Create environment
        env = APIEnvironment()
        print("  ✓ Environment created")
        
        # Reset environment
        state = env.reset()
        print("  ✓ Environment reset successful")
        print(f"    Business requirement: {state.business_requirement[:50]}...")
        
        # Test step
        minimal_schema = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "1.0.0"},
            "paths": {}
        }
        
        action = APIAction(schema_json=json.dumps(minimal_schema), iteration=1)
        obs, reward, done, info = env.step(action)
        
        print("  ✓ Environment step successful")
        print(f"    Reward: {reward:.3f}")
        print(f"    Errors: {obs.error_count}")
        
        return True
        
    except Exception as e:
        print(f"  ✗ Basic functionality test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    print("API Conformance Gym - Quick Test")
    print("=" * 40)
    
    # Test imports
    if not test_imports():
        print("\n❌ Import tests failed!")
        return 1
    
    # Test functionality
    if not test_basic_functionality():
        print("\n❌ Functionality tests failed!")
        return 1
    
    print("\n✅ All tests passed!")
    print("\nNext steps:")
    print("1. Start server: python start_server.py")
    print("2. Test client: python test_inference_local.py")
    print("3. Run with LLM: python inference.py")
    
    return 0

if __name__ == "__main__":
    exit(main())