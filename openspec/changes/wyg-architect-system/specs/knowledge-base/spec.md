## ADDED Requirements

### Requirement: Knowledge base domain structure
The system SHALL organize knowledge into 7 domains under wyg-space/knowledge/: pm/, ba/, sa/, rr/, dev/, cr/, te/. Each domain SHALL contain a main document ({domain-name}.md) and a references/ subdirectory with cases.md, patterns.md, and signals.md.

#### Scenario: Knowledge domain file structure
- **WHEN** the knowledge base is initialized
- **THEN** each domain directory SHALL contain: {domain-name}.md (main document) and references/cases.md, references/patterns.md, references/signals.md

### Requirement: Knowledge base content for PM domain
The PM knowledge base SHALL contain project management methodology, risk case library, and milestone patterns.

#### Scenario: PM knowledge base content
- **WHEN** PM consults its knowledge base
- **THEN** PM SHALL find project management methodology in project-management.md, risk cases in references/cases.md, milestone patterns in references/patterns.md, and early warning signals in references/signals.md

### Requirement: Knowledge base content for BA domain
The BA knowledge base SHALL contain requirement analysis methodology, user story patterns, and acceptance criteria templates.

#### Scenario: BA knowledge base content
- **WHEN** BA consults its knowledge base
- **THEN** BA SHALL find requirement analysis methodology, user story patterns, and acceptance criteria templates

### Requirement: Knowledge base content for SA domain
The SA knowledge base SHALL contain architecture design methodology, architecture pattern library, and technology selection cases.

#### Scenario: SA knowledge base content
- **WHEN** SA consults its knowledge base
- **THEN** SA SHALL find architecture design methodology, architecture patterns, and technology selection cases

### Requirement: Knowledge base content for RR domain
The RR knowledge base SHALL contain readiness criteria definitions, review checklists, and historical review records.

#### Scenario: RR knowledge base content
- **WHEN** RR consults its knowledge base
- **THEN** RR SHALL find readiness criteria definitions, review checklists, and historical review records

### Requirement: Knowledge base content for DEV domain
The DEV knowledge base SHALL contain coding standards, best practices, and code templates.

#### Scenario: DEV knowledge base content
- **WHEN** DEV consults its knowledge base
- **THEN** DEV SHALL find coding standards, best practices, and code templates

### Requirement: Knowledge base content for CR domain
The CR knowledge base SHALL contain code review checklists, code smell library, and security vulnerability patterns.

#### Scenario: CR knowledge base content
- **WHEN** CR consults its knowledge base
- **THEN** CR SHALL find review checklists, code smell patterns, and security vulnerability patterns

### Requirement: Knowledge base content for TE domain
The TE knowledge base SHALL contain testing strategy library, defect pattern library, and test case design methodology.

#### Scenario: TE knowledge base content
- **WHEN** TE consults its knowledge base
- **THEN** TE SHALL find testing strategies, defect patterns, and test case design methodology
