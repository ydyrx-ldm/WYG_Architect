## MODIFIED Requirements

### Requirement: Agent pipeline execution order
The system SHALL execute Agents based on the current opsx phase, with dynamic team formation: explore(BA★+SA), propose(SA★+PM+RR), apply(DEV★+CR+TE), archive(PM★). The `/WYG` command SHALL be the unified entry point that triggers the pipeline. Phases SHALL execute in strict serial order: explore → propose → apply → archive. Gates (RR, CR, TE) SHALL NOT be bypassed.

#### Scenario: /WYG triggers explore phase
- **WHEN** user inputs `/WYG` with an explore-intent requirement
- **THEN** BA (★ lead) and SA (support) SHALL execute, with BA producing the Requirements Exploration Summary and SA providing technical feasibility assessment

#### Scenario: /WYG triggers propose phase
- **WHEN** explore phase completes and user proceeds to propose
- **THEN** SA (★ lead), PM (support), and RR (gate) SHALL execute, with SA producing the proposal, PM producing tasks.md, and RR performing DoR check

#### Scenario: /WYG triggers apply phase
- **WHEN** propose phase completes and RR approves
- **THEN** DEV (★ lead), CR (gate), and TE (gate) SHALL execute in order: DEV implements → CR reviews → TE validates

#### Scenario: /WYG triggers archive phase
- **WHEN** apply phase completes and TE passes
- **THEN** PM (★ lead) SHALL execute archive: move change directory, sync specs, push to GitHub

#### Scenario: Normal sequential execution
- **WHEN** user submits a request via `/WYG`
- **THEN** the pipeline SHALL execute phases in order: explore → propose → apply → archive, with only the relevant Agents participating in each phase

#### Scenario: Pipeline completion
- **WHEN** TE completes execution and passes all tests
- **THEN** WYG Architect SHALL collect all Agent outputs and return the consolidated result to the user, then proceed to archive phase

### Requirement: Pipeline rollback on test failure
The system SHALL support rollback when TE, CR, or any Agent identifies a failure. The discovering Agent SHALL determine which stage to roll back to based on the nature of the failure. The rollback target Agent SHALL receive the error memory as context to avoid repeating the same mistake. The `/WYG` command SHALL support re-entering the pipeline at the rollback point.

#### Scenario: TE discovers content error
- **WHEN** TE finds a content or implementation error during testing
- **THEN** TE SHALL roll back to DEV with error memory, and DEV SHALL re-execute with awareness of the error

#### Scenario: TE discovers design flaw
- **WHEN** TE finds that the design or architecture is fundamentally flawed
- **THEN** TE SHALL roll back to SA with error memory, and the pipeline SHALL re-execute from SA

#### Scenario: CR discovers quality issue
- **WHEN** CR identifies code quality or accuracy issues
- **THEN** CR SHALL roll back to DEV with error memory for rework

#### Scenario: DEV discovers proposal infeasibility
- **WHEN** DEV finds the proposal is not feasible during implementation
- **THEN** DEV SHALL stop implementation and roll back to SA (propose phase) for re-evaluation

### Requirement: Error memory recording
The system SHALL record error memory for every rollback event. Error memory SHALL include: who discovered the error, which stage exposed it, rollback target, error description, reason, lesson learned, and timestamp. Error memory SHALL be stored in a shared errors/ directory accessible to all Agents.

#### Scenario: Error memory created on rollback
- **WHEN** a rollback occurs from TE to DEV due to scheduling conflict
- **THEN** an error memory file SHALL be created in memory/errors/ with fields: who=TE, stage=DEV→CR→TE, rollback_to=DEV, error description, reason, lesson, and timestamp

#### Scenario: Error memory consulted during re-execution
- **WHEN** DEV re-executes after a rollback
- **THEN** DEV SHALL read relevant error memories to avoid repeating the same mistakes

### Requirement: WYG Architect god view
The system SHALL provide a WYG Architect god view layer that receives user requests via the `/WYG` command, identifies intent, prints pipeline orchestration, routes to the correct phase, dispatches to corresponding Agents, and collects outputs to return to the user.

#### Scenario: Request dispatch and collection via /WYG
- **WHEN** user submits a request via `/WYG`
- **THEN** WYG Architect SHALL print orchestration table, dispatch to appropriate Agents, wait for phase completion (or rollback and re-execute), and return consolidated output to user
