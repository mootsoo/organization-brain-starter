from app.ai import MockProvider


def test_mock_provider_marks_output_as_draft():
    context = {
        "tender": {"code": "TEST-001", "title_mn": "Туршилтын тендер"},
        "submissions": [
            {"documents_complete": True},
            {"documents_complete": False},
        ],
        "findings": [
            {"severity": "attention"},
            {"severity": "information"},
        ],
    }

    output = MockProvider().generate_tender_summary(context)

    assert "AI-аар бэлтгэсэн төсөл" in output
    assert "ялагч" in output
