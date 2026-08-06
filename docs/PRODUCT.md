# Product Definition

## Product name

Organization Brain Starter

## Product statement

A small reference application that connects organizational records, explicit workflow rules, an AI drafting service, human approval, and an audit trail.

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
2. checks explicit requirements;
3. shows source-referenced findings;
4. prepares a draft summary in plain Mongolian;
5. requires a human approval action; and
6. records the action in an audit log.

The system does not autonomously rank bidders or select a winner.

## Version 1 scope

Included:

- minimal leadership dashboard;
- tender list and tender detail;
- structured submission comparison;
- rule findings;
- AI gateway with mock mode;
- draft and approval workflow;
- audit records;
- PostgreSQL schema; and
- Docker Compose deployment.

Not included:

- vector search or RAG;
- autonomous scoring;
- production identity integration;
- document OCR;
- national data integration;
- complex workflow engines; or
- multi-agent orchestration.

## Success criteria

A ministry IT team should be able to clone the repository, run one command, open the interface, understand the workflow, and identify where to connect its own database, rules, identity system, and AI provider.
