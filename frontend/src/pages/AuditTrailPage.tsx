import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { apiClient } from '../api/client';
import { PatientJourney } from '../types';
import {
  History,
  Search,
  Calendar,
  PhoneCall,
  Activity,
  Heart,
  Pill,
  AlertTriangle,
  AlertCircle
} from 'lucide-react';

export const AuditTrailPage: React.FC = () => {
  const { token } = useAuth();
  const [patientIdInput, setPatientIdInput] = useState('patient-apex-101');
  const [journey, setJourney] = useState<PatientJourney | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleReconstructJourney = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!patientIdInput.trim()) return;

    setIsLoading(true);
    setErrorMessage(null);
    setJourney(null);

    try {
      const data = await apiClient.getPatientJourney(token, patientIdInput.trim());
      setJourney(data);
    } catch (err: any) {
      setErrorMessage(err.message || `No audit journey records found for patient ${patientIdInput}.`);
    } finally {
      setIsLoading(false);
    }
  };

  const getEventIcon = (type: string) => {
    switch (type) {
      case 'CALL_INTERACTION':
        return <PhoneCall className="w-4 h-4 text-emerald-600" />;
      case 'VITAL_READING':
        return <Activity className="w-4 h-4 text-indigo-600" />;
      case 'SYMPTOM_CHECKIN':
        return <Heart className="w-4 h-4 text-amber-600" />;
      case 'MEDICATION_LOG':
        return <Pill className="w-4 h-4 text-purple-600" />;
      case 'ALERT_TRIGGERED':
      case 'ALERT_ACTION':
        return <AlertTriangle className="w-4 h-4 text-rose-600" />;
      default:
        return <History className="w-4 h-4 text-slate-600" />;
    }
  };

  return (
    <div className="space-y-6">
      
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Clinical Audit & Journey Reconstruction</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            BRD GV-03 & GV-05: Immutable append-only audit trail and chronological interaction reconstruction.
          </p>
        </div>

        {/* Patient ID Search Input */}
        <form onSubmit={handleReconstructJourney} className="flex items-center gap-2">
          <div className="relative">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Enter Patient ID (e.g., patient-apex-101)..."
              value={patientIdInput}
              onChange={(e) => setPatientIdInput(e.target.value)}
              className="pl-9 pr-3 py-1.5 border border-slate-300 rounded-xl text-xs w-64 focus:outline-hidden focus:ring-2 focus:ring-indigo-500"
            />
          </div>
          <button
            type="submit"
            disabled={isLoading}
            className="px-3.5 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-xs rounded-xl transition-colors disabled:bg-slate-300"
          >
            {isLoading ? 'Fetching...' : 'Reconstruct'}
          </button>
        </form>
      </div>

      {/* Error Message */}
      {errorMessage && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* Main Timeline Card */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-xs p-6">
        {isLoading ? (
          <div className="p-12 text-center text-slate-400 text-xs flex items-center justify-center gap-2">
            <div className="w-4 h-4 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin" />
            <span>Reconstructing chronological patient journey from immutable audit records...</span>
          </div>
        ) : !journey ? (
          <div className="p-12 text-center text-slate-500 text-xs">
            <History className="w-8 h-8 text-slate-400 mx-auto mb-2" />
            <p className="font-semibold text-slate-700 text-sm">No Patient Selected</p>
            <p className="mt-1 text-slate-400">Enter a valid patient ID above to reconstruct their end-to-end recovery audit log.</p>
          </div>
        ) : journey.events.length === 0 ? (
          <div className="p-12 text-center text-slate-500 text-xs">
            <p className="font-semibold text-slate-700 text-sm">No Events Recorded</p>
            <p className="mt-1 text-slate-400">There are no audit events recorded for patient {journey.patient_id}.</p>
          </div>
        ) : (
          <div className="space-y-6">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <span className="font-bold text-sm text-slate-900">
                Patient ID: <span className="font-mono text-indigo-700">{journey.patient_id}</span>
              </span>
              <span className="text-xs font-semibold px-2.5 py-1 bg-slate-100 text-slate-700 rounded-md">
                {journey.total_events} Chronological Events Logged
              </span>
            </div>

            {/* Timeline Stream */}
            <div className="relative border-l border-slate-200 ml-4 space-y-6">
              {journey.events.map((event, idx) => (
                <div key={idx} className="relative pl-6">
                  {/* Timeline bullet icon */}
                  <div className="absolute -left-3 top-0 w-6 h-6 rounded-full bg-white border border-slate-300 shadow-xs flex items-center justify-center">
                    {getEventIcon(event.type)}
                  </div>

                  <div className="space-y-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-xs font-bold text-slate-800">
                        {event.subtype || event.type}
                      </span>
                      <span className="text-[11px] text-slate-400 font-mono">
                        {new Date(event.timestamp).toLocaleString()}
                      </span>
                    </div>

                    {/* Event Detail Snippet */}
                    <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/80 text-xs text-slate-600 font-mono text-[11px]">
                      {event.details ? JSON.stringify(event.details) : `${event.type}: ${event.value || ''} ${event.unit || ''} ${event.status || ''}`}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

    </div>
  );
};
