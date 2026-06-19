# Database Design — Onboarding & KYC

PostgreSQL 16. All timestamps are `timestamptz` (UTC). UUID primary keys. Money stored as
integer **paise** (`BIGINT`) to avoid floating-point error.

## Entity-relationship overview

```
onboarding_applications 1───┬──< onboarding_documents
                            │
                            ├──< audit_logs        (by aggregate_id, append-only)
                            └──< event_outbox      (by aggregate_id)
```

## Tables

### `onboarding_applications` (aggregate root)

| Column | Type | Notes |
|--------|------|-------|
| id | uuid PK | application id |
| status | varchar(32) | state-machine value; indexed |
| investor_type | varchar(20) | individual / huf / nri / corporate … |
| full_name | varchar(200) | |
| email | varchar(254) | indexed |
| mobile | varchar(20) | |
| **pan_hash** | varchar(64) **UNIQUE** | SHA-256 of PAN — dedupe without decrypt |
| **pan_enc** | text | Fernet-encrypted PAN |
| aadhaar_last4 | varchar(4) | masked, queryable |
| aadhaar_enc | text | encrypted last4 |
| bank_account_enc | text | encrypted account number |
| bank_ifsc | varchar(11) | |
| bank_holder_name | varchar(200) | |
| demat_bo_id | varchar(16) | NSDL/CDSL 16-digit BO id |
| demat_depository | varchar(4) | NSDL \| CDSL |
| proposed_investment_paise | bigint | ≥ ₹50,00,000 enforced in domain |
| kyc_source | varchar(10) | kra \| ckyc \| manual |
| kyc_reference | varchar(64) | KRA/CKYC record id |
| risk_category | varchar(20) | conservative / moderate / aggressive |
| risk_score | int | questionnaire score |
| agreement_esign_ref | varchar(64) | eSign transaction reference |
| rejection_reason | text | |
| created_at / updated_at | timestamptz | |

Indexes: `ix_onboarding_status`, `ix_onboarding_email`, composite
`ix_onboarding_status_created (status, created_at)` for the compliance work-queue.

### `onboarding_documents`

KYC artefacts live in object storage (S3); the DB stores only the key + integrity hash.

| Column | Type | Notes |
|--------|------|-------|
| id | uuid PK | |
| application_id | uuid FK → applications (ON DELETE CASCADE) | indexed |
| document_type | varchar(30) | pan / aadhaar / bank_proof / demat_cmr / pms_agreement … |
| storage_key | varchar(512) | S3 object key |
| sha256 | varchar(64) | tamper-evidence |
| uploaded_at | timestamptz | |

### `audit_logs` (append-only)

| Column | Type | Notes |
|--------|------|-------|
| id | uuid PK | |
| aggregate_id | uuid | indexed |
| actor | varchar(120) | user / system |
| action | varchar(80) | e.g. `kyc_verified` |
| payload | jsonb | masked details only |
| correlation_id | varchar(64) | ties to request logs |
| created_at | timestamptz | |

> Grant only `INSERT`/`SELECT` on this table in production — no `UPDATE`/`DELETE`.

### `event_outbox` (transactional outbox)

| Column | Type | Notes |
|--------|------|-------|
| id | uuid PK | |
| aggregate_id | uuid | indexed |
| event_type | varchar(80) | `OnboardingActivated`, `KycVerified` … |
| payload | jsonb | event data |
| published | bool | indexed; relay flips to true after publish |
| created_at | timestamptz | |

## Data protection

- **Encryption at rest**: column-level Fernet for PAN / Aadhaar / bank; key in KMS, rotatable.
- **Masking**: only `aadhaar_last4` is stored in the clear; full Aadhaar is never persisted.
- **Uniqueness without exposure**: `pan_hash` enforces one application per PAN.
- **PostgreSQL TDE / disk encryption** and TLS in transit are assumed at the platform layer.

## Migrations

Alembic. Initial revision `0001_initial` creates all four tables and indexes. Run
`alembic upgrade head`. `compare_type=True` is enabled so autogenerate catches type drift.

## Retention

SEBI record-keeping requires onboarding records and audit trails be retained for the
regulatory minimum (≥ 5 years / per latest circular). Use partitioning by `created_at` year on
`audit_logs` and an archival policy to cold storage for closed accounts.
