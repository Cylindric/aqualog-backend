## Purpose

Define how pytest HTML test results are generated and served for browser access.

## Requirements

### Requirement: Pytest HTML report artifacts are generated to a browsable directory
The system SHALL generate pytest test result artifacts as HTML files in a stable output directory suitable for static hosting.

#### Scenario: Test task writes HTML report
- **WHEN** the designated pytest report task is executed
- **THEN** an HTML report file named `index.html` is written to the configured report output directory

#### Scenario: Report assets are colocated with HTML output
- **WHEN** the HTML report is generated with supporting assets
- **THEN** all required files are stored under the same browsable report directory tree

### Requirement: Test report directory is served at `/tests`
The running service SHALL expose the test report directory at URL path `/tests` for browser access.

#### Scenario: Tests route is enabled for development and test environments
- **WHEN** the service runs with `app_env` set to `dev` or `test`
- **THEN** `/tests` is mounted and serves report content from the configured report directory

#### Scenario: Tests route is disabled outside development and test environments
- **WHEN** the service runs with `app_env` set to an environment other than `dev` or `test`
- **THEN** `/tests` is not mounted

#### Scenario: Tests route serves generated report content
- **WHEN** a client requests `/tests` or a file under `/tests`
- **THEN** the server responds with static report content from the configured report directory

#### Scenario: Missing report files return not found
- **WHEN** a requested report file does not exist in the report directory
- **THEN** the server returns a not-found response

### Requirement: Serving reports does not alter API response contracts
Serving test artifacts MUST NOT change established JSON envelope behavior of existing API endpoints.

#### Scenario: Existing API health endpoints remain unchanged
- **WHEN** health endpoints are requested after adding `/tests` static serving
- **THEN** they continue returning the same status behavior and JSON envelope format
