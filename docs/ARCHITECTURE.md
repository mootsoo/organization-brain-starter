# Technical Architecture

## Design goal

Use the smallest understandable architecture that demonstrates an end-to-end controlled AI workflow. No queues, no agents, no orchestration layer, no vector database.

## Components

| Component | Technology | Responsibility |
|---|---|---|
| Web | Next.js 16 (App Router, JavaScript) | Mongolian leadership and reviewer interface |
| API | FastAPI | Workflow endpoints, rule evaluation, AI gateway, approval boundary |
| Rules | `apps/api/app/rules.py` | Deterministic checks computed from database rows |
| Database | PostgreSQL 16 | Structured facts, decisions, audit events |
| AI gateway | `apps/api/app/ai.py` | Mock generation or an OpenAI-compatible API call |
| Runtime | Docker Compose | Local three-service deployment with health checks |

## Request flow

```text
Browser
  → Next.js server component
  → FastAPI endpoint
  → parameterized SQL query (facts)
  → rules.evaluate(tender, submissions)   [pure Python, no model]
  → build_model_input(context)            [minimized: no row ids, no
                                           document pointers, no source_reference]
  → AI gateway, for draft prose only
  → decision stored with status = 'draft'
  → separate human approval endpoint
  → audit event
```

## Where the boundaries are enforced

| Boundary | Enforced in |
|---|---|
| The model never sees a database credential or issues SQL | `app/ai.py` receives a plain dict only |
| The model receives only the facts needed for the draft, with no row identifier, document pointer or `source_reference` string | `build_model_input` in `app/ai.py` |
| Rule results cannot be produced or altered by the model | `app/rules.py` runs before the model and its output is returned to the caller unchanged |
| Generation cannot approve | `POST /draft-summary` always inserts `status = 'draft'` and never touches `tenders.stage` |
| Approval is a separate authorized action | `POST /approve` requires the `approver` demo role and an explicit `decision_id` |
| A draft can be approved only once, even under simultaneous requests | one conditional `UPDATE ... WHERE status = 'draft' RETURNING ...` is the authority; a `None` result raises 409 and rolls the transaction back |
| Every important action is recorded | `record_audit` writes action, actor, actor role, target, metadata and time |
| Provider failures stay recoverable | `ProviderError` is mapped to HTTP 502 with a message that never contains a key or a raw provider body |

### What the model input contains

`build_model_input` in `app/ai.py` is the only place a provider payload is assembled.

| Sent to the provider | Never sent |
|---|---|
| tender code, title, budget, `min_technical_score`, `min_bidders` | `tenders.id`, `tender_submissions.id`, `decisions.id` |
| per-bidder organization name, proposed amount, document and tax flags, technical score | `evidence_reference` (a document pointer) |
| each finding's `rule_id`, `severity` and Mongolian `message_mn` | each finding's `source_reference` (`tender_submissions #<id> · <column> · <document>`) |
| the list of rule identifiers that ran | decision history and audit events |

Excluding `source_reference` does not reduce human traceability. It is still
computed by `app/rules.py`, returned by `GET /api/v1/tenders/{id}`, displayed
under every finding in the interface, and stored with the draft in
`decisions.source_snapshot`.

## Data model

`tenders` and `tender_submissions` hold **facts**. Rule results are **not** stored;
they are recomputed from the same rows on every request, so any reviewer can
reproduce them by hand. `decisions` holds AI prose plus its approval state. `source_snapshot` records
both `model_input` (exactly what the provider was given) and `rule_findings`
(the full human-facing evidence, including the source references that are kept
out of the model input). `audit_events` holds the history.

Rule thresholds (`budget_mnt`, `min_technical_score`, `min_bidders`) live on the
tender row, so policy can change without a code change.

## API surface

| Method | Path | Demo role | Purpose |
|---|---|---|---|
| GET | `/health` | — | Liveness, database state, active AI provider |
| GET | `/api/v1/overview` | — | Dashboard metrics and workflow list |
| GET | `/api/v1/tenders/{id}` | — | Facts, rule checks, findings, decisions, recent audit |
| GET | `/api/v1/tenders/{id}/audit` | — | Full audit trail with Mongolian labels |
| POST | `/api/v1/tenders/{id}/draft-summary` | `reviewer` or `approver` | Create an AI draft. Never approves. |
| POST | `/api/v1/tenders/{id}/approve` | `approver` | Explicit human approval of one draft |

## AI provider interface

Version 1 implements two modes behind one `generate_tender_summary(model_input)` interface:

- `mock` — deterministic local output. No network, no API key. The same input always produces the same text, which keeps demonstrations and tests predictable.
- `openai-compatible` — a single HTTP request to a chat-completions endpoint, with a bounded timeout (`AI_TIMEOUT_SECONDS`, default 30 seconds).

Additional providers should be added as small adapters behind the same interface.

## Timeouts

| Call | Setting | Default |
|---|---|---|
| Database connect | `DB_CONNECT_TIMEOUT` | 5s |
| AI provider request | `AI_TIMEOUT_SECONDS` | 30s |
| Next.js server-side API fetch | `API_TIMEOUT_MS` | 8000ms |

## CORS

`CORS_ORIGINS` defaults to `http://localhost:3000`. Credentials are disabled, only `GET` and `POST` are allowed, and only `Content-Type` and `X-Role` headers are accepted. Widen this deliberately, per deployment.

## Role boundary

The demonstration approval endpoint requires `X-Role: approver`. **This is not authentication.** It proves that the application has a boundary and shows where verified identity claims must be connected. Anyone who can reach the API can set the header.

## Why no RAG

The first workflow uses structured tender records, explicit rules, and selected source references. SQL and ordinary application logic are sufficient and are easier to audit. Retrieval should be introduced only when a validated use case requires searching a large unstructured document collection, and only when indexing, access filtering, citation quality, and evaluation can be governed.

## Testing

| File | Needs a database | Covers |
|---|---|---|
| `tests/test_rules.py` | no | Rule arithmetic, source references, thresholds |
| `tests/test_ai.py` | no | Mock determinism, draft marker, recursive data-minimization checks over the complete payload and over the outbound HTTP body, provider errors |
| `tests/test_api.py` | yes (skips otherwise) | Health, listing, detail, mock draft, no implicit approval, wrong-role rejection, authorized approval, audit records, and competing approvals (exactly one 200, one 409, one audit event) |
| `scripts/smoke.sh` | running stack | The same workflow through HTTP, including the web pages |

## Production extension points

- identity provider and single sign-on to replace `X-Role`;
- organization-specific workflow states and rule sets;
- rules stored as governed configuration rather than code;
- document storage, virus scanning, and source links;
- approved model providers or locally hosted models;
- secrets management and encryption at rest;
- observability, retention, and export controls; and
- integration with existing procurement systems.
