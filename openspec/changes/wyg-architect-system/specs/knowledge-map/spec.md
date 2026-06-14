## ADDED Requirements

### Requirement: Knowledge map node storage
The system SHALL store knowledge nodes as individual YAML files under wyg-space/knowledge-map/nodes/. Each node file SHALL contain: id, type, description, created_at, and updated_at.

#### Scenario: Knowledge node file structure
- **WHEN** a new knowledge node "三叠泉" is created
- **THEN** a file wyg-space/knowledge-map/nodes/三叠泉.yaml SHALL be created with fields: id=三叠泉, type=scenic-spot, description, created_at, updated_at

### Requirement: Knowledge map relation storage
The system SHALL store knowledge relations as individual YAML files under wyg-space/knowledge-map/relations/. Each relation file SHALL be named with pattern: {from}-{relation_type}-{to}.yaml. Each relation file SHALL contain: from (id + type), to (id + type), relation type, confidence score, source (which Agent/output created this), created_at, and context.

#### Scenario: Relation file naming and structure
- **WHEN** AI infers a "part_of" relation from "三叠泉" to "庐山"
- **THEN** a file wyg-space/knowledge-map/relations/三叠泉-part_of-庐山.yaml SHALL be created with fields: from={id:三叠泉, type:scenic-spot}, to={id:庐山, type:scenic-area}, relation=part_of, confidence, source, created_at, context

### Requirement: AI-inferred relation creation
The system SHALL invoke AI to automatically infer relations between new knowledge and existing knowledge nodes whenever a new knowledge node is written. The AI SHALL extract core concepts from the new knowledge, match existing nodes, infer relation types, and write relation files.

#### Scenario: New knowledge triggers relation inference
- **WHEN** a new knowledge node "三叠泉需要爬2000级台阶" is written
- **THEN** the system SHALL invoke AI to scan existing nodes, infer relations (e.g., 三叠泉-requires-体力消耗, 三叠泉-part_of-庐山), and create corresponding relation files

### Requirement: Relation types
The system SHALL support the following relation types: part_of, depends_on, affects, refines, contradicts, exemplifies, generalizes, conflicts_with, requires, sequence. The list MAY be extended in the future.

#### Scenario: Error memory creates conflicts_with relation
- **WHEN** error memory records that "三叠泉 and 五老峰 cannot be scheduled on the same afternoon"
- **THEN** a relation file 三叠泉-conflicts_with-五老峰同日下午.yaml SHALL be created with source=te-error-memory

### Requirement: Knowledge map index
The system SHALL maintain an auto-generated index file (wyg-space/knowledge-map/index.yaml) that maps each node to its outgoing and incoming relation files. The index SHALL be updated automatically whenever a node or relation file is created or modified.

#### Scenario: Index updated on new relation
- **WHEN** a new relation file 三叠泉-requires-体力消耗.yaml is created
- **THEN** index.yaml SHALL be updated to list this file under 三叠泉's outgoing relations and 体力消耗's incoming relations

#### Scenario: Index query for node relations
- **WHEN** an Agent queries "what relations does 三叠泉 have?"
- **THEN** the system SHALL use index.yaml to quickly locate all outgoing and incoming relation files for 三叠泉
