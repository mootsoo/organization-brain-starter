"""End-to-end workflow tests against a real PostgreSQL database.

These protect the Phase 1 boundaries that unit tests cannot prove:
generation does not approve, the wrong role cannot approve, the right role can,
and both actions leave an audit record.

They are skipped when no database is reachable, so `pytest` still works for a
developer who has only checked out the code. CI starts a PostgreSQL service and
loads `database/init.sql`, so there they always run.
"""

import os

import pytest

pytest.importorskip("psycopg")

import psycopg  # noqa: E402
from psycopg.rows import dict_row  # noqa: E402


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://organization_brain:organization_brain@localhost:5432/organization_brain",
)

TEST_TENDER_ID = 9001
TEST_SUBMISSION_IDS = (9101, 9102, 9103)


def _database_available() -> bool:
    try:
        with psycopg.connect(DATABASE_URL, connect_timeout=3) as conn:
            conn.execute("SELECT 1")
        return True
    except Exception:  # noqa: BLE001 - any failure means "skip these tests"
        return False


pytestmark = pytest.mark.skipif(
    not _database_available(),
    reason="No PostgreSQL database reachable at DATABASE_URL",
)


@pytest.fixture(scope="module")
def client():
    os.environ.setdefault("AI_PROVIDER", "mock")
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def sample_tender():
    """Insert a fictional tender for the test, then remove it again."""
    with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
        _cleanup(conn)
        conn.execute(
            """
            INSERT INTO tenders (id, code, title_mn, purpose_mn, owner_unit, status, stage,
                                 budget_mnt, min_technical_score, min_bidders, due_date)
            VALUES (%s, 'ЖИШЭЭ-TEST-9001', 'Туршилтын тендер', 'Зөвхөн автомат туршилтад.',
                    'Жишээ байгууллага', 'active', 'human_review',
                    1200000000, 80.00, 3, CURRENT_DATE + 14)
            """,
            (TEST_TENDER_ID,),
        )
        conn.execute(
            """
            INSERT INTO tender_submissions (id, tender_id, organization_name,
                        proposed_amount_mnt, documents_complete, tax_compliant,
                        technical_score, evidence_reference, status)
            VALUES
              (%s, %s, 'Жишээ-А ХХК', 1080000000, TRUE,  TRUE, 84.50, 'Хавтас №1', 'reviewed'),
              (%s, %s, 'Жишээ-Б ХХК', 1145000000, FALSE, TRUE, 88.00, 'Хавтас №2', 'received'),
              (%s, %s, 'Жишээ-В ХХК', 1230000000, TRUE,  TRUE, 78.00, 'Хавтас №3', 'reviewed')
            """,
            (
                TEST_SUBMISSION_IDS[0], TEST_TENDER_ID,
                TEST_SUBMISSION_IDS[1], TEST_TENDER_ID,
                TEST_SUBMISSION_IDS[2], TEST_TENDER_ID,
            ),
        )
    yield TEST_TENDER_ID
    with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
        _cleanup(conn)


def _cleanup(conn) -> None:
    conn.execute("DELETE FROM audit_events WHERE tender_id = %s", (TEST_TENDER_ID,))
    conn.execute("DELETE FROM decisions WHERE tender_id = %s", (TEST_TENDER_ID,))
    conn.execute("DELETE FROM tender_submissions WHERE tender_id = %s", (TEST_TENDER_ID,))
    conn.execute("DELETE FROM tenders WHERE id = %s", (TEST_TENDER_ID,))


def _tender_stage() -> str:
    with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
        row = conn.execute(
            "SELECT stage FROM tenders WHERE id = %s", (TEST_TENDER_ID,)
        ).fetchone()
    return row["stage"]


def _decision_status(decision_id: int) -> str:
    with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
        row = conn.execute(
            "SELECT status FROM decisions WHERE id = %s", (decision_id,)
        ).fetchone()
    return row["status"]


def _audit_types() -> list[str]:
    with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
        rows = conn.execute(
            "SELECT event_type FROM audit_events WHERE tender_id = %s", (TEST_TENDER_ID,)
        ).fetchall()
    return [row["event_type"] for row in rows]


def _draft(client) -> dict:
    response = client.post(
        f"/api/v1/tenders/{TEST_TENDER_ID}/draft-summary", headers={"X-Role": "reviewer"}
    )
    assert response.status_code == 200, response.text
    return response.json()


# --- health and read endpoints ---------------------------------------------


def test_health_reports_database_and_provider(client):
    payload = client.get("/health").json()

    assert payload["status"] == "ok"
    assert payload["database"] == "ok"
    assert payload["ai_provider"] in {"mock", "openai-compatible"}
    assert "not production authentication" in payload["demo_auth"]


def test_overview_lists_the_tender_with_computed_counts(client):
    payload = client.get("/api/v1/overview").json()

    tender = next(t for t in payload["tenders"] if t["id"] == TEST_TENDER_ID)
    assert tender["submission_count"] == 3
    assert tender["attention_count"] == 3
    assert payload["workflow_steps"]


def test_tender_detail_separates_facts_checks_and_findings(client):
    payload = client.get(f"/api/v1/tenders/{TEST_TENDER_ID}").json()

    assert len(payload["submissions"]) == 3
    assert {check["rule_id"] for check in payload["checks"]}
    assert payload["findings"]
    for finding in payload["findings"]:
        assert finding["source_reference"]
    # Facts and rule results are separate keys; prose lives only in `decisions`.
    assert "content_mn" not in payload["submissions"][0]


def test_unknown_tender_returns_404(client):
    assert client.get("/api/v1/tenders/999999").status_code == 404


# --- AI draft boundary ------------------------------------------------------


def test_draft_requires_a_permitted_demo_role(client):
    assert client.post(
        f"/api/v1/tenders/{TEST_TENDER_ID}/draft-summary", headers={"X-Role": "viewer"}
    ).status_code == 403
    assert client.post(
        f"/api/v1/tenders/{TEST_TENDER_ID}/draft-summary"
    ).status_code == 403


def test_mock_draft_works_without_an_api_key(client, monkeypatch):
    monkeypatch.delenv("AI_API_KEY", raising=False)
    payload = _draft(client)

    assert payload["provider"] == "mock"
    assert payload["summary_mn"].strip()


def test_generating_a_draft_does_not_approve_anything(client):
    stage_before = _tender_stage()
    payload = _draft(client)

    assert payload["status"] == "draft"
    assert payload["official"] is False
    assert _decision_status(payload["decision_id"]) == "draft"
    assert _tender_stage() == stage_before == "human_review"


def test_generating_a_draft_writes_an_audit_event(client):
    _draft(client)

    assert "ai_draft_generated" in _audit_types()


# --- human approval boundary ------------------------------------------------


def test_wrong_role_cannot_approve(client):
    draft = _draft(client)
    body = {"decision_id": draft["decision_id"], "approved_by": "Жишээ хянагч"}

    for role in ({"X-Role": "reviewer"}, {"X-Role": "viewer"}, {}):
        response = client.post(
            f"/api/v1/tenders/{TEST_TENDER_ID}/approve", json=body, headers=role
        )
        assert response.status_code == 403, role

    assert _decision_status(draft["decision_id"]) == "draft"
    assert _tender_stage() == "human_review"
    assert "human_approval_recorded" not in _audit_types()


def test_authorized_role_can_approve_and_only_the_intended_state_changes(client):
    draft = _draft(client)

    response = client.post(
        f"/api/v1/tenders/{TEST_TENDER_ID}/approve",
        json={
            "decision_id": draft["decision_id"],
            "approved_by": "Жишээ эрх бүхий хянагч",
            "note": "Туршилтын баталгаажуулалт.",
        },
        headers={"X-Role": "approver"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["decision"]["approved_by_role"] == "approver"
    assert _decision_status(draft["decision_id"]) == "approved"
    assert _tender_stage() == "approved"

    # The draft text itself is never rewritten by the approval action.
    detail = client.get(f"/api/v1/tenders/{TEST_TENDER_ID}").json()
    approved = next(d for d in detail["decisions"] if d["id"] == draft["decision_id"])
    assert approved["content_mn"] == draft["summary_mn"]


def test_approval_is_recorded_in_the_audit_trail(client):
    draft = _draft(client)
    client.post(
        f"/api/v1/tenders/{TEST_TENDER_ID}/approve",
        json={"decision_id": draft["decision_id"], "approved_by": "Жишээ эрх бүхий хянагч"},
        headers={"X-Role": "approver"},
    )

    audit = client.get(f"/api/v1/tenders/{TEST_TENDER_ID}/audit").json()
    events = {event["event_type"]: event for event in audit["audit_events"]}

    assert "ai_draft_generated" in events
    assert "human_approval_recorded" in events
    approval = events["human_approval_recorded"]
    assert approval["actor_role"] == "approver"
    assert approval["target"] == f"decision:{draft['decision_id']}"
    assert approval["created_at"]
    # Audit records are readable without knowing the internal identifiers.
    assert approval["label_mn"] == "Хүний баталгаажуулалт бүртгэгдсэн"
    assert approval["target_label_mn"] == f"Шийдвэр №{draft['decision_id']}"
    assert approval["actor_role_label_mn"] == "батлах эрх бүхий хүн"
    generation = events["ai_draft_generated"]
    assert generation["actor_label_mn"] == "Үзүүлэнгийн хэрэглэгч (хянагч)"
    assert generation["details"]["official"] is False


def test_a_draft_cannot_be_approved_twice(client):
    draft = _draft(client)
    body = {"decision_id": draft["decision_id"], "approved_by": "Жишээ эрх бүхий хянагч"}
    headers = {"X-Role": "approver"}

    assert client.post(
        f"/api/v1/tenders/{TEST_TENDER_ID}/approve", json=body, headers=headers
    ).status_code == 200
    assert client.post(
        f"/api/v1/tenders/{TEST_TENDER_ID}/approve", json=body, headers=headers
    ).status_code == 409


def test_approving_an_unknown_decision_returns_404(client):
    response = client.post(
        f"/api/v1/tenders/{TEST_TENDER_ID}/approve",
        json={"decision_id": 987654, "approved_by": "Жишээ эрх бүхий хянагч"},
        headers={"X-Role": "approver"},
    )

    assert response.status_code == 404


def test_error_messages_do_not_leak_configuration(client):
    response = client.post(
        f"/api/v1/tenders/{TEST_TENDER_ID}/draft-summary", headers={"X-Role": "viewer"}
    )

    detail = response.json()["detail"]
    for secret_marker in ("postgresql://", "Bearer", "AI_API_KEY=", "password"):
        assert secret_marker not in detail
