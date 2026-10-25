import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { apiClient } from '../api/client';
import { EscalationRule } from '../types';
import { StatusBadge } from '../components/StatusBadge';
import {
  Sliders,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Save,
  Lock
} from 'lucide-react';

export const RulesConfigPage: React.FC = () => {
  const { token, currentUser } = useAuth();
  const isClinicianOrAdmin = currentUser?.role === 'CLINICIAN' || currentUser?.role === 'ADMIN';

  const [rules, setRules] = useState<EscalationRule[]>([
    {
      id: 'rule-1',
      code: 'RULE_VITALS_SPO2_CRITICAL',
      name: 'Critical Pulse Oximetry (SpO2) Threshold Breach',
      category: 'VITALS',
      severity: 'CRITICAL',
      condition_json: { parameter: 'spo2', operator: '<', threshold_default: 88, plausible_min: 50, plausible_max: 100 },
      action_json: { sla_minutes: 15, notify_caregiver: true, emergency_script: true },
      is_active: true
    },
    {
      id: 'rule-2',
      code: 'RULE_RED_FLAG_EMERGENCY',
      name: 'Acute Red-Flag Symptom Emergency Presentation',
      category: 'SYMPTOMS',
      severity: 'CRITICAL',
      condition_json: { pain_level_min: 8, acute_breathlessness: true, purulent_wound_discharge: true },
      action_json: { sla_minutes: 15, emergency_script: true, immediate_care_team_alert: true },
      is_active: true
    },
    {
      id: 'rule-3',
      code: 'RULE_SYMPTOM_SUSTAINED_WORSENING_BREATHLESSNESS',
      name: 'Sustained Deteriorating Breathlessness Trend',
      category: 'SYMPTOMS',
      severity: 'HIGH',
      condition_json: { symptom: 'breathlessness', consecutive_worsening_days: 2 },
      action_json: { sla_minutes: 60, notify_caregiver: true, queue_physician_review: true },
      is_active: true
    },
    {
      id: 'rule-4',
      code: 'RULE_MED_REPEATED_MISS',
      name: 'Repeated Medication Miss Against Patient Threshold',
      category: 'MEDICATION',
      severity: 'HIGH',
      condition_json: { consecutive_misses_threshold: 2 },
      action_json: { sla_minutes: 60, notify_caregiver: true, medication_adherence_review: true },
      is_active: true
    },
    {
      id: 'rule-5',
      code: 'RULE_CONTACT_FAILURE_EXHAUSTED',
      name: 'Outbound Contact Attempts Exhausted',
      category: 'CONTACT',
      severity: 'HIGH',
      condition_json: { retry_limit_reached: true },
      action_json: { sla_minutes: 60, escalate_to_caregiver: true, flag_non_contactable: true },
      is_active: true
    },
    {
      id: 'rule-6',
      code: 'RULE_COMPOSITE_DECLINE',
      name: 'Multi-Indicator Composite Clinical Decline',
      category: 'COMPOSITE',
      severity: 'HIGH',
      condition_json: { score_drop_points: 20, time_window_days: 3 },
      action_json: { sla_minutes: 60, prioritize_on_dashboard: true },
      is_active: true
    }
  ]);

  useEffect(() => {
    apiClient.getRules(token)
      .then((data) => {
        if (data && data.length > 0) setRules(data);
      })
      .catch((err) => console.log('Using default rules fallback:', err.message));
  }, [token]);

  return (
    <div className="space-y-6">
      
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight flex items-center space-x-2">
          <Sliders className="w-6 h-6 text-indigo-600" />
          <span>Clinical Decision Support & Rules Engine</span>
        </h1>
        <p className="text-xs text-slate-500 mt-1">
          Clinician-configured escalation logic and biological plausibility bounds. Protocol modifications require attending physician authorization.
        </p>
      </div>

      {/* RBAC Notice */}
      {!isClinicianOrAdmin && (
        <div className="p-4 bg-amber-50 border border-amber-200 rounded-2xl flex items-center space-x-3 text-xs text-amber-900">
          <Lock className="w-5 h-5 text-amber-700 shrink-0" />
          <div>
            <p className="font-bold">Read-Only Mode: Clinician Role Required</p>
            <p className="text-[11px] text-amber-800">
              Protocol modifications require Clinician or Admin privileges. Switch role in top header to edit.
            </p>
          </div>
        </div>
      )}

      {/* Rules Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {rules.map((rule) => (
          <div key={rule.id} className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-xs space-y-3">
            <div className="flex items-start justify-between gap-2">
              <div>
                <div className="flex items-center space-x-2">
                  <StatusBadge status={rule.severity} size="sm" />
                  <span className="text-[10px] bg-slate-100 font-bold px-2 py-0.5 rounded-sm text-slate-600">
                    {rule.category}
                  </span>
                </div>
                <h3 className="font-bold text-sm text-slate-900 mt-1.5">{rule.name}</h3>
                <p className="text-xs text-slate-400 font-mono">{rule.code}</p>
              </div>
              <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${
                rule.is_active ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-slate-100 text-slate-500'
              }`}>
                {rule.is_active ? 'Active' : 'Disabled'}
              </span>
            </div>

            {/* Condition Parameters Display */}
            <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 text-xs space-y-1">
              <p className="text-[11px] font-bold text-slate-700 uppercase tracking-wider">Evaluation Conditions:</p>
              <div className="flex flex-wrap gap-1.5 pt-1">
                {Object.entries(rule.condition_json).map(([k, v]) => (
                  <span key={k} className="bg-white border border-slate-300 px-2 py-0.5 rounded-md text-[11px] text-slate-700 font-medium">
                    <span className="text-slate-500 capitalize">{k.replace(/_/g, ' ')}:</span> <strong className="text-slate-800">{typeof v === 'boolean' ? (v ? 'Yes' : 'No') : String(v)}</strong>
                  </span>
                ))}
              </div>
            </div>

            {/* Enforced Actions */}
            <div className="p-3 bg-indigo-50/50 rounded-xl border border-indigo-100 text-xs space-y-1 text-indigo-950">
              <p className="text-[11px] font-bold uppercase tracking-wider text-indigo-700">Enforced Clinical SLA & Actions:</p>
              <div className="flex flex-wrap gap-2 text-[11px]">
                <span className="font-semibold bg-white px-2 py-0.5 rounded-md border border-indigo-200 flex items-center">
                  <Clock className="w-3 h-3 mr-1 text-indigo-600" />
                  SLA: {rule.action_json.sla_minutes} mins
                </span>
                {rule.action_json.notify_caregiver && (
                  <span className="font-semibold bg-white px-2 py-0.5 rounded-md border border-indigo-200">
                    Caregiver Notified
                  </span>
                )}
                {rule.action_json.emergency_script && (
                  <span className="font-semibold bg-white px-2 py-0.5 rounded-md border border-indigo-200 text-rose-700">
                    Emergency Protocol Dispatched
                  </span>
                )}
              </div>
            </div>

            {/* Audit Guarantee */}
            <p className="text-[10px] text-slate-400 pt-1">
              All protocol modifications are immutably logged in the clinical governance audit trail.
            </p>
          </div>
        ))}
      </div>

    </div>
  );
};
