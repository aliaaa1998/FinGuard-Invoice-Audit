import json
import logging
import os
from pathlib import Path
from fastapi import FastAPI, File, HTTPException, UploadFile
from openai import OpenAI
from pydantic import BaseModel

from utils.auditor import Auditor, InvoiceData
from utils.ocr_engine import OCREngineSingleton

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="FinGuard Invoice Audit Service",
    description="Bilingual Arabic/English invoice auditing microservice",
    version="1.0.0",
)

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
auditor = Auditor(price_reference_path=Path("price_reference.json"))


class AuditResponse(BaseModel):
    invoice: InvoiceData
    findings: dict
    raw_ocr_text: str


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/audit", response_model=AuditResponse)
async def audit_invoice(file: UploadFile = File(...)) -> AuditResponse:
    if not file.filename:
        raise HTTPException(status_code=400, detail="File name is required")

    suffix = Path(file.filename).suffix.lower()
    if suffix not in {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".pdf"}:
        raise HTTPException(status_code=400, detail="Unsupported file format")

    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    try:
        raw_text = OCREngineSingleton.get_engine().extract_text(contents, suffix=suffix)
        invoice = structure_invoice(raw_text)
        findings = auditor.audit_invoice(invoice, openai_client=client, model=OPENAI_MODEL)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Audit failed")
        raise HTTPException(status_code=500, detail=f"Audit failed: {exc}") from exc

    return AuditResponse(invoice=invoice, findings=findings, raw_ocr_text=raw_text)


def structure_invoice(raw_text: str) -> InvoiceData:
    prompt = (
        "Convert the OCR invoice text into strict JSON with fields: vendor, date, currency, total, "
        "line_items[].description, line_items[].quantity, line_items[].unit_price, line_items[].line_total. "
        "Support Arabic and English text. Return JSON only.\n\n"
        f"OCR Text:\n{raw_text}"
    )

    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        temperature=0,
        messages=[
            {"role": "system", "content": "You are a precise invoice parser. Output only valid JSON."},
            {"role": "user", "content": prompt},
        ],
    )

    content = response.choices[0].message.content
    if not content:
        raise ValueError("OpenAI returned empty content while structuring invoice")

    parsed = _safe_json_loads(content)
    return InvoiceData.model_validate(parsed)


def _safe_json_loads(content: str) -> dict:
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        start = content.find("{")
        end = content.rfind("}")
        if start == -1 or end == -1:
            raise
        return json.loads(content[start : end + 1])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
