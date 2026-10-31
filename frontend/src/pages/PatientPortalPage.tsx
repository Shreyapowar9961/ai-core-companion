import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { apiClient } from '../api/client';
import {
  HeartPulse, Pill, Calendar, Bell, MessageSquare, CheckCircle2,
  AlertCircle, Phone, Clock, FileText, Star, Activity, Sparkles,
  ShieldCheck, LogOut, ChevronRight, Droplets, Footprints, AlertTriangle
} from 'lucide-react';
import { translations, Language } from '../utils/translations';
import {
  CheckinTask, CommunicationLog, PatientFeedback, PatientDashboardSummary
} from '../types';

export const PatientPortalPage: React.FC = () => {
  const { currentUser, token, logout } = useAuth();

  const [activeTab, setActiveTab] = useState<'dashboard' | 'checkin' | 'medications' | 'history' | 'notifications' | 'comms' | 'feedback'>('dashboard');
  const [lang, setLang] = useState<Language>('en');
  const [summary, setSummary] = useState<PatientDashboardSummary | null>(null);
  const [medications, setMedications] = useState<any[]>([]);
  const [medHistory, setMedHistory] = useState<any[]>([]);
  const [checkins, setCheckins] = useState<CheckinTask[]>([]);
  const [notifications, setNotifications] = useState<CommunicationLog[]>([]);
  const [communications, setCommunications] = useState<CommunicationLog[]>([]);
  const [feedbacks, setFeedbacks] = useState<PatientFeedback[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  // Checkin Questionnaire Form State
  const [painLevel, setPainLevel] = useState<number>(2);
  const [breathlessness, setBreathlessness] = useState<string>('none');
  const [dizziness, setDizziness] = useState<string>('none');
  const [swelling, setSwelling] = useState<string>('none');
  const [woundStatus, setWoundStatus] = useState<string>('healing_well');
  const [spo2, setSpo2] = useState<string>('96');
  const [systolicBp, setSystolicBp] = useState<string>('124');
  const [heartRate, setHeartRate] = useState<string>('76');
  const [otherNotes, setOtherNotes] = useState<string>('');
  const [isSubmittingCheckin, setIsSubmittingCheckin] = useState<boolean>(false);
  const [checkinResult, setCheckinResult] = useState<any | null>(null);

  // Missed Medication Modal State
  const [selectedMissedMed, setSelectedMissedMed] = useState<any | null>(null);
  const [missedReason, setMissedReason] = useState<string>('Side effects / nausea');

  // Feedback Form State
  const [feedbackRating, setFeedbackRating] = useState<number>(5);
  const [feedbackCategory, setFeedbackCategory] = useState<string>('RECOVERY_SUPPORT');
  const [feedbackComments, setFeedbackComments] = useState<string>('');
  const [isSubmittingFeedback, setIsSubmittingFeedback] = useState<boolean>(false);

  const t = translations[lang];

  useEffect(() => {
    loadPortalData();
  }, [token]);

  const loadPortalData = async () => {
    if (!token) return;
    setIsLoading(true);
    setActionError(null);
    try {
      const [sumData, medsData, historyData, checkinsData, notifData, commsData, fbData] = await Promise.all([
        apiClient.getPortalDashboard(token).catch(() => null),
        apiClient.getPortalMedicationsSchedule(token).catch(() => []),
        apiClient.getPortalMedicationsHistory(token).catch(() => []),
        apiClient.getPortalCheckinsUpcoming(token).catch(() => []),
        apiClient.getPortalNotifications(token).catch(() => []),
        apiClient.getPortalCommunications(token).catch(() => []),
        apiClient.getPortalFeedback(token).catch(() => [])
      ]);

      if (sumData) {
        setSummary(sumData);
        if (sumData.preferred_language && ['en', 'hi', 'mr'].includes(sumData.preferred_language)) {
          setLang(sumData.preferred_language as Language);
        }
      }
      setMedications(medsData);
      setMedHistory(historyData);
      setCheckins(checkinsData);
      setNotifications(notifData);
      setCommunications(commsData);
      setFeedbacks(fbData);
    } catch (err: any) {
      setActionError(err.message || 'Failed to load recovery portal records.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleLanguageChange = async (newLang: Language) => {
    setLang(newLang);
    if (token) {
      try {
        await apiClient.updatePortalLanguage(token, newLang);
      } catch (e) {
        // Silent update
      }
    }
  };

  const handleConfirmTaken = async (med: any) => {
    if (!token) return;
    try {
      await apiClient.confirmPortalMedicationTaken(token, {
        medication_schedule_id: med.id,
        medicine_name: med.medicine_name,
        dosage: med.dosage
      });
      setActionSuccess(`Recorded dose of ${med.medicine_name} as taken.`);
      setTimeout(() => setActionSuccess(null), 4000);
      loadPortalData();
    } catch (err: any) {
      setActionError(err.message || 'Could not record dose.');
    }
  };

  const handleReportMissed = async () => {
    if (!token || !selectedMissedMed) return;
    try {
      await apiClient.reportPortalMedicationMissed(token, {
        medication_schedule_id: selectedMissedMed.id,
        medicine_name: selectedMissedMed.medicine_name,
        dosage: selectedMissedMed.dosage,
        stated_reason: missedReason
      });
      setSelectedMissedMed(null);
      setActionSuccess(`Recorded missed dose for ${selectedMissedMed.medicine_name}.`);
      setTimeout(() => setActionSuccess(null), 4000);
      loadPortalData();
    } catch (err: any) {
      setActionError(err.message || 'Could not record missed medication.');
    }
  };

  const handleSubmitCheckin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) return;
    setIsSubmittingCheckin(true);
    setCheckinResult(null);
    try {
      const payload: any = {
        pain_level: Number(painLevel),
        breathlessness,
        dizziness,
        swelling,
        wound_status: woundStatus,
        other_notes: otherNotes
      };
      if (spo2) payload.spo2 = parseFloat(spo2);
      if (systolicBp) payload.systolic_bp = parseFloat(systolicBp);
      if (heartRate) payload.heart_rate = parseFloat(heartRate);

      const res = await apiClient.submitPortalCheckin(token, payload);
      setCheckinResult(res);
      setActionSuccess('Your daily check-in has been submitted and reviewed by the recovery engine.');
      setTimeout(() => setActionSuccess(null), 5000);
      loadPortalData();
    } catch (err: any) {
      setActionError(err.message || 'Submission failed.');
    } finally {
      setIsSubmittingCheckin(false);
    }
  };

  const handleSubmitFeedback = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) return;
    setIsSubmittingFeedback(true);
    try {
      await apiClient.submitPortalFeedback(token, {
        rating: feedbackRating,
        category: feedbackCategory,
        comments: feedbackComments
      });
      setFeedbackComments('');
      setActionSuccess('Thank you! Your recovery feedback has been recorded.');
      setTimeout(() => setActionSuccess(null), 4000);
      loadPortalData();
    } catch (err: any) {
      setActionError(err.message || 'Feedback submission failed.');
    } finally {
      setIsSubmittingFeedback(false);
    }
  };

  if (isLoading && !summary) {
    return (
      <div className="min-h-screen bg-slate-900 flex flex-col items-center justify-center p-6 text-white font-sans">
        <div className="w-12 h-12 rounded-2xl bg-indigo-600 flex items-center justify-center shadow-lg mb-4 animate-pulse">
          <HeartPulse className="w-6 h-6 text-white" />
        </div>
        <p className="text-sm font-semibold text-slate-200">Loading Patient Recovery Portal...</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans text-slate-900">
      {/* Top Patient Header */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-30 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-indigo-600 flex items-center justify-center text-white shadow-md shadow-indigo-600/20">
              <HeartPulse className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-slate-900 tracking-tight text-base sm:text-lg">Apex Care</span>
                <span className="text-[11px] font-semibold bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded-full border border-emerald-200">
                  {t.portal_title}
                </span>
              </div>
              <p className="text-xs text-slate-500 hidden sm:block">
                {summary?.patient_name} · {summary?.diagnosis}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {/* Language Selector */}
            <div className="flex items-center bg-slate-100 rounded-lg p-1 border border-slate-200 text-xs font-semibold">
              <button
                onClick={() => handleLanguageChange('en')}
                className={`px-2.5 py-1 rounded-md transition-all ${lang === 'en' ? 'bg-white shadow text-indigo-700 font-bold' : 'text-slate-600 hover:text-slate-900'}`}
              >
                EN
              </button>
              <button
                onClick={() => handleLanguageChange('hi')}
                className={`px-2.5 py-1 rounded-md transition-all ${lang === 'hi' ? 'bg-white shadow text-indigo-700 font-bold' : 'text-slate-600 hover:text-slate-900'}`}
              >
                हिंदी
              </button>
              <button
                onClick={() => handleLanguageChange('mr')}
                className={`px-2.5 py-1 rounded-md transition-all ${lang === 'mr' ? 'bg-white shadow text-indigo-700 font-bold' : 'text-slate-600 hover:text-slate-900'}`}
              >
                मराठी
              </button>
            </div>

            {/* Logout Button */}
            <button
              onClick={logout}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-300 text-slate-700 hover:bg-slate-100 text-xs font-semibold transition-all"
            >
              <LogOut className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">{t.logout}</span>
            </button>
          </div>
        </div>

        {/* Navigation Tabs */}
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex overflow-x-auto gap-2 border-t border-slate-100 py-2 scrollbar-none">
          <button
            onClick={() => setActiveTab('dashboard')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-all flex items-center gap-1.5 ${activeTab === 'dashboard' ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-600 hover:bg-slate-100'}`}
          >
            <Activity className="w-3.5 h-3.5" />
            {t.dashboard_tab}
          </button>
          <button
            onClick={() => setActiveTab('checkin')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-all flex items-center gap-1.5 ${activeTab === 'checkin' ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-600 hover:bg-slate-100'}`}
          >
            <Calendar className="w-3.5 h-3.5" />
            {t.checkin_tab}
          </button>
          <button
            onClick={() => setActiveTab('medications')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-all flex items-center gap-1.5 ${activeTab === 'medications' ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-600 hover:bg-slate-100'}`}
          >
            <Pill className="w-3.5 h-3.5" />
            {t.medications_tab}
          </button>
          <button
            onClick={() => setActiveTab('history')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-all flex items-center gap-1.5 ${activeTab === 'history' ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-600 hover:bg-slate-100'}`}
          >
            <FileText className="w-3.5 h-3.5" />
            {t.med_history_tab}
          </button>
          <button
            onClick={() => setActiveTab('notifications')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-all flex items-center gap-1.5 ${activeTab === 'notifications' ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-600 hover:bg-slate-100'}`}
          >
            <Bell className="w-3.5 h-3.5" />
            {t.notifications_tab} ({notifications.length})
          </button>
          <button
            onClick={() => setActiveTab('comms')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-all flex items-center gap-1.5 ${activeTab === 'comms' ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-600 hover:bg-slate-100'}`}
          >
            <MessageSquare className="w-3.5 h-3.5" />
            {t.comms_tab}
          </button>
          <button
            onClick={() => setActiveTab('feedback')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-all flex items-center gap-1.5 ${activeTab === 'feedback' ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-600 hover:bg-slate-100'}`}
          >
            <Star className="w-3.5 h-3.5" />
            {t.feedback_tab}
          </button>
        </div>
      </header>

      {/* Main Container */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 flex-1 w-full">
        {/* Banner: Honest Simulation Indicator */}
        <div className="mb-6 p-3 rounded-xl bg-gradient-to-r from-indigo-50 to-emerald-50 border border-indigo-100 flex items-center justify-between text-xs text-slate-700">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-emerald-600 shrink-0" />
            <span>
              <strong>{t.simulated_notice}</strong>: Connected directly to Supabase PostgreSQL database. No paid telephony or external SMS charges.
            </span>
          </div>
          <span className="font-semibold text-emerald-700 bg-emerald-100/80 px-2 py-0.5 rounded-md">
            ₹0 Secure Simulation
          </span>
        </div>

        {/* Success Alert */}
        {actionSuccess && (
          <div className="mb-6 p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-semibold flex items-center gap-2 shadow-sm animate-fade-in">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            <span>{actionSuccess}</span>
          </div>
        )}

        {/* Error Alert */}
        {actionError && (
          <div className="mb-6 p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs font-semibold flex items-center gap-2 shadow-sm animate-fade-in">
            <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
            <span>{actionError}</span>
          </div>
        )}

        {/* ----------------- TAB 1: DASHBOARD ----------------- */}
        {activeTab === 'dashboard' && (
          <div className="space-y-6">
            {/* Top Stat Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {/* Recovery Progress */}
              <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex flex-col justify-between">
                <div>
                  <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">{t.recovery_progress}</span>
                  <div className="flex items-baseline gap-2 mt-2">
                    <span className="text-3xl font-extrabold text-indigo-600">{summary?.progress_score || 92}%</span>
                    <span className="text-xs font-semibold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full">Stable</span>
                  </div>
                </div>
                <div className="w-full bg-slate-100 h-2 rounded-full mt-4 overflow-hidden">
                  <div
                    className="bg-indigo-600 h-full rounded-full transition-all duration-500"
                    style={{ width: `${summary?.progress_score || 92}%` }}
                  />
                </div>
              </div>

              {/* Days Post-Op */}
              <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex flex-col justify-between">
                <div>
                  <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">{t.days_post_op}</span>
                  <div className="text-3xl font-extrabold text-slate-900 mt-2">
                    Day {summary?.days_since_discharge || 4}
                  </div>
                </div>
                <p className="text-xs text-slate-500 mt-4">
                  Discharge Care Phase · 30-Day Plan
                </p>
              </div>

              {/* Today's Medications */}
              <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex flex-col justify-between">
                <div>
                  <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">{t.today_meds}</span>
                  <div className="flex items-center gap-3 mt-2">
                    <span className="text-3xl font-extrabold text-slate-900">
                      {summary?.medication_summary.taken || 0}/{summary?.medication_summary.total || 0}
                    </span>
                    <span className="text-xs font-semibold text-indigo-700 bg-indigo-50 px-2 py-0.5 rounded-full">
                      {summary?.medication_summary.adherence_rate || 100}% Adherence
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-2 mt-4 text-[11px] font-semibold text-slate-600">
                  <span className="text-emerald-700">{summary?.medication_summary.taken || 0} {t.taken}</span> ·
                  <span className="text-rose-600">{summary?.medication_summary.missed || 0} {t.missed}</span> ·
                  <span className="text-amber-600">{summary?.medication_summary.pending || 0} {t.pending}</span>
                </div>
              </div>

              {/* Next Check-in */}
              <div className="bg-gradient-to-br from-indigo-600 to-indigo-800 p-5 rounded-2xl text-white shadow-md flex flex-col justify-between">
                <div>
                  <span className="text-xs font-semibold text-indigo-200 uppercase tracking-wider">{t.next_checkin}</span>
                  <div className="text-lg font-bold mt-2 flex items-center gap-2">
                    <Clock className="w-5 h-5 text-indigo-300" />
                    <span>{summary?.next_checkin.is_due ? t.checkin_due : 'Scheduled Daily'}</span>
                  </div>
                </div>
                <button
                  onClick={() => setActiveTab('checkin')}
                  className="mt-4 w-full py-2 px-3 bg-white text-indigo-700 font-bold text-xs rounded-xl hover:bg-indigo-50 transition-all flex items-center justify-center gap-1 shadow-sm"
                >
                  <span>{t.start_checkin}</span>
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>

            {/* Care Team & Daily Guidelines */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Care Guidelines */}
              <div className="lg:col-span-2 bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
                <h3 className="font-bold text-base text-slate-900 mb-4 flex items-center gap-2">
                  <Sparkles className="w-5 h-5 text-indigo-600" />
                  <span>Personalized Post-Discharge Guidelines</span>
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="p-4 rounded-xl bg-slate-50 border border-slate-100">
                    <div className="flex items-center gap-2 text-indigo-700 font-bold text-xs mb-1">
                      <Droplets className="w-4 h-4" />
                      <span>Hydration Target</span>
                    </div>
                    <p className="text-sm font-semibold text-slate-800">8 glasses (1.8 L) daily</p>
                    <p className="text-xs text-slate-500 mt-1">Drink in steady intervals; avoid excessive fluid after 8 PM.</p>
                  </div>
                  <div className="p-4 rounded-xl bg-slate-50 border border-slate-100">
                    <div className="flex items-center gap-2 text-emerald-700 font-bold text-xs mb-1">
                      <Footprints className="w-4 h-4" />
                      <span>Mobility & Ambulation</span>
                    </div>
                    <p className="text-sm font-semibold text-slate-800">20 minutes gentle walking</p>
                    <p className="text-xs text-slate-500 mt-1">Split into two 10-minute sessions; avoid lifting heavy weights.</p>
                  </div>
                </div>
              </div>

              {/* Attending Care Team Card */}
              <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm flex flex-col justify-between">
                <div>
                  <h3 className="font-bold text-base text-slate-900 mb-2 flex items-center gap-2">
                    <Phone className="w-5 h-5 text-indigo-600" />
                    <span>{t.doctor_in_charge}</span>
                  </h3>
                  <div className="mt-4 p-4 rounded-xl bg-indigo-50/50 border border-indigo-100">
                    <p className="font-bold text-sm text-slate-900">{summary?.doctor.name || 'Dr. V. Kulkarni'}</p>
                    <p className="text-xs text-indigo-700 font-semibold mt-0.5">Senior Cardiothoracic Surgeon</p>
                    <p className="text-xs text-slate-600 mt-2">Apex Heart & Recovery Institute, Pune</p>
                    <p className="text-xs font-mono font-bold text-slate-900 mt-1">{summary?.doctor.phone || '+91 20 2612 3456'}</p>
                  </div>
                </div>
                <div className="mt-4 text-[11px] text-slate-500">
                  For severe emergencies or acute chest pressure, dial <strong>112 / 108</strong> immediately.
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ----------------- TAB 2: RECOVERY CHECK-IN FORM ----------------- */}
        {activeTab === 'checkin' && (
          <div className="max-w-3xl mx-auto bg-white rounded-2xl border border-slate-200 p-6 sm:p-8 shadow-sm">
            <div className="mb-6">
              <h2 className="text-lg font-bold text-slate-900">{t.checkin_tab}</h2>
              <p className="text-xs text-slate-500 mt-1">
                Report your current recovery symptoms and vitals. Data is evaluated by our deterministic clinical rules engine.
              </p>
            </div>

            {checkinResult && (
              <div className={`mb-6 p-4 rounded-xl border text-xs font-semibold ${checkinResult.category === 'NEEDS_CLINICIAN_REVIEW' ? 'bg-amber-50 border-amber-300 text-amber-900' : 'bg-emerald-50 border-emerald-300 text-emerald-900'}`}>
                <div className="flex items-center gap-2 text-sm font-bold">
                  {checkinResult.category === 'NEEDS_CLINICIAN_REVIEW' ? <AlertTriangle className="w-5 h-5 text-amber-600" /> : <CheckCircle2 className="w-5 h-5 text-emerald-600" />}
                  <span>Category: {checkinResult.category.replace('_', ' ')}</span>
                </div>
                <p className="mt-1 font-normal text-xs text-slate-700">{checkinResult.category_reason}</p>
                {checkinResult.alert_generated && (
                  <p className="mt-2 text-[11px] font-bold text-rose-700 bg-rose-50 px-2.5 py-1 rounded-md border border-rose-200 inline-block">
                    Clinical escalation alert has been dispatched to your attending cardiologist queue.
                  </p>
                )}
              </div>
            )}

            <form onSubmit={handleSubmitCheckin} className="space-y-6">
              {/* Pain Level Slider */}
              <div>
                <label className="block text-xs font-bold text-slate-700 mb-2">
                  {t.pain_level}: <span className="text-indigo-600 text-sm font-extrabold">{painLevel} / 10</span>
                </label>
                <input
                  type="range"
                  min="0"
                  max="10"
                  value={painLevel}
                  onChange={(e) => setPainLevel(parseInt(e.target.value))}
                  className="w-full accent-indigo-600 cursor-pointer"
                />
                <div className="flex justify-between text-[10px] text-slate-400 font-semibold mt-1">
                  <span>0 - No Pain</span>
                  <span>5 - Moderate</span>
                  <span>10 - Unbearable</span>
                </div>
              </div>

              {/* Breathlessness */}
              <div>
                <label className="block text-xs font-bold text-slate-700 mb-2">{t.breathlessness}</label>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                  {['none', 'mild', 'moderate', 'severe'].map((val) => (
                    <button
                      key={val}
                      type="button"
                      onClick={() => setBreathlessness(val)}
                      className={`py-2 px-3 rounded-xl text-xs font-semibold border transition-all ${breathlessness === val ? 'bg-indigo-600 border-indigo-600 text-white shadow-sm' : 'bg-slate-50 border-slate-200 text-slate-700 hover:bg-slate-100'}`}
                    >
                      {t[val as keyof typeof t] || val}
                    </button>
                  ))}
                </div>
              </div>

              {/* Dizziness */}
              <div>
                <label className="block text-xs font-bold text-slate-700 mb-2">{t.dizziness}</label>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                  {['none', 'mild', 'moderate', 'severe'].map((val) => (
                    <button
                      key={val}
                      type="button"
                      onClick={() => setDizziness(val)}
                      className={`py-2 px-3 rounded-xl text-xs font-semibold border transition-all ${dizziness === val ? 'bg-indigo-600 border-indigo-600 text-white shadow-sm' : 'bg-slate-50 border-slate-200 text-slate-700 hover:bg-slate-100'}`}
                    >
                      {t[val as keyof typeof t] || val}
                    </button>
                  ))}
                </div>
              </div>

              {/* Wound Status */}
              <div>
                <label className="block text-xs font-bold text-slate-700 mb-2">{t.wound_status}</label>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {[
                    { key: 'healing_well', label: t.healing_well },
                    { key: 'redness', label: t.redness },
                    { key: 'discharge', label: t.discharge },
                    { key: 'pain', label: t.pain }
                  ].map((item) => (
                    <button
                      key={item.key}
                      type="button"
                      onClick={() => setWoundStatus(item.key)}
                      className={`py-2.5 px-3 rounded-xl text-xs font-semibold border text-left transition-all ${woundStatus === item.key ? 'bg-indigo-600 border-indigo-600 text-white shadow-sm' : 'bg-slate-50 border-slate-200 text-slate-700 hover:bg-slate-100'}`}
                    >
                      {item.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Optional Vitals */}
              <div className="p-4 rounded-xl bg-slate-50 border border-slate-200">
                <span className="block text-xs font-bold text-slate-800 mb-3">Self-Monitored Vitals (Optional)</span>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  <div>
                    <label className="block text-[11px] font-semibold text-slate-600 mb-1">SpO2 Oxygen (%)</label>
                    <input
                      type="number"
                      value={spo2}
                      onChange={(e) => setSpo2(e.target.value)}
                      placeholder="e.g. 96"
                      className="w-full text-xs font-semibold px-3 py-2 rounded-lg border border-slate-300 focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-[11px] font-semibold text-slate-600 mb-1">Systolic BP (mmHg)</label>
                    <input
                      type="number"
                      value={systolicBp}
                      onChange={(e) => setSystolicBp(e.target.value)}
                      placeholder="e.g. 120"
                      className="w-full text-xs font-semibold px-3 py-2 rounded-lg border border-slate-300 focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-[11px] font-semibold text-slate-600 mb-1">Heart Rate (bpm)</label>
                    <input
                      type="number"
                      value={heartRate}
                      onChange={(e) => setHeartRate(e.target.value)}
                      placeholder="e.g. 74"
                      className="w-full text-xs font-semibold px-3 py-2 rounded-lg border border-slate-300 focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                    />
                  </div>
                </div>
              </div>

              {/* Other Notes */}
              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">Additional Recovery Notes</label>
                <textarea
                  rows={2}
                  value={otherNotes}
                  onChange={(e) => setOtherNotes(e.target.value)}
                  placeholder="Any other sensations, sleep changes, or questions for your doctor..."
                  className="w-full text-xs px-3 py-2 rounded-xl border border-slate-300 focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                />
              </div>

              <button
                type="submit"
                disabled={isSubmittingCheckin}
                className="w-full py-3 px-4 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-sm shadow-md transition-all disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {isSubmittingCheckin ? <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" /> : <CheckCircle2 className="w-4 h-4" />}
                <span>{t.submit_checkin}</span>
              </button>
            </form>
          </div>
        )}

        {/* ----------------- TAB 3: MEDICATIONS SCHEDULE ----------------- */}
        {activeTab === 'medications' && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-bold text-slate-900">{t.medications_tab}</h2>
                <p className="text-xs text-slate-500 mt-0.5">Approved discharge prescriptions and dose confirmation tracking</p>
              </div>
            </div>

            {medications.length === 0 ? (
              <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center text-slate-500 text-xs">
                No active medication schedule currently loaded. Contact your clinical team.
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {medications.map((med: any) => (
                  <div key={med.id} className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm flex flex-col justify-between">
                    <div>
                      <div className="flex items-start justify-between">
                        <div>
                          <h3 className="font-bold text-slate-900 text-sm sm:text-base">{med.medicine_name}</h3>
                          <span className="text-xs font-semibold text-indigo-700 bg-indigo-50 px-2 py-0.5 rounded-md mt-1 inline-block">
                            {med.dosage} · {med.frequency}
                          </span>
                        </div>
                        <span className={`text-[11px] font-bold px-2 py-0.5 rounded-full ${med.status === 'TAKEN' ? 'bg-emerald-100 text-emerald-800' : (med.status === 'MISSED' ? 'bg-rose-100 text-rose-800' : 'bg-amber-100 text-amber-800')}`}>
                          {med.status}
                        </span>
                      </div>
                      <p className="text-xs text-slate-600 mt-3 font-medium">
                        <strong>Timing:</strong> {(med.dose_times || []).join(', ') || '09:00'}
                      </p>
                      <p className="text-xs text-slate-500 mt-1">
                        <strong>Instructions:</strong> {med.instructions || 'Take with water'}
                      </p>
                      {med.reason && (
                        <p className="text-[11px] text-rose-700 bg-rose-50 p-2 rounded-lg mt-2 font-semibold">
                          Reason: {med.reason}
                        </p>
                      )}
                    </div>

                    <div className="flex items-center gap-2 mt-5 pt-4 border-t border-slate-100">
                      <button
                        onClick={() => handleConfirmTaken(med)}
                        disabled={med.status === 'TAKEN'}
                        className={`flex-1 py-2 px-3 rounded-xl text-xs font-bold transition-all flex items-center justify-center gap-1.5 ${med.status === 'TAKEN' ? 'bg-slate-100 text-slate-400 cursor-not-allowed' : 'bg-emerald-600 hover:bg-emerald-700 text-white shadow-sm'}`}
                      >
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        <span>{t.confirm_taken_btn}</span>
                      </button>
                      <button
                        onClick={() => setSelectedMissedMed(med)}
                        className="py-2 px-3 rounded-xl text-xs font-semibold border border-slate-300 text-slate-700 hover:bg-slate-100 transition-all"
                      >
                        {t.report_missed_btn}
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* ----------------- TAB 4: MEDICATION HISTORY ----------------- */}
        {activeTab === 'history' && (
          <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
            <h2 className="text-lg font-bold text-slate-900 mb-4">{t.med_history_tab}</h2>
            {medHistory.length === 0 ? (
              <p className="text-xs text-slate-500">No confirmation logs recorded yet.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 text-slate-500 font-semibold border-b border-slate-200">
                    <tr>
                      <th className="py-2.5 px-3">Medicine</th>
                      <th className="py-2.5 px-3">Dose</th>
                      <th className="py-2.5 px-3">Scheduled Time</th>
                      <th className="py-2.5 px-3">Status</th>
                      <th className="py-2.5 px-3">Reported Notes / Reason</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 font-medium text-slate-700">
                    {medHistory.map((h: any) => (
                      <tr key={h.id} className="hover:bg-slate-50/50">
                        <td className="py-2.5 px-3 font-bold text-slate-900">{h.medicine_name}</td>
                        <td className="py-2.5 px-3">{h.dosage || 'Prescribed'}</td>
                        <td className="py-2.5 px-3 font-mono text-[11px] text-slate-500">
                          {new Date(h.scheduled_time).toLocaleString()}
                        </td>
                        <td className="py-2.5 px-3">
                          <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${h.status === 'TAKEN' ? 'bg-emerald-100 text-emerald-800' : 'bg-rose-100 text-rose-800'}`}>
                            {h.status}
                          </span>
                        </td>
                        <td className="py-2.5 px-3 text-slate-600">{h.stated_reason || '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* ----------------- TAB 5: NOTIFICATIONS ----------------- */}
        {activeTab === 'notifications' && (
          <div className="space-y-4 max-w-3xl mx-auto">
            <h2 className="text-lg font-bold text-slate-900 mb-2">{t.notifications_tab}</h2>
            {notifications.length === 0 ? (
              <div className="bg-white rounded-2xl border border-slate-200 p-8 text-center text-slate-500 text-xs">
                No notifications logged yet.
              </div>
            ) : (
              notifications.map((n) => (
                <div key={n.id} className="bg-white rounded-2xl border border-slate-200 p-4 shadow-sm flex items-start gap-3">
                  <div className="w-8 h-8 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center shrink-0">
                    <Bell className="w-4 h-4" />
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center justify-between">
                      <span className="text-[11px] font-bold text-indigo-700 bg-indigo-50 px-2 py-0.5 rounded-md">
                        {n.channel.replace('_', ' ')} · {n.message_type.replace('_', ' ')}
                      </span>
                      <span className="text-[10px] font-mono text-slate-400">
                        {new Date(n.sent_at).toLocaleString()}
                      </span>
                    </div>
                    <p className="text-xs text-slate-800 mt-2 font-medium">{n.content}</p>
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {/* ----------------- TAB 6: COMMUNICATION LOG ----------------- */}
        {activeTab === 'comms' && (
          <div className="space-y-4 max-w-3xl mx-auto">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-bold text-slate-900">{t.comms_tab}</h2>
                <p className="text-xs text-slate-500 mt-0.5">Automated telephony, WhatsApp, and SMS simulation logs</p>
              </div>
              <span className="text-xs font-bold text-emerald-700 bg-emerald-50 border border-emerald-200 px-2.5 py-1 rounded-lg">
                Honest Local Simulation
              </span>
            </div>

            {communications.length === 0 ? (
              <div className="bg-white rounded-2xl border border-slate-200 p-8 text-center text-slate-500 text-xs">
                No communications recorded yet.
              </div>
            ) : (
              communications.map((c) => (
                <div key={c.id} className="bg-white rounded-2xl border border-slate-200 p-4 shadow-sm">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-[11px] font-bold px-2 py-0.5 rounded-md bg-slate-100 text-slate-700">
                        {c.channel}
                      </span>
                      <span className="text-[10px] font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded">
                        SIMULATED
                      </span>
                    </div>
                    <span className="text-[10px] font-mono text-slate-400">{new Date(c.sent_at).toLocaleString()}</span>
                  </div>
                  <p className="text-xs text-slate-800 mt-2 font-medium bg-slate-50/70 p-3 rounded-xl border border-slate-100">
                    "{c.content}"
                  </p>
                </div>
              ))
            )}
          </div>
        )}

        {/* ----------------- TAB 7: FEEDBACK ----------------- */}
        {activeTab === 'feedback' && (
          <div className="max-w-2xl mx-auto space-y-6">
            <div className="bg-white rounded-2xl border border-slate-200 p-6 sm:p-8 shadow-sm">
              <h2 className="text-lg font-bold text-slate-900 mb-1">{t.feedback_title}</h2>
              <p className="text-xs text-slate-500 mb-6">
                Your feedback helps your cardiology and nursing care team continuously improve recovery assistance.
              </p>

              <form onSubmit={handleSubmitFeedback} className="space-y-4">
                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-2">{t.rating}</label>
                  <div className="flex gap-2">
                    {[1, 2, 3, 4, 5].map((star) => (
                      <button
                        key={star}
                        type="button"
                        onClick={() => setFeedbackRating(star)}
                        className={`p-2 rounded-xl transition-all ${feedbackRating >= star ? 'text-amber-400 bg-amber-50' : 'text-slate-300 hover:text-slate-400'}`}
                      >
                        <Star className="w-6 h-6 fill-current" />
                      </button>
                    ))}
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">Feedback Category</label>
                  <select
                    value={feedbackCategory}
                    onChange={(e) => setFeedbackCategory(e.target.value)}
                    className="w-full text-xs font-semibold px-3 py-2 rounded-xl border border-slate-300 focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                  >
                    <option value="RECOVERY_SUPPORT">Recovery Support & Care</option>
                    <option value="CALL_EXPERIENCE">Automated Call Experience</option>
                    <option value="MEDICATION_CLARITY">Medication Clarity</option>
                    <option value="APP_USABILITY">Portal Usability</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">Comments or Suggestions</label>
                  <textarea
                    rows={3}
                    value={feedbackComments}
                    onChange={(e) => setFeedbackComments(e.target.value)}
                    placeholder="Tell us what went well or what we can do better..."
                    className="w-full text-xs px-3 py-2 rounded-xl border border-slate-300 focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                  />
                </div>

                <button
                  type="submit"
                  disabled={isSubmittingFeedback}
                  className="w-full py-2.5 px-4 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-xs shadow-md transition-all flex items-center justify-center gap-1.5"
                >
                  <Star className="w-4 h-4" />
                  <span>{t.submit_feedback}</span>
                </button>
              </form>
            </div>

            {/* Past Feedback */}
            {feedbacks.length > 0 && (
              <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
                <h3 className="font-bold text-sm text-slate-900 mb-3">Past Feedback Submitted</h3>
                <div className="space-y-3">
                  {feedbacks.map((f) => (
                    <div key={f.id} className="p-3 rounded-xl bg-slate-50 border border-slate-100 text-xs">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-1 text-amber-500">
                          {Array.from({ length: f.rating }).map((_, i) => (
                            <Star key={i} className="w-3.5 h-3.5 fill-current" />
                          ))}
                        </div>
                        <span className="text-[10px] text-slate-400 font-mono">
                          {new Date(f.created_at).toLocaleDateString()}
                        </span>
                      </div>
                      <p className="text-slate-800 font-medium mt-1">{f.comments || 'No comments provided.'}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </main>

      {/* Missed Medication Reason Modal */}
      {selectedMissedMed && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-xl border border-slate-200">
            <h3 className="text-base font-bold text-slate-900">
              Report Missed Dose: {selectedMissedMed.medicine_name}
            </h3>
            <p className="text-xs text-slate-500 mt-1">
              Please specify the reason for missing this scheduled dose. Your doctor will be notified.
            </p>

            <div className="mt-4 space-y-2">
              {[
                'Side effects / nausea / dizziness',
                'Forgot / missed time window',
                'Ran out of medication',
                'Cost / pharmacy stock issue',
                'Feeling better / felt unnecessary'
              ].map((r) => (
                <button
                  key={r}
                  type="button"
                  onClick={() => setMissedReason(r)}
                  className={`w-full py-2 px-3 rounded-xl text-xs font-semibold text-left border transition-all ${missedReason === r ? 'bg-indigo-50 border-indigo-500 text-indigo-700' : 'bg-slate-50 border-slate-200 text-slate-700'}`}
                >
                  {r}
                </button>
              ))}
            </div>

            <div className="flex items-center gap-3 mt-6">
              <button
                type="button"
                onClick={() => setSelectedMissedMed(null)}
                className="flex-1 py-2 px-4 rounded-xl border border-slate-300 text-xs font-semibold text-slate-700 hover:bg-slate-50"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleReportMissed}
                className="flex-1 py-2 px-4 rounded-xl bg-rose-600 hover:bg-rose-700 text-xs font-bold text-white shadow-sm"
              >
                Submit Report
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
