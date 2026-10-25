import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { apiClient } from '../api/client';
import { Patient, SymptomCheckin, VitalReading, CallSession, Alert, DailyProgressScore } from '../types';
import { StatusBadge } from '../components/StatusBadge';
import {
  ArrowLeft,
  User,
  Heart,
  Pill,
  Activity,
  PhoneCall,
  AlertTriangle,
  Clock,
  ShieldCheck,
  PauseCircle,
  PlayCircle,
  RotateCcw,
  CheckCircle2,
  Calendar,
  Volume2
} from 'lucide-react';

export const PatientDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const patientId = id || 'patient-demo-1';
  const { token, currentUser } = useAuth();
  const navigate = useNavigate();

  const [activeTab, setActiveTab] = useState<'overview' | 'vitals' | 'symptoms' | 'meds' | 'calls' | 'alerts'>('overview');
  const [patient, setPatient] = useState<Patient | null>(null);
  const [vitals, setVitals] = useState<VitalReading[]>([]);
  const [symptoms, setSymptoms] = useState<SymptomCheckin[]>([]);
  const [calls, setCalls] = useState<CallSession[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [todayScore, setTodayScore] = useState<DailyProgressScore | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Manual vital input modal
  const [showVitalModal, setShowVitalModal] = useState(false);
  const [newVitalType, setNewVitalType] = useState('SPO2');
  const [newVitalVal, setNewVitalVal] = useState<number>(97);
  const [newVitalDia, setNewVitalDia] = useState<number>(80);

  // Consent & Lifecycle actions
  const [pauseReason, setPauseReason] = useState('');
  const [showPauseModal, setShowPauseModal] = useState(false);

  useEffect(() => {
    setIsLoading(true);
    apiClient.getPatient(token, patientId)
      .then((data) => setPatient(data))
      .catch(() => {
        // Fallback demo patient
        setPatient({
          id: patientId,
          facility_id: 'facility-apex-1',
          first_name: 'Ramesh',
          last_name: 'Patil',
          dob: '1955-06-12',
          gender: 'Male',
          phone: '+919820011223',
          email: 'ramesh.patil@example.com',
          diagnosis: 'Post-CABG (Coronary Artery Bypass Graft)',
          discharge_date: '2026-10-20',
          programme_duration_days: 30,
          preferred_language: 'en',
          status: 'ACTIVE',
          call_window_start: '09:00',
          call_window_end: '18:00',
          checkin_morning_time: '09:30',
          checkin_evening_time: '17:30',
          dnd_start: '21:00',
          dnd_end: '07:00',
          retry_limit: 3,
          max_deferrals: 2,
          treating_doctor_name: 'Dr. Neha Kulkarni',
          treating_doctor_phone: '+919811122233',
          treating_doctor_specialty: 'Cardiothoracic Surgery',
          created_at: new Date().toISOString(),
          consent: {
            id: 'c-1',
            patient_id: patientId,
            voice_contact: true,
            call_recording: true,
            data_processing: true,
            caregiver_disclosure: true,
            emergency_escalation: true,
            consented_at: '2026-10-20T10:00:00Z'
          },
          caregivers: [
            {
              id: 'cg-1',
              patient_id: patientId,
              name: 'Suresh Patil',
              relationship: 'Son',
              phone: '+919833001122',
              email: 'suresh@example.com',
              is_authorized: true,
              consented_channels: ['VOICE_CALL', 'SMS', 'WHATSAPP'],
              consented_categories: ['ALL']
            }
          ],
          care_plan: {
            id: 'cp-1',
            patient_id: patientId,
            hydration_target_glasses: 8,
            hydration_interval_hours: 2,
            activity_target_minutes: 20,
            activity_target_steps: 2000,
            diet_instructions: 'Low sodium, low cholesterol cardiac diet.',
            medications: [
              {
                id: 'med-1',
                patient_id: patientId,
                medicine_name: 'Atorvastatin',
                dosage: '20mg',
                frequency: 'ONCE_DAILY',
                dose_times: ['09:00'],
                instructions: 'Take after breakfast with water',
                route: 'ORAL',
                effective_start_date: '2026-10-20',
                is_active: true
              },
              {
                id: 'med-2',
                patient_id: patientId,
                medicine_name: 'Aspirin',
                dosage: '75mg',
                frequency: 'ONCE_DAILY',
                dose_times: ['13:00'],
                instructions: 'Take after lunch',
                route: 'ORAL',
                effective_start_date: '2026-10-20',
                is_active: true
              }
            ],
            vitals_thresholds: [
              {
                id: 'vt-1',
                patient_id: patientId,
                vital_type: 'SPO2',
                unit: '%',
                plausible_min: 50,
                plausible_max: 100,
                normal_min: 94,
                normal_max: 100,
                warning_min: 90,
                critical_min: 88
              },
              {
                id: 'vt-2',
                patient_id: patientId,
                vital_type: 'BP_SYSTOLIC',
                unit: 'mmHg',
                plausible_min: 60,
                plausible_max: 260,
                normal_min: 100,
                normal_max: 130,
                warning_max: 150,
                critical_max: 180
              }
            ]
          }
        });
      });

    // Vitals
    apiClient.getPatientVitals(token, patientId)
      .then((data) => setVitals(data))
      .catch(() => {
        setVitals([
          { id: 'v1', patient_id: patientId, vital_type: 'SPO2', value: 86, unit: '%', recorded_at: new Date().toISOString(), status: 'CRITICAL', voice_confirmed: true },
          { id: 'v2', patient_id: patientId, vital_type: 'BP_SYSTOLIC', value: 125, secondary_value: 82, unit: 'mmHg', recorded_at: new Date().toISOString(), status: 'NORMAL', voice_confirmed: true },
          { id: 'v3', patient_id: patientId, vital_type: 'SPO2', value: 95, unit: '%', recorded_at: new Date(Date.now() - 86400000).toISOString(), status: 'NORMAL', voice_confirmed: true }
        ]);
      });

    // Symptoms
    apiClient.getPatientSymptoms(token, patientId)
      .then((data) => setSymptoms(data))
      .catch(() => {
        setSymptoms([
          {
            id: 's1',
            patient_id: patientId,
            checkin_type: 'MORNING_CHECKIN',
            recorded_at: new Date().toISOString(),
            pain_level: 8,
            breathlessness: 'moderate',
            dizziness: 'none',
            weakness: 'mild',
            fever: 'none',
            wound_status: 'healing_well',
            comparison_with_yesterday: { pain: 'worsened', breathlessness: 'worsened' }
          }
        ]);
      });

    // Calls
    apiClient.getPatientCalls(token, patientId)
      .then((data) => setCalls(data))
      .catch(() => {
        setCalls([
          {
            id: 'call-1',
            patient_id: patientId,
            direction: 'OUTBOUND',
            call_type: 'MORNING_CHECKIN',
            start_time: new Date().toISOString(),
            duration_seconds: 145,
            status: 'COMPLETED',
            disposition: 'COMPLETED',
            language_used: 'en',
            transferred_to_human: false,
            created_at: new Date().toISOString()
          }
        ]);
      });

    // Today Progress Score (PR-01)
    apiClient.getTodayProgressScore(token, patientId)
      .then((score) => setTodayScore(score))
      .catch(() => {
        setTodayScore({
          id: 'score-1',
          patient_id: patientId,
          score_date: new Date().toISOString().split('T')[0],
          overall_score: 68.5,
          symptom_score: 55.0,
          medication_score: 80.0,
          vitals_score: 60.0,
          lifestyle_score: 85.0,
          trend: 'DECLINING',
          voice_summary_script: 'Today you recorded taking Atorvastatin, but reported increased pain and lower oxygen. Your care team has been notified.',
          caregiver_summary: 'Ramesh completed morning check-in. Alert generated for oxygen reading 86%. Pain level 8/10 noted.'
        });
      })
      .finally(() => setIsLoading(false));

  }, [token, patientId]);

  const handleRecordVital = async () => {
    try {
      const res = await apiClient.recordManualVitals(
        token,
        patientId,
        newVitalType,
        newVitalVal,
        newVitalType === 'BP' ? newVitalDia : undefined,
        newVitalType === 'BP' ? 'mmHg' : '%'
      );
      setVitals((prev) => [res, ...prev]);
      setShowVitalModal(false);
    } catch (err: any) {
      alert(`Error saving vital reading: ${err.message}`);
    }
  };

  const handlePausePatient = async () => {
    try {
      await apiClient.pausePatient(token, patientId, pauseReason || 'Clinical review');
      if (patient) setPatient({ ...patient, status: 'PAUSED' });
      setShowPauseModal(false);
    } catch (err: any) {
      alert(`Error pausing patient: ${err.message}`);
    }
  };

  const handleResumePatient = async () => {
    try {
      await apiClient.resumePatient(token, patientId, 'Recovery continued');
      if (patient) setPatient({ ...patient, status: 'ACTIVE' });
    } catch (err: any) {
      alert(`Error resuming patient: ${err.message}`);
    }
  };

  const handleWithdrawConsent = async () => {
    if (!confirm('Are you sure the patient wishes to withdraw consent? All automated calls will immediately cease (PL-03).')) return;
    try {
      await apiClient.withdrawConsent(token, patientId, 'FULL', 'Patient voice withdrawal request');
      if (patient) setPatient({ ...patient, status: 'CONSENT_WITHDRAWN' });
    } catch (err: any) {
      alert(`Error withdrawing consent: ${err.message}`);
    }
  };

  if (!patient) {
    return <div className="p-8 text-center text-slate-500 font-medium">Loading Patient 360 Profile...</div>;
  }

  return (
    <div className="space-y-6">
      
      {/* Back button & Patient Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center space-x-4">
          <button
            onClick={() => navigate('/patients')}
            className="p-2 hover:bg-slate-200/80 bg-white rounded-xl border border-slate-200 transition-colors shadow-xs"
          >
            <ArrowLeft className="w-5 h-5 text-slate-600" />
          </button>
          <div>
            <div className="flex items-center space-x-3">
              <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
                {patient.first_name} {patient.last_name}
              </h1>
              <StatusBadge status={patient.status} />
              <span className="text-xs bg-slate-100 text-slate-700 font-mono px-2 py-0.5 rounded-md">
                {patient.id}
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-1">
              Diagnosis: <strong className="text-slate-800">{patient.diagnosis}</strong> · Discharge: {patient.discharge_date} · Doctor: {patient.treating_doctor_name || 'Dr. Neha Kulkarni'}
            </p>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center space-x-2">
          {patient.status === 'ACTIVE' ? (
            <button
              onClick={() => setShowPauseModal(true)}
              className="bg-amber-50 hover:bg-amber-100 text-amber-800 border border-amber-200 text-xs font-semibold px-3 py-2 rounded-xl flex items-center space-x-1.5 transition-colors"
            >
              <PauseCircle className="w-4 h-4" />
              <span>Pause Programme</span>
            </button>
          ) : patient.status === 'PAUSED' ? (
            <button
              onClick={handleResumePatient}
              className="bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold px-3 py-2 rounded-xl flex items-center space-x-1.5 transition-colors"
            >
              <PlayCircle className="w-4 h-4" />
              <span>Resume Programme</span>
            </button>
          ) : null}

          {patient.status !== 'CONSENT_WITHDRAWN' && (
            <button
              onClick={handleWithdrawConsent}
              className="bg-rose-50 hover:bg-rose-100 text-rose-700 border border-rose-200 text-xs font-semibold px-3 py-2 rounded-xl transition-colors"
            >
              Withdraw Consent
            </button>
          )}

          <button
            onClick={() => setShowVitalModal(true)}
            className="bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold px-3 py-2 rounded-xl transition-colors shadow-xs"
          >
            + Record Vital
          </button>
        </div>
      </div>

      {/* Daily Progress Score Gauge */}
      {todayScore && (
        <div className="bg-gradient-to-r from-slate-900 to-indigo-950 text-white p-6 rounded-2xl shadow-sm border border-slate-800 flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="space-y-2">
            <div className="flex items-center space-x-2">
              <span className="text-xs uppercase tracking-wider font-semibold text-indigo-400">
                Care Progress Score
              </span>
              <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                todayScore.trend === 'DECLINING' ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30' : 'bg-emerald-500/20 text-emerald-300'
              }`}>
                {todayScore.trend} TREND
              </span>
            </div>
            <p className="text-sm text-slate-300 max-w-xl leading-relaxed">
              "{todayScore.voice_summary_script}"
            </p>
            <p className="text-[11px] text-slate-400">
              Caregiver Summary: <span className="text-indigo-200">{todayScore.caregiver_summary}</span>
            </p>
          </div>

          <div className="flex items-center space-x-6 shrink-0">
            <div className="text-center">
              <div className="text-4xl font-extrabold text-white tracking-tight">
                {Math.round(todayScore.overall_score)}<span className="text-lg text-indigo-400 font-medium">/100</span>
              </div>
              <p className="text-[10px] text-slate-400 uppercase tracking-wider font-semibold mt-0.5">Overall Index</p>
            </div>

            <div className="grid grid-cols-2 gap-2 text-xs border-l border-slate-700/80 pl-6">
              <div>
                <p className="text-slate-400 text-[10px]">Symptoms (30%)</p>
                <p className="font-bold text-slate-200">{todayScore.symptom_score}%</p>
              </div>
              <div>
                <p className="text-slate-400 text-[10px]">Meds (30%)</p>
                <p className="font-bold text-slate-200">{todayScore.medication_score}%</p>
              </div>
              <div>
                <p className="text-slate-400 text-[10px]">Vitals (25%)</p>
                <p className="font-bold text-slate-200">{todayScore.vitals_score}%</p>
              </div>
              <div>
                <p className="text-slate-400 text-[10px]">Lifestyle (15%)</p>
                <p className="font-bold text-slate-200">{todayScore.lifestyle_score}%</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Navigation Tabs (DB-03 Patient 360 View) */}
      <div className="border-b border-slate-200">
        <nav className="flex space-x-6 text-xs font-semibold">
          {[
            { id: 'overview', label: 'Patient 360 Overview' },
            { id: 'vitals', label: `Vitals History (${vitals.length})` },
            { id: 'symptoms', label: `Symptoms & Checks (${symptoms.length})` },
            { id: 'meds', label: 'Care Plan & Medications' },
            { id: 'calls', label: `Call History & Resume (${calls.length})` },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`pb-3 border-b-2 transition-all ${
                activeTab === tab.id
                  ? 'border-indigo-600 text-indigo-600 font-bold'
                  : 'border-transparent text-slate-500 hover:text-slate-800'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab 1: Overview */}
      {activeTab === 'overview' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          
          {/* Demographics & Caregiver Card */}
          <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-xs space-y-4">
            <h3 className="font-bold text-sm text-slate-900 flex items-center space-x-2">
              <User className="w-4 h-4 text-indigo-600" />
              <span>Demographics & Contact</span>
            </h3>
            <div className="space-y-2 text-xs">
              <div className="flex justify-between py-1 border-b border-slate-100">
                <span className="text-slate-500">Full Name</span>
                <span className="font-semibold text-slate-800">{patient.first_name} {patient.last_name}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-100">
                <span className="text-slate-500">Gender / DOB</span>
                <span className="font-semibold text-slate-800">{patient.gender} · {patient.dob}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-100">
                <span className="text-slate-500">Primary Phone</span>
                <span className="font-semibold text-slate-800">{patient.phone}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-100">
                <span className="text-slate-500">Preferred Language</span>
                <span className="font-bold text-indigo-700 uppercase">{patient.preferred_language}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-100">
                <span className="text-slate-500">Call Window</span>
                <span className="font-semibold text-slate-800">{patient.call_window_start} - {patient.call_window_end}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-100">
                <span className="text-slate-500">DND Quiet Hours</span>
                <span className="font-semibold text-slate-800">{patient.dnd_start} - {patient.dnd_end}</span>
              </div>
            </div>

            {/* Caregivers */}
            <div className="pt-2">
              <h4 className="font-semibold text-xs text-slate-800 mb-2">Designated Caregivers</h4>
              {patient.caregivers && patient.caregivers.map((cg) => (
                <div key={cg.id} className="p-3 bg-slate-50 rounded-xl border border-slate-200 text-xs space-y-1">
                  <div className="flex justify-between">
                    <span className="font-bold text-slate-800">{cg.name} ({cg.relationship})</span>
                    <span className="text-[10px] bg-emerald-100 text-emerald-800 px-1.5 py-0.5 rounded-sm font-semibold">Authorized</span>
                  </div>
                  <p className="text-slate-500 text-[11px]">{cg.phone} · {cg.email}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Vitals Summary & Thresholds Card */}
          <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-xs space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="font-bold text-sm text-slate-900 flex items-center space-x-2">
                <Heart className="w-4 h-4 text-rose-500" />
                <span>Latest Vitals & Bounds</span>
              </h3>
              <button
                onClick={() => setActiveTab('vitals')}
                className="text-indigo-600 text-xs font-semibold hover:underline"
              >
                View History →
              </button>
            </div>

            <div className="space-y-3">
              {vitals.slice(0, 3).map((v) => (
                <div key={v.id} className="p-3 rounded-xl border border-slate-200 flex items-center justify-between">
                  <div>
                    <p className="font-bold text-xs text-slate-800">
                      {v.vital_type.replace('_SYSTOLIC', '')}: {v.value} {v.secondary_value ? `/${v.secondary_value}` : ''} {v.unit}
                    </p>
                    <p className="text-[10px] text-slate-400">
                      {new Date(v.recorded_at).toLocaleDateString()} {new Date(v.recorded_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </p>
                  </div>
                  <StatusBadge status={v.status} size="sm" />
                </div>
              ))}
            </div>

            <div className="p-3 bg-indigo-50/60 rounded-xl border border-indigo-100 text-xs space-y-1 text-indigo-900">
              <p className="font-bold">Clinician Rules Active:</p>
              <p className="text-[11px] leading-relaxed">
                • SpO2 Critical Breach: &lt; 88% (15-min SLA)<br />
                • Systolic Warning: &gt; 140 mmHg, Critical: &gt; 180 mmHg
              </p>
            </div>
          </div>

          {/* Active Medications & Adherence Card */}
          <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-xs space-y-4">
            <h3 className="font-bold text-sm text-slate-900 flex items-center space-x-2">
              <Pill className="w-4 h-4 text-emerald-600" />
              <span>Active Care Plan Medications</span>
            </h3>

            <div className="space-y-2 text-xs">
              {patient.care_plan?.medications.map((m) => (
                <div key={m.id} className="p-3 bg-slate-50 rounded-xl border border-slate-200 space-y-1">
                  <div className="flex justify-between items-center">
                    <span className="font-bold text-slate-900">{m.medicine_name} {m.dosage}</span>
                    <span className="text-[10px] bg-slate-200 text-slate-700 px-1.5 py-0.5 rounded-sm font-medium">
                      {m.frequency.replace('_', ' ')}
                    </span>
                  </div>
                  <p className="text-slate-500 text-[11px]">{m.instructions}</p>
                </div>
              ))}
            </div>

            {/* Guardrail Note */}
            <div className="p-3 bg-slate-100 rounded-xl text-[11px] text-slate-600">
              <p className="font-semibold text-slate-800">Prescription Safety Guardrail:</p>
              <p className="mt-0.5">The conversational AI cannot alter doses or determine medications. Any patient inquiries are routed to treating physician.</p>
            </div>
          </div>

        </div>
      )}

      {/* Tab 2: Vitals History */}
      {activeTab === 'vitals' && (
        <div className="bg-white rounded-2xl border border-slate-200/80 shadow-xs overflow-hidden">
          <div className="p-4 border-b border-slate-200 flex justify-between items-center">
            <h3 className="font-bold text-sm text-slate-900">Recorded Vitals History</h3>
            <button
              onClick={() => setShowVitalModal(true)}
              className="bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold px-3 py-1.5 rounded-lg transition-colors"
            >
              + Record Reading
            </button>
          </div>
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 uppercase tracking-wider font-semibold">
              <tr>
                <th className="px-4 py-3">Timestamp</th>
                <th className="px-4 py-3">Vital Type</th>
                <th className="px-4 py-3">Value</th>
                <th className="px-4 py-3">Plausibility & SLA Status</th>
                <th className="px-4 py-3">Voice Confirmed</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {vitals.map((v) => (
                <tr key={v.id} className="hover:bg-slate-50">
                  <td className="px-4 py-3 font-medium text-slate-700">
                    {new Date(v.recorded_at).toLocaleString()}
                  </td>
                  <td className="px-4 py-3 font-bold text-slate-900">{v.vital_type}</td>
                  <td className="px-4 py-3 font-bold text-slate-800">
                    {v.value} {v.secondary_value ? `/${v.secondary_value}` : ''} {v.unit}
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge status={v.status} size="sm" />
                  </td>
                  <td className="px-4 py-3">
                    {v.voice_confirmed ? (
                      <span className="text-emerald-600 font-semibold flex items-center">
                        <CheckCircle2 className="w-3.5 h-3.5 mr-1" />
                        Confirmed via Voice
                      </span>
                    ) : (
                      <span className="text-slate-400">Manual Entry</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Tab 3: Symptoms */}
      {activeTab === 'symptoms' && (
        <div className="bg-white rounded-2xl border border-slate-200/80 shadow-xs overflow-hidden">
          <div className="p-4 border-b border-slate-200">
            <h3 className="font-bold text-sm text-slate-900">Standardized Symptom Check-ins</h3>
            <p className="text-xs text-slate-500">Morning & evening symptom trajectory tracking, pain score 0-10, breathlessness deterioration.</p>
          </div>
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 uppercase tracking-wider font-semibold">
              <tr>
                <th className="px-4 py-3">Recorded Time</th>
                <th className="px-4 py-3">Check-in Type</th>
                <th className="px-4 py-3">Pain (0-10)</th>
                <th className="px-4 py-3">Breathlessness</th>
                <th className="px-4 py-3">Fever / Wound</th>
                <th className="px-4 py-3">Trajectory vs Yesterday</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {symptoms.map((s) => (
                <tr key={s.id} className="hover:bg-slate-50">
                  <td className="px-4 py-3 font-medium text-slate-700">
                    {new Date(s.recorded_at).toLocaleString()}
                  </td>
                  <td className="px-4 py-3 font-bold text-slate-800">{s.checkin_type}</td>
                  <td className="px-4 py-3">
                    <span className={`font-bold ${s.pain_level >= 8 ? 'text-rose-600' : 'text-slate-800'}`}>
                      {s.pain_level}/10
                    </span>
                  </td>
                  <td className="px-4 py-3 capitalize font-medium text-slate-700">{s.breathlessness}</td>
                  <td className="px-4 py-3 text-slate-600">{s.fever} / {s.wound_status}</td>
                  <td className="px-4 py-3">
                    {s.comparison_with_yesterday && s.comparison_with_yesterday.pain === 'worsened' ? (
                      <span className="text-rose-600 font-semibold">Worsened Pain</span>
                    ) : (
                      <span className="text-emerald-600 font-medium">Stable</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Tab 4: Care Plan & Medications */}
      {activeTab === 'meds' && (
        <div className="bg-white rounded-2xl border border-slate-200/80 shadow-xs p-6 space-y-6">
          <div>
            <h3 className="font-bold text-base text-slate-900">Prescription Schedule & Targets</h3>
            <p className="text-xs text-slate-500 mt-1">Configured discharge care plan enforced by deterministic verification.</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {patient.care_plan?.medications.map((m) => (
              <div key={m.id} className="p-4 rounded-xl border border-slate-200 space-y-2 bg-slate-50/50">
                <div className="flex justify-between items-center">
                  <h4 className="font-bold text-sm text-slate-900">{m.medicine_name}</h4>
                  <span className="bg-indigo-50 text-indigo-700 font-bold px-2 py-0.5 rounded-sm text-xs">
                    {m.dosage}
                  </span>
                </div>
                <p className="text-xs text-slate-600">{m.instructions}</p>
                <div className="flex items-center space-x-4 text-[11px] text-slate-500 pt-1">
                  <span>Frequency: {m.frequency}</span>
                  <span>Times: {m.dose_times.join(', ')}</span>
                </div>
              </div>
            ))}
          </div>

          <div className="p-4 bg-slate-100 rounded-xl space-y-2">
            <h4 className="font-bold text-xs text-slate-800">Lifestyle & Recovery Targets</h4>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs">
              <div>
                <p className="text-slate-500 text-[11px]">Hydration Goal</p>
                <p className="font-bold text-slate-800">{patient.care_plan?.hydration_target_glasses} glasses / day</p>
              </div>
              <div>
                <p className="text-slate-500 text-[11px]">Hydration Interval</p>
                <p className="font-bold text-slate-800">Every {patient.care_plan?.hydration_interval_hours} hours</p>
              </div>
              <div>
                <p className="text-slate-500 text-[11px]">Walking Target</p>
                <p className="font-bold text-slate-800">{patient.care_plan?.activity_target_minutes} mins / day</p>
              </div>
              <div>
                <p className="text-slate-500 text-[11px]">Diet Instructions</p>
                <p className="font-bold text-slate-800">{patient.care_plan?.diet_instructions || 'Cardiac Diet'}</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tab 5: Calls History */}
      {activeTab === 'calls' && (
        <div className="bg-white rounded-2xl border border-slate-200/80 shadow-xs overflow-hidden">
          <div className="p-4 border-b border-slate-200">
            <h3 className="font-bold text-sm text-slate-900">Telephone Call Sessions</h3>
            <p className="text-xs text-slate-500">Structured telephony records, attempt dispositions, and interrupted call recovery.</p>
          </div>
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 uppercase tracking-wider font-semibold">
              <tr>
                <th className="px-4 py-3">Call Time</th>
                <th className="px-4 py-3">Direction & Type</th>
                <th className="px-4 py-3">Language</th>
                <th className="px-4 py-3">Duration</th>
                <th className="px-4 py-3">Disposition</th>
                <th className="px-4 py-3">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {calls.map((c) => (
                <tr key={c.id} className="hover:bg-slate-50">
                  <td className="px-4 py-3 font-medium text-slate-700">
                    {new Date(c.start_time).toLocaleString()}
                  </td>
                  <td className="px-4 py-3 font-bold text-slate-800">{c.direction} · {c.call_type}</td>
                  <td className="px-4 py-3 uppercase font-semibold text-indigo-700">{c.language_used}</td>
                  <td className="px-4 py-3 text-slate-600">{c.duration_seconds}s</td>
                  <td className="px-4 py-3 font-semibold text-slate-800">{c.disposition || 'IN_PROGRESS'}</td>
                  <td className="px-4 py-3">
                    <StatusBadge status={c.status} size="sm" />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Record Vital Modal */}
      {showVitalModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl p-6 max-w-md w-full space-y-4 shadow-xl border border-slate-200">
            <h3 className="font-bold text-base text-slate-900">Record Clinical Vital Reading</h3>
            <div className="space-y-3 text-xs">
              <div>
                <label className="font-semibold text-slate-700 block mb-1">Vital Parameter</label>
                <select
                  value={newVitalType}
                  onChange={(e) => setNewVitalType(e.target.value)}
                  className="w-full border border-slate-300 rounded-xl px-3 py-2 font-medium"
                >
                  <option value="SPO2">Pulse Oximetry (SpO2 %)</option>
                  <option value="BP">Blood Pressure (Systolic / Diastolic)</option>
                  <option value="GLUCOSE">Blood Glucose (mg/dL)</option>
                  <option value="PULSE">Heart Rate / Pulse (bpm)</option>
                </select>
              </div>

              <div>
                <label className="font-semibold text-slate-700 block mb-1">
                  {newVitalType === 'BP' ? 'Systolic (mmHg)' : 'Value'}
                </label>
                <input
                  type="number"
                  value={newVitalVal}
                  onChange={(e) => setNewVitalVal(parseFloat(e.target.value))}
                  className="w-full border border-slate-300 rounded-xl px-3 py-2 font-medium"
                />
              </div>

              {newVitalType === 'BP' && (
                <div>
                  <label className="font-semibold text-slate-700 block mb-1">Diastolic (mmHg)</label>
                  <input
                    type="number"
                    value={newVitalDia}
                    onChange={(e) => setNewVitalDia(parseFloat(e.target.value))}
                    className="w-full border border-slate-300 rounded-xl px-3 py-2 font-medium"
                  />
                </div>
              )}
            </div>

            <div className="flex justify-end space-x-2 pt-2">
              <button
                onClick={() => setShowVitalModal(false)}
                className="px-4 py-2 border border-slate-300 rounded-xl text-xs font-semibold text-slate-700 hover:bg-slate-100"
              >
                Cancel
              </button>
              <button
                onClick={handleRecordVital}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-semibold"
              >
                Save Reading & Evaluate Rules
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Pause Modal */}
      {showPauseModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl p-6 max-w-md w-full space-y-4 shadow-xl border border-slate-200">
            <h3 className="font-bold text-base text-slate-900">Pause Programme (PL-02)</h3>
            <p className="text-xs text-slate-500">
              Pausing ceases calls temporarily without losing any historical data or care plan configuration.
            </p>
            <input
              type="text"
              placeholder="Reason for pause (e.g. readmission, family emergency)..."
              value={pauseReason}
              onChange={(e) => setPauseReason(e.target.value)}
              className="w-full border border-slate-300 rounded-xl px-3 py-2 text-xs"
            />
            <div className="flex justify-end space-x-2">
              <button
                onClick={() => setShowPauseModal(false)}
                className="px-4 py-2 border border-slate-300 rounded-xl text-xs font-semibold text-slate-700"
              >
                Cancel
              </button>
              <button
                onClick={handlePausePatient}
                className="px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white rounded-xl text-xs font-semibold"
              >
                Confirm Pause
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
};
