## ADDED Requirements

### Requirement: PM rule definition
The system SHALL define a PM rule file (.codebuddy/rules/pm.mdc) that constrains PM behavior. PM rule SHALL include: task decomposition methodology (keyword extraction from user input), progress management, risk identification, and GitHub sync decision authority. PM rule SHALL enforce the hard constraint that every local update MUST be synced to GitHub.

#### Scenario: PM keyword decomposition
- **WHEN** PM receives user input "制作6月18日三天两夜的九江、南昌旅游攻略"
- **THEN** PM SHALL decompose keywords: "6月18日"(time constraint), "三天两夜"(duration), "九江"(destination1), "南昌"(destination2), "旅游"(task type), "攻略"(deliverable)

#### Scenario: PM GitHub sync enforcement
- **WHEN** any file in the WYG workspace is updated
- **THEN** PM SHALL ensure the update is synced to GitHub, with sync strategy determined by PM autonomously

### Requirement: BA rule definition
The system SHALL define a BA rule file (.codebuddy/rules/ba.mdc) that constrains BA behavior. BA rule SHALL include: requirement analysis methodology, acceptance criteria definition, and priority ranking.

#### Scenario: BA requirement analysis
- **WHEN** BA receives PM's task decomposition output
- **THEN** BA SHALL analyze requirements with acceptance criteria and priority ranking

### Requirement: SA rule definition
The system SHALL define a SA rule file (.codebuddy/rules/sa.mdc) that constrains SA behavior. SA rule SHALL include: architecture decision record (ADR) methodology, technology selection framework, interface design standards, and alternative solution provision.

#### Scenario: SA architecture design
- **WHEN** SA receives BA's requirement specification
- **THEN** SA SHALL produce architecture design with ADR, technology choices, and alternative solutions

### Requirement: RR rule definition
The system SHALL define a RR rule file (.codebuddy/rules/rr.mdc) that constrains RR behavior. RR rule SHALL include: readiness review checklist with hard constraints (execution speed, user friendliness) and placeholder constraints (performance, stability, power consumption). RR SHALL block pipeline progression if any hard constraint is not met.

#### Scenario: RR hard constraint check
- **WHEN** RR reviews SA's design output
- **THEN** RR SHALL check hard constraints: execution speed (product must execute fast) and user friendliness (product must be user-friendly)

#### Scenario: RR placeholder constraint
- **WHEN** RR encounters performance/stability/power consumption checks
- **THEN** RR SHALL mark these as placeholder (TBD) and not block pipeline progression

#### Scenario: RR blocks pipeline
- **WHEN** SA's design fails hard constraint check
- **THEN** RR SHALL roll back to SA with explanation of which constraint was not met

### Requirement: DEV rule definition
The system SHALL define a DEV rule file (.codebuddy/rules/dev.mdc) that constrains DEV behavior. DEV rule SHALL include: coding/content standards, module organization principles, and specification compliance.

#### Scenario: DEV implementation
- **WHEN** DEV receives RR-approved design
- **THEN** DEV SHALL implement according to coding standards and design specifications

### Requirement: CR rule definition
The system SHALL define a CR rule file (.codebuddy/rules/cr.mdc) that constrains CR behavior. CR rule SHALL include: review checklist, review opinion classification (must-fix/suggestion/approve), and accuracy verification.

#### Scenario: CR quality review
- **WHEN** CR receives DEV's implementation output
- **THEN** CR SHALL review for accuracy, completeness, logical coherence, and classify issues as must-fix, suggestion, or approve

### Requirement: TE rule definition
The system SHALL define a TE rule file (.codebuddy/rules/te.mdc) that constrains TE behavior. TE rule SHALL include: testing strategy, simulation execution methodology, problem identification, and rollback target recommendation.

#### Scenario: TE testing and rollback recommendation
- **WHEN** TE tests DEV's implementation and finds failures
- **THEN** TE SHALL identify the problem, recommend rollback target, and create error memory
