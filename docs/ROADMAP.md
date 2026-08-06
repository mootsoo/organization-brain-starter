# Implementation Roadmap

## Phase 1 — Working foundation (this repository)

- runnable three-service stack with health checks;
- minimal Mongolian leadership dashboard;
- one fictional tender workflow, end to end;
- deterministic rules computed from structured facts, with source references;
- provider-neutral AI gateway with a working mock mode;
- separate human approval with a demonstration role boundary;
- persistent audit events;
- unit tests, workflow tests, an end-to-end smoke script, and CI.

## Phase 2 — Real organizational pilot

- select one partner organization and one workflow;
- map official data fields and approval roles;
- replace the demo role header with identity integration;
- import controlled sample records;
- define acceptance metrics; and
- run a supervised pilot.

## Phase 3 — Additional workflows

- the reporting workflow (monthly consolidation);
- the internal-request workflow (receive, route, decide);
- configurable workflow states and rule sets;
- document storage and source links; and
- organization-level permissions.

## Phase 4 — Operational controls

- model and prompt governance;
- retention, export, and deletion policies;
- monitoring, alerting, and incident procedures; and
- performance and cost controls.

## Phase 5 — Optional knowledge retrieval

Add full-text search first. Add RAG only when a proven workflow requires retrieval across a large body of unstructured documents and the organization can govern indexing, access filtering, citations, and evaluation quality.
