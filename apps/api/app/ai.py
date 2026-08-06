import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Protocol

import httpx


class TenderSummaryProvider(Protocol):
    name: str
    model: str

    def generate_tender_summary(self, context: dict[str, Any]) -> str:
        """Return a plain-language Mongolian draft based only on supplied facts."""


@dataclass
class MockProvider:
    name: str = "mock"
    model: str = "deterministic-demo"

    def generate_tender_summary(self, context: dict[str, Any]) -> str:
        tender = context["tender"]
        submissions = context["submissions"]
        findings = context["findings"]
        complete_count = sum(1 for item in submissions if item["documents_complete"])
        attention_count = sum(1 for item in findings if item["severity"] == "attention")

        return (
            f"{tender['code']} дугаартай “{tender['title_mn']}” тендерт "
            f"нийт {len(submissions)} оролцогчийн мэдээлэл бүртгэгдсэн. "
            f"Үүнээс {complete_count} оролцогчийн материал бүрэн гэж тэмдэглэгдсэн бөгөөд "
            f"{attention_count} анхаарах асуудал илэрсэн байна. "
            "Дүрмийн шалгалтын үр дүн, эх сурвалжийн лавлагааг үнэлгээний хороо тус бүрээр нь нягталж, "
            "шаардлагатай тайлбар болон нэмэлт баримтыг авсны дараа эцсийн дүгнэлт гаргана. "
            "Энэ текст нь AI-аар бэлтгэсэн төсөл бөгөөд ялагч сонгосон шийдвэр биш."
        )


@dataclass
class OpenAICompatibleProvider:
    base_url: str
    api_key: str
    model: str
    name: str = "openai-compatible"

    def generate_tender_summary(self, context: dict[str, Any]) -> str:
        if not self.api_key:
            raise ValueError("AI_API_KEY is required for openai-compatible mode")

        system_message = (
            "You prepare a concise draft for a Mongolian government tender evaluator. "
            "Write in clear, non-technical Mongolian. Use only the supplied facts. "
            "Do not rank bidders, recommend a winner, invent evidence, or present the draft as an official decision."
        )
        user_message = (
            "Prepare a short evaluation draft from this structured context:\n"
            f"{context}"
        )

        with httpx.Client(timeout=30.0) as client:
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
            return payload["choices"][0]["message"]["content"].strip()


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
    raise ValueError(f"Unsupported AI_PROVIDER: {provider_name}")


def generated_at_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
