# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""
FastAPI application for the API Conformance Gym Environment.

This module creates an HTTP server that exposes the APIEnvironment
over HTTP and WebSocket endpoints, compatible with EnvClient.

The API Conformance Gym trains RL agents to design robust, secure, and compliant
REST API schemas through iterative feedback from a multi-stage validation pipeline.

Endpoints:
    - POST /reset: Reset the environment with new business requirement
    - POST /step: Execute an action (submit OpenAPI schema)
    - GET /state: Get current environment state with history
    - GET /schema: Get action/observation schemas
    - WS /ws: WebSocket endpoint for persistent sessions

Usage:
    # Development (with auto-reload):
    uvicorn server.app:app --reload --host 0.0.0.0 --port 8000

    # Production:
    uvicorn server.app:app --host 0.0.0.0 --port 8000 --workers 4

    # Or run directly:
    python -m server.app
"""
import sys
import os
import uvicorn
import argparse

try:
    from openenv.core.env_server.http_server import create_app
except Exception as e:
    raise ImportError("uv sync") from e

d = os.path.dirname(os.path.abspath(__file__))
p = os.path.dirname(d)
if p not in sys.path:
    sys.path.insert(0, p)

try:
    from models import APIAction, APIObservation
    from server.api_conformance_gym_environment import APIEnvironment
except ImportError:
    from api_conformance_gym.models import APIAction, APIObservation
    from api_conformance_gym.server.api_conformance_gym_environment import APIEnvironment

app = create_app(
    APIEnvironment,
    APIAction,
    APIObservation,
    env_name="api_conformance_gym",
    max_concurrent_envs=10,
)

def main():
    arg = argparse.ArgumentParser()
    arg.add_argument("--host", default="0.0.0.0")
    arg.add_argument("--port", type=int, default=8000)
    a = arg.parse_args()
    uvicorn.run(app, host=a.host, port=a.port)

if __name__ == "__main__":
    main()