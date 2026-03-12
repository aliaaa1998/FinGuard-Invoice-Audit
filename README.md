# FinGuard Invoice Audit (Arabic/English)

Containerized FastAPI microservice for OCR-based invoice extraction, AI structuring, and fraud checks.

## Why this architecture

- **Bilingual edge**: `PaddleOCR(lang="ar")` handles Arabic + English invoices common in Iraq/MENA.
- **Cost efficiency**: OCR runs locally, while OpenAI is used only for text structuring/risk reasoning.
- **Enterprise readiness**: Docker + compose deployment for easy handover to platform/infrastructure teams.

## System workflow

1. Client uploads invoice (`png/jpg/jpeg/bmp/tiff/pdf`) to `/audit`.
2. OCR engine extracts text with a **Singleton PaddleOCR** instance.
3. OpenAI (`gpt-4o-mini`) converts unstructured OCR text into strict invoice JSON.
4. Auditor runs:
   - Math validation (`quantity * unit_price == line_total`)
   - Price anomaly validation using `price_reference.json` (>20% deviation)
   - Suspicious bilingual description detection (fraud semantics)
5. API returns structured invoice + findings + raw OCR text.

## Project structure

```text
.
├── main.py
├── utils/
│   ├── ocr_engine.py
│   └── auditor.py
├── price_reference.json
├── requirements.txt
├── Dockerfile
├── docker-compose.yaml
└── benchmarks.md
```

## API

### `GET /health`
Simple health probe.

### `POST /audit`
Upload invoice file as `multipart/form-data` (`file`).

Example:

```bash
curl -X POST http://localhost:8000/audit \
  -F "file=@samples/invoice-ar-en.png"
```

Response contains:
- `invoice`: validated schema (`vendor`, `date`, `currency`, `total`, `line_items`)
- `findings`: `math_check`, `price_anomalies`, `suspicious_descriptions`
- `raw_ocr_text`

## Local run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## Docker details

### Build image

```bash
docker build -t finguard-invoice-audit:latest .
```

### Run with Docker

```bash
docker run --rm -p 8000:8000 \
  -e OPENAI_API_KEY="your_key" \
  -e OPENAI_MODEL="gpt-4o-mini" \
  finguard-invoice-audit:latest
```

### Run with docker-compose

1. Create `.env` file:

```env
OPENAI_API_KEY=your_key_here
```

2. Launch service:

```bash
docker compose up --build
```

3. Stop service:

```bash
docker compose down
```

## Environment variables

- `OPENAI_API_KEY` (required)
- `OPENAI_MODEL` (optional, default: `gpt-4o-mini`)

## Notes for ERP integration

- Stateless HTTP service suitable behind API gateway/service mesh.
- Add authentication (JWT or mTLS), rate limiting, and audit logging in production.
- You can externalize `price_reference.json` to DB or config service.

## Strategic value summary

- Handles regional bilingual invoice formats.
- Minimizes OCR spend by keeping image processing local.
- Ready for HCS/on-prem deployment using standard container tooling.
