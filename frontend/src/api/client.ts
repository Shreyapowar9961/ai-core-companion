import {
  Patient, Alert, PriorityPatientItem, DashboardMetrics, DailyProgressScore,
  SymptomCheckin, VitalReading, CallSession, CallTurn, KnowledgeArticle,
  DeclinedQueryLog, EscalationRule, PatientJourney,
  PrescriptionUpload, MonitoringPlan, CheckinTask, CommunicationLog, PatientFeedback, PatientDashboardSummary
} from '../types';

const API_BASE = '/api/v1';

async function fetchWithAuth<T>(
  url: string,
  token?: string | null,
  options: RequestInit = {}
): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
    ...(options.headers as Record<string, string> || {}),
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
  // Authentication
  login: async (email: string, password: string) => {
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.detail || 'Authentication failed. Please check credentials.');
    }
    return await res.json();
  },

  getMe: (token?: string | null) =>
    fetchWithAuth<any>(`/auth/me`, token),

  logout: async (token?: string | null) => {
    if (!token) return;
    try {
      await fetch(`${API_BASE}/auth/logout`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        }
      });
    } catch (e) {
      // Best-effort logout notification
    }
  },

  // Dashboard & Metrics
  getDashboardMetrics: (token?: string | null, facilityId?: string) =>
    fetchWithAuth<DashboardMetrics>(`/dashboard/summary${facilityId ? `?facility_id=${facilityId}` : ''}`, token),

  getPriorityPatients: (token?: string | null, facilityId?: string) =>
    fetchWithAuth<PriorityPatientItem[]>(`/dashboard/priority-patients${facilityId ? `?facility_id=${facilityId}` : ''}`, token),

  getPatientEvidenceSummary: (token: string | null | undefined, patientId: string) =>
    fetchWithAuth<any>(`/dashboard/patient/${patientId}/evidence-summary`, token),

  // Patients
  getPatients: (token?: string | null, facilityId?: string) =>
    fetchWithAuth<Patient[]>(`/patients/${facilityId ? `?facility_id=${facilityId}` : ''}`, token),

  getPatient: (token: string | null | undefined, id: string) =>
    fetchWithAuth<Patient>(`/patients/${id}`, token),

  registerPatient: (token: string | null | undefined, data: any) =>
    fetchWithAuth<Patient>(`/patients/`, token, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  pausePatient: (token: string | null | undefined, id: string, reason: string) =>
    fetchWithAuth<Patient>(`/patients/${id}/pause`, token, {
      method: 'POST',
      body: JSON.stringify({ reason }),
    }),

  resumePatient: (token: string | null | undefined, id: string, reason: string) =>
    fetchWithAuth<Patient>(`/patients/${id}/resume`, token, {
      method: 'POST',
      body: JSON.stringify({ reason }),
    }),

  withdrawConsent: (token: string | null | undefined, id: string, scope: string = 'FULL', reason?: string) =>
    fetchWithAuth<any>(`/patients/${id}/consent/withdraw`, token, {
      method: 'POST',
      body: JSON.stringify({ scope, reason }),
    }),

  // Clinical & Vitals
  getPatientVitals: (token: string | null | undefined, patientId: string) =>
    fetchWithAuth<VitalReading[]>(`/vitals/patient/${patientId}/readings`, token),

  getPatientSymptoms: (token: string | null | undefined, patientId: string) =>
    fetchWithAuth<SymptomCheckin[]>(`/checkins/patient/${patientId}`, token),

  recordManualVitals: (token: string | null | undefined, patientId: string, vitalType: string, value: number, secondaryValue?: number, unit: string = '%') =>
    fetchWithAuth<VitalReading>(`/vitals/patient/${patientId}/reading`, token, {
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
  getPatientProgressScores: (token: string | null | undefined, patientId: string) =>
    fetchWithAuth<DailyProgressScore[]>(`/progress/patient/${patientId}/trends`, token),

  getTodayProgressScore: (token: string | null | undefined, patientId: string) =>
    fetchWithAuth<DailyProgressScore>(`/progress/patient/${patientId}/today`, token),

  // Alerts & Triage
  getAlerts: (token?: string | null, status?: string) =>
    fetchWithAuth<Alert[]>(`/rules-alerts/alerts${status ? `?status_filter=${status}` : ''}`, token),

  acknowledgeAlert: (token: string | null | undefined, alertId: string, notes?: string) =>
    fetchWithAuth<Alert>(`/rules-alerts/alerts/${alertId}/acknowledge`, token, {
      method: 'POST',
      body: JSON.stringify({ notes }),
    }),

  resolveAlert: (token: string | null | undefined, alertId: string, resolutionActionNotes: string) =>
    fetchWithAuth<Alert>(`/rules-alerts/alerts/${alertId}/resolve`, token, {
      method: 'POST',
      body: JSON.stringify({ resolution_action_notes: resolutionActionNotes }),
    }),

  // Conversation & Call Simulator
  startCallSession: (token: string | null | undefined, patientId: string, callType: string = 'MORNING_CHECKIN', language?: string) =>
    fetchWithAuth<any>(`/conversation/start`, token, {
      method: 'POST',
      body: JSON.stringify({
        patient_id: patientId,
        call_type: callType,
        direction: 'OUTBOUND',
        language: language,
        initial_language: language
      }),
    }),

  processCallTurn: (token: string | null | undefined, sessionId: string, userSpeech: string) =>
    fetchWithAuth<any>(`/conversation/turn`, token, {
      method: 'POST',
      body: JSON.stringify({
        session_id: sessionId,
        user_speech_text: userSpeech,
        user_speech: userSpeech
      }),
    }),

  resumeInterruptedCall: (token: string | null | undefined, sessionId: string) =>
    fetchWithAuth<any>(`/conversation/resume`, token, {
      method: 'POST',
      body: JSON.stringify({ session_id: sessionId }),
    }),

  getPatientCalls: (token: string | null | undefined, patientId: string) =>
    fetchWithAuth<CallSession[]>(`/conversation/patient/${patientId}/calls`, token),

  // Rules Engine
  getRules: (token?: string | null) =>
    fetchWithAuth<EscalationRule[]>(`/rules-alerts/rules`, token),

  saveRule: (token: string | null | undefined, rule: any) =>
    fetchWithAuth<EscalationRule>(`/rules-alerts/rules`, token, {
      method: 'POST',
      body: JSON.stringify(rule),
    }),

  // Knowledge Base
  getKnowledgeArticles: (token?: string | null) =>
    fetchWithAuth<KnowledgeArticle[]>(`/knowledge/articles`, token),

  getDeclinedQueries: (token?: string | null) =>
    fetchWithAuth<DeclinedQueryLog[]>(`/knowledge/declined-queries`, token),

  // Audit & Governance
  getPatientJourney: (token: string | null | undefined, patientId: string) =>
    fetchWithAuth<PatientJourney>(`/audit/journey/${patientId}`, token),

  // Phase 2: Patient Registration & Password Reset
  registerPatientAccount: async (data: { email: string; password: string; phone: string; patient_id?: string }) => {
    const res = await fetch(`${API_BASE}/auth/patient-register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.detail || 'Patient registration failed.');
    }
    return await res.json();
  },

  resetPassword: async (email: string, newPassword: string) => {
    const res = await fetch(`${API_BASE}/auth/reset-password`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, new_password: newPassword }),
    });
    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.detail || 'Password reset failed.');
    }
    return await res.json();
  },

  // Phase 2: Patient Portal Endpoints
  getPortalProfile: (token?: string | null) =>
    fetchWithAuth<any>(`/portal/profile`, token),

  getPortalDashboard: (token?: string | null) =>
    fetchWithAuth<PatientDashboardSummary>(`/portal/dashboard`, token),

  getPortalCheckinsUpcoming: (token?: string | null) =>
    fetchWithAuth<CheckinTask[]>(`/portal/checkins/upcoming`, token),

  getPortalCheckinsHistory: (token?: string | null) =>
    fetchWithAuth<any[]>(`/portal/checkins/history`, token),

  submitPortalCheckin: (token: string | null | undefined, data: any) =>
    fetchWithAuth<any>(`/portal/checkins/submit`, token, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  getPortalMedicationsSchedule: (token?: string | null) =>
    fetchWithAuth<any[]>(`/portal/medications/schedule`, token),

  getPortalMedicationsHistory: (token?: string | null) =>
    fetchWithAuth<any[]>(`/portal/medications/history`, token),

  confirmPortalMedicationTaken: (token: string | null | undefined, data: any) =>
    fetchWithAuth<any>(`/portal/medications/confirm-taken`, token, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  reportPortalMedicationMissed: (token: string | null | undefined, data: any) =>
    fetchWithAuth<any>(`/portal/medications/report-missed`, token, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  getPortalNotifications: (token?: string | null) =>
    fetchWithAuth<CommunicationLog[]>(`/portal/notifications`, token),

  getPortalCommunications: (token?: string | null) =>
    fetchWithAuth<CommunicationLog[]>(`/portal/communications`, token),

  submitPortalFeedback: (token: string | null | undefined, data: { rating: number; category: string; comments?: string; checkin_task_id?: string }) =>
    fetchWithAuth<any>(`/portal/feedback`, token, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  getPortalFeedback: (token?: string | null) =>
    fetchWithAuth<PatientFeedback[]>(`/portal/feedback`, token),

  updatePortalLanguage: (token: string | null | undefined, language: string) =>
    fetchWithAuth<any>(`/portal/language`, token, {
      method: 'PUT',
      body: JSON.stringify({ language }),
    }),

  // Phase 4: Prescriptions & OCR
  uploadPrescription: async (token: string | null | undefined, patientId: string, file: File) => {
    const formData = new FormData();
    formData.append('patient_id', patientId);
    formData.append('file', file);

    const headers: Record<string, string> = {};
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const res = await fetch(`${API_BASE}/prescriptions/upload`, {
      method: 'POST',
      headers,
      body: formData,
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Prescription upload failed.');
    }
    return await res.json();
  },

  getPrescriptionsForPatient: (token: string | null | undefined, patientId: string) =>
    fetchWithAuth<PrescriptionUpload[]>(`/prescriptions/patient/${patientId}`, token),

  verifyPrescription: (token: string | null | undefined, prescriptionId: string, data: any) =>
    fetchWithAuth<any>(`/prescriptions/${prescriptionId}/verify`, token, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  // Phase 3 & 5: Monitoring & Communications
  getMonitoringPlan: (token: string | null | undefined, patientId: string) =>
    fetchWithAuth<MonitoringPlan>(`/monitoring/plans/patient/${patientId}`, token),

  saveMonitoringPlan: (token: string | null | undefined, data: MonitoringPlan) =>
    fetchWithAuth<any>(`/monitoring/plans`, token, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  getMonitoringTasks: (token: string | null | undefined, patientId: string) =>
    fetchWithAuth<CheckinTask[]>(`/monitoring/tasks/patient/${patientId}`, token),

  triggerMonitoringScheduler: (token?: string | null) =>
    fetchWithAuth<any>(`/monitoring/scheduler/trigger`, token, { method: 'POST' }),

  getPatientCommunications: (token: string | null | undefined, patientId: string) =>
    fetchWithAuth<CommunicationLog[]>(`/monitoring/communications/patient/${patientId}`, token),

  getPatientFeedback: (token: string | null | undefined, patientId: string) =>
    fetchWithAuth<PatientFeedback[]>(`/monitoring/feedback/patient/${patientId}`, token),
};
