import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { apiClient } from '../api/client';
import { Alert } from '../types';
import { StatusBadge } from '../components/StatusBadge';
import {
  AlertTriangle,
  Clock,
  CheckCircle2,
  Filter,
  Search,
  ShieldAlert,
  ArrowRight
} from 'lucide-react';

export const AlertsPage: React.FC = () => {
  const { token, currentUser } = useAuth();

  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [filterStatus, setFilterStatus] = useState<string>('ALL');
  const [selectedAlertForResolve, setSelectedAlertForResolve] = useState<Alert | null>(null);
  const [resolutionNotes, setResolutionNotes] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const fetchAlerts = () => {
    if (!token) return;
    setIsLoading(true);
    apiClient.getAlerts(token)
      .then((data) => {
        setAlerts(data || []);
      })
      .catch((err) => {
        console.error('Failed to fetch alerts:', err.message);
        setAlerts([]);
      })
      .finally(() => setIsLoading(false));
  };

  useEffect(() => {
    fetchAlerts();
  }, [token]);

  const handleAcknowledge = async (alertId: string) => {
    try {
      await apiClient.acknowledgeAlert(token, alertId, `Acknowledged by ${currentUser?.name || 'Staff'}`);
      fetchAlerts();
    } catch (err: any) {
      console.error('Acknowledge failed:', err.message);
    }
  };

  const handleResolve = async () => {
    if (!selectedAlertForResolve || !resolutionNotes.trim()) return;

    setIsSubmitting(true);
    try {
      await apiClient.resolveAlert(token, selectedAlertForResolve.id, resolutionNotes);
      setSelectedAlertForResolve(null);
      setResolutionNotes('');
      fetchAlerts();
    } catch (err: any) {
      console.error('Resolution failed:', err.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const filteredAlerts = alerts.filter((a) => {
    if (filterStatus === 'ALL') return true;
    return a.status === filterStatus;
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
      
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Clinical Alerts & Triage SLA</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Deterministic rules-based escalation queue with enforced clinical response SLA timers.
          </p>
        </div>
        
        {/* Status Filter */}
        <div className="flex items-center space-x-2">
          {(['ALL', 'OPEN', 'ACKNOWLEDGED', 'RESOLVED'] as const).map((s) => (
            <button
              key={s}
              onClick={() => setFilterStatus(s)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                filterStatus === s
                  ? 'bg-indigo-600 text-white shadow-xs'
                  : 'bg-white border border-slate-200 text-slate-600 hover:bg-slate-50'
              }`}
            >
              {s === 'ALL' ? 'All Alerts' : s}
            </button>
          ))}
        </div>
      </div>

      {/* Real-Time Alerts List */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
        {isLoading ? (
          <div className="p-12 text-center text-slate-400 text-xs flex items-center justify-center gap-2">
            <div className="w-4 h-4 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin" />
            <span>Fetching real-time clinical alerts...</span>
          </div>
        ) : filteredAlerts.length === 0 ? (
          <div className="p-12 text-center text-slate-500 text-xs">
            <CheckCircle2 className="w-8 h-8 text-emerald-500 mx-auto mb-2" />
            <p className="font-semibold text-slate-700 text-sm">No Alerts Found</p>
            <p className="mt-1 text-slate-400">There are no clinical alerts matching the selected status.</p>
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {filteredAlerts.map((alert) => (
              <div key={alert.id} className="p-5 hover:bg-slate-50/70 transition-colors flex flex-col lg:flex-row lg:items-center justify-between gap-4">
                
                <div className="space-y-2 max-w-2xl">
                  <div className="flex items-center gap-2">
                    <StatusBadge status={alert.severity} size="sm" />
                    <span className="font-bold text-sm text-slate-900">{alert.title}</span>
                    <span className="text-xs text-slate-400 font-mono">({alert.patient_id})</span>
                    <span className="text-xs font-semibold px-2 py-0.5 rounded bg-slate-100 text-slate-600">
                      {alert.rule_code}
                    </span>
                  </div>
                  <p className="text-xs text-slate-600">{alert.description}</p>

                  {/* Resolution Notes if Resolved */}
                  {alert.status === 'RESOLVED' && alert.resolution_action_notes && (
                    <div className="p-2.5 rounded-lg bg-emerald-50/80 border border-emerald-200 text-xs text-emerald-900 space-y-0.5">
                      <p className="font-semibold text-[11px] text-emerald-800">
                        Resolved by {alert.resolved_by || 'Clinician'}:
                      </p>
                      <p>{alert.resolution_action_notes}</p>
                    </div>
                  )}
                </div>

                {/* Status & Actions */}
                <div className="flex items-center gap-4 shrink-0">
                  {alert.status === 'OPEN' && (
                    <div className="flex items-center gap-1 text-xs font-mono font-semibold text-rose-600 bg-rose-50 px-2.5 py-1 rounded-md border border-rose-200">
                      <Clock className="w-3.5 h-3.5" />
                      <span>{formatSlaRemaining(alert.sla_due_at)}</span>
                    </div>
                  )}

                  {alert.status === 'OPEN' && (
                    <button
                      onClick={() => handleAcknowledge(alert.id)}
                      className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-100 hover:bg-slate-200 text-slate-700 transition-colors border border-slate-200"
                    >
                      Acknowledge
                    </button>
                  )}

                  {alert.status !== 'RESOLVED' && (
                    <button
                      onClick={() => setSelectedAlertForResolve(alert)}
                      className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-indigo-600 hover:bg-indigo-700 text-white transition-colors shadow-xs"
                    >
                      Resolve Alert
                    </button>
                  )}

                  {alert.status === 'RESOLVED' && (
                    <span className="text-xs font-semibold text-emerald-700 bg-emerald-50 px-2.5 py-1 rounded-md border border-emerald-200 flex items-center gap-1">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      <span>Resolved</span>
                    </span>
                  )}
                </div>

              </div>
            ))}
          </div>
        )}
      </div>

      {/* Resolve Modal (ES-07 Mandatory Clinician Notes) */}
      {selectedAlertForResolve && (
        <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl border border-slate-200 space-y-4">
            <div>
              <h3 className="text-base font-bold text-slate-900">Resolve Clinical Alert</h3>
              <p className="text-xs text-slate-500 mt-1">
                BRD requirement ES-07 mandates documenting clinical action notes prior to alert resolution.
              </p>
            </div>

            <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 text-xs">
              <p className="font-semibold text-slate-800">{selectedAlertForResolve.title}</p>
              <p className="text-slate-500 mt-0.5">{selectedAlertForResolve.description}</p>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Clinical Action Notes *
              </label>
              <textarea
                value={resolutionNotes}
                onChange={(e) => setResolutionNotes(e.target.value)}
                placeholder="Document action taken (e.g., Contacted patient, adjusted diuretic dosage, advised clinic visit)..."
                rows={3}
                className="w-full p-2.5 text-xs rounded-xl border border-slate-300 focus:outline-hidden focus:ring-2 focus:ring-indigo-500"
              />
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setSelectedAlertForResolve(null)}
                className="px-4 py-2 text-xs font-semibold rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 transition-colors"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={!resolutionNotes.trim() || isSubmitting}
                onClick={handleResolve}
                className="px-4 py-2 text-xs font-semibold rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white transition-colors disabled:bg-slate-300"
              >
                {isSubmitting ? 'Resolving...' : 'Confirm Resolution'}
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
};
