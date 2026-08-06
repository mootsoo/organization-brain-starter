import json
import os

import httpx
from typing import Annotated

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .ai import generated_at_iso, get_provider
from .db import connection


app = FastAPI(
    title="Organization Brain Starter API",
    version="0.1.0",
    description="Controlled workflow, AI drafting, human approval, and audit trail.",
)

allowed_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-Role"],
)


class ApprovalRequest(BaseModel):
    decision_id: int
    approved_by: str = Field(min_length=2, max_length=120)
    note: str = Field(default="Хянаж батлав.", max_length=500)


def require_role(actual_role: str | None, allowed_roles: set[str]) -> None:
    if actual_role not in allowed_roles:
        raise HTTPException(
            status_code=403,
            detail=f"This action requires one of these demo roles: {sorted(allowed_roles)}",
        )


def get_tender_context(tender_id: int) -> dict:
    with connection() as conn:
        tender = conn.execute(
            """
            SELECT id, code, title_mn, purpose_mn, owner_unit, status, stage,
                   budget_mnt, due_date, created_at
            FROM tenders
            WHERE id = %s
            """,
            (tender_id,),
        ).fetchone()
        if tender is None:
            raise HTTPException(status_code=404, detail="Tender not found")

        submissions = conn.execute(
            """
            SELECT id, organization_name, proposed_amount_mnt, documents_complete,
                   tax_compliant, technical_score, status
            FROM tender_submissions
            WHERE tender_id = %s
            ORDER BY proposed_amount_mnt ASC
            """,
            (tender_id,),
        ).fetchall()

        findings = conn.execute(
            """
            SELECT f.id, f.submission_id, s.organization_name, f.category,
                   f.severity, f.message_mn, f.source_reference
            FROM tender_findings f
            LEFT JOIN tender_submissions s ON s.id = f.submission_id
            WHERE f.tender_id = %s
            ORDER BY CASE f.severity WHEN 'attention' THEN 1 ELSE 2 END, f.id
            """,
            (tender_id,),
        ).fetchall()

    return {
        "tender": tender,
        "submissions": submissions,
        "findings": findings,
    }


@app.get("/health")
def health() -> dict:
    with connection() as conn:
        conn.execute("SELECT 1").fetchone()
    return {"status": "ok"}


@app.get("/api/v1/overview")
def overview() -> dict:
    with connection() as conn:
        metrics = conn.execute(
            """
            SELECT
              COUNT(*) FILTER (WHERE status = 'active') AS active_workflows,
              COUNT(*) FILTER (WHERE stage = 'human_review') AS waiting_review,
              COUNT(*) FILTER (WHERE stage = 'approved') AS approved_workflows
            FROM tenders
            """
        ).fetchone()

        tenders = conn.execute(
            """
            SELECT t.id, t.code, t.title_mn, t.owner_unit, t.status, t.stage,
                   t.budget_mnt, t.due_date,
                   COUNT(DISTINCT s.id) AS submission_count,
                   COUNT(DISTINCT f.id) FILTER (WHERE f.severity = 'attention') AS attention_count
            FROM tenders t
            LEFT JOIN tender_submissions s ON s.tender_id = t.id
            LEFT JOIN tender_findings f ON f.tender_id = t.id
            GROUP BY t.id
            ORDER BY t.created_at DESC
            """
        ).fetchall()

    return {
        "metrics": metrics,
        "workflow_steps": [
            "Мэдээлэл бүртгэх",
            "Дүрмээр шалгах",
            "AI төсөл бэлтгэх",
            "Хүн хянах",
            "Баталж, аудитад хадгалах",
        ],
        "tenders": tenders,
    }


@app.get("/api/v1/tenders/{tender_id}")
def tender_detail(tender_id: int) -> dict:
    context = get_tender_context(tender_id)
    with connection() as conn:
        decisions = conn.execute(
            """
            SELECT id, decision_type, status, content_mn, generated_by,
                   approved_by, approval_note, created_at, approved_at
            FROM decisions
            WHERE tender_id = %s
            ORDER BY created_at DESC
            LIMIT 10
            """,
            (tender_id,),
        ).fetchall()

        audit_events = conn.execute(
            """
            SELECT id, event_type, actor, details, created_at
            FROM audit_events
            WHERE tender_id = %s
            ORDER BY created_at DESC
            LIMIT 10
            """,
            (tender_id,),
        ).fetchall()

    return {**context, "decisions": decisions, "audit_events": audit_events}


@app.post("/api/v1/tenders/{tender_id}/draft-summary")
def create_draft_summary(
    tender_id: int,
    x_role: Annotated[str | None, Header()] = None,
) -> dict:
    require_role(x_role, {"reviewer", "approver"})
    context = get_tender_context(tender_id)
    provider = get_provider()

    try:
        summary = provider.generate_tender_summary(context)
    except (ValueError, httpx.HTTPError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    with connection() as conn:
        decision = conn.execute(
            """
            INSERT INTO decisions (
              tender_id, decision_type, status, content_mn, generated_by, source_snapshot
            )
            VALUES (%s, 'evaluation_summary', 'draft', %s, %s, %s::jsonb)
            RETURNING id, created_at
            """,
            (
                tender_id,
                summary,
                f"{provider.name}:{provider.model}",
                json.dumps(context, default=str, ensure_ascii=False),
            ),
        ).fetchone()
        conn.execute(
            """
            INSERT INTO audit_events (tender_id, event_type, actor, details)
            VALUES (%s, 'ai_draft_generated', %s, %s::jsonb)
            """,
            (
                tender_id,
                x_role,
                json.dumps(
                    {"provider": provider.name, "model": provider.model},
                    ensure_ascii=False,
                ),
            ),
        )

    return {
        "decision_id": decision["id"],
        "status": "draft",
        "summary_mn": summary,
        "provider": provider.name,
        "model": provider.model,
        "generated_at": generated_at_iso(),
    }


@app.post("/api/v1/tenders/{tender_id}/approve")
def approve_summary(
    tender_id: int,
    request: ApprovalRequest,
    x_role: Annotated[str | None, Header()] = None,
) -> dict:
    require_role(x_role, {"approver"})

    with connection() as conn:
        decision = conn.execute(
            """
            UPDATE decisions
            SET status = 'approved', approved_by = %s, approval_note = %s,
                approved_at = NOW()
            WHERE id = %s AND tender_id = %s AND status = 'draft'
            RETURNING id, status, approved_by, approval_note, approved_at
            """,
            (request.approved_by, request.note, request.decision_id, tender_id),
        ).fetchone()
        if decision is None:
            raise HTTPException(status_code=404, detail="Draft decision not found")

        conn.execute(
            "UPDATE tenders SET stage = 'approved' WHERE id = %s",
            (tender_id,),
        )
        conn.execute(
            """
            INSERT INTO audit_events (tender_id, event_type, actor, details)
            VALUES (%s, 'human_approval_recorded', %s, %s::jsonb)
            """,
            (
                tender_id,
                request.approved_by,
                json.dumps(
                    {"decision_id": request.decision_id, "note": request.note},
                    ensure_ascii=False,
                ),
            ),
        )

    return {"message": "Human approval recorded", "decision": decision}
