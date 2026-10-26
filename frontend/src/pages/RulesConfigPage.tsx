import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { apiClient } from '../api/client';
import { EscalationRule } from '../types';
import { StatusBadge } from '../components/StatusBadge';
import {
  Sliders,
  CheckCircle2,
  Clock,
  Save,
  Lock
} from 'lucide-react';

export const RulesConfigPage: React.FC = () => {
  const { token, currentUser } = useAuth();
  const isClinicianOrAdmin = currentUser?.role === 'CLINICIAN' || currentUser?.role === 'ADMIN';

  const [rules, setRules] = useState<EscalationRule[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [saveSuccessMsg, setSaveSuccessMsg] = useState<string | null>(null);

  const fetchRules = () => {
    if (!token) return;
    setIsLoading(true);
    apiClient.getRules(token)
      .then((data) => {
        setRules(data || []);
      })
      .catch((err) => {
        console.error('Failed to fetch rules:', err.message);
        setRules([]);
      })
      .finally(() => setIsLoading(false));
  };

  useEffect(() => {
    fetchRules();
  }, [token]);

  const handleToggleRule = async (ruleId: string, currentStatus: boolean) => {
    const targetRule = rules.find(r => r.id === ruleId);
    if (!targetRule) return;

    try {
      await apiClient.saveRule(token, {
        ...targetRule,
        is_active: !currentStatus
      });
      setSaveSuccessMsg(`Rule ${targetRule.code} updated successfully.`);
      setTimeout(() => setSaveSuccessMsg(null), 3000);
      fetchRules();
    } catch (err: any) {
      console.error('Failed to update rule:', err.message);
    }
  };

  return (
    <div className="space-y-6">
      
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Clinical Rules Engine Configuration</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            BRD ES-01: Deterministic escalation rules and SLA timers configured by attending clinical staff.
          </p>
        </div>
        {saveSuccessMsg && (
          <div className="px-3 py-1.5 rounded-lg bg-emerald-50 text-emerald-800 border border-emerald-200 text-xs flex items-center gap-1.5 font-medium">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
            <span>{saveSuccessMsg}</span>
          </div>
        )}
      </div>

      {/* Rules List */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="p-5 border-b border-slate-200 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Sliders className="w-4 h-4 text-slate-700" />
            <h2 className="text-sm font-bold text-slate-900">Active Deterministic Protocols</h2>
            <span className="bg-slate-100 text-slate-700 text-xs font-semibold px-2 py-0.5 rounded-full">
              {rules.length} Configured
            </span>
          </div>
        </div>

        {isLoading ? (
          <div className="p-12 text-center text-slate-400 text-xs flex items-center justify-center gap-2">
            <div className="w-4 h-4 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin" />
            <span>Fetching real-time rules from database...</span>
          </div>
        ) : rules.length === 0 ? (
          <div className="p-12 text-center text-slate-500 text-xs">
            <p className="font-semibold text-slate-700 text-sm">No Rules Found</p>
            <p className="mt-1 text-slate-400">There are no escalation rules registered for this facility.</p>
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {rules.map((rule) => (
              <div key={rule.id} className="p-5 hover:bg-slate-50/70 transition-colors flex flex-col lg:flex-row lg:items-center justify-between gap-4">
                
                <div className="space-y-1.5 max-w-2xl">
                  <div className="flex items-center gap-2">
                    <StatusBadge status={rule.severity} size="sm" />
                    <span className="font-bold text-sm text-slate-900">{rule.name}</span>
                    <span className="text-xs font-mono px-2 py-0.5 rounded bg-slate-100 text-slate-600">
                      {rule.code}
                    </span>
                  </div>

                  {/* Conditions & Actions JSON Display */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs pt-1">
                    <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200/80 font-mono text-[11px] text-slate-700">
                      <p className="font-sans font-semibold text-slate-500 text-[10px] uppercase mb-1">Trigger Condition:</p>
                      {JSON.stringify(rule.condition_json)}
                    </div>
                    <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200/80 font-mono text-[11px] text-slate-700">
                      <p className="font-sans font-semibold text-slate-500 text-[10px] uppercase mb-1">Escalation Action:</p>
                      {JSON.stringify(rule.action_json)}
                    </div>
                  </div>
                </div>

                {/* Status Toggle */}
                <div className="flex items-center gap-3 shrink-0">
                  <button
                    onClick={() => handleToggleRule(rule.id, rule.is_active)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors border ${
                      rule.is_active
                        ? 'bg-emerald-50 text-emerald-800 border-emerald-200 hover:bg-emerald-100'
                        : 'bg-slate-100 text-slate-500 border-slate-200 hover:bg-slate-200'
                    }`}
                  >
                    {rule.is_active ? 'Active' : 'Disabled'}
                  </button>
                </div>

              </div>
            ))}
          </div>
        )}
      </div>

    </div>
  );
};
