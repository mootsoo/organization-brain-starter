# Organization Brain Starter

A small, working reference system for connecting organizational data, workflows, rules, AI APIs, and human approval.

The project is designed for government agencies, ministries, state-owned enterprises, NGOs, and companies that want a practical starting point instead of a large “AI transformation” programme.

> AI is not the organization’s brain. Verified data, rules, workflows, decisions, and institutional memory are the brain. AI is a controlled assistant on top of that foundation.

## What this starter solves

Many organizations already have databases, documents, and reporting duties. The missing layer is usually a simple operational workflow that can:

1. collect structured information;
2. apply transparent rules;
3. identify missing or inconsistent evidence;
4. prepare an AI-assisted draft;
5. require a human decision; and
6. preserve a complete audit trail.

The first demonstration workflow is **AI-assisted tender evaluation**. It does not automatically select a winner. It organizes evidence, runs explicit checks, flags issues, and drafts a review summary for an authorized person.

## Product principles

- **Solve one real workflow first.**
- **Keep the interface simple enough for a non-technical leader.**
- **Use normal database queries and rules before advanced AI techniques.**
- **AI may prepare, compare, summarize, and flag. Humans decide.**
- **Every important action must have a source and an audit record.**
- **No RAG or vector database in Version 1.**
- **Provider-neutral AI connection. Mock mode works without an API key.**

## Current demonstration

The starter currently includes:

- a clean Mongolian-language leadership dashboard;
- one sample tender with three fictional bidders;
- rule-based completeness and compliance findings;
- a provider-neutral AI gateway;
- AI-assisted Mongolian draft generation;
- a human approval endpoint with a visible role boundary;
- PostgreSQL storage and audit events; and
- Docker Compose for local startup.

All names and records in the demo database are fictional.

## Architecture

```text
Leader / Officer
       ↓
Minimal Next.js interface
       ↓
FastAPI application API
       ↓
Workflow rules + PostgreSQL
       ↓
AI provider gateway
       ↓
Mock provider or OpenAI-compatible API

Across the workflow:
source references · role boundary · human approval · audit log
```

## Quick start

### Requirements

- Docker Desktop or Docker Engine with Docker Compose

### Run

```bash
cp .env.example .env
docker compose up --build
```

Open:

- Web interface: `http://localhost:3000`
- API documentation: `http://localhost:8000/docs`
- API health: `http://localhost:8000/health`

The default configuration uses `AI_PROVIDER=mock`, so no external AI key is required.

## Connect an AI API

The first external adapter supports an OpenAI-compatible chat-completions endpoint. Set these values in `.env`:

```env
AI_PROVIDER=openai-compatible
AI_BASE_URL=https://api.example.com/v1
AI_API_KEY=replace-me
AI_MODEL=replace-me
```

The application sends only the structured tender facts and explicit findings needed for the draft. It does not give the model unrestricted database access.

## Repository map

```text
apps/web/              Minimal Next.js leadership interface
apps/api/              FastAPI workflow and AI gateway
database/init.sql      Schema and fictional demonstration data
docs/                  Product, architecture, governance, and roadmap
docker-compose.yml     Local three-service deployment
```

## Documentation

- [Product definition](docs/PRODUCT.md)
- [Technical architecture](docs/ARCHITECTURE.md)
- [Governance and safety](docs/GOVERNANCE.md)
- [Leadership guide in Mongolian](docs/LEADERSHIP_MN.md)
- [Implementation roadmap](docs/ROADMAP.md)

## Important limitation

The role header used by the demonstration approval action is intentionally simple and is **not production authentication**. A real deployment must connect the role boundary to the organization’s identity provider, access policy, and legal approval process.

## Status

This repository is at **Phase 1: working foundation**. The goal is not to build a national platform in one step. The goal is to prove one understandable workflow end to end, then add only what real users need.
