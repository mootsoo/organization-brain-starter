# Governance and Safety

## Decision boundary

AI output is advisory. It may organize evidence, identify inconsistencies, and prepare draft language. The authorized human body remains responsible for evaluation, scoring, justification, approval, and legal accountability.

## Required controls

1. **Source traceability**: every finding must identify its source record or document reference.
2. **Rule transparency**: deterministic checks must remain visible and separate from AI prose.
3. **Human approval**: official status cannot change through AI generation alone.
4. **Auditability**: generation and approval actions must be recorded.
5. **Least privilege**: users and integrations should receive only the access needed for their role.
6. **Data minimization**: send only necessary information to an external model.
7. **Provider control**: each deployment must explicitly approve where data may be processed.

## Prohibited Version 1 behavior

- autonomous winner selection;
- hidden or unexplained scoring;
- unrestricted model access to the database;
- automatic publication of an AI draft;
- use of production personal or confidential data in the sample environment; and
- treating generated prose as verified evidence.

## Demonstration warning

The sample database is fictional. The role header is a visible software boundary, not production authentication. Do not use the starter unchanged for official decisions.
