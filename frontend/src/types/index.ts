export type UserRole = 'ADMIN' | 'CLINICIAN' | 'CAREGIVER' | 'PATIENT';

export interface AuthUser {
  id: string;
  email: string;
  role: UserRole;
  name: string;
  facility_id?: string;
  patient_id?: string;
}

export interface Consent {
  id: string;
  patient_id: string;
  voice_contact: boolean;
  call_recording: boolean;
  data_processing: boolean;
  caregiver_disclosure: boolean;
  emergency_escalation: boolean;
  consented_at?: string;
  withdrawn_at?: string;
  withdrawal_scope?: string;
}

export interface Caregiver {
  id: string;
  patient_id: string;
  name: string;
  relationship: string;
  phone: string;
  email?: string;
  is_authorized: boolean;
  consented_channels: string[];
  consented_categories: string[];
}

export interface MedicationSchedule {
  id: string;
  patient_id: string;
  medicine_name: string;
  dosage: string;
  frequency: string;
  dose_times: string[];
  instructions?: string;
  route: string;
  effective_start_date: string;
  is_active: boolean;
}

export interface VitalsThreshold {
  id: string;
  patient_id: string;
  vital_type: string;
  unit: string;
  plausible_min: number;
  plausible_max: number;
  normal_min: number;
  normal_max: number;
  warning_min?: number;
  warning_max?: number;
  critical_min?: number;
  critical_max?: number;
}

export interface CarePlan {
  id: string;
  patient_id: string;
  diet_instructions?: string;
  hydration_target_glasses: number;
  hydration_interval_hours: number;
  activity_target_minutes: number;
  activity_target_steps: number;
  physiotherapy_instructions?: string;
  medications: MedicationSchedule[];
  vitals_thresholds: VitalsThreshold[];
}

export interface Patient {
  id: string;
  facility_id: string;
  first_name: string;
  last_name: string;
  dob: string;
  gender: string;
  phone: string;
  email?: string;
  address?: string;
  emergency_contact_phone?: string;
  diagnosis: string;
  discharge_date: string;
  programme_duration_days: number;
  preferred_language: 'en' | 'hi' | 'mr';
  status: 'DRAFT' | 'ACTIVE' | 'PAUSED' | 'COMPLETED' | 'CONSENT_WITHDRAWN';
  call_window_start: string;
  call_window_end: string;
  checkin_morning_time: string;
  checkin_evening_time: string;
  dnd_start: string;
  dnd_end: string;
  retry_limit: number;
  max_deferrals: number;
  treating_doctor_name?: string;
  treating_doctor_phone?: string;
  treating_doctor_specialty?: string;
  created_at: string;
  consent?: Consent;
  caregivers?: Caregiver[];
  care_plan?: CarePlan;
}

export interface SymptomCheckin {
  id: string;
  patient_id: string;
  call_session_id?: string;
  checkin_type: string;
  recorded_at: string;
  pain_level: number;
  breathlessness: string;
  dizziness: string;
  weakness: string;
  fever: string;
  wound_status: string;
  other_symptoms_verbatim?: string;
  comparison_with_yesterday: Record<string, string>;
}

export interface VitalReading {
  id: string;
  patient_id: string;
  call_session_id?: string;
  vital_type: string;
  value?: number;
  secondary_value?: number;
  unit: string;
  recorded_at: string;
  status: 'NORMAL' | 'WARNING' | 'CRITICAL' | 'IMPLAUSIBLE' | 'NOT_PROVIDED';
  voice_confirmed: boolean;
  notes?: string;
}

export interface MedicationLog {
  id: string;
  patient_id: string;
  medication_schedule_id?: string;
  medicine_name: string;
  scheduled_time: string;
  actual_time?: string;
  status: 'TAKEN' | 'MISSED' | 'DEFERRED' | 'PENDING';
  stated_reason?: string;
  deferral_count: number;
  recorded_via: string;
}

export interface LifestyleLog {
  id: string;
  patient_id: string;
  log_type: string;
  target_value?: number;
  actual_value?: number;
  unit?: string;
  completion_status: string;
  notes?: string;
  recorded_at: string;
}

export interface CallSession {
  id: string;
  patient_id: string;
  direction: 'INBOUND' | 'OUTBOUND';
  call_type: string;
  scheduled_time?: string;
  start_time: string;
  end_time?: string;
  duration_seconds: number;
  status: 'SCHEDULED' | 'RINGING' | 'IN_PROGRESS' | 'COMPLETED' | 'FAILED' | 'INTERRUPTED';
  disposition?: 'COMPLETED' | 'NO_ANSWER' | 'BUSY' | 'FAILED' | 'DISCONNECTED' | 'REFUSED' | 'WRONG_PERSON' | 'DEFERRED' | 'PARTIAL';
  language_used: 'en' | 'hi' | 'mr';
  current_step_key?: string;
  resume_context?: Record<string, any>;
  transferred_to_human: boolean;
  transfer_reason?: string;
  created_at: string;
}

export interface CallTurn {
  id: string;
  call_session_id: string;
  turn_index: number;
  agent_prompt: string;
  patient_audio_transcript?: string;
  detected_language: string;
  was_unanswered: boolean;
  created_at: string;
}

export interface Alert {
  id: string;
  patient_id: string;
  rule_code: string;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'INFO';
  title: string;
  description: string;
  status: 'OPEN' | 'ACKNOWLEDGED' | 'RESOLVED';
  sla_due_at: string;
  acknowledged_at?: string;
  acknowledged_by?: string;
  resolved_at?: string;
  resolved_by?: string;
  resolution_action_notes?: string;
  supporting_data?: Record<string, any>;
  created_at: string;
}

export interface EscalationRule {
  id: string;
  code: string;
  name: string;
  category: string;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'INFO';
  condition_json: Record<string, any>;
  action_json: Record<string, any>;
  is_active: boolean;
  facility_id?: string;
}

export interface DailyProgressScore {
  id: string;
  patient_id: string;
  score_date: string;
  overall_score: number;
  symptom_score: number;
  medication_score: number;
  vitals_score: number;
  lifestyle_score: number;
  trend: 'IMPROVING' | 'STABLE' | 'DECLINING';
  voice_summary_script: string;
  caregiver_summary: string;
}

export interface PriorityPatientItem {
  patient_id: string;
  first_name: string;
  last_name: string;
  diagnosis: string;
  status: string;
  priority_tier: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  priority_score: number;
  inclusion_reasons: string[];
  open_alerts_count: number;
  medication_adherence_7d: number;
  last_call_disposition?: string;
  last_call_time?: string;
}

export interface DashboardMetrics {
  total_active_patients?: number;
  active_patients?: number;
  assigned_patient_count?: number;
  requiring_clinician_review_count?: number;
  upcoming_checkins_count?: number;
  overdue_checkins_count?: number;
  overall_adherence_rate?: number;
  avg_medication_adherence?: number;
  critical_alerts_count?: number;
  high_alerts_count?: number;
  calls_completed_today?: number;
  calls_scheduled_today?: number;
  active_declining_trends_count?: number;
  recent_feedback_count?: number;
  recent_feedback?: {
    id: string;
    patient_id: string;
    rating: number;
    category: string;
    comments?: string;
    created_at: string;
  }[];
}

export interface KnowledgeArticle {
  id: string;
  title: string;
  category: string;
  condition_name?: string;
  content_en: string;
  content_hi?: string;
  content_mr?: string;
  version: number;
  is_approved: boolean;
  approved_by?: string;
  updated_at: string;
}

export interface DeclinedQueryLog {
  id: string;
  patient_id: string;
  call_session_id?: string;
  query_text: string;
  query_type: string;
  routed_to: string;
  standard_response_delivered: string;
  created_at: string;
}

export interface AuditEvent {
  timestamp: string;
  type: string;
  subtype: string;
  actor?: string;
  resource?: string;
  details?: Record<string, any>;
  direction?: string;
  status?: string;
  disposition?: string;
  language?: string;
  value?: number;
  unit?: string;
  notes?: string;
}

export interface PatientJourney {
  patient_id: string;
  total_events: number;
  events: AuditEvent[];
}

export interface PrescriptionUpload {
  id: string;
  patient_id: string;
  filename: string;
  file_size: number;
  mime_type: string;
  status: 'UPLOADED' | 'OCR_PROCESSED' | 'VERIFIED' | 'REJECTED';
  raw_ocr_text?: string;
  extracted_medications: Array<{
    medicine_name: string;
    dosage: string;
    frequency: string;
    dose_times: string[];
    instructions?: string;
    duration?: string;
    status: string;
    needs_review: boolean;
  }>;
  verified_medications?: Array<{
    medicine_name: string;
    dosage: string;
    frequency: string;
    dose_times: string[];
    instructions?: string;
    route?: string;
    duration?: string;
  }>;
  clinician_notes?: string;
  verified_by?: string;
  verified_at?: string;
  created_at: string;
}

export interface MonitoringPlan {
  id?: string;
  has_plan?: boolean;
  patient_id: string;
  start_date: string;
  end_date: string;
  frequency: string;
  timezone?: string;
  approved_questions: string[];
  communication_channel: string;
  is_active: boolean;
}

export interface CheckinTask {
  id: string;
  scheduled_for: string;
  completed_at?: string;
  status: 'PENDING' | 'COMPLETED' | 'MISSED' | 'EXPIRED';
  channel: string;
  category: 'ROUTINE' | 'FOLLOW_UP_REQUIRED' | 'NEEDS_CLINICIAN_REVIEW' | 'UNANSWERED';
  category_reason?: string;
  alert_id?: string;
  response?: Record<string, any>;
  is_due?: boolean;
}

export interface CommunicationLog {
  id: string;
  channel: string; // SIMULATED_VOICE, SIMULATED_WHATSAPP, SIMULATED_SMS
  message_type: string;
  recipient_phone?: string;
  content: string;
  status: 'GENERATED' | 'SENT' | 'DELIVERED' | 'VIEWED' | 'RESPONDED' | 'FAILED';
  is_simulated: boolean;
  sent_at: string;
}

export interface PatientFeedback {
  id: string;
  rating: number;
  category: string;
  comments?: string;
  created_at: string;
}

export interface PatientDashboardSummary {
  patient_name: string;
  diagnosis: string;
  preferred_language: 'en' | 'hi' | 'mr';
  recovery_status: string;
  days_since_discharge: number;
  progress_score: number;
  medication_summary: {
    total: number;
    taken: number;
    missed: number;
    pending: number;
    adherence_rate: number;
  };
  next_checkin: {
    id?: string;
    scheduled_for: string;
    channel: string;
    is_due: boolean;
  };
  doctor: {
    name: string;
    phone: string;
  };
  total_notifications: number;
}
