## ADDED Requirements

### Requirement: File map structure
The system SHALL maintain a file map at wyg-space/file-map/index.yaml that maps project files to the Agent(s) responsible for them. Each entry SHALL include: file path, responsible Agent, file description, and last updated timestamp.

#### Scenario: File map entry structure
- **WHEN** a new file wyg-space/knowledge/sa/architecture-design.md is created by SA
- **THEN** file-map/index.yaml SHALL contain an entry with path, agent=SA, description, and timestamp

### Requirement: File map query
Agents SHALL be able to query the file map to determine which Agent is responsible for a given file, or which files belong to a given Agent.

#### Scenario: Query by file path
- **WHEN** an Agent queries "who is responsible for architecture-design.md?"
- **THEN** the file map SHALL return Agent=SA

#### Scenario: Query by Agent
- **WHEN** an Agent queries "what files does DEV own?"
- **THEN** the file map SHALL return all files where agent=DEV

### Requirement: File map auto-update
The system SHALL automatically update the file map whenever a new file is created or an existing file's responsibility changes.

#### Scenario: New file triggers file map update
- **WHEN** a new file is created in the WYG workspace
- **THEN** the file map SHALL be updated with the new file's path, responsible Agent, description, and timestamp
