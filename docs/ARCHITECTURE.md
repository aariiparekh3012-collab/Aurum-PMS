# Architecture — Client Onboarding & KYC

## 1. Goals & constraints

The onboarding module is the regulatory gate of the PMS platform. It must:

- Enforce SEBI (Portfolio Managers) Regulations, 2020 — minimum ₹50 lakh ticket, KYC, risk
  profiling, signed PMS agreement before any funds are accepted.
- Integrate with regulated third parties: **KRA/CKYC** (identity), **penny-drop** (bank),
  **Aadhaar eSign** (agreement).
- Protect PII (PAN, Aadhaar, bank) with encryption at rest and a tamper-evident audit trail.
- Be independently deployable and feed downstream modules (portfolio, fees, reporting) via
  domain events.

## 2. Clean / Hexagonal architecture

Dependencies point **inward**. The domain knows nothing about FastAPI, SQLAlchemy or HTTP.

```
            ┌──────────────────────────────────────────────┐
            │                   API layer                   │  FastAPI routers, schemas,
            │        (interface adapters / driving)         │  deps (composition root)
            └───────────────────────┬──────────────────────┘
                                    │ calls
            ┌───────────────────────▼──────────────────────┐
            │               Application layer               │  use cases, DTOs, PORTS
            │            (orchestration, no rules)          │  (KycPort, EsignPort…)
            └───────────────────────┬──────────────────────┘
                                    │ depends on abstractions
            ┌───────────────────────▼──────────────────────┐
            │                  Domain layer                 │  entities, value objects,
            │      (pure business rules, framework-free)    │  domain services, events
            └───────────────────────▲──────────────────────┘
                                    │ implements ports
            ┌───────────────────────┴──────────────────────┐
            │              Infrastructure layer             │  SQLAlchemy repos, KRA/CKYC,
            │          (driven adapters / details)          │  eSign, penny-drop, outbox
            └──────────────────────────────────────────────┘
```

### Layer responsibilities

| Layer | Folder | Knows about | Never imports |
|-------|--------|-------------|---------------|
| Domain | `app/domain/onboarding` | Pure Python only | FastAPI, SQLAlchemy, httpx |
| Application | `app/application/onboarding` | Domain + ports | Concrete adapters, FastAPI |
| Infrastructure | `app/infrastructure` | Application ports, domain | API layer |
| API | `app/api` | Application use cases | Infrastructure internals (only via deps) |

The **composition root** (`app/api/dependencies.py`) is the single place where concrete
adapters are bound to ports — swapping KRA vendor or using fakes in tests is a one-line change.

## 3. The onboarding state machine

`OnboardingApplication` (aggregate root) owns a strict lifecycle; illegal transitions raise
`InvalidStateTransition`.

```
DRAFT ─submit_for_kyc→ KYC_PENDING ─┬─verified→ KYC_VERIFIED ─→ RISK_PROFILED
                                    └─rejected→ KYC_REJECTED ─(retry)→ KYC_PENDING
RISK_PROFILED ─→ AGREEMENT_PENDING ─esign→ AGREEMENT_SIGNED ─→ UNDER_REVIEW
UNDER_REVIEW ─┬─approve→ ACTIVE   (emits OnboardingActivated → portfolio module)
              └─reject→  REJECTED
```

## 4. Onboarding sequence (happy path)

```
React Wizard        API           Use Case            Ports/Adapters         DB
    │ create app ───►│ create ─────►│ build aggregate ─────────────────────►│ INSERT (DRAFT)
    │ submit kyc ───►│ submit_kyc ─►│ penny-drop verify ──► PennyDrop       │
    │                │              │ KRA/CKYC verify ────► KRA adapter      │ UPDATE (KYC_VERIFIED)
    │ risk profile ─►│ risk ───────►│ RiskProfilingSvc ─────────────────────►│ UPDATE (AGREEMENT_PENDING)
    │ esign confirm ►│ esign ──────►│ eSign fetch_result ─► Aadhaar eSign    │ UPDATE (UNDER_REVIEW)
    │                │ decision ───►│ approve ─────────────► Outbox          │ UPDATE (ACTIVE) + outbox row
```

## 5. Cross-cutting concerns

**Security.** JWT auth with role guards (RM / investor / compliance). PII is encrypted at
rest with Fernet (`app/core/security.py`); the key comes from a KMS/secret manager in prod.
PAN is additionally SHA-256 hashed for unique lookups without decrypting. Aadhaar is stored
masked (last 4) plus encrypted.

**Auditability.** Append-only `audit_logs` (write-once, no UPDATE/DELETE grants) plus a
**transactional outbox** (`event_outbox`) written in the same DB transaction as the aggregate
change — at-least-once event delivery without distributed transactions. A relay worker polls
the outbox and publishes to the message bus.

**Observability.** Structured JSON logs (structlog) with a per-request `X-Correlation-ID`
propagated through middleware; no raw PII is ever logged.

**Resilience.** External adapters use timeouts + exponential-backoff retries (tenacity) and
raise `ExternalServiceError` (HTTP 502) on vendor outage so the client can retry safely.

## 6. Testing strategy

- **Domain** unit tests (no I/O): state machine + risk scoring — fast, deterministic.
- **Application** tests with fake adapters (`Fake*Adapter`) — verify orchestration.
- **Integration** tests against a disposable Postgres (testcontainers) for the repository.
- **Contract** tests against KRA/CKYC/eSign sandboxes.

## 7. Why these choices

- *FastAPI + Pydantic v2*: typed contracts, OpenAPI for the React client, async-ready.
- *Data Mapper (not Active Record)*: keeps the domain pure and the schema free to evolve.
- *Outbox pattern*: reliable cross-module integration without 2-phase commit.
- *Ports & Adapters*: regulated vendors change; the core shouldn't.
