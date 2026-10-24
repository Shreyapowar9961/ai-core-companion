# AI Care Companion: Voice-Based Post-Discharge Recovery Platform

AI Care Companion is a production-grade, voice-driven post-discharge recovery platform designed to telephone discharged patients daily in their preferred language (Marathi, Hindi, English), conduct structured clinical symptom check-ins, verify medication adherence, track vitals against clinician-defined thresholds, and surface exception-based alerts to the clinical care team.

> **Controlling Principle:** The AI conducts the conversation; the clinician owns every decision. All escalation logic runs in a **deterministic, clinician-configured rules engine in the backend — never in the language model**.

---

## 🏛 Approved System Architecture & Tech Stack

* **Architecture:** Modular monolith.
* **Backend:** FastAPI, Pydantic v2, SQLAlchemy 2.x, Alembic migrations, REST APIs, and OpenAPI 3.0.
* **Database & Auth:** PostgreSQL with relational-first design. Supabase Auth compatibility, backend token validation, and multi-tenant facility authorization.
* **Background Work:** Dedicated Python worker with persistent database jobs, retries, idempotency, concurrency control, and recovery.
* **AI & Speech:** Replaceable `LLMExtractionService` for structured extraction only. Replaceable STT/TTS adapters (Sarvam AI for regional languages, ElevenLabs).
* **Telephony:** Provider-independent `CallChannel` interface with real Twilio Voice API integration and interactive Web Simulator.

---

## 📁 Repository Structure

```
├── backend/
│   ├── app/
│   │   ├── api/v1/          # Modular API endpoints (patients, conversation, vitals, alerts, audit, etc.)
│   │   ├── core/            # Config, security, database session, audit logging, seeding
│   │   ├── models/          # SQLAlchemy 2.x relational ORM models
│   │   ├── schemas/         # Pydantic v2 data contracts
│   │   ├── services/        # Deterministic RulesEngine, ConversationService, LanguageService
│   │   └── main.py          # FastAPI application entrypoint
│   ├── worker/              # Background worker for scheduled calling, retries, and SLA monitoring
│   ├── alembic/             # Alembic database migrations
│   ├── tests/               # Automated unit, integration, and API test suite
│   ├── Dockerfile
│   └── requirements.txt
├── docker-compose.yml       # Production-ready PostgreSQL 16, Backend, Worker, Frontend
├── .env.example             # Documented environment variables
└── README.md
```

---

## 🚀 Quickstart & Setup Guide

### 1. Prerequisites
* Python 3.11+
* Docker & Docker Compose (or local PostgreSQL 16)
* Node.js v20+ & pnpm (for frontend)

### 2. Environment Configuration
Copy the example environment file:
```bash
cp .env.example .env
```
Update your PostgreSQL/Supabase database credentials and telephony API keys in `.env`.

### 3. Running with Docker Compose (Recommended)
Launch PostgreSQL, FastAPI backend, background worker, and frontend simultaneously:
```bash
docker compose up --build
```
* **Interactive OpenAPI Swagger Docs:** `http://localhost:8000/api/v1/docs`
* **Health Check:** `http://localhost:8000/health`

### 4. Running Backend Locally
```bash
cd backend
python -m pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 5. Running the Background Worker
In a separate terminal:
```bash
cd backend
python worker/worker.py
```

### 6. Running Automated Tests
```bash
python -m pytest backend/tests -v
```

---

## 🔒 Clinical Safety & Governance Mandates

1. **Deterministic Escalation:** The conversational LLM layer NEVER triggers alerts or makes clinical decisions. All alerts are evaluated by `RulesEngine` against individual clinician-configured thresholds.
2. **Mandatory Consent (ON-06):** Programme activation is strictly blocked until explicit consent (voice contact, call recording, data processing) and complete care plan are recorded.
3. **Immutable Audit Trail (GV-03, GV-04, GV-05):** Every call turn, patient response, vital reading, alert action, and configuration change is immutably logged with full patient journey reconstruction capabilities.
