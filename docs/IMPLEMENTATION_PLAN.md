# Implementation Plan — Client Onboarding & KYC

A phased plan to take this scaffold to production. Each phase is independently shippable.

## Phase 0 — Foundations (week 1)
- Repo, CI (lint `ruff`, type `mypy`, `pytest`, `npm run build`), branch protection.
- Provision Postgres, object storage (S3), secret manager (KMS) for the PII key.
- Wire `docker compose up` for local dev; seed a compliance user + JWT issuance.

## Phase 1 — Domain core (week 1–2)  ✅ scaffolded
- `OnboardingApplication` aggregate + state machine, value objects, `RiskProfilingService`.
- Unit tests for every transition and risk band (`tests/`).
- **Exit:** 100% domain branch coverage; no framework imports in `app/domain`.

## Phase 2 — Persistence (week 2)  ✅ scaffolded
- SQLAlchemy models, Data-Mapper repository, Alembic `0001_initial`.
- PII encryption + PAN hashing; integration tests on a disposable Postgres.
- **Exit:** round-trip entity↔row tests green; migrations reversible.

## Phase 3 — Application use cases + API (week 3)  ✅ scaffolded
- Use cases, DTOs, FastAPI routers/schemas, composition root, error handlers, middleware.
- AuthN/AuthZ (JWT + role guards), correlation-id logging.
- **Exit:** OpenAPI published; e2e with fake adapters passes the full happy path.

## Phase 4 — Regulated integrations (week 4–5)
- Replace `Fake*Adapter`s with real KRA/CKYC, penny-drop, Aadhaar eSign clients.
- Webhook endpoints for async eSign callback; idempotency keys; circuit breakers.
- Contract tests against each vendor sandbox; secrets via KMS.
- **Exit:** real sandbox onboarding completes end-to-end.

## Phase 5 — Frontend (week 4–5)  ✅ scaffolded
- React wizard (personal → KYC → risk → agreement), React Query, zod validation.
- eSign redirect/callback handling; resumable drafts; accessibility pass.
- **Exit:** UX review; client-side validation mirrors server value objects.

## Phase 6 — Compliance & ops (week 6)
- Maker-checker review console (list/filter by `status`, approve/reject with reason).
- Outbox relay worker → message bus; downstream portfolio provisioning consumer.
- Append-only audit grants; retention/partitioning; dashboards + alerts (latency, KYC fail rate).
- **Exit:** SEBI audit-readiness checklist signed off.

## Phase 7 — Hardening & launch
- Pen test, PII data-flow review, load test (KYC vendor rate limits), DR runbook.
- Feature flag rollout; on-call + runbooks.

## Risk register (top items)
| Risk | Mitigation |
|------|-----------|
| KYC vendor downtime blocks onboarding | retries + circuit breaker; allow manual-officer fallback (`KycSource.MANUAL`) |
| PII leak | column encryption, masked logs, least-privilege grants, KMS key rotation |
| Duplicate applications | unique `pan_hash` + idempotent create |
| Lost events to downstream | transactional outbox (at-least-once) + consumer idempotency |
| eSign callback race | idempotency keys + state-machine guards |

## Definition of done (per use case)
Domain rule covered by unit test · adapter contract-tested · API contract in OpenAPI ·
audit row + outbox event emitted · structured logs with correlation id · no PII in logs.
