import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class InvoiceLineItem(BaseModel):
    description: str
    quantity: float = Field(ge=0)
    unit_price: float = Field(ge=0)
    line_total: float = Field(ge=0)


class InvoiceData(BaseModel):
    vendor: str
    date: str
    currency: str
    total: float = Field(ge=0)
    line_items: list[InvoiceLineItem]


class Auditor:
    def __init__(self, price_reference_path: Path) -> None:
        self.price_reference = self._load_price_reference(price_reference_path)

    @staticmethod
    def _load_price_reference(path: Path) -> dict[str, float]:
        if not path.exists():
            return {}
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def audit_invoice(self, invoice: InvoiceData, openai_client: Any, model: str) -> dict:
        return {
            "math_check": self._math_check(invoice),
            "price_anomalies": self._price_anomaly_check(invoice),
            "suspicious_descriptions": self._suspicious_description_check(invoice, openai_client, model),
        }

    @staticmethod
    def _math_check(invoice: InvoiceData) -> list[dict]:
        issues = []
        for idx, item in enumerate(invoice.line_items):
            expected = round(item.quantity * item.unit_price, 2)
            actual = round(item.line_total, 2)
            if expected != actual:
                issues.append(
                    {
                        "line_index": idx,
                        "description": item.description,
                        "expected_line_total": expected,
                        "actual_line_total": actual,
                    }
                )
        return issues

    def _price_anomaly_check(self, invoice: InvoiceData) -> list[dict]:
        anomalies = []
        for idx, item in enumerate(invoice.line_items):
            key = item.description.strip().lower()
            ref_price = self.price_reference.get(key)
            if ref_price is None or ref_price == 0:
                continue

            variance = abs(item.unit_price - ref_price) / ref_price
            if variance > 0.2:
                anomalies.append(
                    {
                        "line_index": idx,
                        "description": item.description,
                        "reference_price": ref_price,
                        "invoice_unit_price": item.unit_price,
                        "variance_percent": round(variance * 100, 2),
                    }
                )
        return anomalies

    @staticmethod
    def _suspicious_description_check(invoice: InvoiceData, openai_client: Any, model: str) -> list[dict]:
        descriptions = [item.description for item in invoice.line_items]
        prompt = (
            "Review these invoice line-item descriptions (Arabic/English). "
            "Flag suspicious or context-mismatched items for potential fraud. "
            "Examples: Miscellaneous Fees, Consulting on hardware invoices, vague charges. "
            "Return JSON array only with objects: description, reason, risk_level.\n\n"
            f"Descriptions: {json.dumps(descriptions, ensure_ascii=False)}"
        )

        response = openai_client.chat.completions.create(
            model=model,
            temperature=0,
            messages=[
                {"role": "system", "content": "You are an invoice fraud analyst. Output only JSON."},
                {"role": "user", "content": prompt},
            ],
        )

        content = response.choices[0].message.content
        if not content:
            return []

        try:
            return json.loads(content)
        except json.JSONDecodeError:
            start = content.find("[")
            end = content.rfind("]")
            if start == -1 or end == -1:
                return []
            return json.loads(content[start : end + 1])
