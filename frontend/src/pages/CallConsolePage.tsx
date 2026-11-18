import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import { apiClient } from '../api/client';
import {
  PhoneCall,
  PhoneOff,
  Volume2,
  VolumeX,
  RotateCcw,
  Languages,
  Sparkles,
  AlertCircle,
  CheckCircle2,
  Mic,
  MicOff,
  Clock,
  Activity,
  Loader2,
  Info
} from 'lucide-react';

export const CallConsolePage: React.FC = () => {
  const { token } = useAuth();
  const [patientId, setPatientId] = useState<string>('');
  const [language, setLanguage] = useState<'en' | 'hi' | 'mr'>('en');
  const [callType, setCallType] = useState('MORNING_CHECKIN');
  const [patients, setPatients] = useState<Array<{ id: string; name: string; diagnosis: string; lang: 'en' | 'hi' | 'mr' }>>([]);

  // Call status
  const [callStatus, setCallStatus] = useState<'IDLE' | 'CONNECTING' | 'AI_SPEAKING' | 'LISTENING' | 'PROCESSING' | 'COMPLETED' | 'ERROR'>('IDLE');
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [stepKey, setStepKey] = useState<string>('IDENTITY_CHECK');
  const [agentPrompt, setAgentPrompt] = useState<string>('');
  const [turns, setTurns] = useState<Array<{ agent: string; patient?: string; step: string; timestamp: string }>>([]);
  const [userSpeech, setUserSpeech] = useState('');
  const [isCompleted, setIsCompleted] = useState(false);
  const [alerts, setAlerts] = useState<any[]>([]);
  const [callDuration, setCallDuration] = useState(0);

  // Audio controls
  const [speechSynthesisEnabled, setSpeechSynthesisEnabled] = useState(true);
  const [isMuted, setIsMuted] = useState(false);
  const [interimTranscript, setInterimTranscript] = useState('');

  // Refs
  const activeUtteranceRef = useRef<SpeechSynthesisUtterance | null>(null);
  const keepAliveIntervalRef = useRef<any>(null);
  const recognitionRef = useRef<any>(null);
  const timerRef = useRef<any>(null);
  const isCompletedRef = useRef<boolean>(false);
  const isMutedRef = useRef<boolean>(false);
  const isProcessingRef = useRef<boolean>(false);
  const currentLanguageRef = useRef<'en' | 'hi' | 'mr'>('en');

  isMutedRef.current = isMuted;
  currentLanguageRef.current = language;

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

  // Call Duration Timer
  useEffect(() => {
    if (sessionId && callStatus !== 'IDLE' && callStatus !== 'COMPLETED' && callStatus !== 'CONNECTING') {
      timerRef.current = setInterval(() => {
        setCallDuration((prev) => prev + 1);
      }, 1000);
    } else {
      if (timerRef.current) clearInterval(timerRef.current);
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [sessionId, callStatus]);

  const stopListening = useCallback(() => {
    if (recognitionRef.current) {
      try {
        recognitionRef.current.abort();
      } catch (e) {
        // Ignored
      }
      recognitionRef.current = null;
    }
    setInterimTranscript('');
  }, []);

  const stopSpeechSynthesis = useCallback(() => {
    if ('speechSynthesis' in window) {
      try {
        window.speechSynthesis.cancel();
      } catch (e) {
        // Ignored
      }
    }
    if (keepAliveIntervalRef.current) clearInterval(keepAliveIntervalRef.current);
    activeUtteranceRef.current = null;
  }, []);

  const startListening = useCallback(() => {
    if (isCompletedRef.current || isMutedRef.current) return;
    const SpeechRec = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRec) {
      setCallStatus('LISTENING');
      return;
    }

    stopListening();

    try {
      const recognition = new SpeechRec();
      recognition.continuous = false;
      recognition.interimResults = true;
      recognition.lang = currentLanguageRef.current === 'hi' ? 'hi-IN' : currentLanguageRef.current === 'mr' ? 'mr-IN' : 'en-US';

      recognition.onstart = () => {
        setCallStatus('LISTENING');
        setInterimTranscript('');
      };

      recognition.onresult = (event: any) => {
        let currentInterim = '';
        for (let i = event.resultIndex; i < event.results.length; ++i) {
          const transcript = event.results[i][0].transcript;
          if (event.results[i].isFinal) {
            setInterimTranscript('');
            stopListening();
            handleSendSpeech(transcript);
            return;
          } else {
            currentInterim += transcript;
          }
        }
        setInterimTranscript(currentInterim);
      };

      recognition.onerror = (event: any) => {
        console.warn('Speech recognition error in call console:', event.error);
        setCallStatus('LISTENING');
      };

      recognitionRef.current = recognition;
      recognition.start();
    } catch (err) {
      console.warn('Failed to start speech recognition:', err);
      setCallStatus('LISTENING');
    }
  }, [stopListening]);

  const speakAgentPrompt = useCallback((textToSpeak: string, langCode: 'en' | 'hi' | 'mr') => {
    if (!speechSynthesisEnabled || !('speechSynthesis' in window) || !textToSpeak) {
      setTimeout(() => {
        if (!isCompletedRef.current) {
          setCallStatus('LISTENING');
          if (!isMutedRef.current) startListening();
        }
      }, 500);
      return;
    }

    stopListening();
    stopSpeechSynthesis();

    const cleanText = textToSpeak.replace(/\[.*?\]/g, '').replace(/[*_#]/g, '').trim();
    if (!cleanText) {
      setCallStatus('LISTENING');
      if (!isMutedRef.current) startListening();
      return;
    }

    try {
      const utterance = new SpeechSynthesisUtterance(cleanText);
      activeUtteranceRef.current = utterance;

      utterance.lang = langCode === 'hi' ? 'hi-IN' : langCode === 'mr' ? 'mr-IN' : 'en-US';
      utterance.rate = 0.95;
      utterance.pitch = 1.0;

      utterance.onstart = () => {
        setCallStatus('AI_SPEAKING');
        if (keepAliveIntervalRef.current) clearInterval(keepAliveIntervalRef.current);
        keepAliveIntervalRef.current = setInterval(() => {
          if ('speechSynthesis' in window && window.speechSynthesis.speaking) {
            window.speechSynthesis.pause();
            window.speechSynthesis.resume();
          }
        }, 5000);
      };

      utterance.onend = () => {
        if (keepAliveIntervalRef.current) clearInterval(keepAliveIntervalRef.current);
        activeUtteranceRef.current = null;
        if (!isCompletedRef.current) {
          setCallStatus('LISTENING');
          setTimeout(() => {
            if (!isCompletedRef.current && !isMutedRef.current) {
              startListening();
            }
          }, 350);
        }
      };

      utterance.onerror = (e) => {
        console.warn('TTS error:', e);
        if (keepAliveIntervalRef.current) clearInterval(keepAliveIntervalRef.current);
        activeUtteranceRef.current = null;
        if (!isCompletedRef.current) {
          setCallStatus('LISTENING');
          if (!isMutedRef.current) startListening();
        }
      };

      window.speechSynthesis.speak(utterance);
    } catch (err) {
      console.warn('TTS invocation error:', err);
      setCallStatus('LISTENING');
      if (!isMutedRef.current) startListening();
    }
  }, [speechSynthesisEnabled, startListening, stopListening, stopSpeechSynthesis]);

  const handleStartCall = async () => {
    isCompletedRef.current = false;
    isProcessingRef.current = false;
    setCallStatus('CONNECTING');
    setTurns([]);
    setAlerts([]);
    setIsCompleted(false);
    setCallDuration(0);

    try {
      const session = await apiClient.startCallSession(token, patientId, callType, language);
      setSessionId(session.id);
      const initialStep = session.current_step_key || 'IDENTITY_CHECK';
      setStepKey(initialStep);

      setTimeout(() => {
        const prompt = session.initial_prompt_text || 'Hello, I am calling from Apex Heart & Recovery Center.';
        setAgentPrompt(prompt);
        setTurns([
          { agent: prompt, step: initialStep, timestamp: new Date().toLocaleTimeString() }
        ]);
        speakAgentPrompt(prompt, language);
      }, 1200);
    } catch (err: any) {
      setCallStatus('ERROR');
      alert(`Error starting call session: ${err.message}`);
    }
  };

  const handleSendSpeech = async (speech: string) => {
    const trimmed = speech.trim();
    if (!trimmed || !sessionId || isProcessingRef.current) return;

    isProcessingRef.current = true;
    stopListening();
    setCallStatus('PROCESSING');
    setUserSpeech('');

    const curStep = stepKey;
    setTurns((prev) => [
      ...prev,
      { agent: '', patient: trimmed, step: curStep, timestamp: new Date().toLocaleTimeString() }
    ]);

    try {
      const res = await apiClient.processCallTurn(token, sessionId, trimmed);
      const nextStep = res.next_step_key || res.step_key;
      setStepKey(nextStep);
      setAgentPrompt(res.agent_prompt_text);

      const turnLang = (res.language || language) as 'en' | 'hi' | 'mr';
      if (res.language) setLanguage(turnLang);

      if (res.is_completed) {
        setIsCompleted(true);
        isCompletedRef.current = true;
        setCallStatus('COMPLETED');
      }

      if (res.is_red_flag) {
        setAlerts((prev) => [...prev, { title: 'Emergency Alert Triggered', text: trimmed }]);
      }

      setTurns((prev) => {
        const copy = [...prev];
        const last = copy[copy.length - 1];
        if (last && !last.agent) {
          last.agent = res.agent_prompt_text;
          last.step = curStep;
        } else {
          copy.push({
            agent: res.agent_prompt_text,
            step: nextStep,
            timestamp: new Date().toLocaleTimeString()
          });
        }
        return copy;
      });

      isProcessingRef.current = false;
      speakAgentPrompt(res.agent_prompt_text, turnLang);
    } catch (err: any) {
      isProcessingRef.current = false;
      alert(`Error processing speech turn: ${err.message}`);
      setCallStatus('LISTENING');
      if (!isMutedRef.current) startListening();
    }
  };

  const handleInterrupt = () => {
    setIsCompleted(true);
    isCompletedRef.current = true;
    stopSpeechSynthesis();
    stopListening();
    setCallStatus('COMPLETED');
    setTurns((prev) => [
      ...prev,
      { agent: '[CALL DISCONNECTED - NETWORK DROP (CM-05)]', step: stepKey, timestamp: new Date().toLocaleTimeString() }
    ]);
  };

  const handleResume = async () => {
    if (!sessionId) return;
    setIsCompleted(false);
    isCompletedRef.current = false;
    try {
      const res = await apiClient.resumeInterruptedCall(token, sessionId);
      setStepKey(res.resumed_at_step);
      setAgentPrompt(res.agent_prompt_text);
      setTurns((prev) => [
        ...prev,
        { agent: res.agent_prompt_text, step: res.resumed_at_step, timestamp: new Date().toLocaleTimeString() }
      ]);
      speakAgentPrompt(res.agent_prompt_text, language);
    } catch (err: any) {
      const msg = `Resumed from ${stepKey}. Let us continue.`;
      setAgentPrompt(msg);
      setTurns((prev) => [
        ...prev,
        { agent: msg, step: stepKey, timestamp: new Date().toLocaleTimeString() }
      ]);
      speakAgentPrompt(msg, language);
    }
  };

  const activePatientName = patients.find(p => p.id === patientId)?.name || (patients.length > 0 ? patients[0].name : 'Patient');

  const formatTimer = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
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
          Simulate inbound and outbound telephone calls with real-time state machine progression, Web Speech recognition, mid-call language switching, and interruption resumption.
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
                <option value="en">English (en-IN)</option>
                <option value="hi">Hindi (hi-IN)</option>
                <option value="mr">Marathi (mr-IN)</option>
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
                <div className="grid grid-cols-2 gap-2">
                  <button
                    onClick={() => {
                      const next = !isMuted;
                      setIsMuted(next);
                      if (next) stopListening();
                      else if (callStatus === 'LISTENING') startListening();
                    }}
                    className={`py-2 px-3 rounded-xl text-xs font-semibold flex items-center justify-center space-x-1 border ${
                      isMuted ? 'bg-amber-100 border-amber-300 text-amber-800' : 'bg-slate-100 border-slate-200 text-slate-700'
                    }`}
                  >
                    {isMuted ? <MicOff className="w-3.5 h-3.5 text-amber-700" /> : <Mic className="w-3.5 h-3.5 text-emerald-600" />}
                    <span>{isMuted ? 'Muted' : 'Mute Mic'}</span>
                  </button>
                  <button
                    onClick={() => setSpeechSynthesisEnabled(!speechSynthesisEnabled)}
                    className="py-2 px-3 rounded-xl text-xs font-semibold flex items-center justify-center space-x-1 border bg-slate-100 border-slate-200 text-slate-700"
                  >
                    {speechSynthesisEnabled ? <Volume2 className="w-3.5 h-3.5" /> : <VolumeX className="w-3.5 h-3.5" />}
                    <span>{speechSynthesisEnabled ? 'Audio On' : 'Muted'}</span>
                  </button>
                </div>
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
                onClick={() => handleSendSpeech('Can I double my medicine dose to get better faster?')}
                disabled={!sessionId || isCompleted}
                className="w-full text-left p-2 rounded-lg bg-slate-50 hover:bg-indigo-50 border border-slate-200 text-slate-700 hover:text-indigo-700 text-[11px]"
              >
                • Dosage Advice Refusal (MD-07 / KQ-03)
              </button>
              <button
                onClick={() => handleSendSpeech('Please connect me to a human doctor right now.')}
                disabled={!sessionId || isCompleted}
                className="w-full text-left p-2 rounded-lg bg-slate-50 hover:bg-indigo-50 border border-slate-200 text-slate-700 hover:text-indigo-700 text-[11px]"
              >
                • Human Transfer Callback (CV-07)
              </button>
            </div>
          </div>
        </div>

        {/* Live Conversation Transcript Column */}
        <div className="lg:col-span-2 bg-white rounded-2xl border border-slate-200/80 shadow-xs flex flex-col h-[650px] overflow-hidden">
          {/* Transcript Header with Status */}
          <div className="p-4 border-b border-slate-100 bg-slate-50/50 flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <span className={`w-2.5 h-2.5 rounded-full ${
                callStatus === 'AI_SPEAKING' ? 'bg-indigo-600 animate-pulse' :
                callStatus === 'LISTENING' ? 'bg-emerald-500 animate-ping' :
                callStatus === 'PROCESSING' ? 'bg-amber-500 animate-spin' :
                sessionId && !isCompleted ? 'bg-emerald-500' : 'bg-slate-300'
              }`} />
              <span className="text-xs font-bold text-slate-800">
                {callStatus === 'AI_SPEAKING' ? 'AI Care Companion Speaking' :
                 callStatus === 'LISTENING' ? 'Microphone Active — Listening to Patient' :
                 callStatus === 'PROCESSING' ? 'Processing Clinical Turn' :
                 callStatus === 'CONNECTING' ? 'Connecting Call...' :
                 sessionId && !isCompleted ? 'Connected Call Session' : 'No Active Call'}
              </span>
            </div>
            <div className="flex items-center space-x-2 text-xs font-mono text-slate-500">
              <Clock className="w-3.5 h-3.5 text-slate-400" />
              <span>{formatTimer(callDuration)}</span>
            </div>
          </div>

          {/* Interim transcript bar */}
          {callStatus === 'LISTENING' && interimTranscript && (
            <div className="bg-emerald-50 border-b border-emerald-100 px-4 py-2 text-xs text-emerald-900 flex items-center gap-2">
              <Mic className="w-3.5 h-3.5 text-emerald-600 animate-pulse" />
              <span>Hearing: <em>"{interimTranscript}"</em></span>
            </div>
          )}

          {/* Turns Log Area */}
          <div className="flex-1 overflow-y-auto p-4 space-y-3 custom-scrollbar bg-slate-50/30">
            {turns.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-center p-8 text-slate-400">
                <PhoneCall className="w-10 h-10 text-slate-300 mb-2 stroke-1" />
                <p className="font-semibold text-slate-600 text-sm">Interactive Voice Dialogue Console</p>
                <p className="text-xs max-w-sm mt-1 text-slate-500">
                  Select a patient and initiate an outbound recovery call to test turn-taking speech recognition.
                </p>
              </div>
            ) : (
              turns.map((t, idx) => (
                <div key={idx} className="space-y-1">
                  {t.agent && (
                    <div className="flex items-start space-x-2">
                      <div className="w-6 h-6 rounded-full bg-indigo-600 text-white flex items-center justify-center shrink-0 text-[10px] font-bold">
                        AI
                      </div>
                      <div className="bg-white border border-indigo-100 rounded-xl p-3 text-xs max-w-[85%] shadow-2xs">
                        <div className="flex items-center justify-between text-[10px] text-slate-400 mb-1">
                          <span className="font-semibold text-indigo-600">{t.step}</span>
                          <span>{t.timestamp}</span>
                        </div>
                        <p className="text-slate-800">{t.agent}</p>
                      </div>
                    </div>
                  )}

                  {t.patient && (
                    <div className="flex items-start justify-end space-x-2">
                      <div className="bg-indigo-600 text-white rounded-xl p-3 text-xs max-w-[85%] shadow-2xs">
                        <div className="flex items-center justify-between text-[10px] text-indigo-200 mb-1">
                          <span>Patient Speech</span>
                          <span>{t.timestamp}</span>
                        </div>
                        <p>{t.patient}</p>
                      </div>
                      <div className="w-6 h-6 rounded-full bg-slate-700 text-white flex items-center justify-center shrink-0 text-[10px] font-bold">
                        PT
                      </div>
                    </div>
                  )}
                </div>
              ))
            )}

            {alerts.length > 0 && (
              <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-xs space-y-1">
                <div className="flex items-center space-x-1.5 text-rose-700 font-bold">
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  <span>Red-Flag Safety Escalation Triggered</span>
                </div>
                {alerts.map((a, i) => (
                  <p key={i} className="text-rose-600 pl-5 text-[11px]">
                    • {a.title}: {a.text}
                  </p>
                ))}
              </div>
            )}
          </div>

          {/* Speech Input Box */}
          <div className="p-4 bg-white border-t border-slate-100 flex items-center space-x-2">
            <input
              type="text"
              placeholder={
                callStatus === 'AI_SPEAKING' ? "AI speaking... Please wait" :
                callStatus === 'LISTENING' ? "Listening to microphone... Speak or type response" :
                callStatus === 'PROCESSING' ? "Processing..." :
                sessionId && !isCompleted ? "Type speech response..." : "Initiate call to begin speech..."
              }
              value={userSpeech}
              onChange={(e) => setUserSpeech(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSendSpeech(userSpeech)}
              disabled={!sessionId || isCompleted || callStatus === 'PROCESSING'}
              className="flex-1 border border-slate-300 rounded-xl px-4 py-2 text-xs focus:outline-hidden focus:ring-2 focus:ring-indigo-500 disabled:bg-slate-50"
            />
            <button
              onClick={() => handleSendSpeech(userSpeech)}
              disabled={!sessionId || isCompleted || !userSpeech.trim() || callStatus === 'PROCESSING'}
              className="bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-300 text-white font-semibold text-xs px-4 py-2 rounded-xl transition-colors"
            >
              Send Speech
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
