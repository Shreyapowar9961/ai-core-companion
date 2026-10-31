import React, { useState, useEffect } from 'react';
import { apiClient } from '../api/client';
import {
  Calendar, Clock, CheckCircle2, AlertCircle, X, ShieldCheck,
  Play, Sparkles, MessageSquare, Phone
} from 'lucide-react';
import { MonitoringPlan } from '../types';

interface MonitoringPlanModalProps {
  isOpen: boolean;
  onClose: () => void;
  patientId: string;
  patientName: string;
  token?: string | null;
  onPlanSaved: () => void;
}

export const MonitoringPlanModal: React.FC<MonitoringPlanModalProps> = ({
  isOpen,
  onClose,
  patientId,
  patientName,
  token,
  onPlanSaved
}) => {
  const [frequency, setFrequency] = useState<string>('DAILY');
  const [channel, setChannel] = useState<string>('VOICE');
  const [startDate, setStartDate] = useState<string>(new Date().toISOString().split('T')[0]);
  const [endDate, setEndDate] = useState<string>(
    new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]
  );
  const [approvedQuestions, setApprovedQuestions] = useState<string[]>([
    'pain_level',
    'breathlessness',
    'dizziness',
    'wound_status',
    'vitals_spo2'
  ]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isTriggering, setIsTriggering] = useState<boolean>(false);
  const [statusMessage, setStatusMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  useEffect(() => {
    if (isOpen && token) {
      loadPlan();
    }
  }, [isOpen, token, patientId]);

  const loadPlan = async () => {
    if (!token) return;
    try {
      const plan = await apiClient.getMonitoringPlan(token, patientId);
      if (plan && plan.start_date) {
        setStartDate(plan.start_date.split('T')[0]);
        setEndDate(plan.end_date.split('T')[0]);
        setFrequency(plan.frequency || 'DAILY');
        setChannel(plan.communication_channel || 'VOICE');
        if (plan.approved_questions) {
          setApprovedQuestions(plan.approved_questions);
        }
      }
    } catch (e) {
      // Default initial plan
    }
  };

  if (!isOpen) return null;

  const toggleQuestion = (q: string) => {
    if (approvedQuestions.includes(q)) {
      setApprovedQuestions(approvedQuestions.filter((item) => item !== q));
    } else {
      setApprovedQuestions([...approvedQuestions, q]);
    }
  };

  const handleSavePlan = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) return;
    setIsLoading(true);
    setStatusMessage(null);
    try {
      await apiClient.saveMonitoringPlan(token, {
        patient_id: patientId,
        start_date: startDate,
        end_date: endDate,
        frequency,
        communication_channel: channel,
        approved_questions: approvedQuestions,
        is_active: true
      });
      setStatusMessage({ type: 'success', text: 'Monitoring plan configured and scheduled successfully.' });
      setTimeout(() => {
        onPlanSaved();
        onClose();
      }, 1200);
    } catch (err: any) {
      setStatusMessage({ type: 'error', text: err.message || 'Failed to save monitoring plan.' });
    } finally {
      setIsLoading(false);
    }
  };

  const handleTriggerSchedulerCycle = async () => {
    if (!token) return;
    setIsTriggering(true);
    setStatusMessage(null);
    try {
      const res = await apiClient.triggerMonitoringScheduler(token);
      setStatusMessage({
        type: 'success',
        text: `Scheduler cycle ran successfully! Tasks created: ${res.result?.tasks_created || 0}, Reminders: ${res.result?.reminders_created || 0}.`
      });
      onPlanSaved();
    } catch (err: any) {
      setStatusMessage({ type: 'error', text: err.message || 'Scheduler execution failed.' });
    } finally {
      setIsTriggering(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl max-w-xl w-full p-6 sm:p-8 shadow-2xl border border-slate-200">
        
        {/* Modal Header */}
        <div className="flex items-start justify-between border-b border-slate-100 pb-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="p-2 rounded-xl bg-indigo-50 text-indigo-600">
                <Calendar className="w-5 h-5" />
              </span>
              <h3 className="text-lg font-bold text-slate-900">
                Configure Recovery Monitoring Plan
              </h3>
            </div>
            <p className="text-xs text-slate-500 mt-1">
              Patient: <strong>{patientName}</strong> · Automated Database-Persisted Task Generation (Phase 3)
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Status Notification */}
        {statusMessage && (
          <div className={`mt-4 p-3 rounded-xl border text-xs font-semibold flex items-center gap-2 ${statusMessage.type === 'success' ? 'bg-emerald-50 border-emerald-200 text-emerald-800' : 'bg-rose-50 border-rose-200 text-rose-800'}`}>
            {statusMessage.type === 'success' ? <CheckCircle2 className="w-4 h-4 shrink-0" /> : <AlertCircle className="w-4 h-4 shrink-0" />}
            <span>{statusMessage.text}</span>
          </div>
        )}

        <form onSubmit={handleSavePlan} className="mt-5 space-y-4">
          {/* Dates */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">Programme Start Date</label>
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                required
                className="w-full text-xs font-semibold px-3 py-2 rounded-xl border border-slate-300"
              />
            </div>
            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">Programme End Date</label>
              <input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                required
                className="w-full text-xs font-semibold px-3 py-2 rounded-xl border border-slate-300"
              />
            </div>
          </div>

          {/* Frequency & Communication Channel */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">Check-in Frequency</label>
              <select
                value={frequency}
                onChange={(e) => setFrequency(e.target.value)}
                className="w-full text-xs font-semibold px-3 py-2 rounded-xl border border-slate-300"
              >
                <option value="DAILY">Once Daily (Morning)</option>
                <option value="TWICE_DAILY">Twice Daily (Morning & Evening)</option>
                <option value="WEEKLY">Weekly Follow-up</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">Preferred Simulated Channel</label>
              <select
                value={channel}
                onChange={(e) => setChannel(e.target.value)}
                className="w-full text-xs font-semibold px-3 py-2 rounded-xl border border-slate-300"
              >
                <option value="VOICE">Simulated Voice Telephony</option>
                <option value="WHATSAPP">Simulated WhatsApp</option>
                <option value="SMS">Simulated SMS</option>
              </select>
            </div>
          </div>

          {/* Approved Check-in Questions */}
          <div>
            <label className="block text-xs font-bold text-slate-700 mb-2">Approved Clinical Check-in Items</label>
            <div className="grid grid-cols-2 gap-2 text-xs">
              {[
                { id: 'pain_level', label: 'Incision Pain Level (0-10)' },
                { id: 'breathlessness', label: 'Shortness of Breath' },
                { id: 'dizziness', label: 'Postural Dizziness' },
                { id: 'swelling', label: 'Peripheral Edema / Swelling' },
                { id: 'wound_status', label: 'Surgical Wound Condition' },
                { id: 'vitals_spo2', label: 'SpO2 Oxygen Saturation' },
                { id: 'vitals_bp', label: 'Blood Pressure & Heart Rate' }
              ].map((q) => (
                <label key={q.id} className="flex items-center gap-2 p-2 rounded-lg bg-slate-50 border border-slate-200 cursor-pointer text-slate-700">
                  <input
                    type="checkbox"
                    checked={approvedQuestions.includes(q.id)}
                    onChange={() => toggleQuestion(q.id)}
                    className="rounded text-indigo-600 focus:ring-indigo-500"
                  />
                  <span className="font-medium text-[11px]">{q.label}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Trigger Cycle Button */}
          <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 flex items-center justify-between">
            <div>
              <span className="text-xs font-bold text-slate-800 block">Demonstration Trigger</span>
              <span className="text-[10px] text-slate-500">Run an instant scheduler cycle to generate tasks now.</span>
            </div>
            <button
              type="button"
              onClick={handleTriggerSchedulerCycle}
              disabled={isTriggering}
              className="py-1.5 px-3 rounded-lg bg-indigo-50 hover:bg-indigo-100 text-indigo-700 text-xs font-bold border border-indigo-200 flex items-center gap-1.5 transition-all disabled:opacity-50"
            >
              <Play className="w-3.5 h-3.5" />
              <span>{isTriggering ? 'Running...' : 'Run Cycle'}</span>
            </button>
          </div>

          {/* Action Buttons */}
          <div className="flex items-center gap-3 pt-3 border-t border-slate-100">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 py-2 px-4 rounded-xl border border-slate-300 text-xs font-semibold text-slate-700 hover:bg-slate-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isLoading}
              className="flex-1 py-2.5 px-4 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-xs shadow-md transition-all flex items-center justify-center gap-2 disabled:opacity-50"
            >
              <ShieldCheck className="w-4 h-4" />
              <span>Save & Activate Plan</span>
            </button>
          </div>
        </form>

      </div>
    </div>
  );
};
