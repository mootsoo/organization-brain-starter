"""Tests for the deterministic rule engine.

These run without a database and without a language model, which is exactly the
point: the checks must be reproducible by hand.
"""

from decimal import Decimal

from app import rules


TENDER = {
    "id": 1,
    "code": "ЖИШЭЭ-001",
    "budget_mnt": Decimal("1200000000"),
    "min_technical_score": Decimal("80.00"),
    "min_bidders": 3,
}

SUBMISSIONS = [
    {
        "id": 1,
        "organization_name": "Жишээ-А ХХК",
        "proposed_amount_mnt": Decimal("1080000000"),
        "documents_complete": True,
        "tax_compliant": True,
        "technical_score": Decimal("84.50"),
        "evidence_reference": "Материалын хавтас №1",
    },
    {
        "id": 2,
        "organization_name": "Жишээ-Б ХХК",
        "proposed_amount_mnt": Decimal("1145000000"),
        "documents_complete": False,
        "tax_compliant": True,
        "technical_score": Decimal("88.00"),
        "evidence_reference": "Материалын хавтас №2",
    },
    {
        "id": 3,
        "organization_name": "Жишээ-В ХХК",
        "proposed_amount_mnt": Decimal("1230000000"),
        "documents_complete": True,
        "tax_compliant": True,
        "technical_score": Decimal("78.00"),
        "evidence_reference": "Материалын хавтас №3",
    },
]


def _ids(findings):
    return sorted(finding["rule_id"] for finding in findings)


def test_every_catalogued_rule_is_reported_even_when_it_passes():
    result = rules.evaluate(TENDER, SUBMISSIONS)

    reported = {check["rule_id"] for check in result["checks"]}
    catalogued = {rule["rule_id"] for rule in rules.RULE_CATALOGUE}
    assert reported == catalogued


def test_sample_data_produces_the_expected_findings():
    result = rules.evaluate(TENDER, SUBMISSIONS)

    assert _ids(result["findings"]) == [
        "budget_limit",
        "documents_complete",
        "technical_minimum",
    ]
    assert result["attention_count"] == 3


def test_budget_finding_reports_the_computed_difference():
    result = rules.evaluate(TENDER, SUBMISSIONS)
    finding = next(f for f in result["findings"] if f["rule_id"] == "budget_limit")

    assert finding["evidence"]["difference_mnt"] == "30000000"
    assert "30,000,000" in finding["message_mn"]


def test_every_finding_carries_a_source_reference():
    result = rules.evaluate(TENDER, SUBMISSIONS)

    assert result["findings"]
    for finding in result["findings"]:
        assert finding["source_reference"]
        assert finding["severity"] in {"attention", "information"}


def test_clean_submissions_produce_no_findings():
    clean = [dict(SUBMISSIONS[0]), dict(SUBMISSIONS[0], id=2), dict(SUBMISSIONS[0], id=3)]

    result = rules.evaluate(TENDER, clean)

    assert result["findings"] == []
    assert result["attention_count"] == 0
    assert all(check["result"] == "ok" for check in result["checks"])


def test_missing_technical_score_is_treated_as_a_finding():
    submissions = [dict(SUBMISSIONS[0], technical_score=None)]

    result = rules.evaluate(TENDER, submissions)

    assert "technical_minimum" in _ids(result["findings"])


def test_minimum_bidders_is_a_tender_level_rule():
    result = rules.evaluate(TENDER, SUBMISSIONS[:1])

    finding = next(f for f in result["findings"] if f["rule_id"] == "minimum_bidders")
    assert finding["submission_id"] is None
    assert finding["evidence"] == {"submission_count": 1, "min_bidders": 3}
