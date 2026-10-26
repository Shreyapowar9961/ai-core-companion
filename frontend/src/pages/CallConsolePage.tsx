import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { apiClient } from '../api/client';
import {
  PhoneCall,
  PhoneOff,
  Volume2,
  RotateCcw,
  Languages,
  Sparkles,
  AlertCircle,
  CheckCircle2,
  Info
} from 'lucide-react';

export const CallConsolePage: React.FC = () => {
  const { token } = useAuth();
  const [patientId, setPatientId] = useState('patient-apex-101');
  const [language, setLanguage] = useState<'en' | 'hi' | 'mr'>('en');
  const [callType, setCallType] = useState('MORNING_CHECKIN');
  const [patients, setPatients] = useState<Array<{ id: string; name: string; diagnosis: string; lang: 'en' | 'hi' | 'mr' }>>([]);

  useEffect(() => {
    if (!token) return;
    apiClient.getPatients(token)
      .then((data) => {
        if (data && data.length > 0) {
          const mapped = data.map((p) => ({
            id: p.id,
            name: `${p.first_name} ${p.last_name}`,
            diagnosis: p.diagnosis,
            lang: (p.preferred_language || 'en') as 'en' | 'hi' | 'mr'
          }));
          setPatients(mapped);
          setPatientId(mapped[0].id);
          setLanguage(mapped[0].lang);
        }
      })
      .catch((err) => console.warn('Could not fetch patients for call console:', err.message));
  }, [token]);

  const [sessionId, setSessionId] = useState<string | null>(null);
  const [stepKey, setStepKey] = useState<string>('IDENTITY_CHECK');
  const [agentPrompt, setAgentPrompt] = useState<string>('');
  const [turns, setTurns] = useState<Array<{ agent: string; patient?: string; step: string; timestamp: string }>>([]);
  const [userSpeech, setUserSpeech] = useState('');
  const [isCompleted, setIsCompleted] = useState(false);
  const [alerts, setAlerts] = useState<any[]>([]);

  const handleStartCall = async () => {
    setTurns([]);
    setAlerts([]);
    setIsCompleted(false);

    try {
      const session = await apiClient.startCallSession(token, patientId, callType, language);
      setSessionId(session.id);
      setStepKey(session.current_step_key || 'IDENTITY_CHECK');
      setAgentPrompt(session.initial_prompt_text);
      setTurns([
        { agent: session.initial_prompt_text, step: session.current_step_key || 'IDENTITY_CHECK', timestamp: new Date().toLocaleTimeString() }
      ]);
    } catch (err: any) {
      alert(`Error starting call session: ${err.message}`);
    }
  };

  const handleSendSpeech = async (speech: string) => {
    if (!speech.trim() || !sessionId) return;
    setUserSpeech('');

    const curStep = stepKey;
    setTurns((prev) => [
      ...prev,
      { agent: '', patient: speech, step: curStep, timestamp: new Date().toLocaleTimeString() }
    ]);

    try {
      const res = await apiClient.processCallTurn(token, sessionId, speech);
      setStepKey(res.next_step_key || res.step_key);
      setAgentPrompt(res.agent_prompt_text);
      if (res.language) setLanguage(res.language);
      if (res.is_completed) setIsCompleted(true);
      if (res.is_red_flag) {
        setAlerts((prev) => [...prev, { title: 'Emergency Alert Triggered', text: speech }]);
      }

      setTurns((prev) => {
        const copy = [...prev];
        const last = copy[copy.length - 1];
        if (last) {
          last.agent = res.agent_prompt_text;
          last.step = res.step_key;
        }
        return copy;
      });
    } catch (err: any) {
      alert(`Error processing speech turn: ${err.message}`);
    }
  };

  const handleInterrupt = () => {
    setIsCompleted(true);
    setTurns((prev) => [
      ...prev,
      { agent: '[CALL DISCONNECTED - NETWORK DROP (CM-05)]', step: stepKey, timestamp: new Date().toLocaleTimeString() }
    ]);
  };

  const handleResume = async () => {
    if (!sessionId) return;
    setIsCompleted(false);
    try {
      const res = await apiClient.resumeInterruptedCall(token, sessionId);
      setStepKey(res.resumed_at_step);
      setAgentPrompt(res.agent_prompt_text);
      setTurns((prev) => [
        ...prev,
        { agent: res.agent_prompt_text, step: res.resumed_at_step, timestamp: new Date().toLocaleTimeString() }
      ]);
    } catch (err: any) {
      const msg = `Resumed from ${stepKey}. Let us continue.`;
      setAgentPrompt(msg);
      setTurns((prev) => [
        ...prev,
        { agent: msg, step: stepKey, timestamp: new Date().toLocaleTimeString() }
      ]);
    }
  };

  return (
    <div className="space-y-6">
      
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight flex items-center space-x-2">
          <PhoneCall className="w-6 h-6 text-indigo-600" />
          <span>Telephony Call Console & Multilingual Speech Testing (CV-01 to CV-09, LN-01 to LN-05)</span>
        </h1>
        <p className="text-xs text-slate-500 mt-1">
          Simulate inbound and outbound telephone calls with real-time state machine progression, mid-call language switching, and interruption resumption.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Controls Column */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-xs space-y-4">
          <h2 className="text-sm font-bold text-slate-900 border-b border-slate-100 pb-2">
            Call Parameters
          </h2>

          <div className="space-y-3 text-xs">
            <div>
              <label className="font-semibold text-slate-700 block mb-1">Select Patient</label>
              <select
                value={patientId}
                onChange={(e) => {
                  const selId = e.target.value;
                  setPatientId(selId);
                  const p = patients.find(item => item.id === selId);
                  if (p) setLanguage(p.lang);
                }}
                disabled={sessionId !== null && !isCompleted}
                className="w-full border border-slate-300 rounded-xl px-3 py-2 bg-white font-medium"
              >
                {patients.length > 0 ? (
                  patients.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name} ({p.diagnosis})
                    </option>
                  ))
                ) : (
                  <option value={patientId}>{patientId}</option>
                )}
              </select>
            </div>

            <div>
              <label className="font-semibold text-slate-700 block mb-1">Primary Language (LN-01)</label>
              <select
                value={language}
                onChange={(e) => setLanguage(e.target.value as any)}
                className="w-full border border-slate-300 rounded-xl px-3 py-2 bg-white font-semibold text-indigo-700"
              >
                <option value="mr">Marathi (mr)</option>
                <option value="hi">Hindi (hi)</option>
                <option value="en">English (en)</option>
              </select>
            </div>

            <div>
              <label className="font-semibold text-slate-700 block mb-1">Check-in Type</label>
              <select
                value={callType}
                onChange={(e) => setCallType(e.target.value)}
                className="w-full border border-slate-300 rounded-xl px-3 py-2 bg-white font-medium"
              >
                <option value="MORNING_CHECKIN">Morning Check-in (CI-01)</option>
                <option value="EVENING_CHECKIN">Evening Check-in (CI-01)</option>
                <option value="MEDICATION_REMINDER">Medication Reminder (MD-01)</option>
              </select>
            </div>
          </div>

          <div className="pt-2 space-y-2">
            {!sessionId || isCompleted ? (
              <button
                onClick={handleStartCall}
                className="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-bold py-2.5 rounded-xl text-xs flex items-center justify-center space-x-2 transition-colors shadow-xs"
              >
                <PhoneCall className="w-4 h-4" />
                <span>Initiate Outbound Call</span>
              </button>
            ) : (
              <div className="space-y-2">
                <button
                  onClick={handleInterrupt}
                  className="w-full bg-rose-600 hover:bg-rose-700 text-white font-bold py-2.5 rounded-xl text-xs flex items-center justify-center space-x-2 transition-colors"
                >
                  <PhoneOff className="w-4 h-4" />
                  <span>Disconnect / Drop Call (CM-05)</span>
                </button>
              </div>
            )}

            {isCompleted && turns.some(t => t.agent.includes('[CALL DISCONNECTED')) && (
              <button
                onClick={handleResume}
                className="w-full bg-amber-600 hover:bg-amber-700 text-white font-bold py-2.5 rounded-xl text-xs flex items-center justify-center space-x-2 transition-colors shadow-xs"
              >
                <RotateCcw className="w-4 h-4" />
                <span>Resume Interrupted Call (CM-05)</span>
              </button>
            )}
          </div>

          {/* Quick Scenario Buttons */}
          <div className="pt-4 border-t border-slate-100 space-y-2">
            <p className="text-[11px] font-bold text-slate-700 uppercase tracking-wider">Test BRD Scenarios:</p>
            <div className="space-y-1 text-xs">
              <button
                onClick={() => handleSendSpeech('Can we speak in Hindi? Hindi me bolo.')}
                disabled={!sessionId || isCompleted}
                className="w-full text-left p-2 rounded-lg bg-slate-50 hover:bg-indigo-50 border border-slate-200 text-slate-700 hover:text-indigo-700 text-[11px]"
              >
                • Mid-Call Language Switch (LN-03)
              </button>
              <button
                onClick={() => handleSendSpeech('Can I double my medicine dose?')}
                disabled={!sessionId || isCompleted}
                className="w-full text-left p-2 rounded-lg bg-slate-50 hover:bg-indigo-50 border border-slate-200 text-slate-700 hover:text-indigo-700 text-[11px]"
              >
                • Dosage Inquiry Guardrail (MD-07, KQ-03)
              </button>
              <button
                onClick={() => handleSendSpeech('Severe acute pain, 9 out of 10!')}
                disabled={!sessionId || isCompleted}
                className="w-full text-left p-2 rounded-lg bg-slate-50 hover:bg-indigo-50 border border-slate-200 text-slate-700 hover:text-indigo-700 text-[11px]"
              >
                • Red-Flag Emergency Script (ES-03)
              </button>
              <button
                onClick={() => handleSendSpeech('Connect me to a doctor or nurse.')}
                disabled={!sessionId || isCompleted}
                className="w-full text-left p-2 rounded-lg bg-slate-50 hover:bg-indigo-50 border border-slate-200 text-slate-700 hover:text-indigo-700 text-[11px]"
              >
                • Human Transfer Protocol (CV-07)
              </button>
            </div>
          </div>
        </div>

        {/* Live Call Transcript Stream */}
        <div className="lg:col-span-2 bg-white rounded-2xl border border-slate-200/80 shadow-xs flex flex-col h-[600px] overflow-hidden">
          
          <div className="p-4 border-b border-slate-200 bg-slate-50 flex justify-between items-center text-xs">
            <span className="font-bold text-slate-800">
              Active Session: <span className="font-mono text-indigo-700">{sessionId || 'None'}</span>
            </span>
            <span className="bg-indigo-100 text-indigo-800 px-2 py-0.5 rounded-sm font-semibold uppercase text-[10px]">
              Step: {stepKey}
            </span>
          </div>

          <div className="flex-1 p-5 overflow-y-auto space-y-4 bg-slate-100/40 custom-scrollbar">
            {turns.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-slate-400 text-center">
                <PhoneCall className="w-12 h-12 mb-2 text-slate-300 stroke-1" />
                <p className="font-semibold text-slate-600">Console Ready</p>
                <p className="text-xs">Click "Initiate Outbound Call" to place call to selected patient.</p>
              </div>
            ) : (
              turns.map((t, idx) => (
                <div key={idx} className="space-y-2">
                  {t.agent && (
                    <div className="flex items-start space-x-2.5">
                      <div className="w-7 h-7 rounded-full bg-indigo-600 text-white flex items-center justify-center shrink-0 text-xs font-bold shadow-xs">
                        AI
                      </div>
                      <div className="bg-white border border-slate-200 rounded-2xl rounded-tl-xs px-4 py-3 shadow-xs max-w-[85%] text-slate-800 text-xs leading-relaxed">
                        <div className="flex justify-between text-[10px] text-slate-400 mb-1">
                          <span className="font-semibold text-indigo-600">{t.step}</span>
                          <span>{t.timestamp}</span>
                        </div>
                        <p className="font-medium text-slate-900">{t.agent}</p>
                      </div>
                    </div>
                  )}

                  {t.patient && (
                    <div className="flex items-start justify-end space-x-2.5">
                      <div className="bg-indigo-600 text-white rounded-2xl rounded-tr-xs px-4 py-3 shadow-xs max-w-[85%] text-xs leading-relaxed">
                        <div className="flex justify-between text-[10px] text-indigo-200 mb-1">
                          <span>Patient Speech</span>
                          <span>{t.timestamp}</span>
                        </div>
                        <p>{t.patient}</p>
                      </div>
                      <div className="w-7 h-7 rounded-full bg-slate-700 text-white flex items-center justify-center shrink-0 text-xs font-bold shadow-xs">
                        PT
                      </div>
                    </div>
                  )}
                </div>
              ))
            )}
          </div>

          {/* Speech Input Bar */}
          <div className="p-4 bg-white border-t border-slate-200 flex items-center space-x-2">
            <input
              type="text"
              placeholder={sessionId && !isCompleted ? "Type speech response or click quick scenario on left..." : "Call inactive..."}
              value={userSpeech}
              disabled={!sessionId || isCompleted}
              onChange={(e) => setUserSpeech(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSendSpeech(userSpeech)}
              className="flex-1 border border-slate-300 rounded-xl px-4 py-2 text-xs focus:ring-2 focus:ring-indigo-500 disabled:bg-slate-100"
            />
            <button
              onClick={() => handleSendSpeech(userSpeech)}
              disabled={!sessionId || isCompleted || !userSpeech.trim()}
              className="bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-300 text-white text-xs font-semibold px-5 py-2 rounded-xl transition-colors shrink-0"
            >
              Send Speech
            </button>
          </div>

        </div>

      </div>

    </div>
  );
};
