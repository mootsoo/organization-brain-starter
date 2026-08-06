"""Boundary tests for the AI gateway. No database and no network required.

The data-minimization tests inspect the *complete* payload recursively, not
only the `submissions` array, and they also inspect the body of the outbound
HTTP request that the OpenAI-compatible adapter would actually send.
"""

import json

import httpx
import pytest

from app.ai import (
    DRAFT_MARKER_MN,
    MockProvider,
    OpenAICompatibleProvider,
    ProviderError,
    build_model_input,
    get_provider,
)


# Distinctive row identifiers, so a leak is unambiguous when it is searched for
# as a substring of the serialized payload.
TENDER_ROW_ID = 7701
SUBMISSION_ROW_IDS = (8801, 8802)

CONTEXT = {
    "tender": {
        "id": TENDER_ROW_ID,
        "code": "ЖИШЭЭ-001",
        "title_mn": "Туршилтын тендер",
        "purpose_mn": "Зөвхөн туршилт.",
        "budget_mnt": 1000,
        "min_technical_score": 80,
        "min_bidders": 2,
    },
    "submissions": [
        {
            "id": SUBMISSION_ROW_IDS[0],
            "organization_name": "Жишээ-А ХХК",
            "proposed_amount_mnt": 900,
            "documents_complete": True,
            "tax_compliant": True,
            "technical_score": 90,
            "evidence_reference": "Материалын хавтас №1",
        },
        {
            "id": SUBMISSION_ROW_IDS[1],
            "organization_name": "Жишээ-Б ХХК",
            "proposed_amount_mnt": 1100,
            "documents_complete": False,
            "tax_compliant": True,
            "technical_score": 85,
            "evidence_reference": "Материалын хавтас №2",
        },
    ],
    "checks": [{"rule_id": "documents_complete"}, {"rule_id": "budget_limit"}],
    "findings": [
        {
            "rule_id": "documents_complete",
            "severity": "attention",
            "submission_id": SUBMISSION_ROW_IDS[1],
            "organization_name": "Жишээ-Б ХХК",
            "message_mn": "Жишээ-Б ХХК: материал дутуу.",
            # Exactly the shape `app/rules.py` produces.
            "source_reference": (
                f"tender_submissions #{SUBMISSION_ROW_IDS[1]} · documents_complete "
                "· Материалын хавтас №2"
            ),
            "evidence": {"documents_complete": False},
        }
    ],
}

# Keys that must not appear anywhere in the model payload, at any depth.
FORBIDDEN_KEYS = frozenset(
    {
        "id",
        "tender_id",
        "submission_id",
        "decision_id",
        "source_reference",
        "evidence_reference",
        "evidence",
    }
)

# Strings that must not appear anywhere in the serialized model payload.
FORBIDDEN_SUBSTRINGS = (
    "source_reference",
    "evidence_reference",
    "tender_submissions #",
    "tenders #",
    "Материалын хавтас №",
    "submission_id",
    "audit_events",
    str(TENDER_ROW_ID),
    str(SUBMISSION_ROW_IDS[0]),
    str(SUBMISSION_ROW_IDS[1]),
)


def _walk(node, path="$"):
    """Yield `(path, key, value)` for every entry in a nested structure.

    `key` is `None` for list items. Containers are yielded as values too, so a
    caller can inspect both keys and scalars in one pass.
    """
    if isinstance(node, dict):
        for key, value in node.items():
            yield f"{path}.{key}", key, value
            yield from _walk(value, f"{path}.{key}")
    elif isinstance(node, (list, tuple)):
        for index, value in enumerate(node):
            yield f"{path}[{index}]", None, value
            yield from _walk(value, f"{path}[{index}]")


def _serialized(payload) -> str:
    return json.dumps(payload, ensure_ascii=False, default=str)


# --- data minimization ------------------------------------------------------


def test_model_payload_has_no_internal_identifier_key_at_any_depth():
    payload = build_model_input(CONTEXT)

    offenders = [path for path, key, _ in _walk(payload) if key in FORBIDDEN_KEYS]

    assert offenders == []


def test_serialized_model_payload_has_no_row_or_document_pointer():
    serialized = _serialized(build_model_input(CONTEXT))

    for marker in FORBIDDEN_SUBSTRINGS:
        assert marker not in serialized, f"model input leaked {marker!r}"


def test_model_payload_has_no_raw_row_identifier_value():
    payload = build_model_input(CONTEXT)
    raw_ids = {TENDER_ROW_ID, *SUBMISSION_ROW_IDS}
    raw_id_text = {str(value) for value in raw_ids}

    for path, _key, value in _walk(payload):
        if isinstance(value, (dict, list, tuple, bool)):
            continue
        assert value not in raw_ids, path
        assert str(value) not in raw_id_text, path


def test_model_payload_keeps_the_business_facts_a_draft_needs():
    payload = build_model_input(CONTEXT)
    serialized = _serialized(payload)

    assert set(payload) == {"tender", "submissions", "rule_findings", "rules_checked"}
    assert payload["tender"]["code"] == "ЖИШЭЭ-001"
    assert "Жишээ-А ХХК" in serialized
    assert "Жишээ-Б ХХК" in serialized
    assert "900" in serialized and "1100" in serialized
    assert payload["rules_checked"] == ["documents_complete", "budget_limit"]

    finding = payload["rule_findings"][0]
    assert set(finding) == {"rule_id", "severity", "message_mn"}
    assert finding["rule_id"] == "documents_complete"
    assert finding["message_mn"] == "Жишээ-Б ХХК: материал дутуу."


def test_source_traceability_is_preserved_for_human_reviewers():
    """Minimization must not strip the deterministic rule result itself."""
    payload = build_model_input(CONTEXT)

    assert "source_reference" not in payload["rule_findings"][0]
    assert CONTEXT["findings"][0]["source_reference"].startswith("tender_submissions #")
    assert CONTEXT["submissions"][0]["evidence_reference"] == "Материалын хавтас №1"


def test_outbound_provider_request_body_has_no_row_or_document_pointer(monkeypatch):
    """Prove the minimization on the wire, not only on the returned dict."""
    captured: dict[str, str] = {}
    real_client = httpx.Client

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.dumps(
            json.loads(request.content.decode("utf-8")), ensure_ascii=False
        )
        return httpx.Response(
            200, json={"choices": [{"message": {"content": "Туршилтын төсөл."}}]}
        )

    def client_factory(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return real_client(*args, **kwargs)

    monkeypatch.setattr(httpx, "Client", client_factory)

    provider = OpenAICompatibleProvider(
        base_url="https://example.invalid/v1", api_key="test-key", model="m"
    )
    assert provider.generate_tender_summary(build_model_input(CONTEXT)) == "Туршилтын төсөл."

    for marker in FORBIDDEN_SUBSTRINGS:
        assert marker not in captured["body"], f"outbound request leaked {marker!r}"


# --- mock provider behaviour ------------------------------------------------


def test_mock_provider_marks_output_as_draft_and_refuses_to_pick_a_winner():
    output = MockProvider().generate_tender_summary(build_model_input(CONTEXT))

    assert DRAFT_MARKER_MN in output
    assert "ялагч сонгосон шийдвэр биш" in output


def test_mock_provider_is_deterministic():
    model_input = build_model_input(CONTEXT)
    first = MockProvider().generate_tender_summary(model_input)
    second = MockProvider().generate_tender_summary(model_input)

    assert first == second


def test_mock_provider_repeats_findings_without_quoting_a_source_pointer():
    output = MockProvider().generate_tender_summary(build_model_input(CONTEXT))

    assert "Жишээ-Б ХХК: материал дутуу." in output
    # The rule identifier is an ordinary business identifier and may be shown.
    assert "documents_complete" in output
    for marker in FORBIDDEN_SUBSTRINGS:
        assert marker not in output, f"draft leaked {marker!r}"


def test_mock_draft_does_not_claim_the_model_received_source_pointers():
    output = MockProvider().generate_tender_summary(build_model_input(CONTEXT))

    assert "Эх сурвалжийн нарийвчилсан заалтыг AI-д дамжуулаагүй" in output


# --- provider selection and failure modes -----------------------------------


def test_default_provider_is_mock_and_needs_no_api_key(monkeypatch):
    monkeypatch.delenv("AI_PROVIDER", raising=False)
    monkeypatch.delenv("AI_API_KEY", raising=False)

    provider = get_provider()

    assert provider.name == "mock"
    assert provider.generate_tender_summary(build_model_input(CONTEXT))


def test_openai_compatible_provider_without_key_raises_a_recoverable_error():
    provider = OpenAICompatibleProvider(base_url="https://example.invalid/v1", api_key="", model="m")

    with pytest.raises(ProviderError) as error:
        provider.generate_tender_summary(build_model_input(CONTEXT))

    assert "AI_API_KEY" in str(error.value)


def test_unsupported_provider_name_is_rejected(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "something-else")

    with pytest.raises(ProviderError):
        get_provider()
