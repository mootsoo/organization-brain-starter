# Governance and Safety

## Decision boundary

AI output is advisory. It may organize evidence, identify inconsistencies, and prepare draft language. The authorized human body remains responsible for evaluation, scoring, justification, approval, and legal accountability.

## Required controls, and where each one is implemented

| # | Control | Implementation |
|---|---|---|
| 1 | **Source traceability** — every finding identifies its source record | `source_reference` on every finding in `app/rules.py`; shown under each finding in the interface |
| 2 | **Rule transparency** — deterministic checks stay visible and separate from AI prose | `app/rules.py` runs before the model; passing rules are displayed too, not only failures |
| 3 | **Human approval** — official status cannot change through AI generation alone | `POST /draft-summary` writes `status = 'draft'` only; `tenders.stage` is untouched |
| 4 | **Auditability** — generation and approval are recorded | `audit_events` rows with action, actor, actor role, target, metadata, timestamp |
| 5 | **Least privilege** — actions are role-bound | `require_role`; drafting and approving are different permissions |
| 6 | **Data minimization** — only necessary information reaches the model | `build_model_input` drops row identifiers and document pointers |
| 7 | **Provider control** — each deployment approves where data is processed | `AI_PROVIDER`, `AI_BASE_URL` are explicit configuration with a working offline default |
| 8 | **Safe failure** — provider errors do not leak configuration | `ProviderError` messages never include a key, a header, or a raw provider body |

## Prohibited Version 1 behaviour

- autonomous winner selection;
- hidden or unexplained scoring;
- unrestricted model access to the database;
- automatic publication of an AI draft;
- use of production personal or confidential data in the sample environment; and
- treating generated prose as verified evidence.

## What is deliberately weak in this starter

Naming these honestly is part of the governance story.

- **`X-Role` is not authentication.** It is a header any caller can set. It demonstrates that a boundary exists and marks the exact place an identity provider must be connected. Do not describe it as a security control.
- **Credentials in `.env.example` and `docker-compose.yml` are local demonstration defaults**, not secrets. They must be replaced before any shared deployment.
- **The rule set is small on purpose.** Real procurement policy is larger and must be reviewed and owned by the responsible officials.
- **There is no data retention, export, or deletion policy** in Phase 1.

## Demonstration warning

The sample database is fictional: every organization, official, bidder, amount, and document reference exists only to demonstrate the workflow. Do not use this repository unchanged for an official decision.
