import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { apiClient } from '../api/client';
import {
  UserPlus,
  ShieldCheck,
  AlertCircle,
  CheckCircle2,
  Calendar,
  Clock,
  Pill,
  Heart,
  UserCheck,
  FileCode,
  Upload,
  FileText,
  Check,
  ArrowRight
} from 'lucide-react';

export const OnboardingPage: React.FC = () => {
  const { token, currentUser } = useAuth();
  const navigate = useNavigate();

  const [step, setStep] = useState(1);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [createdPatientId, setCreatedPatientId] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);

  // ON-07: FHIR Ingestion State
  const [onboardingMode, setOnboardingMode] = useState<'manual' | 'fhir'>('manual');
  const [fhirRawJson, setFhirRawJson] = useState<string>('');
  const [fhirPreview, setFhirPreview] = useState<any | null>(null);
  const [isFhirPreviewing, setIsFhirPreviewing] = useState<boolean>(false);
  const [isFhirImporting, setIsFhirImporting] = useState<boolean>(false);
  const [fhirError, setFhirError] = useState<string | null>(null);
  const [fhirSuccess, setFhirSuccess] = useState<any | null>(null);

  const handlePreviewFhir = async () => {
    if (!fhirRawJson.trim()) {
      setFhirError('Please enter or paste FHIR R4 JSON before validating.');
      return;
    }
    setFhirError(null);
    setIsFhirPreviewing(true);
    try {
      const parsedJson = JSON.parse(fhirRawJson);
      const res = await apiClient.previewFhirImport(token, parsedJson);
      setFhirPreview(res);
    } catch (err: any) {
      setFhirError(err.message || 'Invalid FHIR JSON payload.');
      setFhirPreview(null);
    } finally {
      setIsFhirPreviewing(false);
    }
  };

  const handleExecuteFhirImport = async () => {
    if (!fhirRawJson.trim()) return;
    setFhirError(null);
    setIsFhirImporting(true);
    try {
      const parsedJson = JSON.parse(fhirRawJson);
      const res = await apiClient.importFhirPatient(token, parsedJson, true, true);
      setFhirSuccess(res);
      setCreatedPatientId(res.patient_id);
    } catch (err: any) {
      setFhirError(err.message || 'Failed to import FHIR patient record.');
    } finally {
      setIsFhirImporting(false);
    }
  };

  // Form State
  const [formData, setFormData] = useState({
    first_name: '',
    last_name: '',
    dob: '',
    gender: 'Male',
    phone: '',
    email: '',
    diagnosis: '',
    discharge_date: new Date().toISOString().split('T')[0],
    programme_duration_days: 30,
    preferred_language: 'en',
    call_window_start: '09:00',
    call_window_end: '18:00',
    checkin_morning_time: '09:30',
    checkin_evening_time: '17:30',
    dnd_start: '21:00',
    dnd_end: '07:00',
    retry_limit: 3,
    max_deferrals: 2,
    treating_doctor_name: currentUser?.name || '',
    treating_doctor_phone: '',
    treating_doctor_specialty: '',

    // Caregiver
    caregiver_name: '',
    caregiver_relationship: 'Spouse',
    caregiver_phone: '',
    caregiver_email: '',

    // Medications
    med_name: '',
    med_dosage: '',
    med_frequency: 'ONCE_DAILY',
    med_instructions: '',

    // Consent (ON-06)
    consent_voice_contact: false,
    consent_call_recording: false,
    consent_data_processing: false,
    consent_caregiver_disclosure: false,
    consent_emergency_escalation: false,
    activate_if_complete: true
  });

  const isConsentComplete =
    formData.consent_voice_contact &&
    formData.consent_call_recording &&
    formData.consent_data_processing;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);

    const payload = {
      facility_id: currentUser?.facility_id || 'facility-apex-1',
      first_name: formData.first_name,
      last_name: formData.last_name,
      dob: formData.dob,
      gender: formData.gender,
      phone: formData.phone,
      email: formData.email,
      diagnosis: formData.diagnosis,
      discharge_date: formData.discharge_date,
      programme_duration_days: formData.programme_duration_days,
      preferred_language: formData.preferred_language,
      call_window_start: formData.call_window_start,
      call_window_end: formData.call_window_end,
      checkin_morning_time: formData.checkin_morning_time,
      checkin_evening_time: formData.checkin_evening_time,
      dnd_start: formData.dnd_start,
      dnd_end: formData.dnd_end,
      retry_limit: formData.retry_limit,
      max_deferrals: formData.max_deferrals,
      treating_doctor_name: formData.treating_doctor_name,
      treating_doctor_phone: formData.treating_doctor_phone,
      treating_doctor_specialty: formData.treating_doctor_specialty,

      caregivers: formData.caregiver_name ? [
        {
          name: formData.caregiver_name,
          relationship: formData.caregiver_relationship,
          phone: formData.caregiver_phone || formData.phone,
          email: formData.caregiver_email,
          is_authorized: true,
          consented_channels: ['VOICE_CALL', 'SMS'],
          consented_categories: ['ALL']
        }
      ] : [],

      care_plan: {
        diet_instructions: 'Low salt, heart-healthy cardiac diet',
        hydration_target_glasses: 8,
        hydration_interval_hours: 2,
        activity_target_minutes: 20,
        activity_target_steps: 2000,
        medications: [
          {
            medicine_name: formData.med_name,
            dosage: formData.med_dosage,
            frequency: formData.med_frequency,
            dose_times: ['09:00'],
            instructions: formData.med_instructions,
            route: 'ORAL'
          }
        ],
        vitals_thresholds: [
          {
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
      },

      consent: {
        voice_contact: formData.consent_voice_contact,
        call_recording: formData.consent_call_recording,
        data_processing: formData.consent_data_processing,
        caregiver_disclosure: formData.consent_caregiver_disclosure,
        emergency_escalation: formData.consent_emergency_escalation,
        consent_notes: 'Explicit verbal & written discharge consent captured per ON-06'
      },

      activate_if_complete: formData.activate_if_complete
    };

    setSubmitError(null);
    try {
      const patient = await apiClient.registerPatient(token, payload);
      setCreatedPatientId(patient.id);
      setStep(4);
    } catch (err: any) {
      setSubmitError(err.message || 'Failed to register patient in clinical system.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight flex items-center space-x-2">
          <UserPlus className="w-6 h-6 text-indigo-600" />
          <span>Patient Discharge Onboarding (ON-01 to ON-07)</span>
        </h1>
        <p className="text-xs text-slate-500 mt-1">
          Configure patient demographics, care plans, caregiver contacts, and mandatory consent before programme activation.
        </p>
      </div>

      {/* Onboarding Mode Selector */}
      <div className="flex border-b border-slate-200 gap-4 text-xs font-bold">
        <button
          type="button"
          onClick={() => { setOnboardingMode('manual'); setFhirError(null); }}
          className={`pb-3 border-b-2 flex items-center space-x-2 transition-colors ${
            onboardingMode === 'manual'
              ? 'border-indigo-600 text-indigo-600'
              : 'border-transparent text-slate-500 hover:text-slate-700'
          }`}
        >
          <UserPlus className="w-4 h-4" />
          <span>Manual Discharge Wizard (ON-01 to ON-06)</span>
        </button>
        <button
          type="button"
          onClick={() => { setOnboardingMode('fhir'); setSubmitError(null); }}
          className={`pb-3 border-b-2 flex items-center space-x-2 transition-colors ${
            onboardingMode === 'fhir'
              ? 'border-indigo-600 text-indigo-600'
              : 'border-transparent text-slate-500 hover:text-slate-700'
          }`}
        >
          <FileCode className="w-4 h-4" />
          <span>Import Hospital Record: HL7 FHIR R4 (ON-07)</span>
        </button>
      </div>

      {onboardingMode === 'manual' ? (
        <>
          {/* Progress Steps */}
          <div className="flex items-center justify-between bg-white p-4 rounded-2xl border border-slate-200/80 shadow-xs text-xs">
            {[
              { num: 1, title: 'Demographics & Preferences' },
              { num: 2, title: 'Care Plan & Medications' },
              { num: 3, title: 'Mandatory Consent (ON-06)' },
              { num: 4, title: 'Activation Confirmation' }
            ].map((s) => (
              <div key={s.num} className="flex items-center space-x-2">
                <div className={`w-7 h-7 rounded-full flex items-center justify-center font-bold ${
                  step >= s.num ? 'bg-indigo-600 text-white' : 'bg-slate-100 text-slate-400'
                }`}>
                  {s.num}
                </div>
                <span className={`hidden sm:inline font-semibold ${step >= s.num ? 'text-slate-900' : 'text-slate-400'}`}>
                  {s.title}
                </span>
              </div>
            ))}
          </div>

          {/* Form Steps */}
          <form onSubmit={handleSubmit} className="bg-white p-6 rounded-2xl border border-slate-200/80 shadow-xs space-y-6">
        
        {/* Step 1: Demographics */}
        {step === 1 && (
          <div className="space-y-4">
            <h2 className="text-base font-bold text-slate-900 border-b border-slate-200 pb-2">
              1. Demographics & Operating Windows (ON-01, ON-05)
            </h2>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
              <div>
                <label className="font-semibold text-slate-700 block mb-1">First Name *</label>
                <input
                  type="text"
                  required
                  placeholder="First name"
                  value={formData.first_name}
                  onChange={(e) => setFormData({ ...formData, first_name: e.target.value })}
                  className="w-full border border-slate-300 rounded-xl px-3 py-2"
                />
              </div>

              <div>
                <label className="font-semibold text-slate-700 block mb-1">Last Name *</label>
                <input
                  type="text"
                  required
                  placeholder="Last name"
                  value={formData.last_name}
                  onChange={(e) => setFormData({ ...formData, last_name: e.target.value })}
                  className="w-full border border-slate-300 rounded-xl px-3 py-2"
                />
              </div>

              <div>
                <label className="font-semibold text-slate-700 block mb-1">Date of Birth</label>
                <input
                  type="date"
                  value={formData.dob}
                  onChange={(e) => setFormData({ ...formData, dob: e.target.value })}
                  className="w-full border border-slate-300 rounded-xl px-3 py-2"
                />
              </div>

              <div>
                <label className="font-semibold text-slate-700 block mb-1">Gender</label>
                <select
                  value={formData.gender}
                  onChange={(e) => setFormData({ ...formData, gender: e.target.value })}
                  className="w-full border border-slate-300 rounded-xl px-3 py-2 bg-white"
                >
                  <option value="Male">Male</option>
                  <option value="Female">Female</option>
                  <option value="Other">Other</option>
                </select>
              </div>

              <div>
                <label className="font-semibold text-slate-700 block mb-1">Phone Number (Mandatory) *</label>
                <input
                  type="tel"
                  required
                  placeholder="+9198XXXXXXXX"
                  value={formData.phone}
                  onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                  className="w-full border border-slate-300 rounded-xl px-3 py-2"
                />
              </div>

              <div>
                <label className="font-semibold text-slate-700 block mb-1">Preferred Language (LN-01)</label>
                <select
                  value={formData.preferred_language}
                  onChange={(e) => setFormData({ ...formData, preferred_language: e.target.value })}
                  className="w-full border border-slate-300 rounded-xl px-3 py-2 bg-white font-semibold text-indigo-700"
                >
                  <option value="en">English (en)</option>
                  <option value="hi">Hindi (hi)</option>
                  <option value="mr">Marathi (mr)</option>
                </select>
              </div>

              <div>
                <label className="font-semibold text-slate-700 block mb-1">Discharge Diagnosis *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Post-CABG / Acute Coronary Syndrome"
                  value={formData.diagnosis}
                  onChange={(e) => setFormData({ ...formData, diagnosis: e.target.value })}
                  className="w-full border border-slate-300 rounded-xl px-3 py-2"
                />
              </div>

              <div>
                <label className="font-semibold text-slate-700 block mb-1">Treating Physician (MD-07)</label>
                <input
                  type="text"
                  placeholder="e.g. Attending Cardiologist"
                  value={formData.treating_doctor_name}
                  onChange={(e) => setFormData({ ...formData, treating_doctor_name: e.target.value })}
                  className="w-full border border-slate-300 rounded-xl px-3 py-2"
                />
              </div>
            </div>

            <div className="pt-4 border-t border-slate-100 flex justify-end">
              <button
                type="button"
                disabled={!formData.first_name || !formData.last_name || !formData.phone}
                onClick={() => setStep(2)}
                className="bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-300 text-white text-xs font-semibold px-5 py-2.5 rounded-xl transition-colors"
              >
                Next: Care Plan & Medications →
              </button>
            </div>
          </div>
        )}

        {/* Step 2: Care Plan */}
        {step === 2 && (
          <div className="space-y-4">
            <h2 className="text-base font-bold text-slate-900 border-b border-slate-200 pb-2">
              2. Discharge Care Plan Configuration (ON-02, ON-04)
            </h2>

            <div className="space-y-3">
              <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider">Primary Medication Schedule (MD-01)</h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
                <div>
                  <label className="font-semibold text-slate-700 block mb-1">Medicine Name</label>
                  <input
                    type="text"
                    placeholder="e.g. Atorvastatin"
                    value={formData.med_name}
                    onChange={(e) => setFormData({ ...formData, med_name: e.target.value })}
                    className="w-full border border-slate-300 rounded-xl px-3 py-2"
                  />
                </div>
                <div>
                  <label className="font-semibold text-slate-700 block mb-1">Dosage</label>
                  <input
                    type="text"
                    placeholder="e.g. 10mg / 1 tablet"
                    value={formData.med_dosage}
                    onChange={(e) => setFormData({ ...formData, med_dosage: e.target.value })}
                    className="w-full border border-slate-300 rounded-xl px-3 py-2"
                  />
                </div>
                <div className="sm:col-span-2">
                  <label className="font-semibold text-slate-700 block mb-1">Patient Instructions</label>
                  <input
                    type="text"
                    placeholder="e.g. Take once daily after meals with water"
                    value={formData.med_instructions}
                    onChange={(e) => setFormData({ ...formData, med_instructions: e.target.value })}
                    className="w-full border border-slate-300 rounded-xl px-3 py-2"
                  />
                </div>
              </div>
            </div>

            <div className="space-y-3 pt-3 border-t border-slate-100">
              <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider">Designated Caregiver Contact (ON-04)</h3>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
                <div>
                  <label className="font-semibold text-slate-700 block mb-1">Caregiver Name</label>
                  <input
                    type="text"
                    placeholder="Caregiver full name"
                    value={formData.caregiver_name}
                    onChange={(e) => setFormData({ ...formData, caregiver_name: e.target.value })}
                    className="w-full border border-slate-300 rounded-xl px-3 py-2"
                  />
                </div>
                <div>
                  <label className="font-semibold text-slate-700 block mb-1">Relationship</label>
                  <input
                    type="text"
                    placeholder="e.g. Son / Spouse"
                    value={formData.caregiver_relationship}
                    onChange={(e) => setFormData({ ...formData, caregiver_relationship: e.target.value })}
                    className="w-full border border-slate-300 rounded-xl px-3 py-2"
                  />
                </div>
                <div>
                  <label className="font-semibold text-slate-700 block mb-1">Caregiver Phone</label>
                  <input
                    type="tel"
                    placeholder="+919833001122"
                    value={formData.caregiver_phone}
                    onChange={(e) => setFormData({ ...formData, caregiver_phone: e.target.value })}
                    className="w-full border border-slate-300 rounded-xl px-3 py-2"
                  />
                </div>
              </div>
            </div>

            <div className="pt-4 border-t border-slate-100 flex justify-between">
              <button
                type="button"
                onClick={() => setStep(1)}
                className="px-4 py-2 border border-slate-300 rounded-xl text-xs font-semibold text-slate-700"
              >
                ← Back
              </button>
              <button
                type="button"
                onClick={() => setStep(3)}
                className="bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold px-5 py-2.5 rounded-xl transition-colors"
              >
                Next: Mandatory Consent (ON-06) →
              </button>
            </div>
          </div>
        )}

        {/* Step 3: Consent (ON-06) */}
        {step === 3 && (
          <div className="space-y-4">
            <div>
              <h2 className="text-base font-bold text-slate-900 border-b border-slate-200 pb-2 flex items-center space-x-2">
                <ShieldCheck className="w-5 h-5 text-indigo-600" />
                <span>3. Mandatory Informed Consent Capturing (ON-06)</span>
              </h2>
              <p className="text-xs text-slate-500 mt-1">
                <strong>CRITICAL RULE ON-06:</strong> The programme activation is strictly blocked until explicit consent
                is recorded. If consent is missing, the patient remains in DRAFT status and no calls can be placed.
              </p>
            </div>

            <div className="space-y-3 bg-slate-50 p-4 rounded-xl border border-slate-200 text-xs">
              
              <label className="flex items-start space-x-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={formData.consent_voice_contact}
                  onChange={(e) => setFormData({ ...formData, consent_voice_contact: e.target.checked })}
                  className="mt-0.5 rounded-sm text-indigo-600 focus:ring-indigo-500 w-4 h-4"
                />
                <div>
                  <span className="font-bold text-slate-800">Voice Contact Consent (Mandatory) *</span>
                  <p className="text-slate-500 text-[11px]">
                    Patient agrees to receive automated telephone recovery check-in calls within their designated calling window.
                  </p>
                </div>
              </label>

              <label className="flex items-start space-x-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={formData.consent_call_recording}
                  onChange={(e) => setFormData({ ...formData, consent_call_recording: e.target.checked })}
                  className="mt-0.5 rounded-sm text-indigo-600 focus:ring-indigo-500 w-4 h-4"
                />
                <div>
                  <span className="font-bold text-slate-800">Call Audio & Transcript Recording Consent *</span>
                  <p className="text-slate-500 text-[11px]">
                    Patient agrees to secure recording and NLP structured transcript analysis for clinical recovery tracking.
                  </p>
                </div>
              </label>

              <label className="flex items-start space-x-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={formData.consent_data_processing}
                  onChange={(e) => setFormData({ ...formData, consent_data_processing: e.target.checked })}
                  className="mt-0.5 rounded-sm text-indigo-600 focus:ring-indigo-500 w-4 h-4"
                />
                <div>
                  <span className="font-bold text-slate-800">Healthcare Data Processing Consent *</span>
                  <p className="text-slate-500 text-[11px]">
                    Patient authorizes secure, encrypted health data storage per hospital privacy standards.
                  </p>
                </div>
              </label>

              <label className="flex items-start space-x-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={formData.consent_caregiver_disclosure}
                  onChange={(e) => setFormData({ ...formData, consent_caregiver_disclosure: e.target.checked })}
                  className="mt-0.5 rounded-sm text-indigo-600 focus:ring-indigo-500 w-4 h-4"
                />
                <div>
                  <span className="font-semibold text-slate-800">Caregiver Disclosure Consent</span>
                  <p className="text-slate-500 text-[11px]">
                    Patient authorizes sharing summary progress and alerts with designated caregivers.
                  </p>
                </div>
              </label>

              <label className="flex items-start space-x-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={formData.consent_emergency_escalation}
                  onChange={(e) => setFormData({ ...formData, consent_emergency_escalation: e.target.checked })}
                  className="mt-0.5 rounded-sm text-indigo-600 focus:ring-indigo-500 w-4 h-4"
                />
                <div>
                  <span className="font-semibold text-slate-800">Emergency Escalation Authorization</span>
                  <p className="text-slate-500 text-[11px]">
                    Patient authorizes immediate alert dispatch to emergency contacts and attending cardiology team.
                  </p>
                </div>
              </label>

            </div>

            {/* Status Preview */}
            <div className={`p-4 rounded-xl border text-xs flex items-center space-x-3 ${
              isConsentComplete ? 'bg-emerald-50 border-emerald-200 text-emerald-800' : 'bg-amber-50 border-amber-200 text-amber-800'
            }`}>
              {isConsentComplete ? (
                <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
              ) : (
                <AlertCircle className="w-5 h-5 text-amber-600 shrink-0" />
              )}
              <div>
                <p className="font-bold">
                  {isConsentComplete
                    ? 'Status upon submission: ACTIVE (Full Activation Permitted)'
                    : 'Status upon submission: DRAFT (Activation Blocked - Mandatory Consent Required)'}
                </p>
                <p className="text-[11px]">
                  {isConsentComplete
                    ? 'All mandatory consent checkboxes checked. Automated recovery calling schedule will activate.'
                    : 'Missing mandatory consent. The patient record will be saved in DRAFT mode only.'}
                </p>
              </div>
            </div>

            {submitError && (
              <div className="p-3 bg-red-50 border border-red-200 rounded-xl text-xs text-red-700 flex items-center space-x-2">
                <AlertCircle className="w-4 h-4 text-red-500 shrink-0" />
                <span>{submitError}</span>
              </div>
            )}

            <div className="pt-4 border-t border-slate-100 flex justify-between">
              <button
                type="button"
                onClick={() => setStep(2)}
                className="px-4 py-2 border border-slate-300 rounded-xl text-xs font-semibold text-slate-700"
              >
                ← Back
              </button>
              <button
                type="submit"
                disabled={isSubmitting}
                className="bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold px-6 py-2.5 rounded-xl transition-colors shadow-xs"
              >
                {isSubmitting ? 'Registering Patient...' : 'Complete Registration & Activate'}
              </button>
            </div>
          </div>
        )}

        {/* Step 4: Success Confirmation */}
        {step === 4 && (
          <div className="text-center py-8 space-y-4">
            <div className="w-14 h-14 bg-emerald-100 text-emerald-600 rounded-full flex items-center justify-center mx-auto">
              <CheckCircle2 className="w-8 h-8" />
            </div>
            <h2 className="text-xl font-bold text-slate-900">Patient Onboarded Successfully</h2>
            <p className="text-xs text-slate-600 max-w-md mx-auto leading-relaxed">
              Patient profile and recovery care plan registered successfully. Automated monitoring scheduled.
            </p>
            <div className="flex justify-center space-x-3 pt-4">
              <button
                type="button"
                onClick={() => navigate(`/patients/${createdPatientId}`)}
                className="bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold px-4 py-2 rounded-xl transition-colors"
              >
                View Patient 360 Profile →
              </button>
              <button
                type="button"
                onClick={() => {
                  setStep(1);
                  setFormData({ ...formData, first_name: '', last_name: '', phone: '' });
                }}
                className="px-4 py-2 border border-slate-300 rounded-xl text-xs font-semibold text-slate-700 hover:bg-slate-50"
              >
                Onboard Another Patient
              </button>
            </div>
          </div>
        )}

      </form>
      </>
      ) : (
        <div className="bg-white p-6 rounded-2xl border border-slate-200/80 shadow-xs space-y-6">
          {fhirSuccess ? (
            <div className="text-center py-8 space-y-4">
              <div className="w-14 h-14 bg-emerald-100 text-emerald-600 rounded-full flex items-center justify-center mx-auto">
                <CheckCircle2 className="w-8 h-8" />
              </div>
              <h2 className="text-xl font-bold text-slate-900">FHIR Discharge Imported Successfully</h2>
              <p className="text-xs text-slate-600 max-w-md mx-auto leading-relaxed">
                Patient <strong>{fhirSuccess.patient_name}</strong> was ingested from HL7 FHIR R4 bundle with {fhirSuccess.medications_count} prescribed medications and {fhirSuccess.caregivers_count} emergency contacts. Status: <strong className="text-emerald-700">{fhirSuccess.status}</strong>.
              </p>
              <div className="flex justify-center space-x-3 pt-4">
                <button
                  type="button"
                  onClick={() => navigate(`/patients/${createdPatientId}`)}
                  className="bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold px-4 py-2 rounded-xl transition-colors"
                >
                  View Patient 360 Profile →
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setFhirSuccess(null);
                    setFhirPreview(null);
                    setFhirRawJson('');
                  }}
                  className="px-4 py-2 border border-slate-300 rounded-xl text-xs font-semibold text-slate-700 hover:bg-slate-50"
                >
                  Import Another FHIR Record
                </button>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              <div>
                <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
                  <FileCode className="w-5 h-5 text-indigo-600" />
                  <span>HL7 FHIR R4 Ingestion Pipeline (ON-07)</span>
                </h3>
                <p className="text-xs text-slate-500 mt-1">
                  Ingest hospital discharge summaries in HL7 FHIR R4 format. Parses Patient, Condition, MedicationRequest, and CarePlan resources with automated duplicate detection and PostgreSQL persistence.
                </p>
              </div>

              {/* Action buttons */}
              <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
                <div className="flex items-center gap-2">
                  <label className="px-3.5 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-semibold flex items-center gap-1.5 cursor-pointer transition-colors shadow-xs">
                    <Upload className="w-4 h-4" />
                    <span>Upload Discharge .json File</span>
                    <input
                      type="file"
                      accept=".json,application/json"
                      className="hidden"
                      onChange={(e) => {
                        const file = e.target.files?.[0];
                        if (file) {
                          const reader = new FileReader();
                          reader.onload = (evt) => {
                            setFhirRawJson((evt.target?.result as string) || '');
                            setFhirPreview(null);
                            setFhirError(null);
                          };
                          reader.readAsText(file);
                        }
                      }}
                    />
                  </label>
                </div>
                {fhirRawJson && (
                  <button
                    type="button"
                    onClick={() => { setFhirRawJson(''); setFhirPreview(null); setFhirError(null); }}
                    className="text-xs text-slate-400 hover:text-slate-600"
                  >
                    Clear Editor
                  </button>
                )}
              </div>

              {/* Textarea */}
              <div className="relative">
                <textarea
                  rows={10}
                  value={fhirRawJson}
                  onChange={(e) => { setFhirRawJson(e.target.value); setFhirPreview(null); }}
                  placeholder="Paste HL7 FHIR R4 JSON Bundle or Patient resource here..."
                  className="w-full font-mono text-xs p-3.5 bg-slate-50 border border-slate-300 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none"
                />
              </div>

              {/* Error Alert */}
              {fhirError && (
                <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-xs text-rose-700 flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 text-rose-500 shrink-0" />
                  <span>{fhirError}</span>
                </div>
              )}

              {/* Validation & Preview Button */}
              <div className="flex justify-between items-center pt-2">
                <button
                  type="button"
                  onClick={handlePreviewFhir}
                  disabled={isFhirPreviewing || !fhirRawJson.trim()}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-900 text-white rounded-xl text-xs font-semibold disabled:opacity-50 transition-colors shadow-xs"
                >
                  {isFhirPreviewing ? 'Validating FHIR...' : 'Validate & Preview Bundle'}
                </button>
              </div>

              {/* Preview Card */}
              {fhirPreview && (
                <div className="mt-4 p-4 bg-slate-50 border border-slate-200 rounded-2xl space-y-4 text-xs">
                  <div className="flex items-center justify-between border-b border-slate-200 pb-2">
                    <h4 className="font-bold text-slate-900 flex items-center gap-1.5">
                      <Check className="w-4 h-4 text-emerald-600" />
                      <span>Pre-Import Validation Review</span>
                    </h4>
                    {fhirPreview.is_duplicate ? (
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-rose-100 text-rose-700">
                        Duplicate Detected
                      </span>
                    ) : (
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-700">
                        Valid & Unique Record
                      </span>
                    )}
                  </div>

                  {/* Duplicate warning */}
                  {fhirPreview.is_duplicate && (
                    <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl text-amber-800 text-xs">
                      <strong>Warning:</strong> A patient with phone <strong>{fhirPreview.summary?.phone}</strong> already exists in the system (ID: {fhirPreview.duplicate_patient?.id}, Name: {fhirPreview.duplicate_patient?.name}). Duplicate creation is blocked.
                    </div>
                  )}

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <p className="text-[11px] font-semibold text-slate-400">PATIENT DEMOGRAPHICS</p>
                      <p className="font-bold text-slate-900 text-sm mt-0.5">{fhirPreview.summary?.patient_name}</p>
                      <p className="text-slate-600">Phone: {fhirPreview.summary?.phone}</p>
                      <p className="text-slate-600">Language: {fhirPreview.parsed_data?.demographics?.preferred_language?.toUpperCase()}</p>
                      <p className="text-slate-600">DOB: {fhirPreview.parsed_data?.demographics?.dob}</p>
                      <p className="text-slate-600">Gender: {fhirPreview.parsed_data?.demographics?.gender}</p>
                    </div>

                    <div>
                      <p className="text-[11px] font-semibold text-slate-400">PRIMARY DIAGNOSIS</p>
                      <p className="font-semibold text-slate-800 mt-0.5">{fhirPreview.summary?.diagnosis}</p>
                      <p className="text-[11px] font-semibold text-slate-400 mt-3">EMERGENCY CONTACTS</p>
                      {fhirPreview.parsed_data?.caregivers?.length === 0 ? (
                        <p className="text-slate-400 italic">None listed</p>
                      ) : (
                        fhirPreview.parsed_data?.caregivers?.map((cg: any, idx: number) => (
                          <p key={idx} className="text-slate-700">
                            {cg.name} ({cg.relationship}) - {cg.phone}
                          </p>
                        ))
                      )}
                    </div>
                  </div>

                  {/* Medications List */}
                  <div>
                    <p className="text-[11px] font-semibold text-slate-400 mb-1.5">PRESCRIBED MEDICATIONS ({fhirPreview.summary?.medications_count})</p>
                    <div className="border border-slate-200 rounded-xl overflow-hidden">
                      <table className="w-full text-left text-xs bg-white">
                        <thead className="bg-slate-100 text-slate-600 font-semibold">
                          <tr>
                            <th className="px-3 py-2">Medicine</th>
                            <th className="px-3 py-2">Dosage</th>
                            <th className="px-3 py-2">Frequency</th>
                            <th className="px-3 py-2">Times</th>
                            <th className="px-3 py-2">Route</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100">
                          {fhirPreview.parsed_data?.medications?.map((m: any, idx: number) => (
                            <tr key={idx}>
                              <td className="px-3 py-2 font-bold text-slate-800">{m.medicine_name}</td>
                              <td className="px-3 py-2 text-slate-600">{m.dosage}</td>
                              <td className="px-3 py-2 font-semibold text-indigo-700">{m.frequency}</td>
                              <td className="px-3 py-2 text-slate-600">{m.dose_times?.join(', ')}</td>
                              <td className="px-3 py-2 text-slate-600">{m.route}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>

                  <div className="pt-2 flex justify-end">
                    <button
                      type="button"
                      onClick={handleExecuteFhirImport}
                      disabled={isFhirImporting || fhirPreview.is_duplicate}
                      className="px-5 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-bold disabled:opacity-50 transition-colors shadow-xs flex items-center gap-1.5"
                    >
                      <CheckCircle2 className="w-4 h-4" />
                      <span>{isFhirImporting ? 'Ingesting Record...' : 'Complete FHIR Ingestion & Activate Programme'}</span>
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

    </div>
  );
};
