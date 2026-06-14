## ADDED Requirements

### Requirement: Agent context memory
The system SHALL maintain a separate memory file for each of the 7 Agents (wyg-space/memory/pm-memory.yaml through te-memory.yaml). Each memory file SHALL store: user input, upstream Agent output, and the Agent's own response. Memory SHALL persist across sessions.

#### Scenario: Memory written after Agent execution
- **WHEN** PM completes task decomposition for a user request
- **THEN** PM memory file SHALL be updated with the user input and PM's decomposition output

#### Scenario: Memory read before Agent execution
- **WHEN** BA begins requirement analysis
- **THEN** BA SHALL read its own memory file for relevant past context, including PM's output for the current request

### Requirement: Shared error memory
The system SHALL maintain a shared error memory directory (wyg-space/memory/errors/). Each error memory file SHALL contain: who (discovering Agent), stage (where exposed), rollback_to (target Agent), error description, reason, lesson, and timestamp. Error memory files SHALL be named with pattern: {AGENT}-{date}-{sequence}.yaml.

#### Scenario: Error memory file naming
- **WHEN** TE discovers an error on 2026-06-14
- **THEN** the error memory file SHALL be named TE-2026-06-14-001.yaml

#### Scenario: Error memory content structure
- **WHEN** an error memory file is created
- **THEN** it SHALL contain fields: who, stage, rollback_to, error, reason, lesson, timestamp

### Requirement: Error memory consultation
All Agents SHALL consult relevant error memories before and during execution. When an Agent is the target of a rollback, it SHALL read all error memories that reference it as rollback_to target.

#### Scenario: Rollback target reads error memory
- **WHEN** DEV is rolled back to from TE
- **THEN** DEV SHALL read all error memories where rollback_to=DEV to understand what went wrong and avoid repeating mistakes
