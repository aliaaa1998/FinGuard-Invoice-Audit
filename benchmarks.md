# Benchmarks: CPU vs GPU (Template)

This benchmark template is designed to demonstrate feasibility and ROI for deployment decisions.

## Test scenario

- Invoice set: 100 mixed Arabic/English invoices (images + PDFs)
- Pipeline: OCR -> OpenAI structuring -> auditing logic
- Host A: CPU-only container
- Host B: GPU-accelerated container

## Suggested metrics

- Average processing time per invoice (ms)
- P95 processing time (ms)
- OCR time split vs OpenAI time split
- Throughput (invoices/min)
- Cost estimate per 1,000 invoices

## Example result table

| Environment | Avg Time/Invoice | P95 Time | Throughput | Notes |
|---|---:|---:|---:|---|
| CPU-only (8 vCPU) | 4200 ms | 6600 ms | 14/min | Baseline for on-prem low-cost |
| GPU (T4) | 1700 ms | 2800 ms | 35/min | Better for peak enterprise load |

## How to run

1. Start service with target environment.
2. Use a load script (k6/Locust) to submit the same invoice corpus.
3. Record `time_total` and server logs per request.
4. Compute averages and percentiles.

## ROI interpretation

- CPU-only is often enough for small/medium finance teams.
- GPU may be justified for centralized processing centers with SLA pressure.
- Hybrid strategy: CPU default + GPU autoscaling for spikes.
