"""Boundary tests for the AI gateway. No database and no network required."""

import pytest

from app.ai import (
    DRAFT_MARKER_MN,
    MockProvider,
    OpenAICompatibleProvider,
    ProviderError,
    build_model_input,
    get_provider,
)


CONTEXT = {
    "tender": {
        "id": 1,
        "code": "ЖИШЭЭ-001",
        "title_mn": "Туршилтын тендер",
        "purpose_mn": "Зөвхөн туршилт.",
        "budget_mnt": 1000,
        "min_technical_score": 80,
        "min_bidders": 2,
    },
    "submissions": [
        {
            "id": 11,
            "organization_name": "Жишээ-А ХХК",
            "proposed_amount_mnt": 900,
            "documents_complete": True,
            "tax_compliant": True,
            "technical_score": 90,
            "evidence_reference": "Материалын хавтас №1",
        },
        {
            "id": 12,
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
            "message_mn": "Жишээ-Б ХХК: материал дутуу.",
            "source_reference": "tender_submissions #12 · documents_complete",
        }
    ],
}


def test_mock_provider_marks_output_as_draft_and_refuses_to_pick_a_winner():
    output = MockProvider().generate_tender_summary(build_model_input(CONTEXT))

    assert DRAFT_MARKER_MN in output
    assert "ялагч сонгосон шийдвэр биш" in output


def test_mock_provider_is_deterministic():
    model_input = build_model_input(CONTEXT)
    first = MockProvider().generate_tender_summary(model_input)
    second = MockProvider().generate_tender_summary(model_input)

    assert first == second


def test_mock_provider_repeats_rule_findings_with_their_source():
    output = MockProvider().generate_tender_summary(build_model_input(CONTEXT))

    assert "Жишээ-Б ХХК: материал дутуу." in output
    assert "tender_submissions #12 · documents_complete" in output


def test_model_input_excludes_internal_identifiers_and_document_pointers():
    model_input = build_model_input(CONTEXT)

    assert set(model_input) == {"tender", "submissions", "rule_findings", "rules_checked"}
    for submission in model_input["submissions"]:
        assert "id" not in submission
        assert "evidence_reference" not in submission


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
