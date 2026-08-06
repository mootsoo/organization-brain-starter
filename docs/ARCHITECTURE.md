# Technical Architecture

## Design goal

Use the smallest understandable architecture that demonstrates an end-to-end controlled AI workflow.

## Components

| Component | Technology | Responsibility |
|---|---|---|
| Web | Next.js | Mongolian leadership and reviewer interface |
| API | FastAPI | Workflow endpoints, rule results, AI gateway, approval boundary |
| Database | PostgreSQL | Structured truth, findings, decisions, audit events |
| AI gateway | Python adapter | Mock generation or OpenAI-compatible API call |
| Runtime | Docker Compose | Local deployment and service wiring |

## Request flow

```text
Browser
  → Next.js page
  → FastAPI endpoint
  → parameterized SQL query
  → explicit tender context
  → AI gateway for draft only
  → human approval endpoint
  → audit event
```

## Data access rule

The model never receives a database credential and cannot issue arbitrary SQL. Application code selects the exact structured facts and findings that are sent to the model.

## AI provider interface

Version 1 implements two modes:

- `mock`: deterministic local output for demonstrations and testing;
- `openai-compatible`: HTTP request to a chat-completions compatible endpoint.

Additional providers should be implemented as small adapters behind the same `generate_tender_summary` interface.

## Role boundary

The demonstration approval endpoint requires `X-Role: approver`. This proves the application boundary but does not authenticate the person. Production deployments must replace it with validated identity claims from an identity provider.

## Why no RAG

The first workflow uses structured tender records, explicit findings, and selected source references. SQL and normal application logic are sufficient. RAG should be introduced only when a validated use case requires retrieval across a large unstructured document collection.

## Production extension points

- identity provider and single sign-on;
- organization-specific workflow states;
- rules stored as governed configuration;
- document storage and malware scanning;
- approved model providers or local models;
- encryption and secrets management;
- observability and retention controls; and
- integration with existing procurement systems.
