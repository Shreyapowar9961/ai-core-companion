-- ==============================================================================
-- AI CARE COMPANION: SUPABASE POSTGRESQL SCHEMA INITIALIZATION
-- ==============================================================================
-- Relational-First Architecture for Post-Discharge Clinical Recovery Platform
-- Supports Supabase Auth, Row-Level Multi-Tenancy, and Immutable Audit Logging

-- 1. Enable Required PostgreSQL Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- 2. Facilities (Multi-Tenancy)
CREATE TABLE IF NOT EXISTS facilities (
    id VARCHAR(64) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    name VARCHAR(255) NOT NULL,
    code VARCHAR(64) UNIQUE NOT NULL,
    contact_phone VARCHAR(32),
    contact_email VARCHAR(128),
    address VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. Patients (ON-01 to ON-07, PL-01 to PL-04)
CREATE TABLE IF NOT EXISTS patients (
    id VARCHAR(64) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    facility_id VARCHAR(64) NOT NULL REFERENCES facilities(id) ON DELETE CASCADE,
    first_name VARCHAR(128) NOT NULL,
    last_name VARCHAR(128) NOT NULL,
    dob DATE NOT NULL,
    gender VARCHAR(32) NOT NULL,
    phone VARCHAR(32) NOT NULL,
    email VARCHAR(128),
    address TEXT,
    emergency_contact_phone VARCHAR(32),
    diagnosis VARCHAR(255) NOT NULL,
    discharge_date DATE NOT NULL,
    programme_duration_days INT DEFAULT 30,
    preferred_language VARCHAR(16) DEFAULT 'en', -- 'mr', 'hi', 'en'
    status VARCHAR(32) DEFAULT 'DRAFT', -- 'DRAFT', 'ACTIVE', 'PAUSED', 'COMPLETED', 'CONSENT_WITHDRAWN'
    paused_at TIMESTAMP WITH TIME ZONE,
    pause_reason VARCHAR(255),
    completed_at TIMESTAMP WITH TIME ZONE,
    call_window_start VARCHAR(8) DEFAULT '09:00',
    call_window_end VARCHAR(8) DEFAULT '19:00',
    checkin_morning_time VARCHAR(8) DEFAULT '09:30',
    checkin_evening_time VARCHAR(8) DEFAULT '18:30',
    dnd_start VARCHAR(8) DEFAULT '21:00',
    dnd_end VARCHAR(8) DEFAULT '08:00',
    retry_limit INT DEFAULT 3,
    max_deferrals INT DEFAULT 2,
    treating_doctor_name VARCHAR(128),
    treating_doctor_phone VARCHAR(64),
    treating_doctor_specialty VARCHAR(128),
    escalation_contacts JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_patients_facility ON patients(facility_id);
CREATE INDEX IF NOT EXISTS idx_patients_status ON patients(status);

-- 4. Designated Caregivers (ON-04)
CREATE TABLE IF NOT EXISTS caregivers (
    id VARCHAR(64) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    patient_id VARCHAR(64) NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    name VARCHAR(128) NOT NULL,
    relationship VARCHAR(64) NOT NULL,
    phone VARCHAR(32) NOT NULL,
    email VARCHAR(128),
    is_authorized BOOLEAN DEFAULT TRUE,
    consented_channels JSONB DEFAULT '["VOICE_CALL", "SMS"]'::jsonb,
    consented_categories JSONB DEFAULT '["ALL"]'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_caregivers_patient ON caregivers(patient_id);

-- 5. Mandatory Explicit Consent (ON-06, PL-03)
CREATE TABLE IF NOT EXISTS consents (
    id VARCHAR(64) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    patient_id VARCHAR(64) UNIQUE NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    voice_contact BOOLEAN DEFAULT FALSE,
    call_recording BOOLEAN DEFAULT FALSE,
    data_processing BOOLEAN DEFAULT FALSE,
    caregiver_disclosure BOOLEAN DEFAULT FALSE,
    emergency_escalation BOOLEAN DEFAULT FALSE,
    consented_at TIMESTAMP WITH TIME ZONE,
    withdrawn_at TIMESTAMP WITH TIME ZONE,
    withdrawal_scope VARCHAR(32),
    consent_notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 6. Care Plans (ON-02, LS-01 to LS-06)
CREATE TABLE IF NOT EXISTS care_plans (
    id VARCHAR(64) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    patient_id VARCHAR(64) NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    diet_instructions TEXT,
    hydration_target_glasses INT DEFAULT 8,
    hydration_interval_hours INT DEFAULT 2,
    activity_target_minutes INT DEFAULT 20,
    activity_target_steps INT DEFAULT 2000,
    physiotherapy_instructions TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 7. Medication Schedules (MD-01, MD-06, MD-09)
CREATE TABLE IF NOT EXISTS medication_schedules (
    id VARCHAR(64) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    care_plan_id VARCHAR(64) NOT NULL REFERENCES care_plans(id) ON DELETE CASCADE,
    patient_id VARCHAR(64) NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    medicine_name VARCHAR(128) NOT NULL,
    dosage VARCHAR(64) NOT NULL,
    frequency VARCHAR(32) NOT NULL,
    dose_times JSONB DEFAULT '["09:00"]'::jsonb,
    instructions TEXT,
    route VARCHAR(32) DEFAULT 'ORAL',
    effective_start_date DATE NOT NULL,
    effective_end_date DATE,
    refill_due_date DATE,
    refill_reminder_days_before INT DEFAULT 3,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_med_schedules_patient ON medication_schedules(patient_id);

-- 8. Medication Adherence Logs (MD-02, MD-04, MD-05)
CREATE TABLE IF NOT EXISTS medication_logs (
    id VARCHAR(64) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    patient_id VARCHAR(64) NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    medication_schedule_id VARCHAR(64) REFERENCES medication_schedules(id) ON DELETE SET NULL,
    medicine_name VARCHAR(128) NOT NULL,
    scheduled_time TIMESTAMP WITH TIME ZONE NOT NULL,
    actual_time TIMESTAMP WITH TIME ZONE,
    status VARCHAR(32) NOT NULL, -- 'TAKEN', 'MISSED', 'DEFERRED', 'PENDING'
    stated_reason VARCHAR(255),
    deferral_count INT DEFAULT 0,
    recorded_via VARCHAR(32) DEFAULT 'VOICE_CALL',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_med_logs_patient ON medication_logs(patient_id);
CREATE INDEX IF NOT EXISTS idx_med_logs_status ON medication_logs(status);

-- 9. Vitals Thresholds (VT-02, VT-03)
CREATE TABLE IF NOT EXISTS vitals_thresholds (
    id VARCHAR(64) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    care_plan_id VARCHAR(64) NOT NULL REFERENCES care_plans(id) ON DELETE CASCADE,
    patient_id VARCHAR(64) NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    vital_type VARCHAR(64) NOT NULL, -- 'SPO2', 'BP_SYSTOLIC', 'GLUCOSE', 'TEMP', 'PULSE'
    unit VARCHAR(16) NOT NULL,
    plausible_min FLOAT NOT NULL,
    plausible_max FLOAT NOT NULL,
    normal_min FLOAT NOT NULL,
    normal_max FLOAT NOT NULL,
    warning_min FLOAT,
    warning_max FLOAT,
    critical_min FLOAT,
    critical_max FLOAT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_vitals_thresh_patient ON vitals_thresholds(patient_id);

-- 10. Vital Readings (VT-01, VT-04, VT-05)
CREATE TABLE IF NOT EXISTS vital_readings (
    id VARCHAR(64) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    patient_id VARCHAR(64) NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    call_session_id VARCHAR(64),
    vital_type VARCHAR(64) NOT NULL,
    value FLOAT,
    secondary_value FLOAT,
    unit VARCHAR(16) NOT NULL,
    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(32) NOT NULL, -- 'NORMAL', 'WARNING', 'CRITICAL', 'IMPLAUSIBLE', 'NOT_PROVIDED'
    voice_confirmed BOOLEAN DEFAULT TRUE,
    notes TEXT
);
CREATE INDEX IF NOT EXISTS idx_vital_readings_patient ON vital_readings(patient_id);

-- 11. Symptom Check-ins (CI-01 to CI-05)
CREATE TABLE IF NOT EXISTS symptom_checkins (
    id VARCHAR(64) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    patient_id VARCHAR(64) NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    call_session_id VARCHAR(64),
    checkin_type VARCHAR(32) NOT NULL, -- 'MORNING_CHECKIN', 'EVENING_CHECKIN'
    pain_level INT DEFAULT 0, -- 0-10 scale
    breathlessness VARCHAR(32) DEFAULT 'none',
    dizziness VARCHAR(32) DEFAULT 'none',
    weakness VARCHAR(32) DEFAULT 'none',
    fever VARCHAR(32) DEFAULT 'none',
    wound_status VARCHAR(32) DEFAULT 'healing_well',
    appetite VARCHAR(32) DEFAULT 'normal',
    sleep_quality VARCHAR(32) DEFAULT 'good',
    mood VARCHAR(32) DEFAULT 'good',
    other_symptoms_verbatim TEXT,
    comparison_with_yesterday JSONB DEFAULT '{}'::jsonb,
    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_symptom_checkins_patient ON symptom_checkins(patient_id);

-- 12. Lifestyle Logs (LS-01 to LS-05)
CREATE TABLE IF NOT EXISTS lifestyle_logs (
    id VARCHAR(64) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    patient_id VARCHAR(64) NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    call_session_id VARCHAR(64),
    log_type VARCHAR(32) NOT NULL, -- 'HYDRATION', 'ACTIVITY', 'MEAL', 'PHYSIOTHERAPY'
    target_value FLOAT,
    actual_value FLOAT,
    unit VARCHAR(32),
    completion_status VARCHAR(32) DEFAULT 'COMPLETED',
    notes TEXT,
    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 13. Call Sessions (CV-01, CM-01 to CM-05)
CREATE TABLE IF NOT EXISTS call_sessions (
    id VARCHAR(64) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    patient_id VARCHAR(64) NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    direction VARCHAR(16) DEFAULT 'OUTBOUND',
    call_type VARCHAR(32) NOT NULL,
    scheduled_time TIMESTAMP WITH TIME ZONE,
    start_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    end_time TIMESTAMP WITH TIME ZONE,
    duration_seconds INT DEFAULT 0,
    status VARCHAR(32) DEFAULT 'IN_PROGRESS',
    disposition VARCHAR(32),
    language_used VARCHAR(16) DEFAULT 'en',
    current_step_key VARCHAR(64),
    resume_context JSONB DEFAULT '{}'::jsonb,
    transferred_to_human BOOLEAN DEFAULT FALSE,
    transfer_reason VARCHAR(255),
    provider_call_id VARCHAR(128),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_call_sessions_patient ON call_sessions(patient_id);

-- 14. Call Turns (CV-03, LN-03)
CREATE TABLE IF NOT EXISTS call_turns (
    id VARCHAR(64) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    call_session_id VARCHAR(64) NOT NULL REFERENCES call_sessions(id) ON DELETE CASCADE,
    turn_index INT NOT NULL,
    step_key VARCHAR(64) NOT NULL,
    agent_prompt TEXT NOT NULL,
    patient_audio_transcript TEXT,
    english_summary TEXT,
    detected_language VARCHAR(16) DEFAULT 'en',
    was_unanswered BOOLEAN DEFAULT FALSE,
    repeat_count INT DEFAULT 0,
    extracted_data JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 15. Appointments (AP-01 to AP-05)
CREATE TABLE IF NOT EXISTS appointments (
    id VARCHAR(64) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    patient_id VARCHAR(64) NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    appointment_type VARCHAR(64) NOT NULL,
    scheduled_time TIMESTAMP WITH TIME ZONE NOT NULL,
    doctor_facility_name VARCHAR(128) NOT NULL,
    location VARCHAR(255),
    preparation_instructions TEXT,
    prerequisite_tests JSONB DEFAULT '[]'::jsonb,
    status VARCHAR(32) DEFAULT 'SCHEDULED',
    attendance_confirmed_at TIMESTAMP WITH TIME ZONE,
    decline_reason VARCHAR(255),
    reschedule_reason VARCHAR(255),
    reschedule_task_created BOOLEAN DEFAULT FALSE,
    reschedule_notes TEXT,
    reminder_sent_7d BOOLEAN DEFAULT FALSE,
    reminder_sent_3d BOOLEAN DEFAULT FALSE,
    reminder_sent_1d BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_appointments_patient ON appointments(patient_id);

-- 16. Approved Knowledge Base & Safety Guardrails (KQ-01 to KQ-05)
CREATE TABLE IF NOT EXISTS knowledge_articles (
    id VARCHAR(64) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    article_code VARCHAR(64) UNIQUE NOT NULL,
    title VARCHAR(255) NOT NULL,
    category VARCHAR(64) NOT NULL,
    keywords JSONB DEFAULT '[]'::jsonb,
    content_en TEXT NOT NULL,
    content_hi TEXT NOT NULL,
    content_mr TEXT NOT NULL,
    version VARCHAR(32) DEFAULT 'v1.0.0',
    is_approved BOOLEAN DEFAULT TRUE,
    approved_by VARCHAR(128) DEFAULT 'Clinical Governance Committee',
    approved_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS declined_query_logs (
    id VARCHAR(64) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    patient_id VARCHAR(64) REFERENCES patients(id) ON DELETE CASCADE,
    call_session_id VARCHAR(64) REFERENCES call_sessions(id) ON DELETE SET NULL,
    query_text TEXT NOT NULL,
    query_type VARCHAR(64) NOT NULL, -- 'DOSAGE', 'DIAGNOSIS', 'PROGNOSIS', 'UNKNOWN_TOPIC'
    routed_to VARCHAR(128) DEFAULT 'CARE_TEAM_ESCALATION_QUEUE',
    standard_response_delivered TEXT,
    logged_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 17. Deterministic Clinical Rules & Escalation Alerts (ES-01 to ES-08)
CREATE TABLE IF NOT EXISTS escalation_rules (
    id VARCHAR(64) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    facility_id VARCHAR(64) REFERENCES facilities(id) ON DELETE CASCADE,
    code VARCHAR(64) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    category VARCHAR(64) NOT NULL,
    severity VARCHAR(32) NOT NULL, -- 'CRITICAL', 'HIGH', 'MEDIUM', 'INFO'
    condition_json JSONB NOT NULL,
    action_json JSONB NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS alerts (
    id VARCHAR(64) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    patient_id VARCHAR(64) NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    rule_code VARCHAR(64) NOT NULL,
    severity VARCHAR(32) NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    supporting_data JSONB DEFAULT '{}'::jsonb,
    status VARCHAR(32) DEFAULT 'OPEN', -- 'OPEN', 'ACKNOWLEDGED', 'RESOLVED'
    sla_due_at TIMESTAMP WITH TIME ZONE NOT NULL,
    acknowledged_at TIMESTAMP WITH TIME ZONE,
    acknowledged_by VARCHAR(128),
    resolved_at TIMESTAMP WITH TIME ZONE,
    resolved_by VARCHAR(128),
    resolution_action_notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_alerts_patient ON alerts(patient_id);
CREATE INDEX IF NOT EXISTS idx_alerts_status ON alerts(status);
CREATE INDEX IF NOT EXISTS idx_alerts_severity ON alerts(severity);

CREATE TABLE IF NOT EXISTS alert_action_logs (
    id VARCHAR(64) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    alert_id VARCHAR(64) NOT NULL REFERENCES alerts(id) ON DELETE CASCADE,
    user_id VARCHAR(128) NOT NULL,
    user_name VARCHAR(128) NOT NULL,
    action VARCHAR(32) NOT NULL,
    notes TEXT,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 18. Daily Progress Scores (PR-01 to PR-06)
CREATE TABLE IF NOT EXISTS daily_progress_scores (
    id VARCHAR(64) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    patient_id VARCHAR(64) NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    score_date DATE NOT NULL,
    overall_score FLOAT NOT NULL,
    symptom_score FLOAT NOT NULL,
    medication_score FLOAT NOT NULL,
    vitals_score FLOAT NOT NULL,
    lifestyle_score FLOAT NOT NULL,
    trend VARCHAR(32) NOT NULL, -- 'IMPROVING', 'STABLE', 'DECLINING'
    voice_summary_script TEXT NOT NULL,
    caregiver_summary TEXT NOT NULL,
    calculated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_patient_score_date UNIQUE (patient_id, score_date)
);

-- 19. Immutable Governance & Configuration Audit Trails (GV-03, GV-04, GV-05)
CREATE TABLE IF NOT EXISTS audit_logs (
    id VARCHAR(64) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    event_type VARCHAR(64) NOT NULL,
    actor_id VARCHAR(128) NOT NULL,
    actor_role VARCHAR(32) DEFAULT 'SYSTEM',
    patient_id VARCHAR(64) REFERENCES patients(id) ON DELETE SET NULL,
    resource VARCHAR(64) NOT NULL,
    details_json JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_audit_patient ON audit_logs(patient_id);
CREATE INDEX IF NOT EXISTS idx_audit_event ON audit_logs(event_type);

CREATE TABLE IF NOT EXISTS config_audit_logs (
    id VARCHAR(64) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    config_type VARCHAR(64) NOT NULL, -- 'RULE', 'SCHEDULE', 'THRESHOLD', 'CONTENT'
    item_id VARCHAR(64) NOT NULL,
    changed_by VARCHAR(128) NOT NULL,
    old_value_json JSONB,
    new_value_json JSONB NOT NULL,
    change_reason VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ==============================================================================
-- INITIAL CLINICAL SEED DATA (Apex Heart & Recovery Center)
-- ==============================================================================
INSERT INTO facilities (id, name, code, contact_phone, contact_email, address)
VALUES ('facility-apex-1', 'Apex Heart & Recovery Institute', 'APEX-CARDIAC', '+912224567890', 'contact@apexcare.org', 'Bandra Kurla Complex, Mumbai, Maharashtra 400051')
ON CONFLICT (id) DO NOTHING;

-- Seed Approved Knowledge Base Articles (KQ-01)
INSERT INTO knowledge_articles (id, article_code, title, category, keywords, content_en, content_hi, content_mr, version, is_approved, approved_by)
VALUES 
(
    'kb-art-1', 'CABG_WOUND', 'Post-CABG Sternal Incision Care', 'WOUND_CARE',
    '["sternal", "wound", "incision", "bathing", "shower", "dressing", "pus", "redness"]'::jsonb,
    'Keep your sternal incision clean and dry. Shower gently using mild soap and pat dry with a clean towel; do not rub or soak the incision. Check daily for redness, warmth, or drainage.',
    'अपने सीने के घाव को साफ और सूखा रखें। हल्के साबुन से नहाएं और साफ तौलिए से थपथपाकर सुखाएं। घाव को रगड़ें नहीं। लालिमा या मवाद दिखने पर तुरंत डॉक्टर को बताएं।',
    'छातीवरील जखम स्वच्छ आणि कोरडी ठेवा. मऊ साबणाने हळुवार आंघोळ करा आणि स्वच्छ टॉवेलने कोरडी करा. जखमेला चोळू नका. लाली किंवा पू दिसल्यास ताबडतोब डॉक्टरांशी संपर्क साधा.',
    'v1.0.0', TRUE, 'Dr. Neha Kulkarni'
),
(
    'kb-art-2', 'STENT_HYDRATION', 'Post-Angioplasty Hydration & Rest', 'LIFESTYLE',
    '["water", "hydration", "rest", "lifting", "weight", "exercise", "contrast"]'::jsonb,
    'Drink at least 8 to 10 glasses of water daily to flush the contrast dye used during angioplasty. Avoid lifting heavy weights (over 5kg) for the first week.',
    'एंजियोप्लास्टी के बाद इस्तेमाल की गई डाई को शरीर से बाहर निकालने के लिए रोजाना 8 से 10 गिलास पानी पिएं। पहले हफ्ते 5 किलो से ज्यादा वजन उठाने से बचें।',
    'एंजिओप्लास्टीनंतर शरीरातून रंगद्रव्य बाहेर टाकण्यासाठी दररोज 8 ते 10 भांडी पाणी प्या. पहिल्या आठवड्यात 5 किलोपेक्षा जास्त वजन उचलणे टाळा.',
    'v1.0.0', TRUE, 'Dr. Sharma'
)
ON CONFLICT (id) DO NOTHING;

-- Seed Deterministic Clinical Rules (ES-01, VT-02, VT-03)
INSERT INTO escalation_rules (id, facility_id, code, name, category, severity, condition_json, action_json, is_active)
VALUES
(
    'rule-spo2-crit', 'facility-apex-1', 'RULE_VITALS_SPO2_CRITICAL',
    'Critical Low SpO2 Threshold Breach', 'VITALS', 'CRITICAL',
    '{"parameter": "spo2", "operator": "<", "threshold_default": 88, "plausible_min": 50, "plausible_max": 100}'::jsonb,
    '{"sla_minutes": 15, "notify_caregiver": true, "emergency_script": true}'::jsonb, TRUE
),
(
    'rule-redflag-emergency', 'facility-apex-1', 'RULE_RED_FLAG_EMERGENCY',
    'Acute Red-Flag Emergency Presentation', 'SYMPTOMS', 'CRITICAL',
    '{"pain_level_min": 8, "acute_breathlessness": true, "purulent_wound_discharge": true}'::jsonb,
    '{"sla_minutes": 15, "emergency_script": true, "immediate_care_team_alert": true}'::jsonb, TRUE
),
(
    'rule-worsening-breathless', 'facility-apex-1', 'RULE_SYMPTOM_SUSTAINED_WORSENING_BREATHLESSNESS',
    'Sustained Deteriorating Breathlessness Trend', 'SYMPTOMS', 'HIGH',
    '{"symptom": "breathlessness", "consecutive_worsening_days": 2}'::jsonb,
    '{"sla_minutes": 60, "notify_caregiver": true, "queue_physician_review": true}'::jsonb, TRUE
),
(
    'rule-med-repeated-miss', 'facility-apex-1', 'RULE_MED_REPEATED_MISS',
    'Repeated Medication Miss Against Threshold', 'MEDICATION', 'HIGH',
    '{"consecutive_misses_threshold": 2}'::jsonb,
    '{"sla_minutes": 60, "notify_caregiver": true, "medication_adherence_review": true}'::jsonb, TRUE
)
ON CONFLICT (id) DO NOTHING;
