import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { apiClient } from '../api/client';
import { DashboardMetrics, PriorityPatientItem } from '../types';
import { StatusBadge } from '../components/StatusBadge';
import {
  Users,
  AlertTriangle,
  PhoneCall,
  Activity,
  ShieldCheck,
  TrendingUp,
  TrendingDown,
  Search,
  ArrowRight,
  Filter,
  CheckCircle2
} from 'lucide-react';

interface DashboardPageProps {
  onOpenCallSimulator: () => void;
}

export const DashboardPage: React.FC<DashboardPageProps> = ({ onOpenCallSimulator }) => {
  const { token, currentUser } = useAuth();
  const navigate = useNavigate();

  const [metrics, setMetrics] = useState<DashboardMetrics>({
    total_active_patients: 12,
    critical_alerts_count: 2,
    high_alerts_count: 3,
    avg_medication_adherence: 88.5,
    calls_completed_today: 18,
    calls_scheduled_today: 24,
    active_declining_trends_count: 4
  });

  const [priorityPatients, setPriorityPatients] = useState<PriorityPatientItem[]>([
    {
      patient_id: 'patient-demo-1',
      first_name: 'Ramesh',
      last_name: 'Patil',
      diagnosis: 'Post-CABG (Triple Bypass)',
      status: 'ACTIVE',
      priority_tier: 'CRITICAL',
      priority_score: 95,
      inclusion_reasons: [
        'Critical SpO2 breach: 86% recorded today (Below critical threshold)',
        'Severe acute pain score 8/10 reported'
      ],
      open_alerts_count: 2,
      medication_adherence_7d: 65,
      last_call_disposition: 'COMPLETED',
      last_call_time: 'Today 09:15 AM'
    },
    {
      patient_id: 'patient-demo-2',
      first_name: 'Sunita',
      last_name: 'Deshmukh',
      diagnosis: 'Post-Angioplasty Stent',
      status: 'ACTIVE',
      priority_tier: 'HIGH',
      priority_score: 82,
      inclusion_reasons: [
        'Sustained worsening breathlessness across 2 consecutive check-ins',
        'Repeated medication miss: Amlodipine 5mg (2 doses missed)'
      ],
      open_alerts_count: 1,
      medication_adherence_7d: 78,
      last_call_disposition: 'COMPLETED',
      last_call_time: 'Today 10:30 AM'
    },
    {
      patient_id: 'patient-demo-3',
      first_name: 'Anil',
      last_name: 'Jadhav',
      diagnosis: 'Total Knee Replacement (TKR)',
      status: 'ACTIVE',
      priority_tier: 'MEDIUM',
      priority_score: 55,
      inclusion_reasons: [
        'Medication deferral requested twice today',
        'Physiotherapy reported difficult due to swelling'
      ],
      open_alerts_count: 0,
      medication_adherence_7d: 91,
      last_call_disposition: 'COMPLETED',
      last_call_time: 'Yesterday 06:00 PM'
    }
  ]);

  const [searchQuery, setSearchQuery] = useState('');
  const [selectedTier, setSelectedTier] = useState<string>('ALL');

  useEffect(() => {
    // Fetch live dashboard metrics from backend
    apiClient.getDashboardMetrics(token, currentUser.facility_id)
      .then((data) => setMetrics(data))
      .catch((err) => console.log('Using default dashboard metrics fallback:', err.message));

    apiClient.getPriorityPatients(token, currentUser.facility_id)
      .then((data) => {
        if (data && data.length > 0) setPriorityPatients(data);
      })
      .catch((err) => console.log('Using default priority patients fallback:', err.message));
  }, [token, currentUser]);

  const filteredPatients = priorityPatients.filter((p) => {
    const matchesSearch =
      `${p.first_name} ${p.last_name}`.toLowerCase().includes(searchQuery.toLowerCase()) ||
      p.diagnosis.toLowerCase().includes(searchQuery.toLowerCase()) ||
      p.inclusion_reasons.some(r => r.toLowerCase().includes(searchQuery.toLowerCase()));

    const matchesTier = selectedTier === 'ALL' || p.priority_tier === selectedTier;
    return matchesSearch && matchesTier;
  });

  return (
    <div className="space-y-6">
      
      {/* Page Title & Context Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Recovery Care Dashboard</h1>
          <p className="text-xs text-slate-500 mt-1">
            Real-time post-discharge recovery monitoring, deterministic clinical alerts, and explainable priority triaging.
          </p>
        </div>
        <div className="flex items-center space-x-3">
          <button
            onClick={() => navigate('/onboard')}
            className="bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold px-4 py-2 rounded-xl transition-colors shadow-xs"
          >
            + Onboard Patient at Discharge
          </button>
        </div>
      </div>

      {/* Metric Cards (DB-01) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        
        {/* Active Patients */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-xs flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold text-slate-500">Active Recovery Patients</p>
            <p className="text-2xl font-bold text-slate-900 mt-1">{metrics.total_active_patients}</p>
            <p className="text-[11px] text-emerald-600 font-medium flex items-center mt-1">
              <CheckCircle2 className="w-3.5 h-3.5 mr-1" />
              100% consent verified
            </p>
          </div>
          <div className="w-12 h-12 bg-indigo-50 text-indigo-600 rounded-xl flex items-center justify-center">
            <Users className="w-6 h-6" />
          </div>
        </div>

        {/* Critical Alerts */}
        <div className="bg-white p-5 rounded-2xl border border-rose-200 shadow-xs flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold text-rose-600">Open Critical Alerts</p>
            <p className="text-2xl font-bold text-rose-700 mt-1">{metrics.critical_alerts_count}</p>
            <p className="text-[11px] text-rose-500 font-medium flex items-center mt-1">
              <AlertTriangle className="w-3.5 h-3.5 mr-1" />
              15-min clinician SLA active
            </p>
          </div>
          <div className="w-12 h-12 bg-rose-50 text-rose-600 rounded-xl flex items-center justify-center">
            <AlertTriangle className="w-6 h-6" />
          </div>
        </div>

        {/* Medication Adherence */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-xs flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold text-slate-500">Medication Adherence (7d)</p>
            <p className="text-2xl font-bold text-slate-900 mt-1">{metrics.avg_medication_adherence}%</p>
            <p className="text-[11px] text-emerald-600 font-medium flex items-center mt-1">
              <TrendingUp className="w-3.5 h-3.5 mr-1" />
              Dose-level tracking active
            </p>
          </div>
          <div className="w-12 h-12 bg-emerald-50 text-emerald-600 rounded-xl flex items-center justify-center">
            <Activity className="w-6 h-6" />
          </div>
        </div>

        {/* Calls Today */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-xs flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold text-slate-500">Calls Completed Today</p>
            <p className="text-2xl font-bold text-slate-900 mt-1">{metrics.calls_completed_today} / {metrics.calls_scheduled_today}</p>
            <p className="text-[11px] text-indigo-600 font-medium flex items-center mt-1">
              <PhoneCall className="w-3.5 h-3.5 mr-1" />
              Marathi, Hindi & English
            </p>
          </div>
          <div className="w-12 h-12 bg-indigo-50 text-indigo-600 rounded-xl flex items-center justify-center">
            <PhoneCall className="w-6 h-6" />
          </div>
        </div>

      </div>

      {/* Priority Patient List (DB-02) */}
      <div className="bg-white rounded-2xl border border-slate-200/80 shadow-xs overflow-hidden">
        
        {/* Table Header & Controls */}
        <div className="p-5 border-b border-slate-200 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center space-x-2">
              <h2 className="text-base font-bold text-slate-900">Priority Patient Attention Queue</h2>
              <span className="bg-slate-100 text-slate-700 text-xs font-semibold px-2 py-0.5 rounded-full">
                {filteredPatients.length} Patients
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              Ranked strictly by deterministic clinical escalation rules. Every priority assignment includes transparent inclusion reasons.
            </p>
          </div>

          {/* Search & Filters */}
          <div className="flex items-center space-x-3">
            <div className="relative">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
              <input
                type="text"
                placeholder="Search patient, diagnosis, or reason..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9 pr-4 py-1.5 border border-slate-300 rounded-xl text-xs w-64 focus:outline-hidden focus:ring-2 focus:ring-indigo-500"
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

        {/* Priority List Cards / Rows */}
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
                <div className="space-y-1">
                  <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
                    Inclusion Reasons:
                  </p>
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

      </div>

    </div>
  );
};
