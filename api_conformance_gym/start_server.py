#!/usr/bin/env python3
"""
Start the API Conformance Gym server.

This script starts the FastAPI server with proper import handling.
"""

import os
import sys
import uvicorn

# Add current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

def main():
    """Start the server."""
    print("Starting API Conformance Gym server...")
    print(f"Working directory: {current_dir}")
    print("Server will be available at: http://localhost:8000")
    print("WebSocket endpoint: ws://localhost:8000/ws")
    print("API docs: http://localhost:8000/docs")
    print()
    
    # Change to the correct directory
    os.chdir(current_dir)
    
    # Start the server
    uvicorn.run(
        "server.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=[current_dir],
        log_level="info"
    )

if __name__ == "__main__":
    main()