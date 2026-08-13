"""Organization Brain Starter API.

Workflow boundaries enforced in this module:

* Facts come from PostgreSQL through parameterized SQL.
* Rule findings are computed in `app.rules` and are never produced or modified
  by a language model.
* `POST /draft-summary` creates a `draft` decision only. It never changes the
  tender stage and never marks anything approved.
* `POST /approve` is a separate, explicit action restricted to the demo
  `approver` role. It is atomic: a single conditional UPDATE decides the
  transition, so two competing requests cannot both record an approval.
* Both actions write an audit event with action, actor, actor role, target,
  timestamp and metadata.

The `X-Role` header is a visible demonstration boundary, NOT production
authentication. A real deployment must replace it with verified identity
claims from an identity provider.
"""

import json
import os
from typing import Annotated

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from . import rules
from .ai import ProviderError, build_model_input, generated_at_iso, get_provider
from .db import connection


DEMO_ROLES = ("viewer", "reviewer", "approver")

# Leadership-facing text stays in Mongolian, so error messages name the demo
# roles in Mongolian rather than repeating the internal English identifiers.
ROLE_LABELS_MN = {
    "viewer": "ажиглагч",
    "reviewer": "хянагч",
    "approver": "батлах эрх бүхий хүн",
    "system": "систем",
}

TARGET_LABELS_MN = {
    "tender": "Тендер",
    "decision": "Шийдвэр",
}

AUDIT_LABELS_MN = {
    "tender_registered": "Тендер бүртгэгдсэн",
    "ai_draft_generated": "AI төсөл бэлтгэсэн",
    "human_approval_recorded": "Хүний баталгаажуулалт бүртгэгдсэн",
}

WORKFLOW_STEPS_MN = [
    "Мэдээлэл бүртгэх",
    "Дүрмээр шалгах",
    "AI төсөл бэлтгэх",
    "Хүн хянах",
    "Батлах, аудитад хадгалах",
]


app = FastAPI(
    title="Organization Brain Starter API",
    version="0.1.1",
    description=(
        "Controlled workflow, deterministic rule checks, AI drafting, human approval "
        "and an audit trail.\n\n"
        "**Demonstration boundary:** the `X-Role` header is not authentication. "
        "It exists to show where an identity provider must be connected."
    ),
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
    decision_id: int = Field(description="Identifier of the draft decision being approved.")
    approved_by: str = Field(min_length=2, max_length=120)
    note: str = Field(default="Хянаж баталлаа.", max_length=500)


def require_role(actual_role: str | None, allowed_roles: tuple[str, ...]) -> str:
    """Demonstration role boundary. Not production authentication."""
    if actual_role not in allowed_roles:
        labels = ", ".join(ROLE_LABELS_MN.get(role, role) for role in allowed_roles)
        raise HTTPException(
            status_code=403,
            detail=f"Энэ үйлдлийг гүйцэтгэх эрх алга. Шаардлагатай эрх: {labels}.",
        )
    return actual_role


def record_audit(
    conn,
    tender_id: int,
    event_type: str,
    actor: str,
    actor_role: str | None,
    target: str,
    details: dict,
) -> None:
    conn.execute(
        """
        INSERT INTO audit_events (tender_id, event_type, actor, actor_role, target, details)
        VALUES (%s, %s, %s, %s, %s, %s::jsonb)
        """,
        (
            tender_id,
            event_type,
            actor,
            actor_role,
            target,
            json.dumps(details, ensure_ascii=False, default=str),
        ),
    )


def load_tender(conn, tender_id: int) -> dict:
    tender = conn.execute(
        """
        SELECT id, code, title_mn, purpose_mn, owner_unit, status, stage,
               budget_mnt, min_technical_score, min_bidders, due_date, created_at
        FROM tenders
        WHERE id = %s
        """,
        (tender_id,),
    ).fetchone()
    if tender is None:
        raise HTTPException(status_code=404, detail="Тендер олдсонгүй.")
    return tender


def load_submissions(conn, tender_id: int) -> list[dict]:
    return conn.execute(
        """
        SELECT id, organization_name, proposed_amount_mnt, documents_complete,
               tax_compliant, technical_score, evidence_reference, status
        FROM tender_submissions
        WHERE tender_id = %s
        ORDER BY proposed_amount_mnt ASC
        """,
        (tender_id,),
    ).fetchall()


def get_tender_context(tender_id: int) -> dict:
    """Facts from the database plus rule results computed from those facts."""
    with connection() as conn:
        tender = load_tender(conn, tender_id)
        submissions = load_submissions(conn, tender_id)

    evaluation = rules.evaluate(tender, submissions)
    return {
        "tender": tender,
        "submissions": submissions,
        "checks": evaluation["checks"],
        "findings": evaluation["findings"],
        "attention_count": evaluation["attention_count"],
    }


def actor_label_mn(actor: str, actor_role: str | None) -> str:
    """Readable Mongolian actor name for the audit list.

    The stored `actor` value stays machine-truthful; this is presentation only.
    """
    if actor == "system":
        return "Систем"
    if actor.startswith("demo:"):
        role = ROLE_LABELS_MN.get(actor.split(":", 1)[1], actor.split(":", 1)[1])
        return f"Үзүүлэнгийн хэрэглэгч ({role})"
    return actor


def target_label_mn(target: str | None) -> str:
    """Turn a machine target such as `decision:2` into `Шийдвэр №2`."""
    if not target or ":" not in target:
        return target or "—"
    kind, identifier = target.split(":", 1)
    return f"{TARGET_LABELS_MN.get(kind, kind)} №{identifier}"


def decorate_audit_events(events: list[dict]) -> list[dict]:
    return [
        {
            **event,
            "label_mn": AUDIT_LABELS_MN.get(event["event_type"], event["event_type"]),
            "actor_label_mn": actor_label_mn(event["actor"], event.get("actor_role")),
            "actor_role_label_mn": ROLE_LABELS_MN.get(
                event.get("actor_role") or "", event.get("actor_role") or "—"
            ),
            "target_label_mn": target_label_mn(event.get("target")),
        }
        for event in events
    ]


@app.get("/health", tags=["system"])
def health() -> dict:
    """Liveness plus the configuration a demonstrator needs to trust the run."""
    provider = get_provider()
    try:
        with connection() as conn:
            conn.execute("SELECT 1").fetchone()
    except Exception as exc:  # noqa: BLE001 - surfaced as a safe generic message
        raise HTTPException(
            status_code=503,
            detail="The database is not available. Check that the db service is running.",
        ) from exc

    return {
        "status": "ok",
        "database": "ok",
        "ai_provider": provider.name,
        "ai_model": provider.model,
        "demo_auth": "X-Role header (demonstration only, not production authentication)",
        "sample_data": "fictional",
    }


@app.get("/api/v1/overview", tags=["workflow"])
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

        tender_rows = conn.execute(
            """
            SELECT id, code, title_mn, owner_unit, status, stage, budget_mnt,
                   min_technical_score, min_bidders, due_date
            FROM tenders
            ORDER BY created_at DESC
            """
        ).fetchall()

        tenders = []
        for tender in tender_rows:
            submissions = load_submissions(conn, tender["id"])
            tenders.append(
                {
                    **tender,
                    "submission_count": len(submissions),
                    "attention_count": rules.attention_count(tender, submissions),
                }
            )

    return {
        "metrics": metrics,
        "workflow_steps": WORKFLOW_STEPS_MN,
        "tenders": tenders,
    }


@app.get("/api/v1/tenders/{tender_id}", tags=["workflow"])
def tender_detail(tender_id: int) -> dict:
    context = get_tender_context(tender_id)
    with connection() as conn:
        decisions = conn.execute(
            """
            SELECT id, decision_type, status, content_mn, generated_by,
                   approved_by, approved_by_role, approval_note, created_at, approved_at
            FROM decisions
            WHERE tender_id = %s
            ORDER BY created_at DESC
            LIMIT 10
            """,
            (tender_id,),
        ).fetchall()

        audit_events = conn.execute(
            """
            SELECT id, event_type, actor, actor_role, target, details, created_at
            FROM audit_events
            WHERE tender_id = %s
            ORDER BY created_at DESC, id DESC
            LIMIT 20
            """,
            (tender_id,),
        ).fetchall()

    return {
        **context,
        "decisions": decisions,
        "audit_events": decorate_audit_events(audit_events),
    }


@app.get("/api/v1/tenders/{tender_id}/audit", tags=["audit"])
def tender_audit(tender_id: int) -> dict:
    with connection() as conn:
        load_tender(conn, tender_id)
        events = conn.execute(
            """
            SELECT id, event_type, actor, actor_role, target, details, created_at
            FROM audit_events
            WHERE tender_id = %s
            ORDER BY created_at DESC, id DESC
            """,
            (tender_id,),
        ).fetchall()

    return {"tender_id": tender_id, "audit_events": decorate_audit_events(events)}


@app.post("/api/v1/tenders/{tender_id}/draft-summary", tags=["workflow"])
def create_draft_summary(
    tender_id: int,
    x_role: Annotated[str | None, Header()] = None,
) -> dict:
    """Prepare an AI draft. This never approves anything and never changes the stage."""
    role = require_role(x_role, ("reviewer", "approver"))
    context = get_tender_context(tender_id)
    provider = get_provider()
    model_input = build_model_input(context)

    try:
        summary = provider.generate_tender_summary(model_input)
    except ProviderError as exc:
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
                json.dumps(
                    {
                        # Exactly what the provider received (minimized).
                        "model_input": model_input,
                        # Full human-facing evidence, including the
                        # `source_reference` that is deliberately kept out of
                        # the model input, so a reviewer can trace the draft.
                        "rule_findings": context["findings"],
                        "checks": context["checks"],
                    },
                    default=str,
                    ensure_ascii=False,
                ),
            ),
        ).fetchone()
        record_audit(
            conn,
            tender_id=tender_id,
            event_type="ai_draft_generated",
            actor=f"demo:{role}",
            actor_role=role,
            target=f"decision:{decision['id']}",
            details={
                "provider": provider.name,
                "model": provider.model,
                "rules_checked": len(context["checks"]),
                "attention_findings": context["attention_count"],
                "official": False,
            },
        )

    return {
        "decision_id": decision["id"],
        "status": "draft",
        "official": False,
        "summary_mn": summary,
        "provider": provider.name,
        "model": provider.model,
        "generated_at": generated_at_iso(),
        "note_mn": "Энэ бол төсөл. Албан ёсны шийдвэр болгохын тулд эрх бүхий хүн тусад нь батлана.",
    }


@app.post("/api/v1/tenders/{tender_id}/approve", tags=["workflow"])
def approve_summary(
    tender_id: int,
    request: ApprovalRequest,
    x_role: Annotated[str | None, Header()] = None,
) -> dict:
    """Explicit human approval. Only this endpoint can make a draft official."""
    role = require_role(x_role, ("approver",))

    with connection() as conn:
        # The conditional UPDATE is the only authority on this transition.
        # Two competing requests can both observe `status = 'draft'`, so the
        # database decides: exactly one UPDATE can match the row while it is
        # still a draft, and the losing request gets no row back.
        decision = conn.execute(
            """
            UPDATE decisions
            SET status = 'approved', approved_by = %s, approved_by_role = %s,
                approval_note = %s, approved_at = NOW()
            WHERE id = %s AND tender_id = %s AND status = 'draft'
            RETURNING id, status, approved_by, approved_by_role, approval_note, approved_at
            """,
            (request.approved_by, role, request.note, request.decision_id, tender_id),
        ).fetchone()

        if decision is None:
            # Nothing was approved. Distinguish "no such draft for this tender"
            # from "already decided" with a single read on this failure path.
            # Raising here rolls the transaction back, so a losing request
            # changes no workflow state and writes no approval audit event.
            exists = conn.execute(
                "SELECT 1 FROM decisions WHERE id = %s AND tender_id = %s",
                (request.decision_id, tender_id),
            ).fetchone()
            if exists is None:
                raise HTTPException(
                    status_code=404, detail="Батлах төсөл олдсонгүй."
                )
            raise HTTPException(
                status_code=409,
                detail="Энэ төсөл аль хэдийн шийдвэрлэгдсэн байна.",
            )

        conn.execute(
            "UPDATE tenders SET stage = 'approved' WHERE id = %s",
            (tender_id,),
        )
        record_audit(
            conn,
            tender_id=tender_id,
            event_type="human_approval_recorded",
            actor=request.approved_by,
            actor_role=role,
            target=f"decision:{request.decision_id}",
            details={"note": request.note, "official": True},
        )

    return {
        "message": "Хүний баталгаажуулалт бүртгэгдлээ.",
        "decision": decision,
    }
