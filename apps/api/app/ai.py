"""Provider-neutral AI gateway.

Two boundaries are enforced here:

1. The model receives only the small structured payload built by
   `build_model_input`. It never receives a database credential, a connection,
   or the freedom to issue SQL.
2. The model produces prose only. Rule results are computed in `app/rules.py`
   and are passed to the model as read-only context; nothing the model returns
   can change them.

Model output is untrusted draft content. It is stored with status `draft` and
becomes official only through a separate human approval action.
"""

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Protocol

import httpx


AI_TIMEOUT_SECONDS = float(os.getenv("AI_TIMEOUT_SECONDS", "30"))

DRAFT_MARKER_MN = "Энэ бол AI-аар бэлтгэсэн төсөл"


class ProviderError(RuntimeError):
    """A recoverable AI provider failure with a message that is safe to show.

    The message must never contain an API key, an authorization header, or a
    raw provider response body.
    """


class TenderSummaryProvider(Protocol):
    name: str
    model: str

    def generate_tender_summary(self, model_input: dict[str, Any]) -> str:
        """Return a plain-language Mongolian draft based only on supplied facts."""


def _plain(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    return value


def build_model_input(context: dict[str, Any]) -> dict[str, Any]:
    """Select the minimum set of facts the model needs for a draft.

    Internal row identifiers, document pointers, decision history and audit
    records are deliberately left out (data minimization).
    """
    tender = context["tender"]
    return {
        "tender": {
            "code": tender["code"],
            "title_mn": tender["title_mn"],
            "budget_mnt": _plain(tender["budget_mnt"]),
            "min_technical_score": _plain(tender.get("min_technical_score")),
            "min_bidders": tender.get("min_bidders"),
        },
        "submissions": [
            {
                "organization_name": item["organization_name"],
                "proposed_amount_mnt": _plain(item["proposed_amount_mnt"]),
                "documents_complete": item["documents_complete"],
                "tax_compliant": item["tax_compliant"],
                "technical_score": _plain(item.get("technical_score")),
            }
            for item in context["submissions"]
        ],
        "rule_findings": [
            {
                "rule_id": item["rule_id"],
                "severity": item["severity"],
                "message_mn": item["message_mn"],
                "source_reference": item["source_reference"],
            }
            for item in context["findings"]
        ],
        "rules_checked": [check["rule_id"] for check in context["checks"]],
    }


@dataclass
class MockProvider:
    """Deterministic local provider. Requires no network and no API key.

    The same input always produces the same text, which keeps demonstrations
    and tests predictable.
    """

    name: str = "mock"
    model: str = "deterministic-demo"

    def generate_tender_summary(self, model_input: dict[str, Any]) -> str:
        tender = model_input["tender"]
        submissions = model_input["submissions"]
        findings = model_input["rule_findings"]
        rules_checked = model_input["rules_checked"]

        complete_count = sum(1 for item in submissions if item["documents_complete"])
        attention = [item for item in findings if item["severity"] == "attention"]

        lines = [
            f"{tender['code']} дугаартай “{tender['title_mn']}” тендерт нийт "
            f"{len(submissions)} оролцогчийн материал бүртгэгдсэн байна.",
            f"Үүнээс {complete_count} оролцогчийн материал бүрэн гэж бүртгэгдсэн.",
            f"Программ {len(rules_checked)} дүрмийн шалгалт хийхэд "
            f"{len(attention)} анхаарах асуудал илэрсэн.",
        ]

        if attention:
            lines.append("Анхаарах асуудлууд:")
            for item in attention:
                lines.append(f"— {item['message_mn']} (эх сурвалж: {item['source_reference']})")
        else:
            lines.append("Дүрмийн шалгалтаар анхаарах асуудал илрээгүй байна.")

        lines.append(
            "Үнэлгээний хороо дээрх баримт, эх сурвалжийг тус бүрээр нь нягталж, "
            "шаардлагатай тодруулгыг авсны дараа эцсийн дүгнэлтээ гаргана."
        )
        lines.append(
            f"{DRAFT_MARKER_MN} бөгөөд ялагч сонгосон шийдвэр биш. "
            "Албан ёсны шийдвэрийг эрх бүхий хүн батална."
        )

        return "\n".join(lines)


@dataclass
class OpenAICompatibleProvider:
    """Adapter for any endpoint that speaks the OpenAI chat-completions shape."""

    base_url: str
    api_key: str
    model: str
    name: str = "openai-compatible"
    timeout: float = AI_TIMEOUT_SECONDS

    def generate_tender_summary(self, model_input: dict[str, Any]) -> str:
        if not self.api_key:
            raise ProviderError(
                "AI_API_KEY is not configured. Set AI_PROVIDER=mock to run without a key."
            )

        system_message = (
            "You prepare a concise draft for a Mongolian tender evaluation officer. "
            "Write in clear, non-technical Mongolian. Use only the supplied facts. "
            "Do not rank bidders, recommend a winner, invent evidence, or present the "
            "draft as an official decision. Finish by stating in Mongolian that the text "
            "is an AI-prepared draft and not a decision."
        )
        user_message = (
            "Prepare a short evaluation draft from this structured context. "
            "Do not add any fact that is not present here.\n"
            f"{model_input}"
        )

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{self.base_url.rstrip('/')}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": system_message},
                            {"role": "user", "content": user_message},
                        ],
                        "temperature": 0.1,
                    },
                )
                response.raise_for_status()
                payload = response.json()
                content = payload["choices"][0]["message"]["content"]
        except httpx.TimeoutException as exc:
            raise ProviderError(
                "The AI provider did not respond in time. Please try again."
            ) from exc
        except httpx.HTTPStatusError as exc:
            # Report the status code only. Provider response bodies can echo
            # request headers and must not be shown to the caller.
            raise ProviderError(
                f"The AI provider rejected the request (HTTP {exc.response.status_code}). "
                "Check AI_BASE_URL and AI_MODEL."
            ) from exc
        except httpx.HTTPError as exc:
            raise ProviderError(
                "The AI provider could not be reached. Check AI_BASE_URL and network access."
            ) from exc
        except (KeyError, IndexError, ValueError) as exc:
            raise ProviderError(
                "The AI provider returned an unexpected response shape."
            ) from exc

        if not isinstance(content, str) or not content.strip():
            raise ProviderError("The AI provider returned an empty draft.")
        return content.strip()


def get_provider() -> TenderSummaryProvider:
    provider_name = os.getenv("AI_PROVIDER", "mock").lower()
    if provider_name == "mock":
        return MockProvider()
    if provider_name == "openai-compatible":
        return OpenAICompatibleProvider(
            base_url=os.getenv("AI_BASE_URL", "https://api.openai.com/v1"),
            api_key=os.getenv("AI_API_KEY", ""),
            model=os.getenv("AI_MODEL", "example-model"),
        )
    raise ProviderError(
        f"Unsupported AI_PROVIDER value: {provider_name!r}. Use 'mock' or 'openai-compatible'."
    )


def generated_at_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
