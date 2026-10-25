import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { apiClient } from '../api/client';
import {
  X,
  Phone,
  PhoneOff,
  Mic,
  Volume2,
  VolumeX,
  RotateCcw,
  Sparkles,
  AlertCircle,
  CheckCircle2,
  Languages
} from 'lucide-react';

interface CallSimulatorModalProps {
  isOpen: boolean;
  onClose: () => void;
  defaultPatientId?: string;
}

export const CallSimulatorModal: React.FC<CallSimulatorModalProps> = ({
  isOpen,
  onClose,
  defaultPatientId = 'patient-demo-1'
}) => {
  const { token } = useAuth();
  const [patientId, setPatientId] = useState(defaultPatientId);
  const [callType, setCallType] = useState('MORNING_CHECKIN');
  const [language, setLanguage] = useState<'en' | 'hi' | 'mr'>('en');
  const [speechSynthesisEnabled, setSpeechSynthesisEnabled] = useState(true);

  // Call State
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [stepKey, setStepKey] = useState<string>('IDENTITY_CHECK');
  const [agentPrompt, setAgentPrompt] = useState<string>('');
  const [turnIndex, setTurnIndex] = useState(0);
  const [isCompleted, setIsCompleted] = useState(false);
  const [isCalling, setIsCalling] = useState(false);
  const [userSpeechInput, setUserSpeechInput] = useState('');
  const [turnsHistory, setTurnsHistory] = useState<Array<{ agent: string; patient?: string; step: string; timestamp: string }>>([]);
  const [alertsTriggered, setAlertsTriggered] = useState<any[]>([]);

  // Pre-configured response chips for quick evaluation
  const quickResponses: Record<string, string[]> = {
    IDENTITY_CHECK: [
      'Yes, I am Ramesh speaking.',
      'Haan, Ramesh bol raha hu.',
      'Ho, me Ramesh boltoy.',
      'No, he is sleeping right now.'
    ],
    WELLBEING: [
      'I am feeling fine today, no issues.',
      'Bahut achha lag raha hai, sudhaar hai.',
      'Thoda kamjori aani chakkar aali hoti.',
      'I have severe chest pain and breathlessness.'
    ],
    SYMPTOMS_PAIN: [
      'No pain at all today.',
      'Mild pain around 2 out of 10.',
      'Dard ho raha hai, lagbhag 5 out of 10.',
      'Severe acute pain, 9 out of 10!'
    ],
    SYMPTOMS_BREATHLESSNESS: [
      'No breathlessness, breathing normally.',
      'Mild breathlessness on walking.',
      'Short of breath, worsening since yesterday.',
      'Thoda dam lagto chalताना.'
    ],
    VITALS_SPO2: [
      'Oxygen is 98 percent.',
      'SpO2 86 percent.',
      'Chhyanau (96) ahe.',
      'I forgot to check my oxygen.'
    ],
    VITALS_BP: [
      'Blood pressure is 120 over 80.',
      'BP 145 over 95.',
      'Ek sau tees aur assi.',
      'Did not measure BP.'
    ],
    MEDICATION: [
      'Yes, I took my morning medicine with water.',
      'Haan goli le li.',
      'Missed it because I felt nauseous.',
      'Can I double my dose to recover faster?'
    ],
    LIFESTYLE_HYDRATION: [
      'Yes, drank 6 glasses of water.',
      'Paani piya hai 5 glasses.',
      'Did not drink enough water today.'
    ]
  };

  // Speak Agent Prompts using browser SpeechSynthesis
  useEffect(() => {
    if (speechSynthesisEnabled && agentPrompt && 'speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(agentPrompt);
      if (language === 'hi') utterance.lang = 'hi-IN';
      else if (language === 'mr') utterance.lang = 'mr-IN';
      else utterance.lang = 'en-US';
      utterance.rate = 0.95; // Unhurried conversational pace
      window.speechSynthesis.speak(utterance);
    }
  }, [agentPrompt, speechSynthesisEnabled, language]);

  const handleStartCall = async () => {
    setIsCalling(true);
    setTurnsHistory([]);
    setAlertsTriggered([]);
    setIsCompleted(false);

    try {
      const session = await apiClient.startCallSession(token, patientId, callType, language);
      setSessionId(session.id);
      setStepKey(session.current_step_key || 'IDENTITY_CHECK');
      setAgentPrompt(session.initial_prompt_text || 'Hello, I am calling from Apex Heart & Recovery Center.');
      setTurnsHistory([
        {
          agent: session.initial_prompt_text || 'Hello, I am calling from Apex Heart & Recovery Center.',
          step: session.current_step_key || 'IDENTITY_CHECK',
          timestamp: new Date().toLocaleTimeString()
        }
      ]);
    } catch (err: any) {
      // Fallback demo session if offline
      const mockSessionId = 'sim-call-' + Date.now();
      setSessionId(mockSessionId);
      setStepKey('IDENTITY_CHECK');
      const mockPrompt = language === 'mr'
        ? 'Namaskar Ramesh ji, me Apex Hospital madhun AI Care Companion boltoy. Tumi bolat ahat ka?'
        : language === 'hi'
        ? 'Namaste Ramesh ji, main Apex Care se bol raha hu. Kya aap Ramesh ji baat kar rahe hain?'
        : 'Hello Ramesh Patil, this is your AI Care Companion from Apex Heart Institute. Am I speaking with Ramesh?';
      setAgentPrompt(mockPrompt);
      setTurnsHistory([
        { agent: mockPrompt, step: 'IDENTITY_CHECK', timestamp: new Date().toLocaleTimeString() }
      ]);
    } finally {
      setIsCalling(false);
    }
  };

  const handleSendSpeech = async (speechText: string) => {
    if (!speechText.trim() || !sessionId) return;
    setUserSpeechInput('');

    // Optimistically log turn
    const curStep = stepKey;
    setTurnsHistory((prev) => [
      ...prev,
      { agent: '', patient: speechText, step: curStep, timestamp: new Date().toLocaleTimeString() }
    ]);

    try {
      const res = await apiClient.processCallTurn(token, sessionId, speechText);
      setStepKey(res.next_step_key);
      setAgentPrompt(res.agent_prompt_text);
      setTurnIndex(res.turn_index);
      if (res.language) setLanguage(res.language);
      if (res.is_completed) setIsCompleted(true);

      if (res.is_red_flag) {
        setAlertsTriggered((prev) => [
          ...prev,
          {
            severity: 'CRITICAL',
            title: 'RED-FLAG Emergency Escalation Triggered',
            reason: speechText
          }
        ]);
      }

      setTurnsHistory((prev) => {
        const copy = [...prev];
        const last = copy[copy.length - 1];
        if (last && !last.agent) {
          last.agent = res.agent_prompt_text;
          last.step = res.step_key;
        } else {
          copy.push({
            agent: res.agent_prompt_text,
            step: res.step_key,
            timestamp: new Date().toLocaleTimeString()
          });
        }
        return copy;
      });
    } catch (err: any) {
      // Smart offline fallback state progression
      let nextStep = 'WELLBEING';
      let nextPrompt = 'Thank you. How are you feeling overall this morning?';

      if (curStep === 'IDENTITY_CHECK') {
        nextStep = 'WELLBEING';
        nextPrompt = 'Glad to connect. How are you feeling overall since discharge? Any chest discomfort or issues?';
      } else if (curStep === 'WELLBEING') {
        nextStep = 'SYMPTOMS_PAIN';
        nextPrompt = 'On a scale from 0 to 10, where 0 is no pain and 10 is severe, how would you rate your pain right now?';
      } else if (curStep === 'SYMPTOMS_PAIN') {
        if (speechText.includes('9') || speechText.includes('severe')) {
          setAlertsTriggered((prev) => [
            ...prev,
            { severity: 'CRITICAL', title: 'Severe Acute Pain (>8/10)', reason: speechText }
          ]);
          nextPrompt = 'You are reporting severe pain. Please sit down immediately. I am alerting your cardiologist and caregiver right now.';
          setIsCompleted(true);
        } else {
          nextStep = 'SYMPTOMS_BREATHLESSNESS';
          nextPrompt = 'Have you had any shortness of breath today? Is it better, unchanged, or worse than yesterday?';
        }
      } else if (curStep === 'SYMPTOMS_BREATHLESSNESS') {
        nextStep = 'VITALS_SPO2';
        nextPrompt = 'If you have your pulse oximeter nearby, please measure your oxygen saturation SpO2 and tell me the number.';
      } else if (curStep === 'VITALS_SPO2') {
        if (speechText.includes('86') || speechText.includes('88')) {
          setAlertsTriggered((prev) => [
            ...prev,
            { severity: 'CRITICAL', title: 'Critical SpO2 Breach (<88%)', reason: speechText }
          ]);
        }
        nextStep = 'VITALS_BP';
        nextPrompt = 'I have noted your oxygen reading. Now please tell me your blood pressure reading if measured today.';
      } else if (curStep === 'VITALS_BP') {
        nextStep = 'MEDICATION';
        nextPrompt = 'Have you taken your morning dose of Atorvastatin 20mg?';
      } else if (curStep === 'MEDICATION') {
        if (speechText.toLowerCase().includes('double') || speechText.toLowerCase().includes('dose')) {
          nextPrompt = 'I cannot advise on changing medication doses. I have queued a call back from Dr. Sharma to review your prescription safely.';
        } else {
          nextStep = 'LIFESTYLE_HYDRATION';
          nextPrompt = 'Understood. Have you been drinking plenty of water today? How many glasses?';
        }
      } else {
        nextPrompt = 'Thank you for completing your daily recovery check-in. Your care team has received your updates. Rest well!';
        setIsCompleted(true);
      }

      setStepKey(nextStep);
      setAgentPrompt(nextPrompt);
      setTurnsHistory((prev) => {
        const copy = [...prev];
        const last = copy[copy.length - 1];
        if (last) last.agent = nextPrompt;
        return copy;
      });
    }
  };

  const handleInterruptCall = () => {
    setIsCompleted(true);
    setTurnsHistory((prev) => [
      ...prev,
      { agent: '[CALL DISCONNECTED / INTERRUPTED BY NETWORK]', step: stepKey, timestamp: new Date().toLocaleTimeString() }
    ]);
  };

  const handleResumeCall = async () => {
    if (!sessionId) return;
    setIsCompleted(false);
    try {
      const res = await apiClient.resumeInterruptedCall(token, sessionId);
      setStepKey(res.resumed_at_step);
      setAgentPrompt(res.agent_prompt_text);
      setTurnsHistory((prev) => [
        ...prev,
        { agent: res.agent_prompt_text, step: res.resumed_at_step, timestamp: new Date().toLocaleTimeString() }
      ]);
    } catch (err: any) {
      const resumeMsg = `Welcome back Ramesh. We were interrupted during your check-in. Let us continue from where we left off at ${stepKey}.`;
      setAgentPrompt(resumeMsg);
      setTurnsHistory((prev) => [
        ...prev,
        { agent: resumeMsg, step: stepKey, timestamp: new Date().toLocaleTimeString() }
      ]);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl max-w-3xl w-full overflow-hidden border border-slate-200 flex flex-col max-h-[90vh]">
        
        {/* Header */}
        <div className="bg-gradient-to-r from-indigo-700 to-indigo-900 text-white px-6 py-4 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-white/10 rounded-xl">
              <Phone className="w-5 h-5 text-emerald-400" />
            </div>
            <div>
              <h3 className="font-bold text-base tracking-tight">Interactive Voice Call Simulator</h3>
              <p className="text-xs text-indigo-200">
                BRD Verification · Multilingual Speech Engine (Marathi, Hindi, English) · Rules Engine
              </p>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            <button
              onClick={() => setSpeechSynthesisEnabled(!speechSynthesisEnabled)}
              title={speechSynthesisEnabled ? "Voice Speech Synthesis Enabled" : "Voice Speech Synthesis Muted"}
              className={`p-2 rounded-lg text-xs font-medium transition-colors ${
                speechSynthesisEnabled ? 'bg-indigo-600 text-white' : 'bg-white/10 text-indigo-200'
              }`}
            >
              {speechSynthesisEnabled ? <Volume2 className="w-4 h-4" /> : <VolumeX className="w-4 h-4" />}
            </button>
            <button
              onClick={onClose}
              className="p-2 hover:bg-white/10 rounded-lg text-indigo-200 hover:text-white transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Configuration Bar */}
        <div className="bg-slate-50 border-b border-slate-200 px-6 py-3 flex flex-wrap items-center justify-between gap-3 text-xs">
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-1.5">
              <span className="text-slate-500 font-medium">Patient:</span>
              <select
                value={patientId}
                onChange={(e) => setPatientId(e.target.value)}
                disabled={sessionId !== null && !isCompleted}
                className="bg-white border border-slate-300 rounded-md px-2 py-1 font-medium text-slate-800 focus:ring-1 focus:ring-indigo-500"
              >
                <option value="patient-demo-1">Ramesh Patil (Post-CABG, Marathi/English)</option>
                <option value="patient-demo-2">Sunita Deshmukh (Post-Angioplasty, Hindi)</option>
              </select>
            </div>

            <div className="flex items-center space-x-1.5">
              <Languages className="w-3.5 h-3.5 text-indigo-600" />
              <select
                value={language}
                onChange={(e) => setLanguage(e.target.value as any)}
                className="bg-white border border-slate-300 rounded-md px-2 py-1 font-medium text-slate-800"
              >
                <option value="en">English (en)</option>
                <option value="hi">Hindi (hi)</option>
                <option value="mr">Marathi (mr)</option>
              </select>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            {!sessionId || isCompleted ? (
              <button
                onClick={handleStartCall}
                disabled={isCalling}
                className="bg-emerald-600 hover:bg-emerald-700 text-white font-semibold px-4 py-1.5 rounded-lg flex items-center space-x-1.5 transition-colors"
              >
                <Phone className="w-3.5 h-3.5" />
                <span>{sessionId ? 'Start New Call' : 'Place Call'}</span>
              </button>
            ) : (
              <div className="flex items-center space-x-2">
                <button
                  onClick={handleInterruptCall}
                  className="bg-rose-600 hover:bg-rose-700 text-white font-semibold px-3 py-1.5 rounded-lg flex items-center space-x-1.5 transition-colors"
                  title="Simulate mid-call connection drop (CM-05)"
                >
                  <PhoneOff className="w-3.5 h-3.5" />
                  <span>Drop Call (CM-05)</span>
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Live Conversation Transcript Area */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4 custom-scrollbar bg-slate-100/50 min-h-[280px] max-h-[360px]">
          {turnsHistory.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center p-8 text-slate-400">
              <Phone className="w-12 h-12 text-slate-300 mb-2 stroke-1" />
              <p className="font-semibold text-slate-600">Simulated Call Inactive</p>
              <p className="text-xs max-w-sm mt-1">
                Click "Place Call" above to initiate a live voice check-in session for the selected post-discharge patient.
              </p>
            </div>
          ) : (
            turnsHistory.map((t, idx) => (
              <div key={idx} className="space-y-2">
                {/* Agent Turn */}
                {t.agent && (
                  <div className="flex items-start space-x-2.5">
                    <div className="w-7 h-7 rounded-full bg-indigo-600 text-white flex items-center justify-center shrink-0 text-xs font-bold shadow-xs">
                      AI
                    </div>
                    <div className="bg-white border border-indigo-100 rounded-2xl rounded-tl-xs px-4 py-3 shadow-xs max-w-[85%] text-slate-800 text-xs leading-relaxed">
                      <div className="flex items-center justify-between mb-1 text-[10px] text-slate-400">
                        <span className="font-semibold text-indigo-600 uppercase tracking-wider">{t.step}</span>
                        <span>{t.timestamp}</span>
                      </div>
                      <p className="text-slate-800 font-medium">{t.agent}</p>
                    </div>
                  </div>
                )}

                {/* Patient Turn */}
                {t.patient && (
                  <div className="flex items-start justify-end space-x-2.5">
                    <div className="bg-indigo-600 text-white rounded-2xl rounded-tr-xs px-4 py-3 shadow-xs max-w-[85%] text-xs leading-relaxed">
                      <div className="flex items-center justify-between mb-1 text-[10px] text-indigo-200">
                        <span>Patient Voice Input</span>
                        <span>{t.timestamp}</span>
                      </div>
                      <p className="font-normal">{t.patient}</p>
                    </div>
                    <div className="w-7 h-7 rounded-full bg-slate-700 text-white flex items-center justify-center shrink-0 text-xs font-bold shadow-xs">
                      PT
                    </div>
                  </div>
                )}
              </div>
            ))
          )}

          {/* Alert Callouts */}
          {alertsTriggered.length > 0 && (
            <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-xs space-y-1">
              <div className="flex items-center space-x-2 text-rose-700 font-bold">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>Deterministic Rules Engine Triggered:</span>
              </div>
              {alertsTriggered.map((a, i) => (
                <p key={i} className="text-rose-600 pl-6 text-[11px]">
                  • <strong>{a.title}</strong>: {a.reason}
                </p>
              ))}
            </div>
          )}

          {/* Interruption Resume Banner */}
          {isCompleted && turnsHistory.some(t => t.agent?.includes('[CALL DISCONNECTED')) && (
            <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl text-xs flex items-center justify-between">
              <div className="text-amber-800">
                <p className="font-bold">Call was interrupted at step: {stepKey}</p>
                <p className="text-[11px] text-amber-700">Per requirement CM-05, all captured vitals/symptoms were persisted.</p>
              </div>
              <button
                onClick={handleResumeCall}
                className="bg-amber-600 hover:bg-amber-700 text-white font-semibold px-3 py-1.5 rounded-lg text-xs flex items-center space-x-1"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                <span>Resume from {stepKey}</span>
              </button>
            </div>
          )}
        </div>

        {/* Quick Chips & Speech Input */}
        <div className="p-4 bg-white border-t border-slate-200 space-y-3">
          
          {/* Response Suggestions (Clinician Testing Aid) */}
          {sessionId && !isCompleted && (
            <div>
              <p className="text-[11px] font-semibold text-slate-500 mb-1.5 flex items-center space-x-1">
                <Sparkles className="w-3 h-3 text-indigo-600" />
                <span>Sample Patient Speech Options ({stepKey}):</span>
              </p>
              <div className="flex flex-wrap gap-1.5">
                {(quickResponses[stepKey] || [
                  'Yes', 'No', 'I am doing better today', 'Doctor se baat karao'
                ]).map((chip, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleSendSpeech(chip)}
                    className="text-[11px] bg-slate-100 hover:bg-indigo-50 hover:text-indigo-700 hover:border-indigo-300 border border-slate-200 text-slate-700 px-2.5 py-1 rounded-lg transition-colors"
                  >
                    "{chip}"
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Manual Input Bar */}
          <div className="flex items-center space-x-2">
            <input
              type="text"
              placeholder={sessionId && !isCompleted ? "Type simulated patient speech or use speech chips..." : "Start call above to speak..."}
              value={userSpeechInput}
              disabled={!sessionId || isCompleted}
              onChange={(e) => setUserSpeechInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSendSpeech(userSpeechInput)}
              className="flex-1 border border-slate-300 rounded-xl px-4 py-2 text-xs focus:outline-hidden focus:ring-2 focus:ring-indigo-500 disabled:bg-slate-100 disabled:text-slate-400"
            />
            <button
              onClick={() => handleSendSpeech(userSpeechInput)}
              disabled={!sessionId || isCompleted || !userSpeechInput.trim()}
              className="bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-300 text-white text-xs font-semibold px-4 py-2 rounded-xl transition-colors shrink-0"
            >
              Send Speech
            </button>
          </div>

        </div>

      </div>
    </div>
  );
};
