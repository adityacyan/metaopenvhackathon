# Requirements Document: api-conformance-gym

## Introduction

The api-conformance-gym is an OpenEnv-compliant reinforcement learning environment that trains RL agents to design robust, secure, and compliant REST API schemas. This requirements document specifies the functional and non-functional requirements derived from the technical design, establishing acceptance criteria for each requirement and defining the correctness properties that validate system behavior.

The system enables agents to iteratively improve OpenAPI 3.0/3.1 schemas through structured feedback from a multi-stage validation pipeline, with rewards calculated server-side to prevent manipulation. The environment supports concurrent agent training with isolated state management and comprehensive error handling.

## Glossary

- **APIAction**: Data structure representing an agent's action—submission of an OpenAPI schema design with iteration metadata
- **APIObservation**: Data structure representing environment feedback including validation errors, scores, and human-readable feedback
- **APIEnvironment**: Server-side core environment logic implementing OpenEnv primitives and state transitions
- **APIEnvClient**: Client-side interface for agents to interact with the environment via WebSocket
- **ValidationPipeline**: Multi-stage validator checking JSON syntax, OpenAPI compliance, security, and best practices
- **ValidationError**: Single validation error with type, severity, location, message, and actionable suggestion
- **APIState**: Complete environment state including business requirement, current schema, validation results, and history
- **ValidationResult**: Aggregated validation results from entire pipeline with scores and per-stage results
- **OpenAPI Schema**: JSON document conforming to OpenAPI 3.0 or 3.1 specification defining REST API structure
- **Best Practices Score**: Compliance metric (0.0-1.0) measuring adherence to API design conventions
- **Validity Score**: Compliance metric (0.0-1.0) measuring adherence to OpenAPI specification requirements
- **Reward**: Numerical value calculated as R = (V × 0.5) + (B × 0.3) - (E × 0.2) representing agent performance
- **Episode**: Single training iteration from reset() to termination (max iterations or perfect schema)
- **WebSocket**: Bidirectional communication protocol for real-time client-server interaction
- **JSON Parser**: Component validating JSON structure and syntax
- **OpenAPI Validator**: Component checking conformance to OpenAPI 3.0/3.1 specification
- **Auth Validator**: Component verifying authentication schemes and security definitions
- **Best Practices Checker**: Component validating HTTP methods, naming conventions, and documentation

## Requirements

### Requirement 1: Client-Server Communication via WebSocket

**User Story:** As an RL agent developer, I want to communicate with the environment through WebSocket, so that I can submit schemas and receive feedback in real-time.

#### Acceptance Criteria

1. WHEN an APIEnvClient connects to the server, THE APIEnvClient SHALL establish a WebSocket connection to the specified endpoint
2. WHEN an APIEnvClient calls reset(), THE APIEnvClient SHALL transmit a reset request via WebSocket and receive an APIState response
3. WHEN an APIEnvClient calls step(action), THE APIEnvClient SHALL serialize the APIAction to JSON, transmit it via WebSocket, and receive an APIObservation response
4. WHEN an APIEnvClient calls state(), THE APIEnvClient SHALL retrieve the current APIState from the server via WebSocket
5. WHEN the WebSocket connection is lost, THE APIEnvClient SHALL attempt to reconnect with exponential backoff (max 5 retries)
6. WHEN an APIEnvClient calls close(), THE APIEnvClient SHALL gracefully close the WebSocket connection

### Requirement 2: Environment Reset and Initialization

**User Story:** As an RL agent, I want to reset the environment with a new business requirement, so that I can start a fresh training episode.

#### Acceptance Criteria

1. WHEN reset() is called with an optional seed parameter, THE APIEnvironment SHALL initialize a new episode with a business requirement prompt
2. WHEN reset() is called, THE APIEnvironment SHALL set iteration_count to 0, clear schema_history, and clear error_history
3. WHEN reset() is called, THE APIEnvironment SHALL return an APIState with current_schema set to None and total_reward set to 0.0
4. WHEN reset() is called, THE APIEnvironment SHALL complete within 100ms
5. WHEN reset() is called with a seed, THE APIEnvironment SHALL use that seed for deterministic requirement selection (if applicable)

### Requirement 3: Schema Submission and Validation

**User Story:** As an RL agent, I want to submit OpenAPI schemas and receive validation feedback, so that I can learn which design patterns are correct.

#### Acceptance Criteria

1. WHEN step(action) is called with a valid APIAction, THE APIEnvironment SHALL validate the schema_json field
2. WHEN step(action) is called, THE APIEnvironment SHALL invoke the ValidationPipeline to check the schema
3. WHEN step(action) is called, THE APIEnvironment SHALL return an APIObservation containing validation_errors, error_count, validity_score, and best_practices_score
4. WHEN step(action) is called, THE APIEnvironment SHALL increment iteration_count by 1
5. WHEN step(action) is called, THE APIEnvironment SHALL append the submitted schema to schema_history
6. WHEN step(action) is called, THE APIEnvironment SHALL append the validation errors to error_history
7. WHEN step(action) is called, THE APIEnvironment SHALL complete within 500ms

### Requirement 4: JSON Parsing and Validation

**User Story:** As a validation system, I want to parse and validate JSON structure, so that I can detect malformed schemas early.

#### Acceptance Criteria

1. WHEN the ValidationPipeline receives a schema_json string, THE JSON_Parser SHALL attempt to parse it as valid JSON
2. WHEN the JSON_Parser receives valid JSON, THE JSON_Parser SHALL return a parsed dictionary
3. WHEN the JSON_Parser receives invalid JSON (malformed syntax), THE JSON_Parser SHALL return a ValidationError with error_type "invalid_json", severity "critical", and a message indicating the parse error location
4. WHEN the JSON_Parser receives an empty string, THE JSON_Parser SHALL return a ValidationError with error_type "empty_schema" and severity "critical"
5. WHEN the JSON_Parser receives a JSON string larger than 100KB, THE JSON_Parser SHALL return a ValidationError with error_type "schema_too_large" and severity "critical"

### Requirement 5: OpenAPI Specification Validation

**User Story:** As a validation system, I want to validate schemas against the OpenAPI 3.0/3.1 specification, so that I can ensure schemas are structurally correct.

#### Acceptance Criteria

1. WHEN the OpenAPI_Validator receives a parsed schema dictionary, THE OpenAPI_Validator SHALL check conformance to OpenAPI 3.0 or 3.1 specification
2. WHEN the OpenAPI_Validator detects a missing required field (e.g., "openapi", "info", "paths"), THE OpenAPI_Validator SHALL return a ValidationError with error_type "missing_required_field", severity "critical", and the field name in the message
3. WHEN the OpenAPI_Validator detects an invalid field value (e.g., invalid version format), THE OpenAPI_Validator SHALL return a ValidationError with error_type "invalid_field_value", severity "critical"
4. WHEN the OpenAPI_Validator detects a path definition without operations, THE OpenAPI_Validator SHALL return a ValidationError with error_type "empty_path", severity "warning"
5. WHEN the OpenAPI_Validator detects an operation with an invalid HTTP method, THE OpenAPI_Validator SHALL return a ValidationError with error_type "invalid_http_method", severity "warning"
6. WHEN the schema is valid according to OpenAPI specification, THE OpenAPI_Validator SHALL return an empty error list

### Requirement 6: Authentication and Security Validation

**User Story:** As a validation system, I want to verify authentication schemes and security definitions, so that I can ensure APIs are properly protected.

#### Acceptance Criteria

1. WHEN the Auth_Validator receives a schema dictionary, THE Auth_Validator SHALL check for the presence of securitySchemes in the components section
2. WHEN the Auth_Validator detects missing securitySchemes, THE Auth_Validator SHALL return a ValidationError with error_type "missing_auth_schemes", severity "critical"
3. WHEN the Auth_Validator detects endpoints without security requirements, THE Auth_Validator SHALL return a ValidationError with error_type "unprotected_endpoint", severity "critical", with the endpoint path in the message
4. WHEN the Auth_Validator detects an invalid security scheme type, THE Auth_Validator SHALL return a ValidationError with error_type "invalid_security_scheme", severity "critical"
5. WHEN the Auth_Validator detects all endpoints are properly protected with valid schemes, THE Auth_Validator SHALL return an empty error list

### Requirement 7: Best Practices Validation

**User Story:** As a validation system, I want to check API design best practices, so that I can guide agents toward industry-standard patterns.

#### Acceptance Criteria

1. WHEN the Best_Practices_Checker receives a schema dictionary, THE Best_Practices_Checker SHALL validate HTTP method correctness (GET for retrieval, POST for creation, PUT/PATCH for updates, DELETE for deletion)
2. WHEN the Best_Practices_Checker detects incorrect HTTP method usage, THE Best_Practices_Checker SHALL return a ValidationError with error_type "incorrect_http_method", severity "warning"
3. WHEN the Best_Practices_Checker receives a schema, THE Best_Practices_Checker SHALL check for operation descriptions and parameter documentation
4. WHEN the Best_Practices_Checker detects missing descriptions, THE Best_Practices_Checker SHALL return a ValidationError with error_type "incomplete_documentation", severity "info"
5. WHEN the Best_Practices_Checker receives a schema, THE Best_Practices_Checker SHALL validate naming conventions (e.g., paths use lowercase with hyphens, parameters use camelCase)
6. WHEN the Best_Practices_Checker detects naming convention violations, THE Best_Practices_Checker SHALL return a ValidationError with error_type "naming_convention_violation", severity "info"
7. WHEN the Best_Practices_Checker receives a schema, THE Best_Practices_Checker SHALL check for API versioning in the path or info section
8. WHEN the Best_Practices_Checker detects missing versioning, THE Best_Practices_Checker SHALL return a ValidationError with error_type "missing_versioning", severity "info"

### Requirement 8: Validation Pipeline Orchestration

**User Story:** As a validation system, I want to orchestrate multiple validation stages, so that I can provide comprehensive feedback on schema quality.

#### Acceptance Criteria

1. WHEN the ValidationPipeline receives a schema_json string, THE ValidationPipeline SHALL execute validation stages in order: JSON Parser → OpenAPI Validator → Auth Validator → Best Practices Checker
2. WHEN a validation stage returns critical errors, THE ValidationPipeline SHALL continue to subsequent stages to collect all errors
3. WHEN all validation stages complete, THE ValidationPipeline SHALL aggregate all errors into a single ValidationResult
4. WHEN the ValidationPipeline completes validation, THE ValidationPipeline SHALL return a ValidationResult with is_valid=True only if the errors list is empty
5. WHEN the ValidationPipeline completes validation, THE ValidationPipeline SHALL include per-stage results in the validation_stages dictionary

### Requirement 9: Reward Calculation

**User Story:** As an RL environment, I want to calculate rewards using a balanced formula, so that agents learn to optimize for validity, best practices, and error minimization.

#### Acceptance Criteria

1. WHEN the Reward_Calculator receives a ValidationResult, THE Reward_Calculator SHALL calculate validity_score as the percentage of OpenAPI specification checks passed (0.0-1.0)
2. WHEN the Reward_Calculator receives a ValidationResult, THE Reward_Calculator SHALL calculate best_practices_score as the percentage of best practices checks passed (0.0-1.0)
3. WHEN the Reward_Calculator receives a ValidationResult, THE Reward_Calculator SHALL calculate normalized_error_count as min(1.0, error_count / max_errors)
4. WHEN the Reward_Calculator has all three components, THE Reward_Calculator SHALL calculate reward as: R = (V × 0.5) + (B × 0.3) - (E × 0.2)
5. WHEN the Reward_Calculator completes calculation, THE Reward_Calculator SHALL return a reward value in the range [-0.2, 1.0]
6. WHEN validity_score is 1.0 and best_practices_score is 1.0 and error_count is 0, THE Reward_Calculator SHALL return reward = 1.0
7. WHEN validity_score is 0.0 and error_count is high, THE Reward_Calculator SHALL return reward = -0.2

### Requirement 10: Observation Generation

**User Story:** As an RL environment, I want to generate structured observations, so that agents receive actionable feedback for learning.

#### Acceptance Criteria

1. WHEN step() completes validation, THE APIEnvironment SHALL create an APIObservation with validation_errors from the ValidationResult
2. WHEN step() completes validation, THE APIEnvironment SHALL set error_count equal to the length of validation_errors
3. WHEN step() completes validation, THE APIEnvironment SHALL set validity_score from the ValidationResult
4. WHEN step() completes validation, THE APIEnvironment SHALL set best_practices_score from the ValidationResult
5. WHEN step() completes validation, THE APIEnvironment SHALL generate schema_feedback as a human-readable summary of errors and suggestions
6. WHEN step() completes validation, THE APIEnvironment SHALL set iteration equal to the current iteration_count
7. WHEN step() completes validation, THE APIEnvironment SHALL include episode_info with metadata about the current episode

### Requirement 11: State Management and History Tracking

**User Story:** As an RL environment, I want to maintain complete state history, so that agents can learn from their progression and I can analyze training dynamics.

#### Acceptance Criteria

1. WHEN step() is called, THE APIEnvironment SHALL append the submitted schema to schema_history
2. WHEN step() is called, THE APIEnvironment SHALL append the validation errors to error_history
3. WHEN state() is called, THE APIEnvironment SHALL return an APIState with schema_history containing all previously submitted schemas
4. WHEN state() is called, THE APIEnvironment SHALL return an APIState with error_history containing all previous validation error lists
5. WHEN state() is called, THE APIEnvironment SHALL return an APIState with iteration_count equal to the length of schema_history
6. WHEN state() is called, THE APIEnvironment SHALL return an APIState with total_reward equal to the cumulative sum of all step rewards

### Requirement 12: Episode Termination

**User Story:** As an RL environment, I want to terminate episodes appropriately, so that agents know when training iterations are complete.

#### Acceptance Criteria

1. WHEN step() is called and iteration_count reaches max_iterations (e.g., 10), THE APIEnvironment SHALL set episode_done to True
2. WHEN step() is called and validity_score equals 1.0 and best_practices_score equals 1.0, THE APIEnvironment SHALL set episode_done to True
3. WHEN step() is called and episode_done is True, THE APIEnvironment SHALL return an APIObservation with episode_done=True
4. WHEN episode_done is True, THE APIEnvironment SHALL include final episode statistics in episode_info

### Requirement 13: Web Interface HTTP Endpoints

**User Story:** As an API consumer, I want to interact with the environment through HTTP endpoints, so that I can integrate with various client frameworks.

#### Acceptance Criteria

1. WHEN a POST request is sent to /reset, THE FastAPI_App SHALL invoke environment.reset() and return the APIState as JSON
2. WHEN a POST request is sent to /step with an APIAction JSON body, THE FastAPI_App SHALL invoke environment.step(action) and return the APIObservation and reward as JSON
3. WHEN a GET request is sent to /state, THE FastAPI_App SHALL invoke environment.state() and return the APIState as JSON
4. WHEN a request is sent to an invalid endpoint, THE FastAPI_App SHALL return HTTP 404 Not Found
5. WHEN a request body fails validation, THE FastAPI_App SHALL return HTTP 422 Unprocessable Entity with error details

### Requirement 14: WebSocket Endpoint

**User Story:** As a real-time client, I want to communicate with the environment through WebSocket, so that I can send actions and receive observations with minimal latency.

#### Acceptance Criteria

1. WHEN a WebSocket connection is established to /ws, THE FastAPI_App SHALL accept the connection and maintain it
2. WHEN a WebSocket client sends a reset message, THE FastAPI_App SHALL invoke environment.reset() and send the APIState response
3. WHEN a WebSocket client sends a step message with an APIAction, THE FastAPI_App SHALL invoke environment.step(action) and send the APIObservation response
4. WHEN a WebSocket client sends a state message, THE FastAPI_App SHALL invoke environment.state() and send the APIState response
5. WHEN a WebSocket connection is closed, THE FastAPI_App SHALL clean up resources and close the connection gracefully

### Requirement 15: Data Serialization and Deserialization

**User Story:** As a distributed system, I want to serialize and deserialize dataclasses to/from JSON, so that data can be transmitted over HTTP and WebSocket.

#### Acceptance Criteria

1. WHEN an APIAction is serialized to JSON, THE Serializer SHALL include schema_json, iteration, and metadata fields
2. WHEN an APIObservation is serialized to JSON, THE Serializer SHALL include all fields with ValidationError objects serialized as dictionaries
3. WHEN an APIState is serialized to JSON, THE Serializer SHALL include all fields with nested objects properly serialized
4. WHEN a JSON string is deserialized to an APIAction, THE Deserializer SHALL validate all required fields are present
5. WHEN a JSON string is deserialized to an APIObservation, THE Deserializer SHALL reconstruct ValidationError objects from dictionaries
6. WHEN deserialization fails, THE Deserializer SHALL raise a clear error indicating which field failed validation

### Requirement 16: Concurrent Episode Isolation

**User Story:** As a multi-agent training system, I want to isolate concurrent episodes, so that multiple agents can train simultaneously without interference.

#### Acceptance Criteria

1. WHEN multiple agents connect to the environment, THE APIEnvironment SHALL create separate environment instances for each agent
2. WHEN agent A submits a schema, THE APIEnvironment SHALL not affect agent B's state or history
3. WHEN agent A calls reset(), THE APIEnvironment SHALL only reset agent A's episode, not agent B's
4. WHEN agent A and agent B both call step() concurrently, THE APIEnvironment SHALL process both requests without data corruption

### Requirement 17: Error Handling for Invalid JSON

**User Story:** As a validation system, I want to handle invalid JSON gracefully, so that agents receive clear feedback on syntax errors.

#### Acceptance Criteria

1. WHEN an agent submits malformed JSON, THE ValidationPipeline SHALL return a ValidationError with error_type "invalid_json"
2. WHEN an agent submits malformed JSON, THE ValidationError SHALL include the line and column number of the parse error
3. WHEN an agent submits malformed JSON, THE APIObservation SHALL have validity_score = 0.0
4. WHEN an agent submits malformed JSON, THE reward SHALL be -0.2

### Requirement 18: Error Handling for Missing Authentication

**User Story:** As a validation system, I want to detect missing authentication, so that agents learn to secure their APIs.

#### Acceptance Criteria

1. WHEN a schema lacks securitySchemes, THE Auth_Validator SHALL return a ValidationError with error_type "missing_auth_schemes"
2. WHEN a schema has unprotected endpoints, THE Auth_Validator SHALL return a ValidationError with error_type "unprotected_endpoint" for each unprotected endpoint
3. WHEN a schema has missing authentication, THE best_practices_score SHALL be reduced
4. WHEN a schema has missing authentication, THE APIObservation SHALL include suggestions for adding security schemes

### Requirement 19: Error Handling for Incorrect HTTP Methods

**User Story:** As a validation system, I want to detect incorrect HTTP method usage, so that agents learn RESTful conventions.

#### Acceptance Criteria

1. WHEN a schema uses POST for retrieval operations, THE Best_Practices_Checker SHALL return a ValidationError with error_type "incorrect_http_method"
2. WHEN a schema uses GET for creation operations, THE Best_Practices_Checker SHALL return a ValidationError with error_type "incorrect_http_method"
3. WHEN a schema has incorrect HTTP methods, THE best_practices_score SHALL be reduced
4. WHEN a schema has incorrect HTTP methods, THE APIObservation SHALL include suggestions for correct HTTP methods

### Requirement 20: Error Handling for Incomplete Documentation

**User Story:** As a validation system, I want to detect incomplete documentation, so that agents learn to document their APIs thoroughly.

#### Acceptance Criteria

1. WHEN a schema lacks operation descriptions, THE Best_Practices_Checker SHALL return a ValidationError with error_type "incomplete_documentation"
2. WHEN a schema lacks parameter documentation, THE Best_Practices_Checker SHALL return a ValidationError with error_type "incomplete_documentation"
3. WHEN a schema has incomplete documentation, THE best_practices_score SHALL be reduced
4. WHEN a schema has incomplete documentation, THE APIObservation SHALL include a checklist of missing documentation

### Requirement 21: Performance - Reset Latency

**User Story:** As a performance-conscious system, I want reset operations to complete quickly, so that training episodes can start without delay.

#### Acceptance Criteria

1. WHEN reset() is called, THE APIEnvironment SHALL complete within 100ms
2. WHEN reset() is called, THE APIEnvironment SHALL not perform unnecessary I/O operations
3. WHEN reset() is called, THE APIEnvironment SHALL initialize state efficiently without blocking

### Requirement 22: Performance - Step Latency

**User Story:** As a performance-conscious system, I want step operations to complete quickly, so that agents can iterate rapidly.

#### Acceptance Criteria

1. WHEN step() is called, THE APIEnvironment SHALL complete within 500ms
2. WHEN step() is called, THE ValidationPipeline SHALL complete within 400ms
3. WHEN step() is called, THE Reward_Calculator SHALL complete within 50ms
4. WHEN step() is called, THE APIEnvironment SHALL not perform unnecessary I/O operations

### Requirement 23: Performance - State Retrieval Latency

**User Story:** As a performance-conscious system, I want state retrieval to be fast, so that agents can query state without overhead.

#### Acceptance Criteria

1. WHEN state() is called, THE APIEnvironment SHALL complete within 50ms
2. WHEN state() is called, THE APIEnvironment SHALL return the current state without recomputation

### Requirement 24: Performance - Concurrent Agent Support

**User Story:** As a scalable system, I want to support multiple concurrent agents, so that training can be parallelized.

#### Acceptance Criteria

1. WHEN 10 agents connect concurrently, THE APIEnvironment SHALL handle all connections without degradation
2. WHEN 10 agents call step() concurrently, THE APIEnvironment SHALL process all requests within 500ms each
3. WHEN 10 agents are active, THE system SHALL maintain <100ms latency for each operation

### Requirement 25: Performance - Schema Size Limits

**User Story:** As a resource-conscious system, I want to limit schema size, so that I can prevent DoS attacks and resource exhaustion.

#### Acceptance Criteria

1. WHEN a schema exceeds 100KB, THE ValidationPipeline SHALL reject it with error_type "schema_too_large"
2. WHEN a schema exceeds 100KB, THE APIObservation SHALL have validity_score = 0.0
3. WHEN a schema exceeds 100KB, THE reward SHALL be -0.2

### Requirement 26: Security - Input Sanitization

**User Story:** As a secure system, I want to sanitize all inputs, so that I can prevent injection attacks.

#### Acceptance Criteria

1. WHEN an APIAction is received, THE APIEnvironment SHALL validate schema_json is a valid JSON string
2. WHEN an APIAction is received, THE APIEnvironment SHALL validate iteration is a non-negative integer
3. WHEN an APIAction is received, THE APIEnvironment SHALL validate metadata is a serializable dictionary
4. WHEN an APIAction contains invalid data, THE APIEnvironment SHALL return an error without processing

### Requirement 27: Security - Session Isolation

**User Story:** As a secure system, I want to isolate agent sessions, so that agents cannot access each other's data.

#### Acceptance Criteria

1. WHEN an agent connects, THE APIEnvironment SHALL create a unique session identifier
2. WHEN an agent submits an action, THE APIEnvironment SHALL verify the session identifier matches
3. WHEN an agent calls state(), THE APIEnvironment SHALL return only that agent's state
4. WHEN an agent calls reset(), THE APIEnvironment SHALL only reset that agent's episode

### Requirement 28: Security - Rate Limiting

**User Story:** As a secure system, I want to rate-limit requests, so that I can prevent abuse.

#### Acceptance Criteria

1. WHEN an agent sends more than 100 requests per minute, THE FastAPI_App SHALL rate-limit subsequent requests
2. WHEN an agent is rate-limited, THE FastAPI_App SHALL return HTTP 429 Too Many Requests
3. WHEN an agent is rate-limited, THE rate limit SHALL reset after 1 minute

### Requirement 29: Deterministic Validation

**User Story:** As a reliable system, I want validation to be deterministic, so that the same schema always produces the same result.

#### Acceptance Criteria

1. WHEN the same schema is validated twice, THE ValidationPipeline SHALL return identical ValidationResult objects
2. WHEN the same schema is validated twice, THE Reward_Calculator SHALL return identical reward values
3. WHEN the same schema is validated twice, THE APIObservation SHALL be identical

### Requirement 30: Reward Boundedness

**User Story:** As a well-designed reward system, I want rewards to be bounded, so that agents can learn stable policies.

#### Acceptance Criteria

1. WHEN any schema is validated, THE Reward_Calculator SHALL return a reward in the range [-0.2, 1.0]
2. WHEN validity_score is 0.0, THE reward SHALL be at least -0.2
3. WHEN validity_score is 1.0 and best_practices_score is 1.0 and error_count is 0, THE reward SHALL be exactly 1.0

### Requirement 31: Error Count Consistency

**User Story:** As a consistent system, I want error counts to match error lists, so that agents receive accurate feedback.

#### Acceptance Criteria

1. WHEN an APIObservation is created, THE error_count SHALL equal the length of validation_errors
2. WHEN an APIObservation is created, THE error_count SHALL never be negative
3. WHEN validation_errors is empty, THE error_count SHALL be 0

### Requirement 32: Score Range Validation

**User Story:** As a well-defined system, I want scores to be in valid ranges, so that agents can interpret feedback correctly.

#### Acceptance Criteria

1. WHEN an APIObservation is created, THE validity_score SHALL be in the range [0.0, 1.0]
2. WHEN an APIObservation is created, THE best_practices_score SHALL be in the range [0.0, 1.0]
3. WHEN a ValidationResult is created, THE validity_score SHALL be in the range [0.0, 1.0]
4. WHEN a ValidationResult is created, THE best_practices_score SHALL be in the range [0.0, 1.0]

### Requirement 33: State Immutability

**User Story:** As a reliable system, I want previous states to remain immutable, so that agents can trust historical data.

#### Acceptance Criteria

1. WHEN a new step() is called, THE previous APIState in history SHALL not be modified
2. WHEN a new step() is called, THE previous schema_history entries SHALL not be modified
3. WHEN a new step() is called, THE previous error_history entries SHALL not be modified

### Requirement 34: Cumulative Reward Tracking

**User Story:** As a tracking system, I want to accumulate rewards across steps, so that agents can see their total performance.

#### Acceptance Criteria

1. WHEN step() is called, THE total_reward in APIState SHALL be incremented by the step reward
2. WHEN reset() is called, THE total_reward in APIState SHALL be reset to 0.0
3. WHEN multiple steps are taken, THE total_reward SHALL equal the sum of all step rewards

### Requirement 35: Validation Error Completeness

**User Story:** As a helpful system, I want validation errors to be complete, so that agents can understand and fix issues.

#### Acceptance Criteria

1. WHEN a ValidationError is created, THE error_type SHALL be from a predefined set (e.g., "invalid_json", "missing_auth_schemes", "incorrect_http_method")
2. WHEN a ValidationError is created, THE severity SHALL be one of: "critical", "warning", "info"
3. WHEN a ValidationError is created, THE path SHALL be a valid JSON path or empty string
4. WHEN a ValidationError is created, THE message SHALL be a non-empty, human-readable string
5. WHEN a ValidationError is created, THE suggestion SHALL be a non-empty, actionable string

### Requirement 36: Business Requirement Persistence

**User Story:** As a stateful system, I want to maintain the business requirement throughout an episode, so that agents can reference it.

#### Acceptance Criteria

1. WHEN reset() is called, THE APIState SHALL include the business_requirement
2. WHEN step() is called, THE APIState SHALL include the same business_requirement as the reset
3. WHEN state() is called, THE APIState SHALL include the business_requirement

### Requirement 37: Metadata Tracking

**User Story:** As a tracking system, I want to record metadata with actions, so that I can analyze agent behavior.

#### Acceptance Criteria

1. WHEN an APIAction is submitted, THE metadata field SHALL be preserved in the state
2. WHEN an APIAction is submitted, THE metadata SHALL be serializable to JSON
3. WHEN an APIAction is submitted, THE metadata SHALL not affect validation or reward calculation

### Requirement 38: Episode Information Reporting

**User Story:** As an informative system, I want to report episode information, so that agents can understand episode context.

#### Acceptance Criteria

1. WHEN step() is called, THE APIObservation SHALL include episode_info with current episode metadata
2. WHEN episode_done is True, THE episode_info SHALL include final episode statistics
3. WHEN episode_done is True, THE episode_info SHALL include the reason for termination (max iterations or perfect schema)

### Requirement 39: Validation Stage Reporting

**User Story:** As a diagnostic system, I want to report per-stage validation results, so that developers can debug validation issues.

#### Acceptance Criteria

1. WHEN validation completes, THE ValidationResult SHALL include validation_stages dictionary
2. WHEN validation completes, THE validation_stages SHALL contain results from all pipeline stages
3. WHEN validation completes, THE validation_stages SHALL indicate which stages passed and which failed

### Requirement 40: Timestamp Recording

**User Story:** As a time-aware system, I want to record validation timestamps, so that I can analyze validation performance.

#### Acceptance Criteria

1. WHEN validation completes, THE ValidationResult SHALL include a timestamp field
2. WHEN validation completes, THE timestamp SHALL be the Unix timestamp when validation occurred
3. WHEN validation completes, THE timestamp SHALL be a finite number


### Requirement 41: Baseline Inference Script

**User Story:** As a hackathon participant, I want a baseline inference script that uses OpenAI API, so that I can establish a reproducible baseline score on all tasks.

#### Acceptance Criteria

1. WHEN the inference script is executed, THE script SHALL be named `inference.py` and placed in the root directory
2. WHEN the inference script is executed, THE script SHALL read API_BASE_URL from environment (default: participant's active endpoint)
3. WHEN the inference script is executed, THE script SHALL read MODEL_NAME from environment (default: participant's active model)
4. WHEN the inference script is executed, THE script SHALL read HF_TOKEN or API_KEY from environment
5. WHEN the inference script is executed, THE script SHALL read IMAGE_NAME from environment for docker image initialization
6. WHEN the inference script is executed, THE script SHALL use OpenAI Client for all LLM calls
7. WHEN the inference script starts an episode, THE script SHALL emit exactly one [START] line: `[START] task=<task_name> env=<benchmark> model=<model_name>`
8. WHEN the inference script calls env.step(), THE script SHALL emit exactly one [STEP] line: `[STEP] step=<n> action=<action_str> reward=<0.00> done=<true|false> error=<msg|null>`
9. WHEN the inference script completes, THE script SHALL emit exactly one [END] line: `[END] success=<true|false> steps=<n> score=<0.000> rewards=<r1,r2,...,rn>`
10. WHEN the inference script emits [STEP] lines, THE reward SHALL be formatted to 2 decimal places
11. WHEN the inference script emits [END] line, THE score SHALL be formatted to 3 decimal places and rewards to 2 decimal places
12. WHEN the inference script emits [STEP] or [END] lines, THE done and success SHALL be lowercase booleans (true or false)
13. WHEN the inference script emits [STEP] lines, THE error SHALL be the raw error string or "null" if none
14. WHEN the inference script emits stdout, ALL fields SHALL be on a single line with no newlines within a line
15. WHEN the inference script completes (even on exception), THE [END] line SHALL always be emitted
16. WHEN the inference script calculates score, THE score SHALL be normalized to range [0.0, 1.0]
17. WHEN the inference script determines success, THE success SHALL be true if score >= SUCCESS_SCORE_THRESHOLD

### Requirement 42: Task Grading System

**User Story:** As a hackathon evaluation system, I want programmatic task graders, so that I can objectively score agent performance.

#### Acceptance Criteria

1. WHEN an episode completes, THE environment SHALL evaluate performance on at least 3 distinct tasks
2. WHEN a task is evaluated, THE grader SHALL return a score in the range [0.0, 1.0]
3. WHEN a task is evaluated, THE grader SHALL have clear, deterministic success/failure criteria
4. WHEN all tasks are evaluated, THE environment SHALL return an aggregate score across all tasks
5. WHEN tasks are defined, THE tasks SHALL range from easy to hard difficulty
6. WHEN tasks are defined, THE tasks SHALL represent real-world API design scenarios (e.g., e-commerce API, authentication system, data analytics API)

### Requirement 43: Real-World Task Simulation

**User Story:** As a hackathon environment, I want to simulate real-world API design tasks, so that agents learn practical skills.

#### Acceptance Criteria

1. WHEN reset() is called, THE environment SHALL select from a pool of real-world business requirements
2. WHEN a business requirement is selected, THE requirement SHALL represent actual human tasks (not games or toys)
3. WHEN a business requirement is selected, THE requirement SHALL include examples such as: library management API, e-commerce checkout API, user authentication system, data analytics API, scheduling system, content moderation API
4. WHEN a business requirement is selected, THE requirement SHALL specify functional requirements, security requirements, and expected endpoints
