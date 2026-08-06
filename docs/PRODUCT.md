# Product Definition

## Product name

Organization Brain Starter

## Product statement

A small reference application that connects organizational records, explicit workflow rules, an AI drafting service, human approval, and an audit trail.

It is a reference implementation for learning and adaptation. It is not a production-ready procurement platform.

## Primary users

- ministry and agency leaders;
- procurement and evaluation officers;
- department managers;
- internal IT teams; and
- implementation partners.

## Problem

Organizations often start AI initiatives by selecting a model or buying infrastructure. The operational problem appears earlier: records are fragmented, work is handled through messages and spreadsheets, rules are interpreted inconsistently, and official decisions are difficult to trace.

The starter addresses that gap with one controlled workflow rather than a broad chatbot.

## Version 1 use case

**AI-assisted tender evaluation**

The system:

1. stores tender and submission facts;
2. computes explicit checks from those facts;
3. shows both passing and failing checks, each finding with its source record;
4. prepares a draft summary in plain Mongolian;
5. requires a separate human approval action; and
6. records both actions in an audit log.

The system does not autonomously rank bidders or select a winner.

## Version 1 scope

Included:

- one minimal leadership dashboard;
- one fictional tender with three fictional bidders;
- structured tender and bidder data;
- five deterministic rules with visible source references;
- AI gateway with a deterministic mock mode and one OpenAI-compatible adapter;
- separate draft and approval actions with a demonstration role boundary;
- persistent audit records;
- PostgreSQL, FastAPI, Next.js, Docker Compose;
- unit tests, workflow tests, and an end-to-end smoke script;
- English technical documentation and a simple Mongolian leadership guide.

Not included:

- vector search or RAG;
- autonomous scoring or winner selection;
- production identity integration;
- document upload, storage, or OCR;
- the reporting workflow or the internal-request workflow (later phases);
- national data integration;
- workflow engines, queues, agents, or Kubernetes.

## Language policy

- Visible leadership and operational text: simple Mongolian.
- Technical terminology, code comments, architecture and API documentation, developer documentation: English.

## Core message

> AI шийдвэр гаргахгүй. Хүний шийдвэрийг илүү баримттай болгоно.

## Success criteria

A ministry IT team should be able to clone the repository, run one command, open the interface, follow the ten-step walkthrough in the README, and identify exactly where to connect its own database, rules, identity system, and AI provider.
