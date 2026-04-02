# Implementation Plan: api-conformance-gym

## Overview

This implementation plan breaks down the api-conformance-gym OpenEnv environment into discrete coding tasks. The environment trains RL agents to design robust REST API schemas through iterative feedback. Implementation follows a bottom-up approach: data models → validation pipeline → environment logic → web interface → client → containerization → documentation.

## Tasks

- [ ] 1. Set up project structure and core data models
  - [x] 1.1 Create project directory structure and __init__.py files
    - Create `models.py`, `server/` directory, `tests/` directory
    - Add `__init__.py` files for proper Python package structure
    - _Requirements: Foundation for all components_
  
  - [x] 1.2 Implement core data models in models.py
    - Implement `ValidationError` dataclass with error_type, severity, path, message, suggestion fields
    - Implement `ValidationResult` dataclass with is_valid, errors, validity_score, best_practices_score, validation_stages, timestamp
    - Implement `APIAction` dataclass with schema_json, iteration, metadata fields
    - Implement `APIObservation` dataclass with validation_errors, error_count, validity_score, best_practices_score, schema_feedback, iteration, episode_info
    - Implement `APIState` dataclass with business_requirement, current_schema, validation_result, iteration_count, schema_history, error_history, episode_done, total_reward
    - Add validation methods to ensure field constraints (scores in [0.0, 1.0], non-negative iteration counts)
    - _Requirements: 1.1, 2.1, 3.1, 10.1-10.7, 11.1-11.6, 35.1-35.5, 36.1-36.3_
  
  - [ ]* 1.3 Write unit tests for data models
    - Test dataclass instantiation with valid and invalid data
    - Test field validation (score ranges, non-negative integers)
    - Test serialization/deserialization to/from JSON
    - _Requirements: 15.1-15.6, 32.1-32.4_

- [ ] 2. Implement validation pipeline components
  - [x] 2.1 Create server/validators.py with JSONParser class
    - Implement `parse(schema_json: str)` method that validates JSON syntax
    - Handle empty strings, malformed JSON, and schemas >100KB
    - Return parsed dict on success or ValidationError on failure
    - Include line/column information in parse errors
    - _Requirements: 4.1-4.5, 17.1-17.4, 25.1-25.3_
  
  - [ ]* 2.2 Write property test for JSONParser
    - **Property 6: Deterministic validation - Same schema always produces same result**
    - **Validates: Requirements 29.1-29.3**
    - Use hypothesis to generate random JSON strings
    - Verify parse results are identical across multiple calls
  
  - [x] 2.3 Implement OpenAPIValidator class in server/validators.py
    - Implement `validate(schema_dict: dict)` method using openapi-spec-validator
    - Check for required fields (openapi, info, paths)
    - Detect invalid field values, empty paths, invalid HTTP methods
    - Return list of ValidationError objects
    - _Requirements: 5.1-5.6_
  
  - [ ]* 2.4 Write unit tests for OpenAPIValidator
    - Test valid OpenAPI 3.0 and 3.1 schemas
    - Test missing required fields
    - Test invalid field values and empty paths
    - _Requirements: 5.1-5.6_
  
  - [x] 2.5 Implement AuthValidator class in server/validators.py
    - Implement `validate(schema_dict: dict)` method
    - Check for securitySchemes in components section
    - Detect unprotected endpoints (missing security requirements)
    - Validate security scheme types
    - Return list of ValidationError objects
    - _Requirements: 6.1-6.5, 18.1-18.4_
  
  - [ ]* 2.6 Write unit tests for AuthValidator
    - Test schemas with valid security schemes
    - Test missing securitySchemes
    - Test unprotected endpoints
    - Test invalid security scheme types
    - _Requirements: 6.1-6.5_
  
  - [x] 2.7 Implement BestPracticesChecker class in server/validators.py
    - Implement `validate(schema_dict: dict)` method
    - Check HTTP method correctness (GET for retrieval, POST for creation, etc.)
    - Validate naming conventions (lowercase paths with hyphens, camelCase parameters)
    - Check for operation descriptions and parameter documentation
    - Check for API versioning
    - Return list of ValidationError objects with severity "warning" or "info"
    - _Requirements: 7.1-7.8, 19.1-19.3, 20.1-20.4_
  
  - [ ]* 2.8 Write unit tests for BestPracticesChecker
    - Test correct and incorrect HTTP method usage
    - Test naming convention violations
    - Test missing documentation
    - Test missing versioning
    - _Requirements: 7.1-7.8_

- [ ] 3. Implement validation pipeline orchestration and reward calculation
  - [x] 3.1 Create ValidationPipeline class in server/validators.py
    - Implement `validate(schema_json: str)` method that orchestrates all validators
    - Execute stages in order: JSONParser → OpenAPIValidator → AuthValidator → BestPracticesChecker
    - Continue through all stages even if critical errors found
    - Aggregate all errors into ValidationResult
    - Calculate validity_score and best_practices_score
    - Include per-stage results in validation_stages dict
    - Add timestamp to ValidationResult
    - _Requirements: 8.1-8.5, 39.1-39.3, 40.1-40.3_
  
  - [ ]* 3.2 Write property test for ValidationPipeline
    - **Property 6: Deterministic validation - Same schema always produces same ValidationResult**
    - **Validates: Requirements 29.1-29.3**
    - Use hypothesis to generate OpenAPI schemas
    - Verify validation results are identical across multiple calls
  
  - [x] 3.3 Create RewardCalculator class in server/reward.py
    - Implement `calculate(validation_result: ValidationResult)` method
    - Calculate normalized_error_count as min(1.0, error_count / max_errors)
    - Apply formula: R = (V × 0.5) + (B × 0.3) - (E × 0.2)
    - Ensure reward is always in range [-0.2, 1.0]
    - Return reward = 1.0 when V=1.0, B=1.0, error_count=0
    - Return reward = -0.2 when V=0.0 and high error count
    - _Requirements: 9.1-9.7, 30.1-30.3_
  
  - [ ]* 3.4 Write property test for RewardCalculator
    - **Property 2: Reward boundedness - Reward always in range [-0.2, 1.0]**
    - **Validates: Requirements 30.1-30.3**
    - Use hypothesis to generate random ValidationResult objects
    - Verify reward is always within bounds
  
  - [ ]* 3.5 Write unit tests for RewardCalculator
    - Test perfect schema (V=1.0, B=1.0, E=0) returns reward=1.0
    - Test worst schema (V=0.0, high errors) returns reward=-0.2
    - Test intermediate cases
    - _Requirements: 9.1-9.7_

- [ ] 4. Checkpoint - Ensure validation pipeline tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 5. Implement core APIEnvironment server logic
  - [x] 5.1 Create server/environment.py with APIEnvironment class
    - Inherit from `openenv.core.env_server.EnvServer`
    - Implement `__init__` to initialize ValidationPipeline and RewardCalculator
    - Add instance variables for state management (current_state, max_iterations=10, max_errors=20)
    - _Requirements: Foundation for environment primitives_
  
  - [x] 5.2 Implement reset() method in APIEnvironment
    - Accept optional seed parameter
    - Initialize new APIState with business_requirement, iteration_count=0, empty histories
    - Set current_schema=None, total_reward=0.0, episode_done=False
    - Complete within 100ms (no I/O operations)
    - Return APIState
    - _Requirements: 2.1-2.5, 21.1-21.3, 36.1-36.3_
  
  - [ ]* 5.3 Write unit tests for reset()
    - Test state initialization
    - Test seed parameter handling
    - Test performance (<100ms)
    - _Requirements: 2.1-2.5_
  
  - [x] 5.4 Implement step() method in APIEnvironment
    - Accept APIAction parameter
    - Validate action using ValidationPipeline
    - Calculate reward using RewardCalculator
    - Create APIObservation with validation errors, scores, and feedback
    - Update APIState: increment iteration_count, append to histories, update total_reward
    - Check termination conditions (max_iterations or perfect schema)
    - Complete within 500ms
    - Return tuple (APIObservation, reward, done, info)
    - _Requirements: 3.1-3.7, 9.1-9.7, 10.1-10.7, 11.1-11.6, 12.1-12.4, 22.1-22.4, 31.1-31.3, 34.1-34.3_
  
  - [ ]* 5.5 Write property test for step()
    - **Property 3: Error consistency - error_count always equals length of validation_errors**
    - **Validates: Requirements 31.1-31.3**
    - Use hypothesis to generate random APIAction objects
    - Verify error_count matches validation_errors length
  
  - [ ]* 5.6 Write property test for step() score validation
    - **Property 4: Score validation - validity_score and best_practices_score always in [0.0, 1.0]**
    - **Validates: Requirements 32.1-32.4**
    - Use hypothesis to generate random APIAction objects
    - Verify all scores are within valid range
  
  - [x] 5.7 Implement state() method in APIEnvironment
    - Return current APIState
    - Complete within 50ms (no recomputation)
    - _Requirements: 11.1-11.6, 23.1-23.2_
  
  - [ ]* 5.8 Write property test for state immutability
    - **Property 5: State immutability - Previous states in history never change**
    - **Validates: Requirements 33.1-33.3**
    - Call step() multiple times, verify previous history entries unchanged
  
  - [ ]* 5.9 Write unit tests for step() and state()
    - Test full episode workflow
    - Test termination conditions
    - Test cumulative reward tracking
    - Test state retrieval
    - _Requirements: 3.1-3.7, 11.1-11.6, 12.1-12.4_

- [ ] 6. Implement session management and isolation
  - [ ] 6.1 Add session management to APIEnvironment
    - Create session ID generation mechanism
    - Implement session-based environment instance storage
    - Add session validation in step() and state() methods
    - _Requirements: 16.1-16.4, 27.1-27.4_
  
  - [ ] 6.2 Write integration tests for concurrent episodes
    - Test multiple agents with separate environment instances
    - Verify agent A's actions don't affect agent B's state
    - Test concurrent step() calls without data corruption
    - _Requirements: 16.1-16.4, 24.1-24.3_

- [ ] 7. Checkpoint - Ensure environment core logic tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 8. Implement FastAPI web interface
  - [x] 8.1 Create server/app.py with create_web_interface_app function
    - Create FastAPI application instance
    - Add CORS middleware for cross-origin requests
    - Set up environment instance management (one per session)
    - _Requirements: Foundation for HTTP/WebSocket endpoints_
  
  - [x] 8.2 Implement HTTP POST /reset endpoint
    - Accept optional seed parameter
    - Call environment.reset(seed)
    - Return APIState as JSON with HTTP 200
    - Handle errors with appropriate HTTP status codes
    - _Requirements: 13.1, 13.4-13.5_
  
  - [x] 8.3 Implement HTTP POST /step endpoint
    - Accept APIAction JSON body
    - Deserialize to APIAction dataclass
    - Call environment.step(action)
    - Return APIObservation and reward as JSON with HTTP 200
    - Handle validation errors with HTTP 422
    - _Requirements: 13.2, 13.4-13.5, 15.1-15.6_
  
  - [x] 8.4 Implement HTTP GET /state endpoint
    - Call environment.state()
    - Return APIState as JSON with HTTP 200
    - Handle errors with appropriate HTTP status codes
    - _Requirements: 13.3, 13.4-13.5_
  
  - [x] 8.5 Implement WebSocket /ws endpoint
    - Accept WebSocket connections
    - Handle "reset", "step", and "state" message types
    - Deserialize incoming messages to appropriate dataclasses
    - Call corresponding environment methods
    - Serialize responses and send via WebSocket
    - Handle connection close gracefully
    - _Requirements: 14.1-14.5, 15.1-15.6_
  
  - [ ] 8.6 Add rate limiting middleware
    - Implement rate limiter (100 requests per minute per client)
    - Return HTTP 429 when rate limit exceeded
    - Reset rate limit after 1 minute
    - _Requirements: 28.1-28.3_
  
  - [ ]* 8.7 Write integration tests for HTTP endpoints
    - Test POST /reset with and without seed
    - Test POST /step with valid and invalid actions
    - Test GET /state
    - Test error handling (404, 422)
    - _Requirements: 13.1-13.5_
  
  - [ ]* 8.8 Write integration tests for WebSocket endpoint
    - Test connection establishment
    - Test reset, step, and state messages
    - Test connection close
    - Test error handling
    - _Requirements: 14.1-14.5_

- [ ] 9. Implement client-side APIEnvClient
  - [x] 9.1 Create client.py with APIEnvClient class
    - Inherit from `openenv.core.EnvClient`
    - Implement `__init__` with server URL parameter
    - Add WebSocket connection management
    - _Requirements: 1.1-1.5_
  
  - [x] 9.2 Implement async reset() method in APIEnvClient
    - Send reset message via WebSocket
    - Receive and deserialize APIState response
    - Return APIState
    - _Requirements: 1.1-1.5_
  
  - [x] 9.3 Implement async step() method in APIEnvClient
    - Serialize APIAction to JSON
    - Send step message via WebSocket
    - Receive and deserialize APIObservation response
    - Return tuple (observation, reward, done, info)
    - _Requirements: 1.1-1.5_
  
  - [x] 9.4 Implement async state() method in APIEnvClient
    - Send state message via WebSocket
    - Receive and deserialize APIState response
    - Return APIState
    - _Requirements: 1.1-1.5_
  
  - [x] 9.5 Implement async close() method in APIEnvClient
    - Gracefully close WebSocket connection
    - Clean up resources
    - _Requirements: 1.1-1.5_
  
  - [x] 9.6 Add reconnection logic with exponential backoff
    - Implement reconnection on connection loss
    - Use exponential backoff (max 5 retries)
    - _Requirements: 1.1-1.5_
  
  - [ ]* 9.7 Write integration tests for APIEnvClient
    - Test full episode workflow (reset → multiple steps → close)
    - Test reconnection logic
    - Test error handling
    - _Requirements: 1.1-1.5_

- [ ] 10. Checkpoint - Ensure client-server integration tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 11. Create containerization and deployment files
  - [x] 11.1 Create Dockerfile
    - Use `openenv-base:latest` as base image
    - Copy source files to container
    - Install dependencies from requirements.txt
    - Expose WebSocket port
    - Set entrypoint to run FastAPI server with uvicorn
    - _Requirements: Containerization for deployment_
  
  - [x] 11.2 Create requirements.txt
    - List all dependencies: openenv, fastapi, uvicorn, websockets, pydantic, jsonschema, openapi-spec-validator, orjson, pytest, hypothesis, pytest-asyncio
    - Pin versions for reproducibility
    - _Requirements: Dependency management_
  
  - [x] 11.3 Create openenv.yaml manifest
    - Define environment metadata (name, version, description)
    - Specify OpenEnv version compatibility
    - Define action and observation spaces
    - Include performance characteristics
    - _Requirements: OpenEnv compliance_

- [ ] 12. Create documentation and examples
  - [x] 12.1 Create README.md
    - Add project overview and features
    - Include installation instructions
    - Document API endpoints and WebSocket protocol
    - Add usage examples with code snippets
    - Include reward formula in LaTeX: $R = (V \times 0.5) + (B \times 0.3) - (E \times 0.2)$
    - Document performance targets and limitations
    - Add troubleshooting section
    - _Requirements: Professional documentation_
  
  - [x] 12.2 Create examples/simple_agent.py
    - Implement basic RL agent that connects to environment
    - Demonstrate reset(), step(), and state() usage
    - Show how to parse observations and improve schemas
    - _Requirements: Usage examples_
  
  - [ ] 12.3 Add inline code documentation
    - Add docstrings to all classes and methods
    - Include parameter descriptions and return types
    - Add usage examples in docstrings
    - _Requirements: Code documentation_
  
  - [x] 12.4 Create inference.py baseline script
    - Read environment variables: API_BASE_URL, MODEL_NAME, HF_TOKEN/API_KEY, IMAGE_NAME
    - Use OpenAI Client for all LLM calls
    - Implement log_start(), log_step(), log_end() functions for stdout formatting
    - Emit [START] line at episode begin: `[START] task=<task_name> env=<benchmark> model=<model_name>`
    - Emit [STEP] line per step: `[STEP] step=<n> action=<action_str> reward=<0.00> done=<true|false> error=<msg|null>`
    - Emit [END] line at completion: `[END] success=<true|false> steps=<n> score=<0.000> rewards=<r1,r2,...,rn>`
    - Format rewards to 2 decimal places, score to 3 decimal places
    - Use lowercase booleans (true/false) for done and success
    - Always emit [END] line even on exception
    - Calculate normalized score in range [0.0, 1.0]
    - Determine success based on SUCCESS_SCORE_THRESHOLD
    - _Requirements: 41.1-41.17_
  
  - [x] 12.5 Implement task grading system in server/graders.py
    - Define at least 3 distinct API design tasks (easy, medium, hard)
    - Implement programmatic graders that return scores in [0.0, 1.0]
    - Use clear, deterministic success/failure criteria
    - Include real-world scenarios: e-commerce API, authentication system, data analytics API
    - Return aggregate score across all tasks
    - _Requirements: 42.1-42.6, 43.1-43.4_

- [ ] 13. Final integration and testing
  - [ ] 13.1 Create tests/test_integration.py
    - Test full end-to-end workflow: client connects → reset → multiple steps → episode completion
    - Test error recovery scenarios (invalid JSON → corrected schema)
    - Test concurrent agents (10 agents running simultaneously)
    - Verify performance targets (reset <100ms, step <500ms, state <50ms)
    - _Requirements: 21.1-21.3, 22.1-22.4, 23.1-23.2, 24.1-24.3_
  
  - [ ]* 13.2 Run all property-based tests
    - Execute all hypothesis tests
    - Verify all properties hold across generated test cases
    - _Requirements: All property test requirements_
  
  - [ ]* 13.3 Run performance benchmarks
    - Measure reset(), step(), and state() latency
    - Test concurrent agent throughput
    - Verify schema size limits
    - _Requirements: 21.1-21.3, 22.1-22.4, 23.1-23.2, 24.1-24.3_

- [ ] 14. Final checkpoint - Ensure all tests pass and documentation is complete
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation at key milestones
- Property tests validate universal correctness properties using hypothesis
- Unit tests validate specific examples and edge cases
- Integration tests validate end-to-end workflows and client-server communication
- The implementation follows a bottom-up approach: data models → validators → environment → web interface → client → deployment
- All code should include type hints for better IDE support and type checking
- Use Python 3.11+ features where appropriate (e.g., union types with `|`)
