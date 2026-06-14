## ADDED Requirements

### Requirement: Agent pipeline execution order
The system SHALL execute 7 Agents in strict sequential order: PM → BA → SA → RR → DEV → CR → TE. Each Agent SHALL receive the output of the previous Agent as input. No Agent SHALL begin execution until the previous Agent has completed.

#### Scenario: Normal sequential execution
- **WHEN** user submits a request to WYG Architect
- **THEN** PM executes first, followed by BA, SA, RR, DEV, CR, and TE in order, each receiving the previous Agent's output

#### Scenario: Pipeline completion
- **WHEN** TE completes execution and passes all tests
- **THEN** WYG Architect SHALL collect all 7 Agent outputs and return the consolidated result to the user

### Requirement: Pipeline rollback on test failure
The system SHALL support rollback when TE or CR identifies a failure. The discovering Agent SHALL determine which stage to roll back to based on the nature of the failure. The rollback target Agent SHALL receive the error memory as context to avoid repeating the same mistake.

#### Scenario: TE discovers content error
- **WHEN** TE finds a content or implementation error during testing
- **THEN** TE SHALL roll back to DEV with error memory, and DEV SHALL re-execute with awareness of the error

#### Scenario: TE discovers design flaw
- **WHEN** TE finds that the design or architecture is fundamentally flawed
- **THEN** TE SHALL roll back to SA with error memory, and the pipeline SHALL re-execute from SA

#### Scenario: CR discovers quality issue
- **WHEN** CR identifies code quality or accuracy issues
- **THEN** CR SHALL roll back to DEV with error memory for rework

### Requirement: Error memory recording
The system SHALL record error memory for every rollback event. Error memory SHALL include: who discovered the error, which stage exposed it, rollback target, error description, reason, lesson learned, and timestamp. Error memory SHALL be stored in a shared errors/ directory accessible to all Agents.

#### Scenario: Error memory created on rollback
- **WHEN** a rollback occurs from TE to DEV due to scheduling conflict
- **THEN** an error memory file SHALL be created in memory/errors/ with fields: who=TE, stage=DEV→CR→TE, rollback_to=DEV, error description, reason, lesson, and timestamp

#### Scenario: Error memory consulted during re-execution
- **WHEN** DEV re-executes after a rollback
- **THEN** DEV SHALL read relevant error memories to avoid repeating the same mistakes

### Requirement: WYG Architect god view
The system SHALL provide a WYG Architect god view layer that receives user requests, dispatches them to PM, and collects all 7 Agent outputs to return to the user. WYG Architect rule is placeholder for future definition.

#### Scenario: Request dispatch and collection
- **WHEN** user submits a request
- **THEN** WYG Architect dispatches to PM, waits for all 7 Agents to complete (or rollback and re-execute), and returns consolidated output to user
