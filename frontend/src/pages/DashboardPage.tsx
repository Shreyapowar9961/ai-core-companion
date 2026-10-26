import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { apiClient } from '../api/client';
import { PriorityPatientItem, Alert } from '../types';
import { StatusBadge } from '../components/StatusBadge';
import {
  AlertTriangle,
  PhoneCall,
  Search,
  ArrowRight,
  Clock,
  ShieldCheck,
  CheckCircle2,
  Users
} from 'lucide-react';

interface DashboardPageProps {
  onOpenCallSimulator: () => void;
}

export const DashboardPage: React.FC<DashboardPageProps> = ({ onOpenCallSimulator }) => {
  const { token, currentUser } = useAuth();
  const navigate = useNavigate();

  const [priorityPatients, setPriorityPatients] = useState<PriorityPatientItem[]>([]);
  const [activeAlerts, setActiveAlerts] = useState<Alert[]>([]);
  const [isLoadingPatients, setIsLoadingPatients] = useState<boolean>(true);
  const [isLoadingAlerts, setIsLoadingAlerts] = useState<boolean>(true);

  const [searchQuery, setSearchQuery] = useState('');
  const [selectedTier, setSelectedTier] = useState<string>('ALL');

  useEffect(() => {
    if (!token) return;

    // 1. Fetch live priority patients from backend API (DB-02)
    setIsLoadingPatients(true);
    apiClient.getPriorityPatients(token, currentUser?.facility_id)
      .then((data) => {
        setPriorityPatients(data || []);
      })
      .catch((err) => {
        console.error('Failed to fetch priority patients:', err.message);
        setPriorityPatients([]);
      })
      .finally(() => setIsLoadingPatients(false));

    // 2. Fetch live open triage alerts from backend API (ES-01 to ES-07)
    setIsLoadingAlerts(true);
    apiClient.getAlerts(token, 'OPEN')
      .then((data) => {
        setActiveAlerts(data || []);
      })
      .catch((err) => {
        console.error('Failed to fetch active alerts:', err.message);
        setActiveAlerts([]);
      })
      .finally(() => setIsLoadingAlerts(false));
  }, [token, currentUser]);

  const filteredPatients = priorityPatients.filter((p) => {
    const matchesSearch =
      `${p.first_name} ${p.last_name}`.toLowerCase().includes(searchQuery.toLowerCase()) ||
      p.diagnosis.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (p.inclusion_reasons && p.inclusion_reasons.some(r => r.toLowerCase().includes(searchQuery.toLowerCase())));

    const matchesTier = selectedTier === 'ALL' || p.priority_tier === selectedTier;
    return matchesSearch && matchesTier;
  });

  const formatSlaRemaining = (dueAtStr: string) => {
    const diff = new Date(dueAtStr).getTime() - Date.now();
    if (diff <= 0) return 'SLA Expired';
    const mins = Math.floor(diff / 60000);
    const secs = Math.floor((diff % 60000) / 1000);
    return `${mins}m ${secs}s`;
  };

  return (
    <div className="space-y-6">
      
      {/* Action Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Clinical Recovery Workstation</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Real-time patient triaging, active SLA alerts, and voice telephony check-ins.
          </p>
        </div>
        <div className="flex items-center space-x-3">
          <button
            onClick={onOpenCallSimulator}
            className="inline-flex items-center space-x-2 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold px-4 py-2 rounded-xl transition-colors shadow-xs"
          >
            <PhoneCall className="w-4 h-4" />
            <span>Simulate Voice Call</span>
          </button>
          <button
            onClick={() => navigate('/onboard')}
            className="bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold px-4 py-2 rounded-xl transition-colors shadow-xs"
          >
            + Onboard Patient
          </button>
        </div>
      </div>

      {/* Active Clinical Triage Alerts (ES-01 to ES-07) */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="px-5 py-4 border-b border-slate-200 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <AlertTriangle className="w-4 h-4 text-rose-600" />
            <h2 className="text-sm font-bold text-slate-900">Active Triage Alerts</h2>
            <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${
              activeAlerts.length > 0 ? 'bg-rose-100 text-rose-800' : 'bg-slate-100 text-slate-600'
            }`}>
              {activeAlerts.length} Active
            </span>
          </div>
          <button
            onClick={() => navigate('/alerts')}
            className="text-xs text-indigo-600 hover:text-indigo-800 font-semibold flex items-center gap-1"
          >
            <span>View Full Triage Drawer</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>

        {isLoadingAlerts ? (
          <div className="p-8 text-center text-slate-400 text-xs flex items-center justify-center gap-2">
            <div className="w-4 h-4 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin" />
            <span>Loading active clinical alerts...</span>
          </div>
        ) : activeAlerts.length === 0 ? (
          <div className="p-6 text-center text-slate-500 text-xs flex items-center justify-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-500" />
            <span>All clinical triage alerts are resolved for this facility.</span>
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {activeAlerts.slice(0, 3).map((alert) => (
              <div key={alert.id} className="p-4 hover:bg-slate-50/70 transition-colors flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <StatusBadge status={alert.severity} size="sm" />
                    <span className="font-semibold text-xs text-slate-900">{alert.title}</span>
                    <span className="text-[11px] text-slate-400 font-mono">({alert.patient_id})</span>
                  </div>
                  <p className="text-xs text-slate-600">{alert.description}</p>
                </div>
                <div className="flex items-center gap-4 shrink-0">
                  <div className="flex items-center gap-1 text-xs font-mono font-semibold text-rose-600 bg-rose-50 px-2.5 py-1 rounded-md border border-rose-200">
                    <Clock className="w-3.5 h-3.5" />
                    <span>{formatSlaRemaining(alert.sla_due_at)}</span>
                  </div>
                  <button
                    onClick={() => navigate('/alerts')}
                    className="text-xs font-semibold px-3 py-1.5 rounded-lg bg-indigo-50 hover:bg-indigo-100 text-indigo-700 transition-colors border border-indigo-200"
                  >
                    Resolve
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Explainable Priority Patient Queue (DB-02) */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
        
        {/* Table Controls */}
        <div className="p-5 border-b border-slate-200 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center space-x-2">
              <Users className="w-4 h-4 text-slate-700" />
              <h2 className="text-sm font-bold text-slate-900">Priority Patient Attention Queue</h2>
              <span className="bg-slate-100 text-slate-700 text-xs font-semibold px-2 py-0.5 rounded-full">
                {filteredPatients.length} Patients
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              Ranked strictly by deterministic clinical escalation rules with transparent inclusion reasons.
            </p>
          </div>

          {/* Search & Filters */}
          <div className="flex items-center space-x-3">
            <div className="relative">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
              <input
                type="text"
                placeholder="Search patient or diagnosis..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9 pr-4 py-1.5 border border-slate-300 rounded-xl text-xs w-56 focus:outline-hidden focus:ring-2 focus:ring-indigo-500"
              />
            </div>

            <select
              value={selectedTier}
              onChange={(e) => setSelectedTier(e.target.value)}
              className="border border-slate-300 rounded-xl px-3 py-1.5 text-xs text-slate-700 font-medium bg-white"
            >
              <option value="ALL">All Tiers</option>
              <option value="CRITICAL">Critical</option>
              <option value="HIGH">High</option>
              <option value="MEDIUM">Medium</option>
              <option value="LOW">Low</option>
            </select>
          </div>
        </div>

        {/* Real-Time Patient Rows */}
        {isLoadingPatients ? (
          <div className="p-12 text-center text-slate-400 text-xs flex items-center justify-center gap-2">
            <div className="w-4 h-4 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin" />
            <span>Fetching real-time patient queue from database...</span>
          </div>
        ) : filteredPatients.length === 0 ? (
          <div className="p-12 text-center text-slate-500 text-xs">
            <p className="font-semibold text-slate-700 text-sm">No Patients in Priority Queue</p>
            <p className="mt-1 text-slate-400">All assigned patients are currently stable with no pending escalation alerts.</p>
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {filteredPatients.map((patient) => (
              <div
                key={patient.patient_id}
                className="p-5 hover:bg-slate-50/70 transition-colors flex flex-col lg:flex-row lg:items-center justify-between gap-4"
              >
                {/* Patient Basic & Priority Info */}
                <div className="space-y-2 max-w-2xl">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-bold text-sm text-slate-900">
                      {patient.first_name} {patient.last_name}
                    </span>
                    <span className="text-xs text-slate-400 font-mono">({patient.patient_id})</span>
                    <StatusBadge status={patient.priority_tier} size="sm" />
                    <span className="text-xs text-slate-500">· {patient.diagnosis}</span>
                  </div>

                  {/* Explicit Inclusion Reasons (DB-02 Requirement) */}
                  {patient.inclusion_reasons && patient.inclusion_reasons.length > 0 && (
                    <div className="space-y-1">
                      <div className="flex flex-wrap gap-1.5">
                        {patient.inclusion_reasons.map((reason, idx) => (
                          <span
                            key={idx}
                            className={`text-xs px-2.5 py-1 rounded-md font-medium border ${
                              patient.priority_tier === 'CRITICAL'
                                ? 'bg-rose-50 text-rose-800 border-rose-200'
                                : 'bg-amber-50 text-amber-800 border-amber-200'
                            }`}
                          >
                            • {reason}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                {/* Metrics & Actions */}
                <div className="flex items-center space-x-6 shrink-0 pt-2 lg:pt-0">
                  <div className="text-right">
                    <p className="text-[11px] text-slate-400 font-medium">Med Adherence</p>
                    <p className={`text-sm font-bold ${
                      patient.medication_adherence_7d < 70 ? 'text-rose-600' : 'text-slate-800'
                    }`}>
                      {patient.medication_adherence_7d}%
                    </p>
                  </div>

                  <div className="text-right">
                    <p className="text-[11px] text-slate-400 font-medium">Open Alerts</p>
                    <p className="text-sm font-bold text-rose-600">{patient.open_alerts_count}</p>
                  </div>

                  <div className="text-right hidden sm:block">
                    <p className="text-[11px] text-slate-400 font-medium">Last Call</p>
                    <p className="text-xs font-medium text-slate-700">{patient.last_call_time || 'Pending'}</p>
                  </div>

                  <button
                    onClick={() => navigate(`/patients/${patient.patient_id}`)}
                    className="bg-indigo-50 hover:bg-indigo-100 text-indigo-700 font-semibold px-3 py-2 rounded-xl text-xs flex items-center space-x-1.5 transition-colors border border-indigo-200"
                  >
                    <span>Patient 360</span>
                    <ArrowRight className="w-3.5 h-3.5" />
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
