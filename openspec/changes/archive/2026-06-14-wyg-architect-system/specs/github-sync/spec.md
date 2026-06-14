## ADDED Requirements

### Requirement: GitHub sync hard constraint
The system SHALL enforce that every local update (rule, memory, knowledge, knowledge-map, file-map changes) MUST be synced to GitHub. PM SHALL be the sole decision-maker for sync strategy (timing, granularity, branching, commit message format).

#### Scenario: Knowledge update triggers sync
- **WHEN** a new knowledge node is written to wyg-space/knowledge-map/nodes/
- **THEN** PM SHALL ensure this change is synced to GitHub before proceeding

#### Scenario: Memory update triggers sync
- **WHEN** an Agent's memory file is updated
- **THEN** PM SHALL ensure this change is synced to GitHub

### Requirement: PM sync strategy autonomy
PM SHALL have full autonomy to decide: sync timing (real-time/batch/per-stage), commit granularity (single-file/per-feature/per-stage), branching strategy (main-push/feature-branch/per-agent-branch), commit message format, and conflict resolution approach. PM MAY update its sync strategy based on accumulated experience in PM memory.

#### Scenario: PM switches sync strategy
- **WHEN** PM observes that per-stage sync causes too many merge conflicts
- **THEN** PM MAY switch to real-time sync strategy and record this decision in PM memory

### Requirement: Sync notification
The system SHALL notify PM whenever a file change occurs in the WYG workspace. PM SHALL decide whether to sync immediately or batch.

#### Scenario: Knowledge map relation created
- **WHEN** a new relation file is created in wyg-space/knowledge-map/relations/
- **THEN** PM SHALL be notified and decide sync timing
