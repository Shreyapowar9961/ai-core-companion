# AI Care Companion: Voice-Based Post-Discharge Recovery Platform

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?style=flat&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Supabase](https://img.shields.io/badge/Supabase-Auth%20&%20DB-3FCF8E?style=flat&logo=supabase&logoColor=white)](https://supabase.com/)
[![React](https://img.shields.io/badge/React-18-61DAFB?style=flat&logo=react&logoColor=black)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.6-3178C6?style=flat&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Vite](https://img.shields.io/badge/Vite-5.4-646CFF?style=flat&logo=vite&logoColor=white)](https://vitejs.dev/)
[![TailwindCSS](https://img.shields.io/badge/TailwindCSS-3.4-06B6D4?style=flat&logo=tailwindcss&logoColor=white)](https://tailwindcss.com/)

**AI Care Companion** is a voice-driven post-discharge recovery monitoring platform designed to telephone discharged patients daily in their preferred language (**Marathi**, **Hindi**, **English**), conduct structured clinical symptom check-ins, verify medication adherence, track vitals against clinician-defined thresholds, and surface exception-based alerts to the clinical care team.

> ⚖️ **Controlling Principle:** *The AI conducts the conversation; the clinician owns every decision.* All escalation logic runs in a **deterministic, clinician-configured rules engine in the backend — never in the language model**.

---

## 📋 Comprehensive Requirements Traceability

The system fulfills all 14 functional requirement groups (`ON-01` through `GV-05`) specified in the Business Requirements Document (`BRD_AI_Care_Taker(4).pdf`).

👉 **[View the Complete Requirements Traceability Matrix (RTM)](docs/TRACEABILITY_MATRIX.md)**

1. **Onboarding & Configuration (`ON-01` to `ON-07`):** Demographics, care plans, designated caregivers, operating preferences, and **mandatory consent blocking** (`ON-06`).
2. **Language Support (`LN-01` to `LN-05`):** Marathi, Hindi, English, code-mixed speech (Hinglish/Maranglish), and mid-call language switching (`LN-03`).
3. **Conversation Engine (`CV-01` to `CV-09`):** Natural unhurried cadence, multi-turn state machine, readback confirmation (`CV-08`), and human clinician transfer (`CV-07`).
4. **Daily Check-in & Symptom Monitoring (`CI-01` to `CI-08`):** Morning/evening checks, 9-item symptom set, comparison with yesterday, and sustained worsening detection (`CI-05`).
5. **Medication Adherence (`MD-01` to `MD-10`):** Reminders, Taken/Missed/Deferred outcomes, repeat miss detection (`MD-05`), and strict dosage inquiry guardrails (`MD-07`).
6. **Lifestyle, Diet & Activity Tracking (`LS-01` to `LS-06`):** Meal reminders, hydration intervals, walking targets, and physiotherapy exercise monitoring.
7. **Vitals Collection & Threshold Monitoring (`VT-01` to `VT-05`):** Voice vitals, biological plausibility validation (`VT-02`), and individual threshold breach alerting (`VT-03`, `VT-04`).
8. **Appointments & Coordination (`AP-01` to `AP-05`):** Attendance confirmation, decline reasons, and care-team rescheduling task generation.
9. **Knowledge Delivery & Guardrails (`KQ-01` to `KQ-05`):** Clinician-approved documentation only (`KQ-01`), plain statement of unavailability (`KQ-02`), and declined query logging (`KQ-05`).
10. **Alerts & Clinical Escalation (`ES-01` to `ES-08`):** Pure deterministic rules engine (`ES-01`), emergency red-flag scripts verbatim (`ES-03`), severity SLAs (`ES-06`), and closure with required clinical action notes (`ES-07`).
11. **Call Management & Scheduling (`CM-01` to `CM-07`):** Dispositions, retry policies (`CM-02`), DND enforcement (`CM-06`), and **interruption resumption without restarting** (`CM-05`).
12. **Progress Scoring & Reporting (`PR-01` to `PR-06`):** Daily weighted Care Progress Score (PR-01), voice summaries, simplified caregiver updates, and 7/30-day trends.
13. **Clinical Dashboard & Prioritisation (`DB-01` to `DB-05`):** Priority Patient List ranked strictly by explicit rules with transparent inclusion reasons (`DB-02`), Patient 360 View (`DB-03`), and RBAC (`DB-05`).
14. **Programme Lifecycle, Consent & Governance (`PL-01` to `PL-04`, `GV-01` to `GV-05`):** Pause/resume (`PL-02`), immediate contact cessation on consent withdrawal (`PL-03`), immutable audit trail (`GV-03`), and complete patient journey reconstruction (`GV-05`).

---

## 🏛 Architecture & Tech Stack

```
                                  ┌────────────────────────────────────────────────────────┐
                                  │                  React / Vite Frontend                 │
                                  │   (TanStack Query, TailwindCSS, Accessible Components) │
                                  └──────────────────────────┬─────────────────────────────┘
                                                             │ REST / JSON (JWT / Supabase Auth)
                                                             ▼
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│                                 FastAPI Modular Monolith                                 │
│  ┌───────────────────────────┐  ┌───────────────────────────┐  ┌──────────────────────┐  │
│  │     API Routers (v1)      │  │     Services & Engine     │  │   Core & Security    │  │
│  │  - /patients              │  │  - Deterministic          │  │  - Supabase Auth /   │  │
│  │  - /conversation          │  │    RulesEngine (ES-01)    │  │    JWT RBAC (DB-05)  │  │
│  │  - /vitals & /checkins    │  │  - ConversationService    │  │  - Multi-Tenancy     │  │
│  │  - /medications           │  │  - LanguageService        │  │  - Immutable Audit   │  │
│  │  - /rules-alerts          │  │    (mr, hi, en)           │  │    Ledger (GV-03)    │  │
│  │  - /dashboard & /audit    │  │  - ProgressService (PR-01)│  │                      │  │
│  └───────────────────────────┘  └───────────────────────────┘  └──────────────────────┘  │
└──────────────────────────┬───────────────────────────────────────────────────────────────┘
                           │ SQLAlchemy 2.x (psycopg2 / asyncpg)
                           ▼
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│                         PostgreSQL 16 Relational Architecture                            │
│  ┌───────────────────────────┐  ┌───────────────────────────┐  ┌──────────────────────┐  │
│  │  Patients & Facilities    │  │   Clinical & Vitals Logs  │  │  Alerts & Governance │  │
│  │  - patients, caregivers   │  │  - medication_schedules   │  │  - escalation_rules  │  │
│  │  - consents, care_plans   │  │  - medication_logs        │  │  - alerts            │  │
│  │  - facilities             │  │  - vitals_thresholds      │  │  - alert_action_logs │  │
│  │                           │  │  - vital_readings         │  │  - audit_logs (GV-03)│  │
│  │                           │  │  - symptom_checkins       │  │  - config_audit_logs │  │
│  └───────────────────────────┘  └───────────────────────────┘  └──────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────────────────────┘
```

* **Backend:** FastAPI, Pydantic v2, SQLAlchemy 2.x, Alembic, psycopg2 & asyncpg.
* **Database & Auth:** PostgreSQL 16 (Strict Relational-First), Supabase Auth JWT validation, Multi-Tenant Facility RBAC.
* **Frontend:** React 18, TypeScript 5.6, Vite 5.4, TanStack Query v5, Tailwind CSS v3.
* **Background Worker:** Standalone Python process for call retries (`CM-02`), SLA timers (`ES-06`), and daily progress scoring (`PR-01`).
* **Telephony & Speech:** Provider-independent `CallChannel` interface, Twilio Voice implementation, and browser-based Web Speech Simulator.

---

## 📁 Repository Structure

```
├── backend/
│   ├── app/
│   │   ├── api/v1/          # REST endpoints (patients, conversation, vitals, alerts, audit, etc.)
│   │   ├── core/            # Config, security, PostgreSQL database engine, audit, seeding
│   │   ├── models/          # SQLAlchemy 2.x relational ORM models
│   │   ├── schemas/         # Pydantic v2 validation contracts
│   │   ├── services/        # RulesEngine, ConversationService, LanguageService, ProgressService
│   │   └── main.py          # FastAPI application entrypoint
│   ├── worker/              # Background worker for scheduled calling, retries, and SLA monitoring
│   ├── alembic/             # Alembic database migrations
│   ├── tests/               # Automated unit, integration, and API test suite
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/             # API client & TanStack Query hooks
│   │   ├── components/      # Navbar, Sidebar, StatusBadge, CallSimulatorModal
│   │   ├── context/         # AuthContext with dynamic RBAC role switcher
│   │   ├── pages/           # Dashboard, Patient 360, Onboarding, Alerts, Rules, Knowledge, Audit
│   │   ├── types/           # Complete TypeScript interfaces
│   │   ├── App.tsx          # React Router entrypoint
│   │   └── main.tsx
│   ├── Dockerfile
│   ├── package.json
│   └── vite.config.ts
├── docs/
│   └── TRACEABILITY_MATRIX.md # Comprehensive BRD requirement mapping
├── docker-compose.yml       # Production PostgreSQL 16, Backend, Worker, Frontend
├── .env.example             # Documented environment variables
└── README.md
```

---

## 🚀 Quickstart & Setup Guide

### 1. Prerequisites
* Python 3.11+
* Node.js v20+ & pnpm v10+
* Docker & Docker Compose (or local PostgreSQL 16)

### 2. Environment Configuration
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Key configuration items:
```ini
# PostgreSQL Database & Supabase
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=care_companion
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/care_companion
SYNC_DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/care_companion

# Supabase Auth
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-anon-key
SUPABASE_JWT_SECRET=your-supabase-jwt-secret

# Telephony (Twilio / Web Simulator)
TELEPHONY_PROVIDER=twilio
TWILIO_ACCOUNT_SID=your-account-sid
TWILIO_AUTH_TOKEN=your-auth-token
TWILIO_PHONE_NUMBER=+1234567890
```

---

### 3. Running with Docker Compose (Recommended)

To launch the full stack (PostgreSQL 16, FastAPI backend, Python background worker, and React frontend):
```bash
docker compose up --build
```
* **Frontend Dashboard:** `http://localhost:5173`
* **Interactive OpenAPI Swagger Docs:** `http://localhost:8000/api/v1/docs`
* **Backend Health Check:** `http://localhost:8000/health`

---

### 4. Running Locally Without Docker

#### Step A: PostgreSQL Database
Ensure PostgreSQL 16 is running and create the database:
```sql
CREATE DATABASE care_companion;
```

#### Step B: Backend & Database Migrations
```bash
cd backend
python -m pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
On startup, FastAPI automatically verifies the PostgreSQL schema and seeds clinical knowledge articles, demo escalation rules, and demo recovery patients (`patient-demo-1`, `patient-demo-2`).

#### Step C: Background Worker
In a separate terminal:
```bash
cd backend
python worker/worker.py
```

#### Step D: Frontend Application
In a third terminal:
```bash
cd frontend
pnpm install
pnpm run dev
```
Open `http://localhost:5173` in your browser.

---

## 🧪 Running the Automated Test Suite

All 18 automated integration tests execute against the relational PostgreSQL models:
```bash
python -m pytest backend/tests -v
```

### Verified Test Cases:
1. `test_health_endpoint`: Verifies service health and PostgreSQL database architecture.
2. `test_rbac_admin_clinician_access`: Validates that non-clinicians are blocked (HTTP 403) from configuring escalation rules (`DB-05`).
3. `test_full_alert_resolution_lifecycle`: Tests that alerts require explicit named clinician action notes for resolution (`DB-04`, `ES-07`).
4. `test_journey_reconstruction`: Validates reconstruction of complete patient interaction histories (`GV-05`).
5. `test_call_interruption_and_resumption`: Validates context persistence on drop and resumption from exact interruption step (`CM-05`).
6. `test_human_transfer_request`: Validates human clinician transfer protocol triggers on voice request (`CV-07`).
7. `test_language_switch_detection`: Validates mid-call switching between Marathi, Hindi, and English (`LN-03`).
8. `test_code_mixed_speech_medication_parsing`: Tests parsing Hinglish/Maranglish medication responses (`LN-02`).
9. `test_code_mixed_vitals_extraction`: Tests extracting vitals readings from conversational speech (`VT-01`).
10. `test_activation_blocked_without_consent`: **Guarantees programme activation is blocked until consent is captured** (`ON-06`).
11. `test_activation_succeeds_when_all_complete`: Validates activation succeeds when care plan, phone, and consent are recorded (`ON-06`).
12. `test_consent_withdrawal_halts_contact`: Validates immediate cessation of calls upon consent withdrawal (`PL-03`).
13. `test_deterministic_vitals_critical_threshold`: Validates critical SpO2 breach (<88%) triggers critical alert with 15-min SLA (`VT-03`, `ES-01`).
14. `test_vitals_plausibility_check`: Validates biological plausibility bounds (rejects SpO2 > 100% or systolic BP > 300) (`VT-02`).
15. `test_red_flag_acute_symptom_emergency`: Validates severe acute pain (>=8/10) triggers emergency red-flag scripts (`ES-03`).
16. `test_sustained_worsening_trend`: Validates sustained breathlessness deterioration across 2 consecutive check-ins (`CI-05`).
17. `test_medication_repeated_miss_escalation`: Validates escalation upon 2 consecutive missed medication doses (`MD-05`).
18. `test_contact_failure_escalation`: Validates escalation to caregiver once call retry attempts are exhausted (`CM-02`).

---

## 🔒 Security & Clinical Safety Governance

1. **Deterministic Rules Engine (`ES-01`):** The LLM is used **strictly for structured speech transcript parsing**. All clinical decisions, triage, and alert generations run in the backend `RulesEngine`.
2. **Prescription Guardrail (`MD-07`):** The conversational agent is strictly prohibited from altering dosages or determining prescriptions. Patient dosage queries automatically trigger a callback task for the treating doctor.
3. **Emergency Red-Flag Verbatim Scripts (`ES-03`):** Critical clinical presentations immediately halt the conversation and deliver emergency clinician-approved scripts.
4. **Mandatory Informed Consent (`ON-06`):** The patient record remains in `DRAFT` status until explicit consent is granted. No outbound calls can be initiated without voice consent.
5. **Immediate Consent Withdrawal Effect (`PL-03`):** Any verbal or recorded withdrawal of consent immediately halts all automated contact.
6. **Immutable Audit Ledger (`GV-03`, `GV-04`, `GV-05`):** Every interaction, call turn, vital reading, alert action, and configuration edit is immutably stored with chronological patient journey reconstruction.
