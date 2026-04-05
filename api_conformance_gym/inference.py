#!/usr/bin/env python3
"""
Inference Script for API Conformance Gym Environment

This script provides a baseline implementation for the 2026 Meta PyTorch Hackathon.
It uses the OpenAI API client to interact with the API Conformance Gym environment,
demonstrating how to train agents to design robust REST API schemas.

MANDATORY Environment Variables:
- API_BASE_URL: The API endpoint for the LLM (default: active endpoint)
- MODEL_NAME: The model identifier to use for inference (default: active model)
- HF_TOKEN or API_KEY: Your Hugging Face / API key
- IMAGE_NAME: The name of the local image for docker environment

STDOUT FORMAT:
The script emits exactly three line types to stdout:
- [START] task=<task_name> env=<benchmark> model=<model_name>
- [STEP] step=<n> action=<action_str> reward=<0.00> done=<true|false> error=<msg|null>
- [END] success=<true|false> steps=<n> score=<0.000> rewards=<r1,r2,...,rn>

Example Output:
[START] task=api-design env=api_conformance_gym model=Qwen2.5-72B-Instruct
[STEP] step=1 action={"openapi":"3.0.0",...} reward=0.30 done=false error=null
[STEP] step=2 action={"openapi":"3.0.0",...} reward=0.65 done=false error=null
[STEP] step=3 action={"openapi":"3.0.0",...} reward=0.85 done=true error=null
[END] success=true steps=3 score=0.600 rewards=0.30,0.65,0.85
"""

import asyncio
import json
import os
import sys
import textwrap
from datetime import datetime
from typing import List, Optional, Tuple


# Load environment variables from .env file
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    # dotenv not available, skip loading .env file
    pass

from openai import OpenAI

# Add current directory to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

try:
    from api_conformance_gym import APIEnvClient, APIAction
except ImportError:
    try:
        from client import APIEnvClient
        from models import APIAction
    except ImportError:
        # Last resort - try direct imports
        from api_conformance_gym.client import APIEnvClient
        from api_conformance_gym.models import APIAction

# Environment configuration
IMAGE_NAME = os.getenv("IMAGE_NAME")  # Docker image name (optional)
USE_DOCKER = os.getenv("USE_DOCKER", "false").lower() == "true"  # Explicit Docker flag
API_KEY = os.getenv("HF_TOKEN") or os.getenv("API_KEY") or os.getenv("OPENAI_API_KEY")
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
ENV_SERVER_URL = os.getenv(
    "ENV_SERVER_URL", "http://localhost:8000"
)  # Local server URL
LOG_FILE_PATH = os.path.join(current_dir, "log.txt")

# Validate API key
if not API_KEY:
    print(
        "[ERROR] No API key found. Set one of: API_KEY, HF_TOKEN, or OPENAI_API_KEY environment variables",
        flush=True,
    )
    print(
        "[INFO] For testing without LLM, you can run the environment tests instead:",
        flush=True,
    )
    print("       python test_environment.py", flush=True)
    sys.exit(1)

# Task configuration
TASK_NAME = os.getenv("API_CONFORMANCE_GYM_TASK", "api-design")
BENCHMARK = os.getenv("API_CONFORMANCE_GYM_BENCHMARK", "api_conformance_gym")
MAX_STEPS = 10
TEMPERATURE = 0.3
MAX_TOKENS = 10000
SUCCESS_SCORE_THRESHOLD = 0.5  # Normalized score in [0, 1]
BASELINE_EPISODES = 3

# Reward calculation constants
MAX_REWARD_PER_STEP = 1.0  # Maximum possible reward per step

SYSTEM_PROMPT = textwrap.dedent(
    """
You are an expert API architect tasked with designing robust, secure, and compliant REST API schemas.

Your goal is to create valid OpenAPI 3.0/3.1 schemas that meet business requirements while following best practices:
- Include proper authentication/security schemes
- Use correct HTTP methods (GET for retrieval, POST for creation, etc.)
- Provide comprehensive documentation
- Follow RESTful naming conventions
- Include proper error responses
- Add request/response schemas

You will receive:
1. A business requirement describing the API to design
2. Validation feedback from previous attempts (if any)

Respond with ONLY a valid JSON OpenAPI schema - no explanations, no markdown, just the raw JSON.

Example minimal structure:
{
  "openapi": "3.0.0",
  "info": {
    "title": "API Title",
    "version": "1.0.0",
    "description": "API description"
  },
  "servers": [{"url": "https://api.example.com/v1"}],
  "paths": {
    "/endpoint": {
      "get": {
        "summary": "Description",
        "responses": {
          "200": {"description": "Success"},
          "404": {"description": "Not found"}
        }
      }
    }
  },
  "components": {
    "securitySchemes": {
      "bearerAuth": {
        "type": "http",
        "scheme": "bearer"
      }
    }
  },
  "security": [{"bearerAuth": []}]
}
"""
).strip()


def log_start(task: str, env: str, model: str) -> None:
    """Log the start of an episode."""
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(
    step: int, action: str, reward: float, done: bool, error: Optional[str]
) -> None:
    """Log a single step."""
    error_val = error if error else "null"
    done_val = str(done).lower()
    # Truncate action for readability but keep it informative
    action_preview = action[:100] + "..." if len(action) > 100 else action
    print(
        f"[STEP] step={step} action={action_preview} reward={reward:.2f} done={done_val} error={error_val}",
        flush=True,
    )


def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    """Log the end of an episode."""
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(
        f"[END] success={str(success).lower()} steps={steps} score={score:.3f} rewards={rewards_str}",
        flush=True,
    )


def _extract_components(schema_json: str) -> dict:
    """Extract components object from a schema JSON string."""
    try:
        schema_obj = json.loads(schema_json)
    except Exception:
        return {}

    components = schema_obj.get("components", {})
    return components if isinstance(components, dict) else {}


def log_components(
    step: int, schema_json: str, reward: float, done: bool, source: str
) -> None:
    """Append per-step components to log.txt for offline inspection."""
    components = _extract_components(schema_json)
    timestamp = datetime.utcnow().isoformat() + "Z"
    with open(LOG_FILE_PATH, "a", encoding="utf-8") as log_file:
        log_file.write(
            f"\n[{timestamp}] step={step} source={source} reward={reward:.3f} done={str(done).lower()}\n"
        )
        log_file.write(json.dumps(components, indent=2, ensure_ascii=False))
        log_file.write("\n")


def build_user_prompt(
    business_requirement: str,
    step: int,
    last_feedback: str,
    last_reward: float,
    history: List[str],
) -> str:
    """Build the user prompt for the LLM."""
    history_block = "\n".join(history[-3:]) if history else "None"

    return textwrap.dedent(
        f"""
    Business Requirement:
    {business_requirement}
    
    Step: {step}
    Last feedback: {last_feedback}
    Last reward: {last_reward:.2f}
    
    Previous attempts:
    {history_block}
    
    Design a complete OpenAPI 3.0/3.1 schema that addresses the business requirement and fixes any issues from the feedback.
    Respond with ONLY the JSON schema - no explanations.
    """
    ).strip()


def get_model_response(
    client: OpenAI,
    business_requirement: str,
    step: int,
    last_feedback: str,
    last_reward: float,
    history: List[str],
) -> Tuple[str, str]:
    """Get schema design from the model."""
    user_prompt = build_user_prompt(
        business_requirement, step, last_feedback, last_reward, history
    )

    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
            stream=False,
        )

        response = (completion.choices[0].message.content or "").strip()
        # Try to extract JSON if the response contains extra text
        if response.startswith("```"):
            # Remove markdown code blocks
            lines = response.split("\n")
            json_lines = []
            in_json = False
            for line in lines:
                if line.strip().startswith("```"):
                    in_json = not in_json
                    continue
                if in_json:
                    json_lines.append(line)
            response = "\n".join(json_lines)

        # Validate it's valid JSON
        try:
            json.loads(response)
            return response, "llm"
        except json.JSONDecodeError:
            # Return a minimal valid schema as fallback
            return (
                json.dumps(
                    {
                        "openapi": "3.0.0",
                        "info": {"title": "API", "version": "1.0.0"},
                        "paths": {},
                        "components": {
                            "securitySchemes": {
                                "bearerAuth": {"type": "http", "scheme": "bearer"}
                            }
                        },
                        "security": [{"bearerAuth": []}],
                    }
                ),
                "fallback_invalid_json",
            )

    except Exception as exc:
        print(f"[DEBUG] Model request failed: {exc}", flush=True)
        # Return minimal valid schema as fallback
        return (
            json.dumps(
                {
                    "openapi": "3.0.0",
                    "info": {"title": "Fallback API", "version": "1.0.0"},
                    "paths": {},
                    "components": {
                        "securitySchemes": {
                            "bearerAuth": {"type": "http", "scheme": "bearer"}
                        }
                    },
                    "security": [{"bearerAuth": []}],
                }
            ),
            "fallback_model_error",
        )


async def run_episode(env: APIEnvClient, client: OpenAI, episode_index: int) -> dict:
    """Run one episode and return episode metrics."""
    history: List[str] = []
    rewards: List[float] = []
    steps_taken = 0
    score = 0.0
    success = False

    try:
        # Reset environment (task rotates server-side across resets)
        result = await env.reset()
        observation = result.observation
        business_requirement = observation.episode_info["business_requirement"]
        task_name = observation.episode_info.get("task_name", TASK_NAME)
        task_difficulty = observation.episode_info.get("task_difficulty", "unknown")

        log_start(
            task=f"{task_name}({task_difficulty})",
            env=BENCHMARK,
            model=MODEL_NAME,
        )

        last_feedback = "Starting new API design task"
        last_reward = 0.0

        for step in range(1, MAX_STEPS + 1):
            schema_json, source = await asyncio.to_thread(
                get_model_response,
                client,
                business_requirement,
                step,
                last_feedback,
                last_reward,
                history,
            )

            action = APIAction(schema_json=schema_json, iteration=step)
            result = await env.step(action)
            observation = result.observation
            reward = result.reward or 0.0
            done = result.done
            error = None

            rewards.append(reward)
            steps_taken = step
            last_feedback = observation.schema_feedback
            last_reward = reward

            log_step(
                step=step, action=schema_json, reward=reward, done=done, error=error
            )
            log_components(
                step=step,
                schema_json=schema_json,
                reward=reward,
                done=done,
                source=f"{source};episode={episode_index};task={task_name}",
            )

            history.append(f"Step {step}: reward {reward:+.2f} - {last_feedback}")
            if done:
                break

        executed_steps = max(steps_taken, 1)
        score = sum(rewards) / (executed_steps * MAX_REWARD_PER_STEP)
        score = min(max(score, 0.0), 1.0)
        success = score >= SUCCESS_SCORE_THRESHOLD
        return {
            "task_name": task_name,
            "task_difficulty": task_difficulty,
            "steps": steps_taken,
            "score": score,
            "success": success,
            "rewards": rewards,
        }

    except Exception as e:
        print(f"[DEBUG] Execution error: {e}", flush=True)
        with open(LOG_FILE_PATH, "a", encoding="utf-8") as log_file:
            ts = datetime.utcnow().isoformat() + "Z"
            log_file.write(f"\n[{ts}] episode={episode_index} execution_error={e}\n")
        return {
            "task_name": f"episode_{episode_index}",
            "task_difficulty": "unknown",
            "steps": steps_taken,
            "score": score,
            "success": False,
            "rewards": rewards,
        }


async def main() -> None:
    """Run reproducible baseline across all three tasks."""
    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)

    if USE_DOCKER and IMAGE_NAME:
        print(f"[INFO] Using Docker image: {IMAGE_NAME}")
        env = await APIEnvClient.from_docker_image(IMAGE_NAME)
    else:
        print(f"[INFO] Connecting to local server: {ENV_SERVER_URL}")
        env = APIEnvClient(base_url=ENV_SERVER_URL)

    with open(LOG_FILE_PATH, "w", encoding="utf-8") as log_file:
        run_time = datetime.utcnow().isoformat() + "Z"
        log_file.write(
            f"[{run_time}] run_start task={TASK_NAME} env={BENCHMARK} model={MODEL_NAME} episodes={BASELINE_EPISODES}\n"
        )

    episode_results = []
    try:
        for episode_index in range(1, BASELINE_EPISODES + 1):
            episode_result = await run_episode(env, client, episode_index)
            episode_results.append(episode_result)
            log_end(
                success=episode_result["success"],
                steps=episode_result["steps"],
                score=episode_result["score"],
                rewards=episode_result["rewards"],
            )

        aggregate_score = (
            sum(item["score"] for item in episode_results) / len(episode_results)
            if episode_results
            else 0.0
        )
        passed = sum(1 for item in episode_results if item["success"])
        print(
            f"[BASELINE] episodes={len(episode_results)} passed={passed} aggregate_score={aggregate_score:.3f}",
            flush=True,
        )

    finally:
        try:
            await env.close()
        except Exception as e:
            print(f"[DEBUG] env.close() error: {e}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
