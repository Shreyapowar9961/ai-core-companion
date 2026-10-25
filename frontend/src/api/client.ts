import {
  Patient, Alert, PriorityPatientItem, DashboardMetrics, DailyProgressScore,
  SymptomCheckin, VitalReading, CallSession, CallTurn, KnowledgeArticle,
  DeclinedQueryLog, EscalationRule, PatientJourney
} from '../types';

const API_BASE = '/api/v1';

async function fetchWithAuth<T>(
  url: string,
  token: string,
  options: RequestInit = {}
): Promise<T> {
  const headers = {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`,
    ...options.headers,
  };

  try {
    const res = await fetch(`${API_BASE}${url}`, {
      ...options,
      headers,
    });

    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.detail || `HTTP Error ${res.status}`);
    }

    return await res.json();
  } catch (err: any) {
    console.warn(`API call ${url} fallback/note:`, err.message);
    throw err;
  }
}

export const apiClient = {
  // Dashboard & Metrics
  getDashboardMetrics: (token: string, facilityId?: string) =>
    fetchWithAuth<DashboardMetrics>(`/dashboard/metrics${facilityId ? `?facility_id=${facilityId}` : ''}`, token),

  getPriorityPatients: (token: string, facilityId?: string) =>
    fetchWithAuth<PriorityPatientItem[]>(`/dashboard/priority-list${facilityId ? `?facility_id=${facilityId}` : ''}`, token),

  // Patients
  getPatients: (token: string, facilityId?: string) =>
    fetchWithAuth<Patient[]>(`/patients/${facilityId ? `?facility_id=${facilityId}` : ''}`, token),

  getPatient: (token: string, id: string) =>
    fetchWithAuth<Patient>(`/patients/${id}`, token),

  registerPatient: (token: string, data: any) =>
    fetchWithAuth<Patient>(`/patients/`, token, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  pausePatient: (token: string, id: string, reason: string) =>
    fetchWithAuth<Patient>(`/patients/${id}/pause`, token, {
      method: 'POST',
      body: JSON.stringify({ reason }),
    }),

  resumePatient: (token: string, id: string, reason: string) =>
    fetchWithAuth<Patient>(`/patients/${id}/resume`, token, {
      method: 'POST',
      body: JSON.stringify({ reason }),
    }),

  withdrawConsent: (token: string, id: string, scope: string = 'FULL', reason?: string) =>
    fetchWithAuth<any>(`/patients/${id}/withdraw-consent`, token, {
      method: 'POST',
      body: JSON.stringify({ withdrawal_scope: scope, reason }),
    }),

  // Clinical & Vitals
  getPatientVitals: (token: string, patientId: string) =>
    fetchWithAuth<VitalReading[]>(`/vitals/history/${patientId}`, token),

  getPatientSymptoms: (token: string, patientId: string) =>
    fetchWithAuth<SymptomCheckin[]>(`/checkins/history/${patientId}`, token),

  recordManualVitals: (token: string, patientId: string, vitalType: string, value: number, secondaryValue?: number, unit: string = '%') =>
    fetchWithAuth<VitalReading>(`/vitals/record`, token, {
      method: 'POST',
      body: JSON.stringify({
        patient_id: patientId,
        vital_type: vitalType,
        value,
        secondary_value: secondaryValue,
        unit,
        voice_confirmed: true
      }),
    }),

  // Progress & Reporting
  getPatientProgressScores: (token: string, patientId: string) =>
    fetchWithAuth<DailyProgressScore[]>(`/progress/history/${patientId}`, token),

  getTodayProgressScore: (token: string, patientId: string) =>
    fetchWithAuth<DailyProgressScore>(`/progress/today/${patientId}`, token),

  // Alerts & Triage
  getAlerts: (token: string, status?: string) =>
    fetchWithAuth<Alert[]>(`/rules-alerts/alerts${status ? `?status_filter=${status}` : ''}`, token),

  acknowledgeAlert: (token: string, alertId: string, notes?: string) =>
    fetchWithAuth<Alert>(`/rules-alerts/alerts/${alertId}/acknowledge`, token, {
      method: 'POST',
      body: JSON.stringify({ notes }),
    }),

  resolveAlert: (token: string, alertId: string, resolutionActionNotes: string) =>
    fetchWithAuth<Alert>(`/rules-alerts/alerts/${alertId}/resolve`, token, {
      method: 'POST',
      body: JSON.stringify({ resolution_action_notes: resolutionActionNotes }),
    }),

  // Conversation & Call Simulator
  startCallSession: (token: string, patientId: string, callType: string = 'MORNING_CHECKIN', language?: string) =>
    fetchWithAuth<any>(`/conversation/sessions/initiate`, token, {
      method: 'POST',
      body: JSON.stringify({
        patient_id: patientId,
        call_type: callType,
        direction: 'OUTBOUND',
        initial_language: language
      }),
    }),

  processCallTurn: (token: string, sessionId: string, userSpeech: string) =>
    fetchWithAuth<any>(`/conversation/turns/process`, token, {
      method: 'POST',
      body: JSON.stringify({
        session_id: sessionId,
        user_speech: userSpeech
      }),
    }),

  resumeInterruptedCall: (token: string, sessionId: string) =>
    fetchWithAuth<any>(`/conversation/sessions/${sessionId}/resume`, token, {
      method: 'POST',
    }),

  getPatientCalls: (token: string, patientId: string) =>
    fetchWithAuth<CallSession[]>(`/conversation/patient/${patientId}/calls`, token),

  // Rules Engine
  getRules: (token: string) =>
    fetchWithAuth<EscalationRule[]>(`/rules-alerts/rules`, token),

  saveRule: (token: string, rule: any) =>
    fetchWithAuth<EscalationRule>(`/rules-alerts/rules`, token, {
      method: 'POST',
      body: JSON.stringify(rule),
    }),

  // Knowledge Base
  getKnowledgeArticles: (token: string) =>
    fetchWithAuth<KnowledgeArticle[]>(`/knowledge/articles`, token),

  getDeclinedQueries: (token: string) =>
    fetchWithAuth<DeclinedQueryLog[]>(`/knowledge/declined-queries`, token),

  // Audit & Governance
  getPatientJourney: (token: string, patientId: string) =>
    fetchWithAuth<PatientJourney>(`/audit/journey/${patientId}`, token),
};
