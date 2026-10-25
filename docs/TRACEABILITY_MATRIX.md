# AI Care Companion - Requirements Traceability Matrix (RTM)

**Document Version:** 1.0.0  
**Source of Truth:** Business Requirements Document `BRD_AI_Care_Taker(4).pdf`  
**Architecture:** Modular Monolith (FastAPI + PostgreSQL 16 / Supabase + React/TypeScript/Vite)  
**Controlling Clinical Principle:** *The AI conducts the conversation; the clinician owns every decision.* Escalation decisions execute strictly in a deterministic backend rules engine—**NEVER** in an LLM.

---

## 1. Onboarding & Configuration (ON-01 to ON-07)

| Requirement ID | Requirement Summary | Implementation Module / Files | API Endpoint / Service Method | Verification Status |
| :--- | :--- | :--- | :--- | :--- |
| **ON-01** | Register demographics (Name, DOB, gender, phone, email, address, diagnosis, discharge date) | `backend/app/models/patient.py`<br>`backend/app/schemas/patient.py`<br>`frontend/src/pages/OnboardingPage.tsx` | `POST /api/v1/patients/`<br>`Patient` model | **IMPLEMENTED & VERIFIED** |
| **ON-02** | Configure clinical care plan (Medications, vitals thresholds, diet, hydration, exercise) | `backend/app/models/patient.py`<br>`backend/app/models/clinical.py`<br>`frontend/src/pages/OnboardingPage.tsx` | `CarePlan`, `MedicationSchedule`, `VitalsThreshold` tables | **IMPLEMENTED & VERIFIED** |
| **ON-03** | Record operating preferences (Language, call window, check-in times, DND, max retry, max deferrals) | `backend/app/models/patient.py`<br>`backend/app/schemas/patient.py` | `Patient.call_window_start`, `dnd_start`, `retry_limit` fields | **IMPLEMENTED & VERIFIED** |
| **ON-04** | Record designated caregivers (relationship, contacts, authorized channels, consented categories) | `backend/app/models/patient.py`<br>`frontend/src/pages/PatientDetailPage.tsx` | `Caregiver` model<br>`POST /api/v1/patients/{id}/caregivers` | **IMPLEMENTED & VERIFIED** |
| **ON-05** | Configurable operating window (default 08:00-20:00 local time) & DND silent hours enforcement | `backend/app/services/conversation_service.py`<br>`backend/worker/tasks.py` | `Patient.dnd_start`, `Patient.dnd_end`<br>`worker.check_scheduled_calls` | **IMPLEMENTED & VERIFIED** |
| **ON-06** | **MANDATORY CONSENT BLOCK:** Block programme activation until care plan, phone, and consent are recorded | `backend/app/api/v1/patients.py`<br>`backend/tests/test_onboarding_consent.py`<br>`frontend/src/pages/OnboardingPage.tsx` | `register_patient()` check:<br>`initial_status = "ACTIVE" if (req.activate_if_complete and is_consent_complete) else "DRAFT"` | **TESTED & VERIFIED** (`test_activation_blocked_without_consent`) |
| **ON-07** | Assign patient to a care team / facility / treating clinician | `backend/app/models/patient.py`<br>`backend/app/core/security.py` | `Patient.facility_id`, `Patient.treating_doctor_name` | **IMPLEMENTED & VERIFIED** |

---

## 2. Language Support (LN-01 to LN-05)

| Requirement ID | Requirement Summary | Implementation Module / Files | API Endpoint / Service Method | Verification Status |
| :--- | :--- | :--- | :--- | :--- |
| **LN-01** | Full conversational support for Marathi (`mr`), Hindi (`hi`), English (`en`) | `backend/app/services/language_service.py`<br>`frontend/src/components/CallSimulatorModal.tsx` | `LanguageService.PROMPT_LIBRARY`<br>`LanguageService.get_prompt()` | **TESTED & VERIFIED** (`test_language_switch_detection`) |
| **LN-02** | Handle code-mixed speech (Hinglish, Maranglish) in medication and vitals parsing | `backend/app/services/language_service.py`<br>`backend/tests/test_language.py` | `LanguageService.parse_code_mixed_medication_response()`<br>`LanguageService.parse_vitals_reading_from_speech()` | **TESTED & VERIFIED** (`test_code_mixed_speech_medication_parsing`) |
| **LN-03** | Mid-conversation language switching upon voice request without restarting | `backend/app/services/language_service.py`<br>`backend/app/services/conversation_service.py` | `LanguageService.detect_language_switch_request()`<br>`ConversationService.process_turn()` | **TESTED & VERIFIED** (`test_language_switch_detection`) |
| **LN-04** | English as standard language for clinician records, summaries, alerts, dashboards | `backend/app/services/conversation_service.py`<br>`backend/app/services/progress_service.py` | `CallTurn.english_summary`, `DailyProgressScore.caregiver_summary` | **IMPLEMENTED & VERIFIED** |
| **LN-05** | Clinician-approved prompt translations library | `backend/app/services/language_service.py` | Curated prompts dictionary for all clinical interactions | **IMPLEMENTED & VERIFIED** |

---

## 3. Conversation Engine (CV-01 to CV-09)

| Requirement ID | Requirement Summary | Implementation Module / Files | API Endpoint / Service Method | Verification Status |
| :--- | :--- | :--- | :--- | :--- |
| **CV-01** | Scheduled & outbound calls; accept inbound calls | `backend/app/services/conversation_service.py`<br>`backend/app/services/telephony/` | `ConversationService.initiate_session()`<br>`TwilioCallChannel.initiate_call()` | **IMPLEMENTED & VERIFIED** |
| **CV-02** | Natural, unhurried, empathetic conversational pace | `backend/app/services/language_service.py`<br>`frontend/src/components/CallSimulatorModal.tsx` | Speech synthesis rate 0.95x, unhurried prompt phrasing | **IMPLEMENTED & VERIFIED** |
| **CV-03** | Multi-turn context within session; carry forward across turns | `backend/app/models/conversation.py`<br>`backend/app/services/conversation_service.py` | `CallSession.resume_context`<br>`CallTurn` sequence | **IMPLEMENTED & VERIFIED** |
| **CV-04** | Limit repeat / rephrase prompts (max 2 attempts per step) | `backend/app/services/conversation_service.py` | Step re-prompt count tracking in `resume_context` | **IMPLEMENTED & VERIFIED** |
| **CV-05** | Handle silence, background noise, unclear responses gracefully | `backend/app/services/conversation_service.py` | `LanguageService.parse_code_mixed_medication_response()` fallback | **IMPLEMENTED & VERIFIED** |
| **CV-06** | Restrict clinical responses to clinician-approved library; never invent advice | `backend/app/services/conversation_service.py`<br>`backend/app/services/knowledge_service.py` | Guardrail checks in `process_turn()`, approved article lookup | **IMPLEMENTED & VERIFIED** |
| **CV-07** | Human transfer on voice request or protocol trigger | `backend/app/services/conversation_service.py`<br>`backend/tests/test_conversation_interruption.py` | `ConversationService.process_turn()` (is_transferred=True) | **TESTED & VERIFIED** (`test_human_transfer_request`) |
| **CV-08** | Confirmation readback of vital readings by voice | `backend/app/services/conversation_service.py` | `LanguageService.get_prompt("VITALS_CONFIRMATION_READBACK")` | **IMPLEMENTED & VERIFIED** |
| **CV-09** | Caller verification protocol; authenticate identity before clinical inquiries | `backend/app/services/conversation_service.py` | Step `IDENTITY_CHECK` with `UNAUTHORIZED_CALLER_REFUSAL` | **IMPLEMENTED & VERIFIED** |

---

## 4. Daily Check-in & Symptom Monitoring (CI-01 to CI-08)

| Requirement ID | Requirement Summary | Implementation Module / Files | API Endpoint / Service Method | Verification Status |
| :--- | :--- | :--- | :--- | :--- |
| **CI-01** | Structured check-in morning and evening | `backend/app/models/clinical.py`<br>`backend/app/api/v1/checkins.py` | `SymptomCheckin.checkin_type` (`MORNING_CHECKIN`, `EVENING_CHECKIN`) | **IMPLEMENTED & VERIFIED** |
| **CI-02** | Standard 9-item symptom set (pain, breathlessness, dizziness, weakness, fever, wound, appetite, sleep, mood) | `backend/app/models/clinical.py`<br>`backend/app/schemas/clinical.py` | `SymptomCheckin` columns: `pain_level`, `breathlessness`, etc. | **IMPLEMENTED & VERIFIED** |
| **CI-03** | Compare symptoms against previous day (better, unchanged, worse) | `backend/app/services/llm_extraction.py`<br>`backend/app/models/clinical.py` | `SymptomCheckin.comparison_with_yesterday` | **IMPLEMENTED & VERIFIED** |
| **CI-04** | Capture unlisted symptoms verbatim | `backend/app/models/clinical.py`<br>`backend/app/services/llm_extraction.py` | `SymptomCheckin.other_symptoms_verbatim` | **IMPLEMENTED & VERIFIED** |
| **CI-05** | Detect sustained worsening trends across consecutive check-ins (e.g. 2 days) | `backend/app/services/rules_engine.py`<br>`backend/tests/test_rules_engine.py` | `RulesEngine.evaluate_symptom_checkin()`<br>`RULE_SYMPTOM_SUSTAINED_WORSENING_BREATHLESSNESS` | **TESTED & VERIFIED** (`test_sustained_worsening_trend`) |
| **CI-06** | Log symptom changes against recovery milestone expectations | `backend/app/models/clinical.py` | `SymptomCheckin` records logged with timestamp and milestone tags | **IMPLEMENTED & VERIFIED** |
| **CI-07** | Retry missed check-ins within window per retry policy | `backend/worker/tasks.py`<br>`backend/worker/worker.py` | `tasks.retry_missed_calls()` background worker job | **IMPLEMENTED & VERIFIED** |
| **CI-08** | Skip questions not relevant to patient diagnosis/care plan | `backend/app/services/conversation_service.py` | Dynamic step skipping based on `CarePlan` configuration | **IMPLEMENTED & VERIFIED** |

---

## 5. Medication Adherence (MD-01 to MD-10)

| Requirement ID | Requirement Summary | Implementation Module / Files | API Endpoint / Service Method | Verification Status |
| :--- | :--- | :--- | :--- | :--- |
| **MD-01** | Remind per care plan dosing schedule | `backend/app/models/clinical.py`<br>`backend/app/services/conversation_service.py` | `MedicationSchedule`, `ConversationService.process_turn()` | **IMPLEMENTED & VERIFIED** |
| **MD-02** | Record adherence outcome: Taken, Missed, Deferred, Pending | `backend/app/models/clinical.py`<br>`backend/app/api/v1/medications.py` | `MedicationLog.status` enum (`TAKEN`, `MISSED`, `DEFERRED`, `PENDING`) | **IMPLEMENTED & VERIFIED** |
| **MD-03** | Support deferral (remind in 30 mins) up to patient max_deferrals | `backend/app/services/conversation_service.py` | `MedicationLog.deferral_count`, `Patient.max_deferrals` | **IMPLEMENTED & VERIFIED** |
| **MD-04** | Record stated reason for missed doses (side effects, cost, forgot, ran out) | `backend/app/models/clinical.py`<br>`backend/app/services/language_service.py` | `MedicationLog.stated_reason`<br>`LanguageService.parse_code_mixed_medication_response()` | **IMPLEMENTED & VERIFIED** |
| **MD-05** | Detect repeated misses against threshold (>=2 doses) and invoke escalation rule | `backend/app/services/rules_engine.py`<br>`backend/tests/test_rules_engine.py` | `RulesEngine.evaluate_medication_miss()`<br>`RULE_MED_REPEATED_MISS` | **TESTED & VERIFIED** (`test_medication_repeated_miss_escalation`) |
| **MD-06** | Track medication supply / refill reminders | `backend/app/models/clinical.py` | `MedicationSchedule.refill_due_date`, `refill_reminder_days_before` | **IMPLEMENTED & VERIFIED** |
| **MD-07** | **NO DOSAGE DETERMINATION GUARDRAIL:** Never alter doses; route queries to treating clinician | `backend/app/services/conversation_service.py`<br>`backend/app/models/knowledge.py` | `ConversationService.process_turn()` dosage regex guardrail -> `DeclinedQueryLog` | **IMPLEMENTED & VERIFIED** |
| **MD-08** | Next dose lookup on patient inquiry | `backend/app/services/conversation_service.py` | `next_dose_lookup` in `conversation_service` | **IMPLEMENTED & VERIFIED** |
| **MD-09** | Support prescription updates by clinicians | `backend/app/api/v1/medications.py` | `POST /api/v1/medications/update-schedule` | **IMPLEMENTED & VERIFIED** |
| **MD-10** | Calculate dose-level and aggregate adherence rates | `backend/app/services/progress_service.py`<br>`backend/app/api/v1/medications.py` | `GET /api/v1/medications/adherence/{patient_id}` | **IMPLEMENTED & VERIFIED** |

---

## 6. Lifestyle, Diet & Activity Tracking (LS-01 to LS-06)

| Requirement ID | Requirement Summary | Implementation Module / Files | API Endpoint / Service Method | Verification Status |
| :--- | :--- | :--- | :--- | :--- |
| **LS-01** | Remind & track meal intake per diet instructions | `backend/app/models/clinical.py`<br>`backend/app/api/v1/lifestyle.py` | `LifestyleLog.log_type = 'MEAL'` | **IMPLEMENTED & VERIFIED** |
| **LS-02** | Hydration reminders at clinician-configured intervals; track glass count | `backend/app/models/patient.py`<br>`backend/app/models/clinical.py` | `CarePlan.hydration_interval_hours`<br>`LifestyleLog.log_type = 'HYDRATION'` | **IMPLEMENTED & VERIFIED** |
| **LS-03** | Reinforce condition-specific dietary instructions | `backend/app/models/patient.py` | `CarePlan.diet_instructions` | **IMPLEMENTED & VERIFIED** |
| **LS-04** | Remind & track physical activity (walking minutes/steps) | `backend/app/models/clinical.py` | `CarePlan.activity_target_steps`<br>`LifestyleLog.log_type = 'ACTIVITY'` | **IMPLEMENTED & VERIFIED** |
| **LS-05** | Physiotherapy exercise check; log difficulty / pain on exercise | `backend/app/models/clinical.py` | `LifestyleLog.log_type = 'PHYSIOTHERAPY'` | **IMPLEMENTED & VERIFIED** |
| **LS-06** | Track only parameters activated in patient care plan | `backend/app/services/conversation_service.py` | Check `patient.care_plan` attributes before executing lifestyle turns | **IMPLEMENTED & VERIFIED** |

---

## 7. Vitals Collection & Threshold Monitoring (VT-01 to VT-05)

| Requirement ID | Requirement Summary | Implementation Module / Files | API Endpoint / Service Method | Verification Status |
| :--- | :--- | :--- | :--- | :--- |
| **VT-01** | Collect vitals by voice with confirmation readback | `backend/app/services/conversation_service.py`<br>`backend/app/models/clinical.py` | `VitalReading.voice_confirmed = True` | **IMPLEMENTED & VERIFIED** |
| **VT-02** | Validate biological plausibility before acceptance; reject impossible values | `backend/app/services/rules_engine.py`<br>`backend/tests/test_rules_engine.py` | `RulesEngine.evaluate_vital_reading()` (status: `IMPLAUSIBLE`) | **TESTED & VERIFIED** (`test_vitals_plausibility_check`) |
| **VT-03** | Evaluate readings against patient-specific thresholds configured by clinician | `backend/app/services/rules_engine.py`<br>`backend/models/clinical.py` | `VitalsThreshold` normal, warning, critical ranges | **TESTED & VERIFIED** (`test_deterministic_vitals_critical_threshold`) |
| **VT-04** | Immediate alert on threshold breach per severity tier SLA | `backend/app/services/rules_engine.py`<br>`backend/models/rules_alert.py` | `Alert.severity = "CRITICAL"`, `Alert.sla_due_at` (15m) | **TESTED & VERIFIED** (`test_deterministic_vitals_critical_threshold`) |
| **VT-05** | Record "not measured" / "device unavailable" distinctly from normal/abnormal | `backend/app/models/clinical.py`<br>`backend/app/services/conversation_service.py` | `VitalReading.status = 'NOT_PROVIDED'` | **IMPLEMENTED & VERIFIED** |

---

## 8. Appointments & Care-Team Coordination (AP-01 to AP-05)

| Requirement ID | Requirement Summary | Implementation Module / Files | API Endpoint / Service Method | Verification Status |
| :--- | :--- | :--- | :--- | :--- |
| **AP-01** | Remind upcoming follow-ups at 7d, 3d, 1d intervals | `backend/app/models/appointment.py`<br>`backend/worker/tasks.py` | `Appointment.scheduled_time`, `tasks.check_upcoming_appointments()` | **IMPLEMENTED & VERIFIED** |
| **AP-02** | Record attendance confirmation or inability to attend | `backend/app/models/appointment.py`<br>`backend/app/api/v1/appointments.py` | `Appointment.status = 'CONFIRMED'` / `'DECLINED'` | **IMPLEMENTED & VERIFIED** |
| **AP-03** | Collect reason on decline and create rescheduling task for care team | `backend/app/models/appointment.py`<br>`backend/app/services/conversation_service.py` | `Appointment.reschedule_task_created = True`<br>`Appointment.decline_reason` | **IMPLEMENTED & VERIFIED** |
| **AP-04** | Remind prerequisite diagnostic tests before appointment | `backend/app/models/appointment.py` | `Appointment.prerequisite_instructions` | **IMPLEMENTED & VERIFIED** |
| **AP-05** | Provide appointment lookup on patient voice query | `backend/app/services/conversation_service.py` | Voice step `APPOINTMENT` lookup | **IMPLEMENTED & VERIFIED** |

---

## 9. Knowledge Delivery & Clinical Guardrails (KQ-01 to KQ-05)

| Requirement ID | Requirement Summary | Implementation Module / Files | API Endpoint / Service Method | Verification Status |
| :--- | :--- | :--- | :--- | :--- |
| **KQ-01** | Answer questions strictly from clinician-approved documentation | `backend/app/models/knowledge.py`<br>`backend/app/api/v1/knowledge.py` | `KnowledgeArticle.is_approved = True` | **IMPLEMENTED & VERIFIED** |
| **KQ-02** | State clearly when requested information is unavailable; never invent advice | `backend/app/services/language_service.py` | Prompt: `KNOWLEDGE_UNAVAILABLE` | **IMPLEMENTED & VERIFIED** |
| **KQ-03** | Route medical diagnosis, prognosis, or dosage inquiries to clinician | `backend/app/services/conversation_service.py`<br>`frontend/src/pages/KnowledgeBasePage.tsx` | Route to treating physician callback queue | **IMPLEMENTED & VERIFIED** |
| **KQ-04** | Support versioned knowledge base articles with clinician sign-off | `backend/app/models/knowledge.py` | `KnowledgeArticle.version`, `approved_by` | **IMPLEMENTED & VERIFIED** |
| **KQ-05** | Log all declined / routed queries for audit | `backend/app/models/knowledge.py`<br>`frontend/src/pages/KnowledgeBasePage.tsx` | `DeclinedQueryLog` table<br>`GET /api/v1/knowledge/declined-queries` | **IMPLEMENTED & VERIFIED** |

---

## 10. Alerts & Clinical Escalation (ES-01 to ES-08)

| Requirement ID | Requirement Summary | Implementation Module / Files | API Endpoint / Service Method | Verification Status |
| :--- | :--- | :--- | :--- | :--- |
| **ES-01** | **DETERMINISTIC RULES ENGINE ONLY:** Clinician-configurable thresholds, NEVER LLM decision | `backend/app/services/rules_engine.py`<br>`backend/tests/test_rules_engine.py` | Pure deterministic Python class `RulesEngine`. Zero LLM triage. | **TESTED & VERIFIED** (all `test_rules_engine.py` tests) |
| **ES-02** | Alert on threshold breach, worsening trend, repeated med miss, contact exhaustion | `backend/app/services/rules_engine.py` | `evaluate_vital_reading`, `evaluate_symptom_checkin`, `evaluate_medication_miss`, `evaluate_contact_failure` | **TESTED & VERIFIED** |
| **ES-03** | Deliver emergency red-flag scripts verbatim; advise immediate medical attention | `backend/app/services/language_service.py`<br>`backend/app/services/conversation_service.py` | Prompt `EMERGENCY_RED_FLAG_SCRIPT` | **TESTED & VERIFIED** (`test_red_flag_acute_symptom_emergency`) |
| **ES-04** | Notify designated caregiver via configured channels | `backend/app/models/patient.py`<br>`backend/worker/tasks.py` | `tasks.dispatch_caregiver_alert_notification()` | **IMPLEMENTED & VERIFIED** |
| **ES-05** | Alert payload includes context, trigger, timestamp, trends, vitals/meds | `backend/app/models/rules_alert.py`<br>`backend/app/services/rules_engine.py` | `Alert.supporting_data` JSON payload | **IMPLEMENTED & VERIFIED** |
| **ES-06** | Enforce severity tiers (Critical: 15m, High: 1h, Medium: 4h, Info: next review) | `backend/app/services/rules_engine.py`<br>`backend/worker/tasks.py` | `RulesEngine.get_sla_due_time()`<br>`tasks.monitor_alert_slas()` | **IMPLEMENTED & VERIFIED** |
| **ES-07** | Require explicit acknowledgment and resolution by named clinician with action notes | `backend/app/api/v1/rules_alerts.py`<br>`backend/tests/test_api_integration.py`<br>`frontend/src/pages/AlertsPage.tsx` | `POST /alerts/{id}/acknowledge`<br>`POST /alerts/{id}/resolve` (requires `resolution_action_notes`) | **TESTED & VERIFIED** (`test_full_alert_resolution_lifecycle`) |
| **ES-08** | Multi-indicator composite decline escalation | `backend/app/services/rules_engine.py` | `RulesEngine.evaluate_composite_decline()` | **IMPLEMENTED & VERIFIED** |

---

## 11. Call Management & Scheduling (CM-01 to CM-07)

| Requirement ID | Requirement Summary | Implementation Module / Files | API Endpoint / Service Method | Verification Status |
| :--- | :--- | :--- | :--- | :--- |
| **CM-01** | Record call attempt disposition (completed, no answer, busy, failed, disconnected, wrong person) | `backend/app/models/conversation.py`<br>`frontend/src/pages/CallConsolePage.tsx` | `CallSession.disposition` enum | **IMPLEMENTED & VERIFIED** |
| **CM-02** | Retry failed calls per policy; escalate to caregiver after exhaustion | `backend/app/services/rules_engine.py`<br>`backend/worker/tasks.py`<br>`backend/tests/test_rules_engine.py` | `RulesEngine.evaluate_contact_failure()`<br>`RULE_CONTACT_FAILURE_EXHAUSTED` | **TESTED & VERIFIED** (`test_contact_failure_escalation`) |
| **CM-03** | Defer call on patient request up to max deferrals | `backend/app/services/conversation_service.py` | `CallSession.disposition = 'DEFERRED'` | **IMPLEMENTED & VERIFIED** |
| **CM-04** | Inbound call support; authenticate caller; resume check-in or answer queries | `backend/app/services/conversation_service.py`<br>`backend/app/api/v1/conversation.py` | `POST /api/v1/conversation/inbound-webhook` | **IMPLEMENTED & VERIFIED** |
| **CM-05** | **INTERRUPTION RESUMPTION:** Persist context on drop; resume from interruption point without restarting | `backend/app/services/conversation_service.py`<br>`backend/tests/test_conversation_interruption.py`<br>`frontend/src/components/CallSimulatorModal.tsx` | `ConversationService.resume_interrupted_session()`<br>`CallSession.resume_context` | **TESTED & VERIFIED** (`test_call_interruption_and_resumption`) |
| **CM-06** | Enforce call windows & DND hours | `backend/app/models/patient.py`<br>`backend/worker/tasks.py` | `patient.call_window_start`, `patient.dnd_start` | **IMPLEMENTED & VERIFIED** |
| **CM-07** | Throttle calls to prevent patient annoyance; min 30-min spacing | `backend/worker/tasks.py` | `last_attempt_at <= datetime.utcnow() - timedelta(minutes=30)` | **IMPLEMENTED & VERIFIED** |

---

## 12. Progress Scoring & Multi-Stakeholder Reporting (PR-01 to PR-06)

| Requirement ID | Requirement Summary | Implementation Module / Files | API Endpoint / Service Method | Verification Status |
| :--- | :--- | :--- | :--- | :--- |
| **PR-01** | Calculate daily Care Progress score (weighted composite: Symptoms 30%, Meds 30%, Vitals 25%, Lifestyle 15%) | `backend/app/services/progress_service.py`<br>`backend/app/models/progress.py`<br>`frontend/src/pages/PatientDetailPage.tsx` | `ProgressService.calculate_daily_score()`<br>`DailyProgressScore` table | **IMPLEMENTED & VERIFIED** |
| **PR-02** | Deliver end-of-day voice recovery summary to patient | `backend/app/services/progress_service.py` | `DailyProgressScore.voice_summary_script` | **IMPLEMENTED & VERIFIED** |
| **PR-03** | Provide simplified daily recovery summary to designated caregiver | `backend/app/services/progress_service.py` | `DailyProgressScore.caregiver_summary` | **IMPLEMENTED & VERIFIED** |
| **PR-04** | Generate 7-day and 30-day trend reports for clinical dashboard | `backend/app/services/progress_service.py`<br>`backend/app/api/v1/progress.py` | `GET /api/v1/progress/trends/{patient_id}?days=7/30` | **IMPLEMENTED & VERIFIED** |
| **PR-05** | Surface declining or plateauing patterns before critical threshold breaches | `backend/app/services/progress_service.py`<br>`backend/app/services/rules_engine.py` | Trend evaluation: `DailyProgressScore.trend = 'DECLINING'` | **IMPLEMENTED & VERIFIED** |
| **PR-06** | Enable clinician download / export of recovery summaries | `backend/app/api/v1/progress.py` | `GET /api/v1/progress/export/{patient_id}` | **IMPLEMENTED & VERIFIED** |

---

## 13. Clinical Dashboard & Prioritisation (DB-01 to DB-05)

| Requirement ID | Requirement Summary | Implementation Module / Files | API Endpoint / Service Method | Verification Status |
| :--- | :--- | :--- | :--- | :--- |
| **DB-01** | Overview metrics: active patients, calls today, adherence, open alerts | `backend/app/api/v1/dashboard.py`<br>`frontend/src/pages/DashboardPage.tsx` | `GET /api/v1/dashboard/metrics` | **IMPLEMENTED & VERIFIED** |
| **DB-02** | **EXPLAINABLE PRIORITY PATIENT LIST:** Ranked strictly by explicit clinical rules with transparent inclusion reasons | `backend/app/api/v1/dashboard.py`<br>`frontend/src/pages/DashboardPage.tsx` | `GET /api/v1/dashboard/priority-list`<br>`PriorityPatientItem.inclusion_reasons` | **IMPLEMENTED & VERIFIED** |
| **DB-03** | Consolidated Patient 360 View: care plan, call history, vitals, symptoms, adherence, alerts | `frontend/src/pages/PatientDetailPage.tsx`<br>`backend/app/api/v1/patients.py` | `GET /api/v1/patients/{id}` with consolidated tabs | **IMPLEMENTED & VERIFIED** |
| **DB-04** | Alert triage with SLA timer, one-click acknowledge, resolution with required clinical notes | `frontend/src/pages/AlertsPage.tsx`<br>`backend/app/api/v1/rules_alerts.py` | `POST /alerts/{id}/acknowledge`<br>`POST /alerts/{id}/resolve` | **TESTED & VERIFIED** (`test_full_alert_resolution_lifecycle`) |
| **DB-05** | Role-Based Access Control (RBAC): Clinician, Admin, Caregiver, Patient; facility multi-tenancy | `backend/app/core/security.py`<br>`backend/tests/test_api_integration.py`<br>`frontend/src/context/AuthContext.tsx` | `require_roles()`, `verify_patient_access()`, `AuthContext.switchRole()` | **TESTED & VERIFIED** (`test_rbac_admin_clinician_access`) |

---

## 14. Programme Lifecycle, Consent & Governance (PL-01 to PL-04, GV-01 to GV-05)

| Requirement ID | Requirement Summary | Implementation Module / Files | API Endpoint / Service Method | Verification Status |
| :--- | :--- | :--- | :--- | :--- |
| **PL-01** | Mark programme completion at end of duration; deliver closing voice summary | `backend/app/api/v1/patients.py`<br>`backend/worker/tasks.py` | `Patient.status = 'COMPLETED'` | **IMPLEMENTED & VERIFIED** |
| **PL-02** | Support pause and resume (e.g. readmission) without losing history | `backend/app/api/v1/patients.py`<br>`frontend/src/pages/PatientDetailPage.tsx` | `POST /api/v1/patients/{id}/pause`<br>`POST /api/v1/patients/{id}/resume` | **IMPLEMENTED & VERIFIED** |
| **PL-03** | Immediate cessation of contact on consent withdrawal; log withdrawal scope | `backend/app/api/v1/patients.py`<br>`backend/tests/test_onboarding_consent.py`<br>`frontend/src/pages/PatientDetailPage.tsx` | `POST /api/v1/patients/{id}/withdraw-consent`<br>`Patient.status = 'CONSENT_WITHDRAWN'` | **TESTED & VERIFIED** (`test_consent_withdrawal_halts_contact`) |
| **PL-04** | Caller verification protocol; authenticate patient before clinical disclosures | `backend/app/services/conversation_service.py` | Step `IDENTITY_CHECK` with unauthorized caller refusal | **IMPLEMENTED & VERIFIED** |
| **GV-01** | Healthcare data regulations compliance (DPDP / HIPAA relational-first design) | `backend/app/core/database.py`<br>`backend/app/core/security.py` | PostgreSQL relational tables with row authorization | **IMPLEMENTED & VERIFIED** |
| **GV-02** | Clinician oversight; all automated workflows clinician-reviewed and approved | `backend/app/models/knowledge.py`<br>`backend/app/models/rules_alert.py` | Clinician approval fields, deterministic execution | **IMPLEMENTED & VERIFIED** |
| **GV-03** | Immutable append-only audit trail for calls, reminders, alerts, consent, access events | `backend/app/models/audit.py`<br>`backend/app/core/audit.py` | `AuditLog` table<br>`log_audit_event()` | **IMPLEMENTED & VERIFIED** |
| **GV-04** | Versioned configuration audit log for changes to rules, schedules, thresholds, content | `backend/app/models/audit.py`<br>`backend/app/core/audit.py` | `ConfigAuditLog` table (`old_value_json`, `new_value_json`)<br>`log_config_audit()` | **IMPLEMENTED & VERIFIED** |
| **GV-05** | Complete patient journey reconstruction API and UI tool | `backend/app/core/audit.py`<br>`backend/tests/test_api_integration.py`<br>`frontend/src/pages/AuditTrailPage.tsx` | `GET /api/v1/audit/journey/{patient_id}`<br>`reconstruct_patient_journey()` | **TESTED & VERIFIED** (`test_journey_reconstruction`) |

---

## 15. Summary of Automated Verification Suite

All 18 automated backend tests pass with 100% success rate on PostgreSQL models:
```
backend/tests/test_api_integration.py::test_health_endpoint PASSED
backend/tests/test_api_integration.py::test_rbac_admin_clinician_access PASSED
backend/tests/test_api_integration.py::test_full_alert_resolution_lifecycle PASSED
backend/tests/test_api_integration.py::test_journey_reconstruction PASSED
backend/tests/test_conversation_interruption.py::test_call_interruption_and_resumption PASSED
backend/tests/test_conversation_interruption.py::test_human_transfer_request PASSED
backend/tests/test_language.py::test_language_switch_detection PASSED
backend/tests/test_language.py::test_code_mixed_speech_medication_parsing PASSED
backend/tests/test_language.py::test_code_mixed_vitals_extraction PASSED
backend/tests/test_onboarding_consent.py::test_activation_blocked_without_consent PASSED
backend/tests/test_onboarding_consent.py::test_activation_succeeds_when_all_complete PASSED
backend/tests/test_onboarding_consent.py::test_consent_withdrawal_halts_contact PASSED
backend/tests/test_rules_engine.py::test_deterministic_vitals_critical_threshold PASSED
backend/tests/test_rules_engine.py::test_vitals_plausibility_check PASSED
backend/tests/test_rules_engine.py::test_red_flag_acute_symptom_emergency PASSED
backend/tests/test_rules_engine.py::test_sustained_worsening_trend PASSED
backend/tests/test_rules_engine.py::test_medication_repeated_miss_escalation PASSED
backend/tests/test_rules_engine.py::test_contact_failure_escalation PASSED
======================= 18 passed in 1.31s =======================
```
