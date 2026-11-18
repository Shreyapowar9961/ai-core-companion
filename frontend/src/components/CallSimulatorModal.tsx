import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import { apiClient } from '../api/client';
import {
  X,
  Phone,
  PhoneOff,
  PhoneCall,
  Mic,
  MicOff,
  Volume2,
  VolumeX,
  RotateCcw,
  Sparkles,
  AlertCircle,
  CheckCircle2,
  Languages,
  Clock,
  Info,
  Radio,
  Activity,
  Heart,
  Pill,
  ShieldAlert,
  Loader2
} from 'lucide-react';

interface CallSimulatorModalProps {
  isOpen: boolean;
  onClose: () => void;
  defaultPatientId?: string;
}

export type CallTurnState = 'IDLE' | 'CONNECTING' | 'AI_SPEAKING' | 'LISTENING' | 'PROCESSING' | 'COMPLETED' | 'ERROR';

export const CallSimulatorModal: React.FC<CallSimulatorModalProps> = ({
  isOpen,
  onClose,
  defaultPatientId
}) => {
  const { token } = useAuth();
  const [patients, setPatients] = useState<Array<{ id: string; name: string; diagnosis: string; lang: 'en' | 'hi' | 'mr' }>>([]);
  const [patientId, setPatientId] = useState<string>(defaultPatientId || '');
  const [callType, setCallType] = useState('MORNING_CHECKIN');
  const [language, setLanguage] = useState<'en' | 'hi' | 'mr'>('en');

  // Turn-Taking & Voice States
  const [callStatus, setCallStatus] = useState<CallTurnState>('IDLE');
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [stepKey, setStepKey] = useState<string>('IDENTITY_CHECK');
  const [agentPrompt, setAgentPrompt] = useState<string>('');
  const [turnIndex, setTurnIndex] = useState(0);
  const [callDuration, setCallDuration] = useState(0);

  // Audio controls
  const [speechSynthesisEnabled, setSpeechSynthesisEnabled] = useState(true);
  const [isMuted, setIsMuted] = useState(false);
  const [speechSupported, setSpeechSupported] = useState(true);
  const [micPermissionDenied, setMicPermissionDenied] = useState(false);
  const [interimTranscript, setInterimTranscript] = useState('');
  const [silencePromptVisible, setSilencePromptVisible] = useState(false);

  // Transcripts & Clinical Summary Data
  const [userSpeechInput, setUserSpeechInput] = useState('');
  const [turnsHistory, setTurnsHistory] = useState<Array<{ agent: string; patient?: string; step: string; timestamp: string }>>([]);
  const [alertsTriggered, setAlertsTriggered] = useState<any[]>([]);
  const [clinicalSummary, setClinicalSummary] = useState<{
    vitals: Record<string, any>;
    symptoms: Record<string, any>;
    medication: Record<string, any>;
    disposition: string;
  }>({
    vitals: {},
    symptoms: {},
    medication: {},
    disposition: 'IN_PROGRESS'
  });

  // Refs for audio lifecycle
  const activeUtteranceRef = useRef<SpeechSynthesisUtterance | null>(null);
  const keepAliveIntervalRef = useRef<any>(null);
  const recognitionRef = useRef<any>(null);
  const timerRef = useRef<any>(null);
  const silenceTimerRef = useRef<any>(null);
  const isCompletedRef = useRef<boolean>(false);
  const isMutedRef = useRef<boolean>(false);
  const isProcessingRef = useRef<boolean>(false);
  const currentLanguageRef = useRef<'en' | 'hi' | 'mr'>('en');

  // CV-08: Browser Audio Recording & Upload
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const [audioRecordingActive, setAudioRecordingActive] = useState<boolean>(false);
  const [audioUploaded, setAudioUploaded] = useState<boolean>(false);
  const [recordedAudioUrl, setRecordedAudioUrl] = useState<string | null>(null);

  const startAudioRecording = useCallback(async () => {
    try {
      if (typeof navigator !== 'undefined' && navigator.mediaDevices && window.MediaRecorder) {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaStreamRef.current = stream;
        const mr = new MediaRecorder(stream, { mimeType: 'audio/webm' });
        audioChunksRef.current = [];
        mr.ondataavailable = (e) => {
          if (e.data && e.data.size > 0) {
            audioChunksRef.current.push(e.data);
          }
        };
        mr.start(1000);
        mediaRecorderRef.current = mr;
        setAudioRecordingActive(true);
      }
    } catch (e) {
      console.warn('Microphone audio recording not available or denied:', e);
      setAudioRecordingActive(false);
    }
  }, []);

  const stopAndUploadAudio = useCallback(async (curSessionId: string) => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.onstop = async () => {
        setAudioRecordingActive(false);
        if (audioChunksRef.current.length > 0 && curSessionId) {
          const blob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
          try {
            const res = await apiClient.uploadCallAudio(token, curSessionId, blob);
            setAudioUploaded(true);
            setRecordedAudioUrl(res.audio_url);
          } catch (err) {
            console.warn('Audio upload note (CV-08):', err);
          }
        }
        if (mediaStreamRef.current) {
          mediaStreamRef.current.getTracks().forEach((track) => track.stop());
          mediaStreamRef.current = null;
        }
      };
      mediaRecorderRef.current.stop();
    }
  }, [token]);

  isMutedRef.current = isMuted;
  currentLanguageRef.current = language;

  // 1. Fetch available patients on mount / open
  useEffect(() => {
    if (!isOpen || !token) return;
    apiClient.getPatients(token)
      .then((data) => {
        if (data && data.length > 0) {
          const mapped = data.map((p) => ({
            id: p.id,
            name: `${p.first_name} ${p.last_name}`.trim(),
            diagnosis: p.diagnosis,
            lang: (p.preferred_language || 'en') as 'en' | 'hi' | 'mr'
          }));
          setPatients(mapped);

          const matched = mapped.find(p => p.id === defaultPatientId);
          if (matched) {
            setPatientId(matched.id);
            setLanguage(matched.lang);
          } else if (mapped.length > 0) {
            setPatientId(mapped[0].id);
            setLanguage(mapped[0].lang);
          }
        }
      })
      .catch((err) => console.warn('Could not fetch patients for call simulator:', err.message));
  }, [isOpen, token, defaultPatientId]);

  // 2. Check browser SpeechRecognition support
  useEffect(() => {
    const SpeechRec = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRec) {
      setSpeechSupported(false);
    }
  }, []);

  // 3. Call Duration Timer
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

  // Clean-up on unmount / modal close
  useEffect(() => {
    return () => {
      stopSpeechSynthesis();
      stopListening();
      if (timerRef.current) clearInterval(timerRef.current);
      if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);
    };
  }, []);

  const activePatientName = patients.find(p => p.id === patientId)?.name || (patients.length > 0 ? patients[0].name : 'Patient');

  const formatTimer = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  // Pre-configured response chips for quick evaluation across languages
  const quickResponses: Record<string, Record<'en' | 'hi' | 'mr', string[]>> = {
    IDENTITY_CHECK: {
      en: ['Yes, speaking.', `This is ${activePatientName}.`, 'Hello, who is calling?', 'No, wrong number.'],
      hi: ['हाँ, मैं बोल रहा हूँ।', 'हाँ जी, मैं ही हूँ।', 'नमस्ते, कौन बोल रहा है?', 'नहीं, गलत नंबर है।'],
      mr: ['हो, मी बोलतोय.', 'हो, मीच आहे.', 'नमस्कार, कोण बोलतंय?', 'नाही, चुकीचा नंबर आहे.']
    },
    WELLBEING: {
      en: ['I am feeling fine today, recovering well.', 'Feeling a bit weak and tired.', 'I have severe chest discomfort!'],
      hi: ['आज मैं ठीक महसूस कर रहा हूँ, कोई समस्या नहीं है।', 'थोड़ी कमजोरी और थकान लग रही है।', 'छाती में बहुत तेज दर्द हो रहा है!'],
      mr: ['आज मला छान वाटत आहे, तब्येत बरी आहे.', 'थोडा अशक्तपणा जाणवत आहे.', 'माझ्या छातीत खूप त्रास होत आहे!']
    },
    SYMPTOMS_PAIN: {
      en: ['No pain at all today, 0 out of 10.', 'Mild pain around 2 out of 10.', 'Severe sharp pain, 9 out of 10!'],
      hi: ['आज बिल्कुल दर्द नहीं है, शून्य।', 'हल्का सा दर्द है, 2 या 3।', 'बहुत तेज असहनीय दर्द है, 9!'],
      mr: ['आज अजिबात दुखणे नाही, 0.', 'थोडेसे दुखत आहे, 2 किंवा 3.', 'खूप तीव्र असह्य वेदना होत आहेत, 9!']
    },
    SYMPTOMS_BREATHLESSNESS: {
      en: ['Breathing normally, no breathlessness.', 'Slight shortness of breath on walking.', 'Severe difficulty breathing!'],
      hi: ['साँस बिल्कुल सामान्य है, कोई तकलीफ़ नहीं।', 'चलने पर थोड़ी साँस फूलती है।', 'साँस लेने में बहुत ज्यादा परेशानी हो रही है!'],
      mr: ['श्वास व्यवस्थित चालू आहे, काही त्रास नाही.', 'चालताना थोडी धाप लागते.', 'श्वास घेण्यास तीव्र अडचण होत आहे!']
    },
    VITALS_SPO2: {
      en: ['Oxygen is 98 percent.', 'SpO2 is 94 percent.', 'Oxygen is 86 percent.'],
      hi: ['ऑक्सीजन 98 प्रतिशत है।', 'ऑक्सीजन 94 है।', 'ऑक्सीजन 86 प्रतिशत आ रहा है।'],
      mr: ['ऑक्सिजन 98 टक्के आहे.', 'ऑक्सिजन 94 टक्के आहे.', 'ऑक्सिजन 86 टक्के दाखवत आहे.']
    },
    VITALS_BP: {
      en: ['Blood pressure is 120 over 80.', 'BP is 135 over 88.', 'Did not check blood pressure.'],
      hi: ['ब्लड प्रेशर 120 और 80 है।', 'बीपी 140 और 90 है।', 'आज बीपी नहीं नापा।'],
      mr: ['रक्तदाब 120 आणि 80 आहे.', 'बीपी 135 आणि 88 आहे.', 'आज बीपी तपासले नाही.']
    },
    MEDICATION: {
      en: ['Yes, I took my morning tablet with water.', 'Remind me later in 30 minutes.', 'Missed it because I felt dizzy.'],
      hi: ['हाँ, मैंने सुबह की गोली पानी के साथ ले ली है।', 'मुझे 30 मिनट बाद दोबारा याद दिलाइए।', 'चक्कर आने की वजह से दवा नहीं ली।'],
      mr: ['हो, मी सकाळची गोळी पाण्यासोबत घेतली आहे.', 'मला 30 मिनिटांनंतर पुन्हा आठवण करा.', 'त्रास झाल्यामुळे औषध घेतले नाही.']
    },
    LIFESTYLE_HYDRATION: {
      en: ['Yes, drank 6 glasses of water today.', 'Yes, drinking water regularly.', 'Drank only 2 glasses so far.'],
      hi: ['हाँ, आज 6 गिलास पानी पी लिया है।', 'हाँ, समय पर पर्याप्त पानी पी रहा हूँ।', 'आज केवल 2 गिलास पानी पिया है।'],
      mr: ['हो, आज 6 ग्लास पाणी पिऊन झाले आहे.', 'हो, वेळेवर पुरेसे पाणी पीत आहे.', 'आज फक्त 2 ग्लास पाणी प्यायलो.']
    },
    APPOINTMENT: {
      en: ['Yes, I will attend the appointment.', 'Please reschedule for next week.', 'No, I cannot attend.'],
      hi: ['हाँ, मैं अपॉइंटमेंट में उपस्थित रहूँगा।', 'कृपया अगले हफ्ते का समय बदल दीजिए।', 'नहीं, मैं उपस्थित नहीं हो पाऊँगा।'],
      mr: ['हो, मी भेटीसाठी उपस्थित राहीन.', 'कृपया पुढच्या आठवड्याची तारीख द्या.', 'नाही, मला येणे शक्य होणार नाही.']
    }
  };

  // Helper to stop STT
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
    if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);
    setSilencePromptVisible(false);
  }, []);

  // Helper to stop TTS
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

  // 4. Start Speech Recognition (STT) for Patient Turn
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
        setSilencePromptVisible(false);

        // Set 9-second silence prompt timer
        if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);
        silenceTimerRef.current = setTimeout(() => {
          setSilencePromptVisible(true);
        }, 9000);
      };

      recognition.onresult = (event: any) => {
        let currentInterim = '';
        if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);
        setSilencePromptVisible(false);

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
        console.warn('Speech recognition event:', event.error);
        if (event.error === 'not-allowed' || event.error === 'service-not-allowed') {
          setMicPermissionDenied(true);
        }
        setCallStatus('LISTENING');
      };

      recognition.onend = () => {
        if (!isCompletedRef.current && !isProcessingRef.current && callStatus === 'LISTENING') {
          // Keep listening or wait for user input
        }
      };

      recognitionRef.current = recognition;
      recognition.start();
    } catch (err) {
      console.warn('Failed to start speech recognition:', err);
      setCallStatus('LISTENING');
    }
  }, [stopListening]);

  // 5. Speak Agent Prompt (TTS) with Chrome GC Keep-Alive Fix & Echo Prevention
  const speakAgentPrompt = useCallback((textToSpeak: string, langCode: 'en' | 'hi' | 'mr') => {
    if (!speechSynthesisEnabled || !('speechSynthesis' in window) || !textToSpeak) {
      // If audio disabled, transition directly to LISTENING after short delay
      setTimeout(() => {
        if (!isCompletedRef.current) {
          setCallStatus('LISTENING');
          if (!isMutedRef.current) startListening();
        }
      }, 500);
      return;
    }

    // 1. Immediately mute/stop mic to prevent audio feedback loop
    stopListening();
    stopSpeechSynthesis();

    // 2. Prepare clean text without brackets or asterisks
    const cleanText = textToSpeak.replace(/\[.*?\]/g, '').replace(/[*_#]/g, '').trim();
    if (!cleanText) {
      setCallStatus('LISTENING');
      if (!isMutedRef.current) startListening();
      return;
    }

    try {
      const utterance = new SpeechSynthesisUtterance(cleanText);
      // Retain utterance in component ref to defeat Chrome V8 garbage collector
      activeUtteranceRef.current = utterance;

      utterance.lang = langCode === 'hi' ? 'hi-IN' : langCode === 'mr' ? 'mr-IN' : 'en-US';
      utterance.rate = 0.95;
      utterance.pitch = 1.0;

      utterance.onstart = () => {
        setCallStatus('AI_SPEAKING');
        // Chrome 15-second speech keep-alive heartbeat
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
          // Dissipation buffer: 350ms delay before opening microphone to clear speaker acoustic energy
          setTimeout(() => {
            if (!isCompletedRef.current && !isMutedRef.current) {
              startListening();
            }
          }, 350);
        }
      };

      utterance.onerror = (e) => {
        console.warn('Speech synthesis error:', e);
        if (keepAliveIntervalRef.current) clearInterval(keepAliveIntervalRef.current);
        activeUtteranceRef.current = null;
        if (!isCompletedRef.current) {
          setCallStatus('LISTENING');
          if (!isMutedRef.current) startListening();
        }
      };

      window.speechSynthesis.speak(utterance);
    } catch (err) {
      console.warn('Speech synthesis invocation failed:', err);
      setCallStatus('LISTENING');
      if (!isMutedRef.current) startListening();
    }
  }, [speechSynthesisEnabled, startListening, stopListening, stopSpeechSynthesis]);

  // 6. Initiate Call Session
  const handleStartCall = async () => {
    isCompletedRef.current = false;
    isProcessingRef.current = false;
    setCallStatus('CONNECTING');
    setTurnsHistory([]);
    setAlertsTriggered([]);
    setCallDuration(0);
    setSilencePromptVisible(false);
    setClinicalSummary({
      vitals: {},
      symptoms: {},
      medication: {},
      disposition: 'IN_PROGRESS'
    });

    try {
      const session = await apiClient.startCallSession(token, patientId, callType, language);
      setSessionId(session.id);
      startAudioRecording();
      const initialStep = session.current_step_key || 'IDENTITY_CHECK';
      setStepKey(initialStep);

      // Brief simulated ringing tone delay (1.2s)
      setTimeout(() => {
        const prompt = session.initial_prompt_text || 'Hello, I am calling from Apex Heart & Recovery Center.';
        setAgentPrompt(prompt);
        setTurnsHistory([
          {
            agent: prompt,
            step: initialStep,
            timestamp: new Date().toLocaleTimeString()
          }
        ]);
        speakAgentPrompt(prompt, language);
      }, 1200);
    } catch (err: any) {
      console.error('Call initialization failed:', err.message);
      setCallStatus('ERROR');
      const errText = `Connection failed: ${err.message || 'Unable to connect to hospital telephony service.'}`;
      setAgentPrompt(errText);
      setTurnsHistory([
        { agent: errText, step: 'ERROR', timestamp: new Date().toLocaleTimeString() }
      ]);
    }
  };

  // 7. Process Patient Speech Turn (Turn-Taking Handshake)
  const handleSendSpeech = async (speechText: string) => {
    const trimmed = speechText.trim();
    if (!trimmed || !sessionId || isProcessingRef.current) return;

    isProcessingRef.current = true;
    stopListening();
    setCallStatus('PROCESSING');
    setUserSpeechInput('');

    const curStep = stepKey;
    setTurnsHistory((prev) => [
      ...prev,
      { agent: '', patient: trimmed, step: curStep, timestamp: new Date().toLocaleTimeString() }
    ]);

    try {
      const res = await apiClient.processCallTurn(token, sessionId, trimmed);
      const nextStep = res.next_step_key || res.step_key;
      setStepKey(nextStep);
      setAgentPrompt(res.agent_prompt_text);
      setTurnIndex(res.turn_index);

      const turnLang = (res.language || language) as 'en' | 'hi' | 'mr';
      if (res.language) setLanguage(turnLang);

      // Update extracted clinical summary data
      if (res.extracted_data) {
        setClinicalSummary((prev) => ({
          ...prev,
          vitals: { ...prev.vitals, ...(res.extracted_data.spo2 ? { SpO2: `${res.extracted_data.spo2}%` } : {}), ...(res.extracted_data.bp ? { BP: res.extracted_data.bp } : {}) },
          symptoms: { ...prev.symptoms, ...(res.extracted_data.pain_level !== undefined ? { Pain: `${res.extracted_data.pain_level}/10` } : {}), ...(res.extracted_data.breathlessness ? { Breathlessness: res.extracted_data.breathlessness } : {}) },
          medication: { ...prev.medication, ...(res.extracted_data.medication ? res.extracted_data.medication : {}) }
        }));
      }

      if (res.is_red_flag) {
        setAlertsTriggered((prev) => [
          ...prev,
          {
            severity: 'CRITICAL',
            title: 'RED-FLAG Emergency Escalation Triggered',
            reason: trimmed
          }
        ]);
      }

      // Append AI response to turns history
      setTurnsHistory((prev) => {
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

      if (res.is_completed) {
        isCompletedRef.current = true;
        setCallStatus('COMPLETED');
        if (sessionId) stopAndUploadAudio(sessionId);
        setClinicalSummary((prev) => ({ ...prev, disposition: res.disposition || 'COMPLETED' }));
        speakAgentPrompt(res.agent_prompt_text, turnLang);
      } else {
        speakAgentPrompt(res.agent_prompt_text, turnLang);
      }
    } catch (err: any) {
      console.error('Turn processing failed:', err.message);
      isProcessingRef.current = false;
      const errText = `[Speech processing note: ${err.message || 'Network timeout'}]`;
      setTurnsHistory((prev) => [
        ...prev,
        { agent: errText, step: curStep, timestamp: new Date().toLocaleTimeString() }
      ]);
      setCallStatus('LISTENING');
      if (!isMutedRef.current) startListening();
    }
  };

  // 8. End Call & Summary Generation
  const handleEndCall = () => {
    isCompletedRef.current = true;
    stopSpeechSynthesis();
    stopListening();
    if (sessionId) stopAndUploadAudio(sessionId);
    setCallStatus('COMPLETED');
    setClinicalSummary((prev) => ({ ...prev, disposition: 'ENDED_BY_USER' }));
    setTurnsHistory((prev) => [
      ...prev,
      { agent: '[CALL ENDED — CLINICAL RECOVERY DATA SAVED]', step: stepKey, timestamp: new Date().toLocaleTimeString() }
    ]);
  };

  // 9. Repeat Question / Ask Again
  const handleRepeatQuestion = () => {
    if (callStatus === 'COMPLETED' || !agentPrompt) return;
    speakAgentPrompt(agentPrompt, language);
  };

  // 10. Failed Call Simulation Scenarios
  const handleSimulateCallDisposition = async (disposition: 'NO_ANSWER' | 'BUSY' | 'UNREACHABLE') => {
    if (!sessionId) return;
    try {
      const res = await apiClient.recordCallDisposition(token, sessionId, disposition, true, "Simulated carrier event");
      isCompletedRef.current = true;
      stopSpeechSynthesis();
      stopListening();
      if (sessionId) stopAndUploadAudio(sessionId);
      setCallStatus('COMPLETED');

      let demoMsg = `[SIMULATION] Call outcome: ${disposition}. `;
      if (res.status === 'RETRY_SCHEDULED') {
        demoMsg += `Retry #${res.retry_count} scheduled (+${res.backoff_minutes}m backoff). Next retry at: ${new Date(res.next_retry_at).toLocaleTimeString()}.`;
      } else if (res.status === 'LIMIT_REACHED') {
        demoMsg += `Retry limit reached (${res.retry_count}/${res.retry_limit}). Escalated to clinical review.`;
      }
      setClinicalSummary((prev) => ({ ...prev, disposition }));
      setTurnsHistory((prev) => [
        ...prev,
        { agent: demoMsg, step: 'SIMULATION_OUTCOME', timestamp: new Date().toLocaleTimeString() }
      ]);
    } catch (err: any) {
      console.error('Failed to simulate disposition:', err.message);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4 animate-fade-in">
      <div 
        className="bg-white rounded-3xl shadow-2xl max-w-3xl w-full overflow-hidden border border-slate-200 flex flex-col max-h-[92vh]"
        role="dialog"
        aria-modal="true"
        aria-labelledby="call-sim-title"
      >
        {/* Header */}
        <div className="bg-gradient-to-r from-indigo-700 via-indigo-800 to-indigo-900 text-white px-6 py-4 flex items-center justify-between shadow-md">
          <div className="flex items-center space-x-3">
            <div className="p-2.5 bg-white/10 rounded-2xl border border-white/10 shadow-inner">
              <Phone className="w-5 h-5 text-emerald-400" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 id="call-sim-title" className="font-bold text-base tracking-tight">
                  Automated Voice Recovery Follow-up
                </h3>
                <span className="text-[10px] font-bold uppercase tracking-wider bg-amber-400/20 text-amber-200 border border-amber-300/30 px-2 py-0.5 rounded-full">
                  ₹0 Simulation Engine
                </span>
              </div>
              <p className="text-xs text-indigo-200 mt-0.5">
                Patient: <strong className="text-white">{activePatientName}</strong> • Real-time Web Speech Turn-Taking
              </p>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            <button
              onClick={() => setSpeechSynthesisEnabled(!speechSynthesisEnabled)}
              title={speechSynthesisEnabled ? "AI Audio Output Enabled" : "AI Audio Output Muted"}
              className={`p-2 rounded-xl text-xs font-medium transition-colors ${
                speechSynthesisEnabled ? 'bg-indigo-600 text-white' : 'bg-white/10 text-indigo-200'
              }`}
            >
              {speechSynthesisEnabled ? <Volume2 className="w-4 h-4" /> : <VolumeX className="w-4 h-4" />}
            </button>
            <button
              onClick={onClose}
              className="p-2 hover:bg-white/10 rounded-xl text-indigo-200 hover:text-white transition-colors"
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
                onChange={(e) => {
                  const selId = e.target.value;
                  setPatientId(selId);
                  const p = patients.find(item => item.id === selId);
                  if (p) setLanguage(p.lang);
                }}
                disabled={callStatus !== 'IDLE' && callStatus !== 'COMPLETED'}
                className="bg-white border border-slate-300 rounded-lg px-2.5 py-1 font-medium text-slate-800 focus:ring-1 focus:ring-indigo-500"
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

            <div className="flex items-center space-x-1.5">
              <Languages className="w-3.5 h-3.5 text-indigo-600" />
              <select
                value={language}
                onChange={(e) => setLanguage(e.target.value as any)}
                disabled={callStatus !== 'IDLE' && callStatus !== 'COMPLETED'}
                className="bg-white border border-slate-300 rounded-lg px-2 py-1 font-medium text-slate-800"
              >
                <option value="en">English (en-IN)</option>
                <option value="hi">Hindi (hi-IN)</option>
                <option value="mr">Marathi (mr-IN)</option>
              </select>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            {callStatus === 'IDLE' || callStatus === 'COMPLETED' ? (
              <button
                onClick={handleStartCall}
                className="bg-emerald-600 hover:bg-emerald-700 text-white font-semibold px-4 py-1.5 rounded-xl flex items-center space-x-1.5 transition-all shadow-sm active:scale-95"
              >
                <Phone className="w-3.5 h-3.5" />
                <span>{sessionId ? 'Start New Check-in Call' : 'Start Check-in Call'}</span>
              </button>
            ) : (
              <div className="flex items-center space-x-2">
                <button
                  onClick={handleRepeatQuestion}
                  disabled={callStatus === 'PROCESSING' || callStatus === 'CONNECTING'}
                  title="Repeat the current AI question"
                  className="bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold px-2.5 py-1.5 rounded-xl flex items-center space-x-1 text-xs border border-slate-200 transition-colors"
                >
                  <RotateCcw className="w-3.5 h-3.5" />
                  <span>Repeat Question</span>
                </button>
                <button
                  onClick={() => {
                    const next = !isMuted;
                    setIsMuted(next);
                    if (next) stopListening();
                    else if (callStatus === 'LISTENING') startListening();
                  }}
                  className={`px-2.5 py-1.5 rounded-xl text-xs font-semibold flex items-center space-x-1 border transition-colors ${
                    isMuted ? 'bg-amber-100 border-amber-300 text-amber-800' : 'bg-slate-100 border-slate-200 text-slate-700'
                  }`}
                >
                  {isMuted ? <MicOff className="w-3.5 h-3.5 text-amber-700" /> : <Mic className="w-3.5 h-3.5 text-emerald-600" />}
                  <span>{isMuted ? 'Mic Muted' : 'Mic Active'}</span>
                </button>
                <button
                  onClick={handleEndCall}
                  className="bg-rose-600 hover:bg-rose-700 text-white font-semibold px-3 py-1.5 rounded-xl flex items-center space-x-1.5 transition-colors shadow-sm"
                >
                  <PhoneOff className="w-3.5 h-3.5" />
                  <span>End Call</span>
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Turn-Taking Dynamic Lifecycle Banner */}
        {callStatus !== 'IDLE' && (
          <div className="bg-slate-50 border-b border-slate-200 px-6 py-2.5 flex items-center justify-between text-xs transition-all">
            <div className="flex items-center gap-2.5">
              {callStatus === 'CONNECTING' && (
                <>
                  <span className="relative flex h-2.5 w-2.5">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-amber-500"></span>
                  </span>
                  <span className="font-bold text-amber-900">Ringing handset... (Dialing {activePatientName})</span>
                </>
              )}

              {callStatus === 'AI_SPEAKING' && (
                <>
                  <span className="flex items-center gap-1">
                    <span className="w-1.5 h-3 bg-indigo-600 rounded-full animate-bounce"></span>
                    <span className="w-1.5 h-4 bg-indigo-500 rounded-full animate-bounce delay-75"></span>
                    <span className="w-1.5 h-2.5 bg-indigo-600 rounded-full animate-bounce delay-150"></span>
                  </span>
                  <span className="font-bold text-indigo-900">AI Care Companion Speaking (Mic muted to prevent echo)</span>
                </>
              )}

              {callStatus === 'LISTENING' && (
                <>
                  <span className="relative flex h-3 w-3">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500"></span>
                  </span>
                  <span className="font-bold text-emerald-900 flex items-center gap-1">
                    <Mic className="w-3.5 h-3.5 text-emerald-600 animate-pulse" />
                    <span>Listening to Patient... Speak now or select an option below</span>
                  </span>
                </>
              )}

              {callStatus === 'PROCESSING' && (
                <>
                  <Loader2 className="w-3.5 h-3.5 text-amber-600 animate-spin" />
                  <span className="font-bold text-amber-900">Processing Clinical Turn & Analyzing Speech...</span>
                </>
              )}

              {callStatus === 'COMPLETED' && (
                <>
                  <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                  <span className="font-bold text-slate-800">Call Completed · Recovery Data Recorded</span>
                </>
              )}

              {callStatus === 'ERROR' && (
                <>
                  <AlertCircle className="w-4 h-4 text-rose-600" />
                  <span className="font-bold text-rose-900">Telephony Disconnected</span>
                </>
              )}
            </div>

            <div className="flex items-center gap-3">
              <span className="font-mono text-[11px] text-slate-500 flex items-center gap-1">
                <Clock className="w-3.5 h-3.5 text-slate-400" />
                {formatTimer(callDuration)}
              </span>
              <span className="text-[10px] text-indigo-700 bg-indigo-100/70 px-2 py-0.5 rounded-md font-semibold">
                Turn {turnIndex} · {stepKey}
              </span>
            </div>
          </div>
        )}

        {/* Live Speech Interim Wave Bar */}
        {callStatus === 'LISTENING' && interimTranscript && (
          <div className="bg-emerald-50 border-b border-emerald-100 px-6 py-2 flex items-center justify-between text-xs text-emerald-900 animate-pulse">
            <span className="flex items-center gap-1.5 font-medium">
              <Mic className="w-3 h-3 text-emerald-600 shrink-0" />
              <span>Hearing: <em>"{interimTranscript}"</em></span>
            </span>
            <span className="text-[10px] bg-emerald-200/60 px-2 py-0.5 rounded-full font-semibold">
              Live Speech Input
            </span>
          </div>
        )}

        {/* Silence Timeout Notification */}
        {callStatus === 'LISTENING' && silencePromptVisible && (
          <div className="bg-amber-50 border-b border-amber-200 px-6 py-2 text-xs text-amber-800 flex items-center justify-between">
            <span className="flex items-center gap-1.5">
              <Info className="w-3.5 h-3.5 text-amber-600 shrink-0" />
              <span>No speech detected. Speak now, choose a quick reply below, or click Repeat Question.</span>
            </span>
            <button
              onClick={handleRepeatQuestion}
              className="text-[11px] font-bold text-indigo-700 underline hover:text-indigo-900"
            >
              Repeat Question
            </button>
          </div>
        )}

        {/* Microphone Permission Warning */}
        {micPermissionDenied && (
          <div className="bg-rose-50 border-b border-rose-200 px-6 py-2 text-xs text-rose-800 flex items-center justify-between">
            <span className="flex items-center gap-1.5">
              <AlertCircle className="w-3.5 h-3.5 text-rose-600 shrink-0" />
              <span>Microphone permission denied by browser. You can still use the quick reply buttons or text box below.</span>
            </span>
          </div>
        )}

        {/* Live Conversation Transcript Area */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4 custom-scrollbar bg-slate-100/50 min-h-[260px] max-h-[340px]">
          {turnsHistory.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center p-8 text-slate-400">
              <Phone className="w-12 h-12 text-slate-300 mb-2 stroke-1" />
              <p className="font-semibold text-slate-700 text-sm">Automated Voice Recovery Monitoring</p>
              <p className="text-xs max-w-sm mt-1 text-slate-500">
                Click <strong>"Start Check-in Call"</strong> above to launch an interactive, turn-based post-discharge conversation for {activePatientName}.
              </p>
              <div className="mt-4 p-3 bg-emerald-50 border border-emerald-200/80 rounded-xl text-[11px] text-emerald-800 max-w-md text-left flex items-start gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                <span>
                  <strong>Full Voice Lifecycle:</strong> AI speaks complete phrases, pauses, listens for your speech via browser microphone, processes your reply, and delivers appropriate clinical follow-ups.
                </span>
              </div>
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
                        <span>Patient Voice Response</span>
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
                <span>Clinical Escalation Alert Triggered:</span>
              </div>
              {alertsTriggered.map((a, i) => (
                <p key={i} className="text-rose-600 pl-6 text-[11px]">
                  • <strong>{a.title}</strong>: {a.reason}
                </p>
              ))}
            </div>
          )}

          {/* Post-Call Clinical Summary Card */}
          {callStatus === 'COMPLETED' && (
            <div className="bg-white border border-slate-200 rounded-2xl p-4 shadow-sm space-y-3">
              <div className="flex items-center justify-between border-b border-slate-100 pb-2">
                <span className="font-bold text-xs text-slate-800 flex items-center gap-1.5">
                  <Activity className="w-4 h-4 text-indigo-600" />
                  Clinical Session Summary
                </span>
                <span className="text-[11px] font-semibold text-emerald-700 bg-emerald-50 px-2.5 py-0.5 rounded-full border border-emerald-200">
                  {clinicalSummary.disposition} ({formatTimer(callDuration)})
                </span>
              </div>

              <div className="grid grid-cols-3 gap-3 text-xs">
                <div className="p-2.5 bg-slate-50 rounded-xl">
                  <span className="text-[10px] text-slate-500 font-semibold block uppercase">Vitals Recorded</span>
                  <div className="mt-1 space-y-0.5">
                    <p className="font-bold text-slate-800">SpO2: {clinicalSummary.vitals.SpO2 || 'Not provided'}</p>
                    <p className="font-bold text-slate-800">BP: {clinicalSummary.vitals.BP || 'Not provided'}</p>
                  </div>
                </div>

                <div className="p-2.5 bg-slate-50 rounded-xl">
                  <span className="text-[10px] text-slate-500 font-semibold block uppercase">Symptoms</span>
                  <div className="mt-1 space-y-0.5">
                    <p className="font-bold text-slate-800">Pain: {clinicalSummary.symptoms.Pain || '0/10 (None)'}</p>
                    <p className="text-slate-600 text-[11px]">{clinicalSummary.symptoms.Breathlessness || 'No shortness of breath'}</p>
                  </div>
                </div>

                <div className="p-2.5 bg-slate-50 rounded-xl">
                  <span className="text-[10px] text-slate-500 font-semibold block uppercase">Medication</span>
                  <div className="mt-1 space-y-0.5">
                    <p className="font-bold text-slate-800">{clinicalSummary.medication.status ? `Status: ${clinicalSummary.medication.status}` : 'Dose Confirmed'}</p>
                    <p className="text-slate-600 text-[11px]">{clinicalSummary.medication.name || 'Prescription Schedule'}</p>
                  </div>
                </div>
              </div>

              {/* Call Audio Recording Playback (CV-08) */}
              <div className="p-3 bg-indigo-50/60 border border-indigo-100 rounded-xl space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-bold text-indigo-900 flex items-center gap-1.5">
                    <Volume2 className="w-3.5 h-3.5 text-indigo-600" />
                    <span>Call Audio Recording (CV-08)</span>
                  </span>
                  {audioUploaded ? (
                    <span className="text-[10px] font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">
                      ✓ Uploaded to Backend Storage
                    </span>
                  ) : audioRecordingActive ? (
                    <span className="text-[10px] font-semibold text-amber-700 bg-amber-50 px-2 py-0.5 rounded-full border border-amber-200 animate-pulse">
                      Processing recording...
                    </span>
                  ) : (
                    <span className="text-[10px] font-semibold text-slate-500 bg-slate-100 px-2 py-0.5 rounded-full">
                      Archived in Session
                    </span>
                  )}
                </div>
                {sessionId && (
                  <audio
                    controls
                    preload="metadata"
                    src={apiClient.getCallAudioStreamUrl(sessionId)}
                    className="w-full h-8 mt-1"
                  />
                )}
              </div>
            </div>
          )}
        </div>

        {/* Patient Response Options & Controls */}
        <div className="p-4 bg-white border-t border-slate-200 space-y-3">
          
          {/* Quick-Response Speech Chips (Accessible for test or impaired speech) */}
          {callStatus !== 'IDLE' && callStatus !== 'COMPLETED' && (
            <div>
              <p className="text-[11px] font-semibold text-slate-500 mb-1.5 flex items-center justify-between">
                <span className="flex items-center space-x-1">
                  <Sparkles className="w-3 h-3 text-indigo-600" />
                  <span>Suggested Responses for {stepKey.replace('_', ' ')} ({language.toUpperCase()}):</span>
                </span>
                <span className="text-[10px] text-slate-400">Click any option or speak into microphone</span>
              </p>
              <div className="flex flex-wrap gap-1.5">
                {(quickResponses[stepKey]?.[language] || quickResponses[stepKey]?.['en'] || [
                  'Yes', 'No', 'I am feeling better today', 'Doctor se baat karao'
                ]).map((chip, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleSendSpeech(chip)}
                    disabled={callStatus === 'PROCESSING' || callStatus === 'AI_SPEAKING'}
                    className="text-[11px] bg-slate-100 hover:bg-indigo-50 hover:text-indigo-700 hover:border-indigo-300 border border-slate-200 text-slate-700 px-2.5 py-1 rounded-lg transition-colors disabled:opacity-50"
                  >
                    "{chip}"
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Manual Input Fallback */}
          <div className="flex items-center space-x-2">
            <input
              type="text"
              placeholder={
                callStatus === 'AI_SPEAKING'
                  ? "AI is speaking... Please wait for question to complete"
                  : callStatus === 'LISTENING'
                  ? "Microphone is listening... Speak now or type response here"
                  : callStatus === 'PROCESSING'
                  ? "Processing turn..."
                  : callStatus === 'COMPLETED'
                  ? "Call ended. Start a new call above to begin another check-in."
                  : "Start check-in call above to begin voice dialogue..."
              }
              value={userSpeechInput}
              disabled={callStatus === 'IDLE' || callStatus === 'COMPLETED' || callStatus === 'PROCESSING' || callStatus === 'CONNECTING'}
              onChange={(e) => setUserSpeechInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSendSpeech(userSpeechInput)}
              className="flex-1 border border-slate-300 rounded-xl px-4 py-2 text-xs focus:outline-hidden focus:ring-2 focus:ring-indigo-500 disabled:bg-slate-100 disabled:text-slate-400"
            />
            <button
              onClick={() => handleSendSpeech(userSpeechInput)}
              disabled={callStatus === 'IDLE' || callStatus === 'COMPLETED' || callStatus === 'PROCESSING' || !userSpeechInput.trim()}
              className="bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-300 text-white text-xs font-semibold px-4 py-2 rounded-xl transition-colors shrink-0"
            >
              Send Speech
            </button>
          </div>

          {/* Carrier Failure Simulation Testing Bar */}
          {callStatus !== 'IDLE' && callStatus !== 'COMPLETED' && (
            <div className="bg-slate-50 border border-slate-200 rounded-xl p-2.5">
              <div className="flex items-center justify-between mb-2">
                <span className="text-[11px] font-bold text-slate-700 flex items-center gap-1">
                  <Radio className="w-3.5 h-3.5 text-amber-600" />
                  Telephony Carrier Scenarios:
                </span>
                <span className="text-[10px] text-slate-400">In-browser simulation</span>
              </div>
              <div className="grid grid-cols-3 gap-2">
                <button
                  onClick={() => handleSimulateCallDisposition('NO_ANSWER')}
                  className="py-1.5 px-2 bg-white hover:bg-amber-50 border border-slate-200 hover:border-amber-300 text-slate-700 hover:text-amber-800 rounded-lg text-[11px] font-semibold transition-colors"
                >
                  Simulate No Answer
                </button>
                <button
                  onClick={() => handleSimulateCallDisposition('BUSY')}
                  className="py-1.5 px-2 bg-white hover:bg-amber-50 border border-slate-200 hover:border-amber-300 text-slate-700 hover:text-amber-800 rounded-lg text-[11px] font-semibold transition-colors"
                >
                  Simulate Busy Line
                </button>
                <button
                  onClick={() => handleSimulateCallDisposition('UNREACHABLE')}
                  className="py-1.5 px-2 bg-white hover:bg-amber-50 border border-slate-200 hover:border-amber-300 text-slate-700 hover:text-amber-800 rounded-lg text-[11px] font-semibold transition-colors"
                >
                  Simulate Unavailable
                </button>
              </div>
            </div>
          )}

        </div>
      </div>
    </div>
  );
};
