# Aurum PMS

**A full-stack portfolio-management prototype for client onboarding, compliance review, portfolio operations, trading, and investor reporting.**

[![CI](https://github.com/aariiparekh3012-collab/Aurum-PMS/actions/workflows/ci.yml/badge.svg)](https://github.com/aariiparekh3012-collab/Aurum-PMS/actions/workflows/ci.yml)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=white)](frontend/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)](backend/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white)](docker-compose.yml)

[Live prototype](https://aurum-pms-nine.vercel.app) · [API documentation](#api-documentation) · [Architecture notes](docs/ARCHITECTURE.md) · [Database design](docs/DATABASE_v2.md)

> **Project status:** Aurum is a functional prototype built around workflows used by Indian discretionary portfolio managers. It is not a registered PMS, a production financial service, or a claim of regulatory certification. External KYC, bank-verification, e-sign and brokerage connections require vendor credentials and production validation.

## Project overview

Aurum models the operational path from a prospective investor's application to an active, reportable portfolio:

1. An applicant completes personal details, KYC data, risk profiling and agreement steps.
2. A compliance user reviews the application and records a decision.
3. Approval provisions the client and unlocks portfolio creation.
4. Staff can record capital flows, holdings, orders and trades.
5. Investors can view portfolio value, performance, fees, documents and activity.

The prototype was built and deployed during a 25-day internship in July–August 2026 and demonstrated to the project supervisor. My implementation covered the **React/TypeScript frontend, FastAPI backend and PostgreSQL schema**.

## What is implemented

| Area | Implemented workflow |
| --- | --- |
| Authentication | JWT-based login, refresh tokens, password recovery and role-aware routes |
| Onboarding | Personal details, document capture, KYC data, risk questionnaire, agreement confirmation and application status tracking |
| Compliance | Review queue, application detail view, approve/reject decisions and audit history |
| Client management | Client records, bank/demat details, nominees and risk profiles |
| Portfolio operations | Accounts, capital flows, cash ledger, holdings, lots and recorded trades |
| Trading | Orders, approvals, allocations and trade blotter |
| Performance and fees | Valuation snapshots, returns, management/performance fees and exit-load calculations |
| Reporting | Portfolio statements, transaction reports, performance reports and fee invoices |
| Supporting modules | NSE bhavcopy ingestion, notifications, messaging, documents and reference data |

## Architecture

The backend follows a clean/hexagonal structure: business rules live in the domain layer, use cases depend on ports, and infrastructure adapters handle persistence and external services.

```mermaid
flowchart LR
    UI[React + TypeScript] --> API[FastAPI API]
    API --> APP[Application use cases]
    APP --> DOMAIN[Domain model]
    APP --> PORTS[Ports and adapters]
    PORTS --> DB[(PostgreSQL)]
    PORTS --> REDIS[(Redis / Outbox)]
    PORTS --> EXT[External service adapters]
```

### Onboarding lifecycle

```mermaid
stateDiagram-v2
    [*] --> Draft
    Draft --> KYCPending: KYC submitted
    KYCPending --> KYCVerified: verification passed
    KYCPending --> KYCRejected: verification failed
    KYCRejected --> KYCPending: resubmitted
    KYCVerified --> RiskProfiled: risk profile completed
    RiskProfiled --> AgreementPending
    AgreementPending --> AgreementSigned: agreement confirmed
    AgreementSigned --> UnderReview
    UnderReview --> Active: approved
    UnderReview --> Rejected: rejected
```

The application also uses a transactional outbox for reliable domain-event processing, SQLAlchemy repositories for persistence, Alembic migrations for schema evolution, and structured request logging.

## Technology

| Layer | Tools |
| --- | --- |
| Frontend | React 18, TypeScript, Vite, React Router, TanStack Query, Axios, Zod |
| Backend | Python, FastAPI, Pydantic, SQLAlchemy, Alembic |
| Data and messaging | PostgreSQL 16, Redis 7, transactional outbox |
| Testing | pytest, pytest-cov, Vitest, Testing Library |
| Delivery | Docker Compose, GitHub Actions, Vercel/Render configuration |

## Run locally

### Prerequisites

- Docker Desktop
- Python 3.11 or newer
- Node.js 20 or newer

### 1. Start PostgreSQL and Redis

```bash
docker compose up -d db redis
```

### 2. Configure and run the backend

```bash
cd backend
cp .env.example .env
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Update `backend/.env` for the local Docker database and generate a development encryption key:

```dotenv
DATABASE_URL=postgresql+psycopg://pms:localdev123@localhost:5432/pms
FERNET_KEY=<generated-fernet-key>
```

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
alembic upgrade head
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`; interactive documentation is at `http://localhost:8000/docs`.

### 3. Run the frontend

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

For Windows-specific instructions and troubleshooting, see the [local setup guide](docs/LOCAL_SETUP_GUIDE.md).

## Demo data

With the backend running in local mode, seed a populated demonstration environment:

```bash
cd backend
python scripts/seed_presentation.py
```

The script creates sample users for compliance, relationship-manager and investor views, along with fictional clients, portfolios, trades and performance history. Credentials are defined in the script and are intended only for local demonstration.

## Testing

Run the backend tests:

```bash
cd backend
pytest -q
```

Run the frontend tests and production build:

```bash
cd frontend
npm test
npm run build
```

GitHub Actions runs backend linting, type checking, migrations and tests; frontend type checking, tests and build; and Docker image build checks on pushes and pull requests to `main`.

## API documentation

Once the backend is running:

- Swagger UI: `http://localhost:8000/docs`
- OpenAPI schema: `http://localhost:8000/openapi.json`
- Health check: `http://localhost:8000/api/v1/healthz`

The API is grouped by authentication, onboarding, clients, portfolios, trading, performance, fees, reporting, audit, notifications, messaging and market data.

## Repository structure

```text
.
├── backend/
│   ├── app/domain/          # Entities, value objects and business rules
│   ├── app/application/     # Use cases, DTOs and ports
│   ├── app/infrastructure/  # Persistence and external-service adapters
│   ├── app/api/             # FastAPI routers and dependencies
│   ├── alembic/             # Database migrations
│   └── tests/               # Unit and integration tests
├── frontend/
│   └── src/features/        # Feature-oriented React application
├── mobile/                  # Expo/React Native prototype client
├── docs/                    # Architecture and database documentation
├── .github/workflows/       # CI and deployment workflows
└── docker-compose.yml       # Local PostgreSQL, Redis, API and web app
```

## Security and limitations

- Sensitive identity and banking fields are designed to be encrypted at rest; secrets must be supplied through environment variables.
- Development adapters and seeded identities are for demonstration only.
- Live KRA/CKYC, penny-drop, e-sign, broker and depository integrations are not included as verified production connections.
- Regulatory rules and minimum-investment checks are implemented as prototype business logic and require professional review before real-world use.
- The deployment has not been independently security-audited or certified for handling real investor data.
- Never use real PAN, Aadhaar, bank, demat or investor information in the demo environment.

## Further documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Database design](docs/DATABASE_v2.md)
- [Local setup guide](docs/LOCAL_SETUP_GUIDE.md)
- [KRA integration design](docs/KRA_INTEGRATION.md)
- [eSign integration design](docs/ESIGN_INTEGRATION.md)
- [Transactional outbox](docs/OUTBOX_PATTERN.md)
- [Testing guide](TESTING_GUIDE.md)

---

Built by [Aarya Parekh](https://github.com/aariiparekh3012-collab) as a full-stack portfolio-management systems project.
