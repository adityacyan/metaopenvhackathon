#!/usr/bin/env python3
"""
Debug script to check what the client actually receives from reset() and step().
"""

import asyncio
import json
import sys
import os

# Add current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from client import APIEnvClient
from models import APIAction

async def debug_client():
    """Debug the client responses."""
    print("Debug: Testing client responses")
    print("=" * 40)
    
    try:
        client = APIEnvClient(base_url="http://localhost:8000")
        print("✓ Connected to server")
        
        # Test reset
        print("\n1. Testing reset()...")
        try:
            reset_result = await client.reset()
            print(f"   Type: {type(reset_result)}")
            print(f"   Attributes: {dir(reset_result)}")
            
            if hasattr(reset_result, 'observation'):
                print(f"   Has observation: {type(reset_result.observation)}")
                print(f"   Observation attributes: {dir(reset_result.observation)}")
                if hasattr(reset_result.observation, 'business_requirement'):
                    print(f"   Business requirement: {reset_result.observation.business_requirement[:50]}...")
            
            if hasattr(reset_result, 'reward'):
                print(f"   Has reward: {reset_result.reward}")
            
            if hasattr(reset_result, 'done'):
                print(f"   Has done: {reset_result.done}")
                
        except Exception as e:
            print(f"   ✗ Reset failed: {e}")
            import traceback
            traceback.print_exc()
            return
        
        # Test step
        print("\n2. Testing step()...")
        try:
            minimal_schema = {
                "openapi": "3.0.0",
                "info": {"title": "Test API", "version": "1.0.0"},
                "paths": {}
            }
            
            action = APIAction(schema_json=json.dumps(minimal_schema), iteration=1)
            step_result = await client.step(action)
            
            print(f"   Type: {type(step_result)}")
            print(f"   Attributes: {dir(step_result)}")
            
            if hasattr(step_result, 'observation'):
                print(f"   Has observation: {type(step_result.observation)}")
                print(f"   Error count: {step_result.observation.error_count}")
            
            if hasattr(step_result, 'reward'):
                print(f"   Has reward: {step_result.reward}")
            
            if hasattr(step_result, 'done'):
                print(f"   Has done: {step_result.done}")
                
        except Exception as e:
            print(f"   ✗ Step failed: {e}")
            import traceback
            traceback.print_exc()
        
        await client.close()
        
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        print("Make sure server is running: python start_server.py")

def main():
    """Main function."""
    asyncio.run(debug_client())

if __name__ == "__main__":
    main()