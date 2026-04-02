# Design Document: api-conformance-gym

## Overview

The api-conformance-gym is an OpenEnv-compliant reinforcement learning environment that trains RL agents to design robust, secure, and compliant REST API schemas. The environment presents agents with natural language business requirements and expects them to produce valid OpenAPI 3.0/3.1 schemas. Through iterative feedback from a validator pipeline, agents learn to incrementally improve their API designs across multiple steps, optimizing for validity, best practices compliance, and error minimization.

## Architecture

```mermaid
graph TB
    subgraph Client["Client Layer"]
        Agent["RL Agent"]
        Client["APIEnvClient"]
    end
    
    subgraph Network["HTTP/WebSocket Layer"]
        WS["WebSocket Connection"]
    end
    
    subgraph Server["Server Layer"]
        App["FastAPI App<br/>create_web_interface_app"]
        Env["APIEnvironment<br/>reset/step/state"]
    end
    
    subgraph Validation["Validation Pipeline"]
        Parser["JSON Parser"]
        SchemaValidator["OpenAPI Schema Validator"]
        AuthValidator["Auth/Security Validator"]
        BestPractices["Best Practices Checker"]
        RewardCalc["Reward Calculator"]
    endpip install openenv-core
    
    subgraph Storage["State Management"]
        State["APIState<br/>current_schema, errors, history"]
        Metrics["Metrics Tracker"]
    end
    
    Agent -->|action: schema| Client
    Client -->|WebSocket: step()| WS
    WS -->|HTTP POST| App
    App -->|delegate| Env
    Env -->|validate| Parser
    Parser -->|parse| SchemaValidator
    SchemaValidator -->|check auth| AuthValidator
    AuthValidator -->|check practices| BestPractices
    BestPractices -->|calculate| RewardCalc
    RewardCalc -->|update| State
    State -->|track| Metrics
    Env -->|observation| App
    App -->|WebSocket: response| WS
    WS -->|observation| Client
    Client -->|state| Agent
```

## Components and Interfaces

### Component 1: APIEnvClient

**Purpose**: Client-side interface for agents to interact with the environment. Handles WebSocket communication, action submission, and state observation retrieval.

**Interface**:
```python
class APIEnvClient(EnvClient):
    async def reset(self) -> APIState
    async def step(self, action: APIAction) -> tuple[APIObservation, float, bool, dict]
    async def state(self) -> APIState
    async def close() -> None
```

**Responsibilities**:
- Establish and maintain WebSocket connection to server
- Serialize APIAction to JSON and transmit via WebSocket
- Deserialize APIObservation and APIState from server responses
- Handle connection errors and reconnection logic
- Provide synchronous wrapper for async operations if needed

### Component 2: APIEnvironment (Server-Side)

**Purpose**: Core environment logic implementing OpenEnv primitives. Manages state transitions, orchestrates validation pipeline, and calculates rewards server-side to prevent reward hacking.

**Interface**:
```python
class APIEnvironment(env_server.EnvServer):
    def reset(self, seed: int | None = None) -> APIState
    def step(self, action: APIAction) -> tuple[APIObservation, float, bool, dict]
    def state(self) -> APIState
    def _validate_schema(self, schema_json: str) -> ValidationResult
    def _calculate_reward(self, validation_result: ValidationResult) -> float
```

**Responsibilities**:
- Initialize environment state with business requirements prompt
- Accept agent actions (OpenAPI schemas) and validate them
- Orchestrate validation pipeline and collect error information
- Calculate rewards server-side using formula: R = (Validity × 0.5) + (Best Practices Score × 0.3) - (Error Count × 0.2)
- Track schema history and iteration count
- Determine episode termination conditions
- Return structured observations with error details for agent learning

### Component 3: Validation Pipeline

**Purpose**: Multi-stage validator that checks schema validity, security compliance, and best practices adherence.

**Stages**:
1. **JSON Parser**: Validates JSON structure and syntax
2. **OpenAPI Schema Validator**: Checks conformance to OpenAPI 3.0/3.1 specification
3. **Auth/Security Validator**: Verifies authentication schemes, security definitions, and proper endpoint protection
4. **Best Practices Checker**: Validates HTTP method correctness, naming conventions, versioning, documentation completeness

**Interface**:
```python
class ValidationPipeline:
    def validate(self, schema_json: str) -> ValidationResult
    def _parse_json(self, schema_json: str) -> dict | ValidationError
    def _validate_openapi_spec(self, schema_dict: dict) -> list[ValidationError]
    def _validate_auth_security(self, schema_dict: dict) -> list[ValidationError]
    def _check_best_practices(self, schema_dict: dict) -> list[ValidationError]
```

**Responsibilities**:
- Parse and validate JSON structure
- Check OpenAPI specification compliance
- Verify security schemes and authentication configuration
- Evaluate best practices (HTTP methods, naming, documentation)
- Aggregate errors with severity levels and actionable feedback
- Return structured ValidationResult with error details

### Component 4: Web Interface (FastAPI)

**Purpose**: HTTP/WebSocket server exposing environment primitives via OpenEnv standard interface.

**Interface**:
```python
def create_web_interface_app(env: APIEnvironment) -> FastAPI
    POST /reset -> APIState
    POST /step -> APIObservation, reward, done, info
    GET /state -> APIState
    WebSocket /ws -> bidirectional communication
```

**Responsibilities**:
- Create FastAPI application with OpenEnv-compliant endpoints
- Handle HTTP POST requests for reset/step/state operations
- Manage WebSocket connections for real-time communication
- Serialize/deserialize dataclasses to/from JSON
- Route requests to environment instance
- Handle errors and return appropriate HTTP status codes

## Data Models

### Model 1: APIAction

**Purpose**: Represents an agent's action—submitting an OpenAPI schema design.

```python
@dataclass
class APIAction:
    schema_json: str  # JSON-stringified OpenAPI 3.0/3.1 schema
    iteration: int    # Current iteration number for tracking
    metadata: dict    # Optional metadata (agent_id, timestamp, etc.)
```

**Validation Rules**:
- `schema_json` must be valid JSON string
- `schema_json` must be non-empty
- `iteration` must be non-negative integer
- `metadata` must be serializable dict

### Model 2: APIObservation

**Purpose**: Represents environment feedback to agent after action submission.

```python
@dataclass
class APIObservation:
    validation_errors: list[ValidationError]  # Structured error list
    error_count: int                          # Total error count
    validity_score: float                     # 0.0-1.0 validity percentage
    best_practices_score: float               # 0.0-1.0 best practices score
    schema_feedback: str                      # Human-readable feedback
    iteration: int                            # Current iteration
    episode_info: dict                        # Additional episode metadata
```

**Validation Rules**:
- All scores must be in range [0.0, 1.0]
- `validation_errors` must be non-empty list if validity_score < 1.0
- `error_count` must match length of validation_errors
- `iteration` must match action iteration

### Model 3: ValidationError

**Purpose**: Represents a single validation error with actionable feedback.

```python
@dataclass
class ValidationError:
    error_type: str      # e.g., "missing_auth", "invalid_method", "incomplete_docs"
    severity: str        # "critical", "warning", "info"
    path: str            # JSON path to error location (e.g., "paths./users.get")
    message: str         # Human-readable error message
    suggestion: str      # Actionable fix suggestion
```

**Validation Rules**:
- `error_type` must be from predefined set
- `severity` must be one of: "critical", "warning", "info"
- `path` must be valid JSON path or empty string
- `message` and `suggestion` must be non-empty strings

### Model 4: APIState

**Purpose**: Represents complete environment state at any point in time.

```python
@dataclass
class APIState:
    business_requirement: str           # Original natural language requirement
    current_schema: str | None          # Current OpenAPI schema (JSON string)
    validation_result: ValidationResult # Latest validation result
    iteration_count: int                # Number of steps taken
    schema_history: list[str]           # Previous schema submissions
    error_history: list[list[ValidationError]]  # Error progression
    episode_done: bool                  # Whether episode is complete
    total_reward: float                 # Cumulative reward
```

**Validation Rules**:
- `business_requirement` must be non-empty string
- `iteration_count` must be non-negative
- `schema_history` length must equal iteration_count
- `error_history` length must equal iteration_count
- `total_reward` must be finite number

### Model 5: ValidationResult

**Purpose**: Aggregated validation results from entire pipeline.

```python
@dataclass
class ValidationResult:
    is_valid: bool                      # Overall validity
    errors: list[ValidationError]       # All errors found
    validity_score: float               # Percentage of checks passed
    best_practices_score: float         # Best practices compliance score
    validation_stages: dict             # Per-stage results
    timestamp: float                    # When validation occurred
```

**Validation Rules**:
- `is_valid` must be True if errors list is empty
- Scores must be in range [0.0, 1.0]
- `validation_stages` must contain results from all pipeline stages

## Reward Formula

The reward calculation balances three objectives: schema validity, best practices compliance, and error minimization.

**Formula**:
$$R = (V \times 0.5) + (B \times 0.3) - (E \times 0.2)$$

Where:
- $V$ = Validity Score (0.0-1.0): Percentage of OpenAPI specification requirements met
- $B$ = Best Practices Score (0.0-1.0): Compliance with API design best practices
- $E$ = Normalized Error Count (0.0-1.0): $\min(1.0, \text{error\_count} / \text{max\_errors})$

**Reward Range**: [-0.2, 1.0]
- Maximum reward (1.0): Valid schema with perfect best practices, zero errors
- Minimum reward (-0.2): Invalid schema with many errors
- Typical reward (0.5-0.8): Valid schema with minor best practices issues

**Calculation Location**: Server-side in `APIEnvironment.step()` to prevent reward hacking by agents.

## Error Handling

### Error Scenario 1: Invalid JSON Schema

**Condition**: Agent submits malformed JSON string
**Response**: Observation with critical error, validity_score = 0.0, reward = -0.2
**Recovery**: Agent receives detailed JSON parsing error with line/column information; can resubmit corrected schema

### Error Scenario 2: Missing Authentication

**Condition**: Schema lacks security schemes or endpoints unprotected
**Response**: Observation with critical auth errors, best_practices_score reduced
**Recovery**: Agent receives specific guidance on required auth schemes; can add securitySchemes and apply to endpoints

### Error Scenario 3: Incorrect HTTP Methods

**Condition**: Schema uses wrong HTTP methods for operations (e.g., POST for retrieval)
**Response**: Observation with warning-level errors, best_practices_score reduced
**Recovery**: Agent receives suggestions for correct HTTP methods; can update operation definitions

### Error Scenario 4: Incomplete Documentation

**Condition**: Schema missing descriptions, examples, or parameter documentation
**Response**: Observation with info-level errors, best_practices_score reduced
**Recovery**: Agent receives checklist of missing documentation; can add descriptions and examples

### Error Scenario 5: Episode Termination

**Condition**: Agent reaches max iterations (e.g., 10 steps) or achieves perfect schema
**Response**: Episode marked as done, final observation returned
**Recovery**: Client calls reset() to start new episode with different requirement

## Testing Strategy

### Unit Testing Approach

**Scope**: Individual components (validators, reward calculator, state management)

**Key Test Cases**:
- JSON parser: valid/invalid JSON, edge cases (empty strings, special characters)
- OpenAPI validator: valid/invalid schemas, missing required fields, version compatibility
- Auth validator: missing schemes, unprotected endpoints, invalid scheme types
- Best practices checker: HTTP method correctness, naming conventions, documentation completeness
- Reward calculator: boundary conditions, formula correctness, edge cases

**Coverage Goals**: >90% line coverage for core validation logic

### Property-Based Testing Approach

**Property Test Library**: `hypothesis` (Python)

**Key Properties**:
1. **Validity Monotonicity**: If agent fixes all errors from previous iteration, validity_score should not decrease
2. **Reward Boundedness**: Reward always in range [-0.2, 1.0]
3. **Error Consistency**: error_count always equals length of validation_errors list
4. **Score Consistency**: validity_score and best_practices_score always in [0.0, 1.0]
5. **State Immutability**: Previous states in history never change after new step
6. **Deterministic Validation**: Same schema always produces same validation result

### Integration Testing Approach

**Scope**: End-to-end workflows (client → server → validation → reward)

**Key Scenarios**:
- Full episode: reset → multiple steps → episode completion
- Error recovery: invalid schema → corrected schema → improved reward
- State consistency: state() returns same data as last step() observation
- WebSocket communication: connection establishment, message serialization, error handling
- Concurrent episodes: multiple agents running simultaneously without interference

## Performance Considerations

**Latency Requirements**:
- Single step() call: <500ms (validation + reward calculation)
- reset() call: <100ms (state initialization)
- state() call: <50ms (state retrieval)

**Throughput**:
- Support 10+ concurrent agents per container instance
- Validation pipeline should process schemas up to 100KB

**Optimization Strategies**:
- Cache OpenAPI specification rules to avoid recompilation
- Parallelize validation stages where possible
- Use efficient JSON parsing (orjson or ujson)
- Implement schema caching for repeated validations

## Security Considerations

**Input Validation**:
- Sanitize all JSON inputs before parsing
- Limit schema size to prevent DoS (max 100KB)
- Validate all string fields for length and character restrictions

**Isolation**:
- Each agent session isolated via unique environment instance
- No shared state between concurrent episodes
- WebSocket connections authenticated and rate-limited

**Containerization**:
- Run in openenv-base:latest container with minimal privileges
- No direct file system access outside container
- Network access restricted to WebSocket port only

## Dependencies

**Core Framework**:
- `openenv`: OpenEnv standard library and base classes
- `fastapi`: Web framework for HTTP/WebSocket server
- `pydantic`: Data validation and serialization
- `python-multipart`: Form data handling

**Validation**:
- `jsonschema`: OpenAPI schema validation
- `openapi-spec-validator`: OpenAPI 3.0/3.1 specification validation
- `orjson`: High-performance JSON parsing

**Development**:
- `pytest`: Unit testing framework
- `hypothesis`: Property-based testing
- `pytest-asyncio`: Async test support
- `docker`: Containerization

**Runtime**:
- `python:3.11+`: Python runtime
- `openenv-base:latest`: Base container image with OpenEnv runtime
