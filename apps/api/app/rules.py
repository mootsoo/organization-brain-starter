"""Deterministic tender rules.

Every check in this module is ordinary Python arithmetic over structured
database rows. No language model is involved, and no language model can change
a result produced here. This separation is the point of the whole starter:

    facts (database)  ->  rules (this file)  ->  AI prose (app/ai.py)

Each finding carries the exact source row and the values that produced it, so a
reviewer can recompute any check by hand from the same data.

Thresholds (`min_technical_score`, `min_bidders`, `budget_mnt`) are stored with
the tender rather than hard-coded here, so an organization can change the policy
without changing the code.
"""

from decimal import Decimal
from typing import Any


def _decimal(value: Any) -> Decimal:
    """Coerce a database numeric value to Decimal for exact comparison."""
    if value is None:
        return Decimal(0)
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _mnt(value: Decimal) -> str:
    """Render an amount with thousands separators, e.g. 30,000,000."""
    return f"{int(value):,}"


# Rule catalogue. Keeping it as data makes the checks easy to list in the
# interface, so a leader can see which rules ran even when nothing failed.
RULE_CATALOGUE = [
    {
        "rule_id": "documents_complete",
        "title_mn": "Материалын бүрдэл",
        "description_mn": "Оролцогч бүрийн шаардлагатай материал бүрэн эсэхийг шалгана.",
        "scope": "submission",
    },
    {
        "rule_id": "tax_compliant",
        "title_mn": "Татварын тодорхойлолт",
        "description_mn": "Татварын тодорхойлолт хүчинтэй гэж бүртгэгдсэн эсэхийг шалгана.",
        "scope": "submission",
    },
    {
        "rule_id": "budget_limit",
        "title_mn": "Төсвийн хязгаар",
        "description_mn": "Үнийн санал батлагдсан төсвөөс хэтэрсэн эсэхийг тооцно.",
        "scope": "submission",
    },
    {
        "rule_id": "technical_minimum",
        "title_mn": "Техникийн доод оноо",
        "description_mn": "Техникийн оноо тендерт заасан доод хэмжээнд хүрсэн эсэхийг шалгана.",
        "scope": "submission",
    },
    {
        "rule_id": "minimum_bidders",
        "title_mn": "Оролцогчийн доод тоо",
        "description_mn": "Тендерт бүртгэгдсэн оролцогчийн тоо шаардлагад нийцэж байгаа эсэхийг шалгана.",
        "scope": "tender",
    },
]


def _submission_source(submission: dict, column: str) -> str:
    return f"tender_submissions #{submission['id']} · {column} · {submission.get('evidence_reference', 'Demonstration record')}"


def _check_documents_complete(tender: dict, submissions: list[dict]) -> list[dict]:
    findings = []
    for submission in submissions:
        if not submission["documents_complete"]:
            findings.append(
                {
                    "rule_id": "documents_complete",
                    "severity": "attention",
                    "submission_id": submission["id"],
                    "organization_name": submission["organization_name"],
                    "message_mn": (
                        f"{submission['organization_name']}: шаардлагатай материал бүрэн ирээгүй "
                        "тул тодруулга авах шаардлагатай."
                    ),
                    "source_reference": _submission_source(submission, "documents_complete"),
                    "evidence": {"documents_complete": False},
                }
            )
    return findings


def _check_tax_compliant(tender: dict, submissions: list[dict]) -> list[dict]:
    findings = []
    for submission in submissions:
        if not submission["tax_compliant"]:
            findings.append(
                {
                    "rule_id": "tax_compliant",
                    "severity": "attention",
                    "submission_id": submission["id"],
                    "organization_name": submission["organization_name"],
                    "message_mn": (
                        f"{submission['organization_name']}: татварын тодорхойлолт хүчинтэй гэж "
                        "бүртгэгдээгүй байна."
                    ),
                    "source_reference": _submission_source(submission, "tax_compliant"),
                    "evidence": {"tax_compliant": False},
                }
            )
    return findings


def _check_budget_limit(tender: dict, submissions: list[dict]) -> list[dict]:
    findings = []
    budget = _decimal(tender["budget_mnt"])
    for submission in submissions:
        amount = _decimal(submission["proposed_amount_mnt"])
        if amount > budget:
            difference = amount - budget
            findings.append(
                {
                    "rule_id": "budget_limit",
                    "severity": "attention",
                    "submission_id": submission["id"],
                    "organization_name": submission["organization_name"],
                    "message_mn": (
                        f"{submission['organization_name']}: үнийн санал батлагдсан төсвөөс "
                        f"{_mnt(difference)} төгрөгөөр давсан байна."
                    ),
                    "source_reference": _submission_source(submission, "proposed_amount_mnt"),
                    "evidence": {
                        "proposed_amount_mnt": str(amount),
                        "budget_mnt": str(budget),
                        "difference_mnt": str(difference),
                    },
                }
            )
    return findings


def _check_technical_minimum(tender: dict, submissions: list[dict]) -> list[dict]:
    findings = []
    minimum = _decimal(tender.get("min_technical_score"))
    for submission in submissions:
        score = submission.get("technical_score")
        if score is None:
            findings.append(
                {
                    "rule_id": "technical_minimum",
                    "severity": "attention",
                    "submission_id": submission["id"],
                    "organization_name": submission["organization_name"],
                    "message_mn": (
                        f"{submission['organization_name']}: техникийн оноо бүртгэгдээгүй байна."
                    ),
                    "source_reference": _submission_source(submission, "technical_score"),
                    "evidence": {"technical_score": None, "minimum": str(minimum)},
                }
            )
            continue
        if _decimal(score) < minimum:
            findings.append(
                {
                    "rule_id": "technical_minimum",
                    "severity": "attention",
                    "submission_id": submission["id"],
                    "organization_name": submission["organization_name"],
                    "message_mn": (
                        f"{submission['organization_name']}: техникийн оноо {score} нь "
                        f"шаардагдах доод оноо {minimum}-аас бага байна."
                    ),
                    "source_reference": _submission_source(submission, "technical_score"),
                    "evidence": {"technical_score": str(score), "minimum": str(minimum)},
                }
            )
    return findings


def _check_minimum_bidders(tender: dict, submissions: list[dict]) -> list[dict]:
    required = int(tender.get("min_bidders") or 0)
    if len(submissions) >= required:
        return []
    return [
        {
            "rule_id": "minimum_bidders",
            "severity": "attention",
            "submission_id": None,
            "organization_name": None,
            "message_mn": (
                f"Тендерт {len(submissions)} оролцогч бүртгэгдсэн нь шаардагдах "
                f"{required} оролцогчид хүрэхгүй байна."
            ),
            "source_reference": f"tenders #{tender['id']} · min_bidders",
            "evidence": {"submission_count": len(submissions), "min_bidders": required},
        }
    ]


_CHECKS = {
    "documents_complete": _check_documents_complete,
    "tax_compliant": _check_tax_compliant,
    "budget_limit": _check_budget_limit,
    "technical_minimum": _check_technical_minimum,
    "minimum_bidders": _check_minimum_bidders,
}


def evaluate(tender: dict, submissions: list[dict]) -> dict:
    """Run every rule and return both the rule summary and the findings.

    Returns a dict with:
      checks   - one entry per rule, including rules that passed, so the
                 interface can show what was verified and not only what failed;
      findings - one entry per failed check, each with a source reference and
                 the values that produced it.
    """
    findings: list[dict] = []
    checks: list[dict] = []

    for rule in RULE_CATALOGUE:
        rule_findings = _CHECKS[rule["rule_id"]](tender, submissions)
        findings.extend(rule_findings)
        subject_count = len(submissions) if rule["scope"] == "submission" else 1
        checks.append(
            {
                **rule,
                "checked": subject_count,
                "failed": len(rule_findings),
                "passed": max(subject_count - len(rule_findings), 0),
                "result": "attention" if rule_findings else "ok",
            }
        )

    return {
        "checks": checks,
        "findings": findings,
        "attention_count": sum(1 for item in findings if item["severity"] == "attention"),
    }


def attention_count(tender: dict, submissions: list[dict]) -> int:
    """Convenience helper for list views."""
    return evaluate(tender, submissions)["attention_count"]
