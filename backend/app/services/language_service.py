import re
from typing import Dict, Any, Optional, Tuple

class LanguageService:
    """
    Multilingual Care Conversation & Localization Service
    Supports Marathi ('mr'), Hindi ('hi'), and English ('en') (LN-01).
    Extensible architecture to further regional languages without redesign.
    """

    SUPPORTED_LANGUAGES = ["en", "hi", "mr"]
    
    # Prompt library for unhurried, elder-friendly conversations (CV-02, LN-05)
    PROMPTS: Dict[str, Dict[str, str]] = {
        "WELCOME_FIRST_CALL": {
            "en": "Hello {name}, this is your AI Care Companion from {facility}. I will be calling you daily to check on your recovery. Are you comfortable speaking in English, or would you prefer Hindi or Marathi?",
            "hi": "नमस्ते {name} जी, मैं {facility} से आपका AI केयर साथी बात कर रहा हूँ। मैं आपकी सेहत जानने के लिए रोज़ कॉल करूँगा। क्या आप हिंदी में बात करना चाहेंगे?",
            "mr": "नमस्कार {name} जी, मी {facility} कडून तुमचा AI केअर सोबती बोलत आहे. मी दररोज तुमच्या प्रकृतीची विचारपूस करण्यासाठी कॉल करेन. आपण मराठीत बोलणे पसंत कराल का?"
        },
        "IDENTITY_VERIFICATION": {
            "en": "Before we begin, to protect your privacy, could you please confirm if I am speaking with {name}?",
            "hi": "शुरू करने से पहले, आपकी गोपनीयता के लिए, क्या आप पुष्टि कर सकते हैं कि क्या मैं {name} जी से बात कर रहा हूँ?",
            "mr": "सुरुवात करण्यापूर्वी, आपल्या सुरक्षेसाठी, कृपया पुष्टी कराल का की मी {name} यांच्याशी बोलत आहे?"
        },
        "UNAUTHORIZED_CALLER_REFUSAL": {
            "en": "Thank you for answering. For patient confidentiality, I can only discuss clinical care details with {name} or an authorized caregiver. I will arrange a callback for {name}.",
            "hi": "कॉल उठाने के लिए धन्यवाद। मरीज की गोपनीयता के लिए, मैं केवल {name} जी या अधिकृत देखभालकर्ता से ही स्वास्थ्य संबंधी बात कर सकता हूँ। मैं बाद में संपर्क करूँगा।",
            "mr": "कॉल घेतल्याबद्दल धन्यवाद. रुग्णाच्या गोपनीयतेसाठी, मी केवळ {name} किंवा अधिकृत काळजीवाहकांशीच आरोग्याबद्दल बोलू शकतो. मी नंतर पुन्हा कॉल करेन."
        },
        "WELLBEING_MORNING": {
            "en": "Good morning {name}. How are you feeling overall today? Take your time.",
            "hi": "शुभ प्रभात {name} जी। आज आप कैसा महसूस कर रहे हैं? आराम से बताइए।",
            "mr": "शुभ सकाळ {name} जी. आज तुम्हाला एकंदरीत कसे वाटत आहे? शांतपणे सांगा."
        },
        "WELLBEING_EVENING": {
            "en": "Good evening {name}. I am checking in to see how your day went and review your evening recovery.",
            "hi": "शुभ संध्या {name} जी। आपकी दिनचर्या कैसी रही और शाम को आपकी सेहत कैसी है, यह जानने के लिए मैंने कॉल किया है।",
            "mr": "शुभ संध्याकाळ {name} जी. तुमचा आजचा दिवस कसा गेला आणि संध्याकाळी प्रकृती कशी आहे हे जाणून घेण्यासाठी मी कॉल केला आहे."
        },
        "SYMPTOMS_PAIN": {
            "en": "Are you experiencing any pain today? If yes, on a scale of 0 to 10, how would you rate it?",
            "hi": "क्या आज आपको कोई दर्द महसूस हो रहा है? यदि हाँ, तो 0 से 10 के पैमाने पर आप इसे कितना बताएँगे?",
            "mr": "आज तुम्हाला कुठेही वेदना किंवा दुखणे जाणवत आहे का? असल्यास, 0 ते 10 च्या प्रमाणात किती त्रास आहे?"
        },
        "SYMPTOMS_BREATHLESSNESS": {
            "en": "Have you felt any shortness of breath or difficulty breathing today?",
            "hi": "क्या आज आपको साँस लेने में कोई तकलीफ़ या बेचैनी महसूस हुई है?",
            "mr": "आज तुम्हाला श्वास घेण्यास काही अडचण किंवा धाप लागल्यासारखे वाटले का?"
        },
        "SYMPTOMS_PREVIOUS_COMPARISON": {
            "en": "Yesterday you mentioned feeling {previous_symptom}. Is that feeling better, the same, or worse today?",
            "hi": "कल आपने {previous_symptom} के बारे में बताया था। आज वह पहले से बेहतर है, वैसा ही है, या ज्यादा खराब है?",
            "mr": "काल तुम्ही {previous_symptom} बद्दल सांगितले होते. आज त्यात सुधारणा झाली आहे, तसेच आहे, की जास्त त्रास होत आहे?"
        },
        "MEDICATION_REMINDER": {
            "en": "It is time for your scheduled medication: {medicine_name}, dose {dosage}. Have you taken this dose?",
            "hi": "यह आपकी दवा {medicine_name}, खुराक {dosage} का समय है। क्या आपने यह दवा ले ली है?",
            "mr": "ही तुमची औषध {medicine_name}, मात्रा {dosage} घेण्याची वेळ आहे. तुम्ही हे औषध घेतले आहे का?"
        },
        "MEDICATION_REASON_INQUIRY": {
            "en": "Understood. Could you share the reason for missing this dose? For example, side effects or forgetting?",
            "hi": "समझ गया। क्या आप बता सकते हैं कि दवा न लेने का क्या कारण था? जैसे कि कोई समस्या या भूल जाना?",
            "mr": "समजले. हे औषध न घेण्याचे कारण सांगू शकाल का? जसे की काही त्रास किंवा विसर पडणे?"
        },
        "MEDICATION_DOSAGE_GUARDRAIL": {
            "en": "I cannot advise on changing your dose or stopping medications. Please take only the exact dosage prescribed by {doctor_name}. I will alert your care team to contact you regarding dosage questions.",
            "hi": "मैं दवा की खुराक बदलने या बंद करने की सलाह नहीं दे सकता। कृपया केवल {doctor_name} द्वारा लिखी गई खुराक ही लें। मैं आपकी स्वास्थ्य टीम को इस बारे में सूचित कर रहा हूँ।",
            "mr": "मी औषधाची मात्रा बदलण्याचा किंवा बंद करण्याचा सल्ला देऊ शकत नाही. कृपया फक्त {doctor_name} यांनी दिलेली नेमकी मात्राच घ्या. मी तुमच्या डॉक्टरांच्या टीमला माहिती देत आहे."
        },
        "VITALS_BP_PROMPT": {
            "en": "Could you please share your Blood Pressure reading today? For example, 120 over 80.",
            "hi": "क्या आप आज का अपना ब्लड प्रेशर (बीपी) बता सकते हैं? जैसे कि 120 और 80.",
            "mr": "कृपया तुम्ही आज मोजलेला रक्तदाब (बीपी) सांगू शकाल का? जसे की 120 आणि 80."
        },
        "VITALS_SPO2_PROMPT": {
            "en": "Please share your pulse oximeter oxygen reading, SpO2 percentage.",
            "hi": "कृपया अपने ऑक्सीमीटर की ऑक्सीजन रीडिंग (SpO2 प्रतिशत) बताइए।",
            "mr": "कृपया पल्स ऑक्सिमीटरवरील ऑक्सिजनची पातळी (SpO2 टक्केवारी) सांगा."
        },
        "VITALS_CONFIRMATION_READBACK": {
            "en": "I recorded your {vital_name} as {value} {unit}. Is that correct?",
            "hi": "मैंने आपका {vital_name} {value} {unit} दर्ज किया है। क्या यह सही है?",
            "mr": "मी तुमचे {vital_name} {value} {unit} नोंदवले आहे. हे बरोबर आहे का?"
        },
        "VITALS_IMPLAUSIBLE_REASK": {
            "en": "That reading of {value} seems unusually high or low. Let us verify together: could you check your monitor and read the numbers once more?",
            "hi": "यह रीडिंग {value} सामान्य सीमा से काफी अलग लग रही है। कृपया एक बार दोबारा मशीन देखकर सही संख्या बताएँ।",
            "mr": "ही नोंद {value} नेहमीपेक्षा खूप जास्त किंवा कमी दिसत आहे. कृपया मशीन तपासून पुन्हा एकदा बरोबर आकडा सांगा."
        },
        "EMERGENCY_RED_FLAG_SCRIPT": {
            "en": "IMPORTANT NOTICE: What you described may require urgent medical attention. Please call emergency services immediately or have someone take you to the nearest hospital emergency room right now. I have notified your care team and caregiver.",
            "hi": "अत्यंत महत्वपूर्ण सूचना: आपने जो लक्षण बताए हैं, उनके लिए तत्काल आपातकालीन चिकित्सा सहायता की आवश्यकता है। कृपया तुरंत 108 पर कॉल करें या नजदीकी अस्पताल के इमरजेंसी वार्ड में जाएँ। मैंने आपकी केयर टीम और परिवार को तुरंत सूचित कर दिया है।",
            "mr": "अतिशय महत्त्वाची सूचना: तुम्ही सांगितलेली लक्षणे पाहता तातडीच्या वैद्यकीय उपचारांची गरज आहे. कृपया त्वरित 108 ला कॉल करा किंवा जवळच्या रुग्णालयाच्या इमर्जन्सी वॉर्डमध्ये जा. मी तुमच्या डॉक्टरांच्या टीमला आणि काळजीवाहकांना तात्काळ कळवले आहे."
        },
        "TRANSFER_HUMAN_CONNECTING": {
            "en": "Connecting you to a care team member now. Please stay on the line.",
            "hi": "मैं आपको अभी केयर टीम के सदस्य से कनेक्ट कर रहा हूँ। कृपया लाइन पर बने रहें।",
            "mr": "मी तुम्हाला आता डॉक्टरांच्या टीममधील सदस्याशी जोडून देत आहे. कृपया फोनवर थांबा."
        },
        "TRANSFER_CALLBACK_LOGGED": {
            "en": "Our clinical staff is currently on urgent calls. I have logged an immediate callback request with your conversation details. A nurse will reach you shortly.",
            "hi": "हमारी क्लिनिकल टीम अभी अन्य कॉल में व्यस्त है। मैंने आपके विवरण के साथ तुरंत कॉलबैक का अनुरोध दर्ज कर लिया है। एक नर्स जल्द ही आपसे संपर्क करेगी।",
            "mr": "आमचे वैद्यकीय कर्मचारी सध्या व्यस्त आहेत. मी तुमच्या कॉलच्या संपूर्ण माहितीसह तातडीचा कॉलबॅक नोंदवला आहे. एक परिचारिका लवकरच आपल्याशी संपर्क साधेल."
        },
        "PROGRAMME_CLOSING_MESSAGE": {
            "en": "Congratulations {name}! You have successfully completed your {programme_days}-day recovery programme. Your care team commends your commitment to recovery. Stay healthy!",
            "hi": "बधाई हो {name} जी! आपने अपना {programme_days} दिनों का रिकवरी कार्यक्रम सफलतापूर्वक पूरा कर लिया है। आपकी केयर टीम आपके स्वास्थ्य और सुधार की सराहना करती है। स्वस्थ रहें!",
            "mr": "अभिनंदन {name} जी! तुम्ही तुमचा {programme_days} दिवसांचा रिकव्हरी कार्यक्रम यशस्वीरीत्या पूर्ण केला आहे. तुमच्या काळजीवाहू टीमला तुमच्या प्रगतीचा अभिमान आहे. नेहमी निरोगी राहा!"
        }
    }

    @classmethod
    def get_prompt(cls, key: str, lang: str = "en", **kwargs) -> str:
        lang = lang if lang in cls.SUPPORTED_LANGUAGES else "en"
        template_dict = cls.PROMPTS.get(key, {})
        template = template_dict.get(lang) or template_dict.get("en", "")
        try:
            return template.format(**kwargs)
        except Exception:
            return template

    @classmethod
    def detect_language_switch_request(cls, text: str) -> Optional[str]:
        """
        LN-03: Allow language change mid-conversation and continue without losing context.
        Returns target language code ('mr', 'hi', 'en') or None.
        """
        text_lower = text.lower()
        
        # Marathi switch triggers
        if any(term in text_lower for term in [
            "मराठी", "marathi", "marathit", "speak in marathi", "मराठीत बोला", "मराठी बोला", "mala marathi"
        ]):
            return "mr"
            
        # Hindi switch triggers
        if any(term in text_lower for term in [
            "हिंदी", "hindi", "hindime", "speak in hindi", "हिंदी में बोलो", "हिंदी में बात करो", "hindi me bolo"
        ]):
            return "hi"
            
        # English switch triggers
        if any(term in text_lower for term in [
            "english", "ingreji", "angrezi", "speak in english", "talk in english", "इंग्रजी", "अंग्रेजी"
        ]):
            return "en"
            
        return None

    @classmethod
    def parse_code_mixed_medication_response(cls, text: str) -> Tuple[str, Optional[str]]:
        """
        LN-04: Interpret code-mixed speech (regional language with English drug/clinical terms).
        Returns (status: 'TAKEN' | 'MISSED' | 'DEFERRED' | 'UNKNOWN', stated_reason: Optional[str])
        """
        text_lower = text.lower()

        # Check "Remind me later" / deferral triggers (MD-04)
        if any(term in text_lower for term in [
            "later", "remind me later", "after some time", "baad me", "baad mein", "thodi der me", 
            "nantar", "thodya velani", "nantar gheto", "nantar ghein", "call me back"
        ]):
            return "DEFERRED", "Patient requested reminder later"

        # Check positive confirmation triggers (MD-02)
        taken_terms = [
            "yes", "taken", "took", "i took it", "have taken", "done", 
            "le li", "le liya", "kha li", "kha liya", "pe li", "pe liya", "khaa li",
            "ghetli", "aadhi ghetli", "ghetla", "khalii", "khall", "piylo", "sampli", "ho ghetli"
        ]
        if any(term in text_lower for term in taken_terms):
            return "TAKEN", None

        # Check missed triggers with reasons (MD-03)
        missed_terms = [
            "no", "not yet", "missed", "forgot", "did not take", "haven't",
            "nahi li", "nahi liya", "nahi khaya", "nahi khayi", "bhul gaya", "bhul gayi", "chhoot gayi", "khatam ho gayi",
            "nahi ghetli", "nahi ghetla", "visarlo", "visarli", "sampali", "tras hoto", "chhakkar"
        ]
        if any(term in text_lower for term in missed_terms):
            # Extract common reasons
            reason = "Patient reported not taken"
            if "bhul" in text_lower or "visar" in text_lower or "forgot" in text_lower:
                reason = "Forgot dose"
            elif "khatam" in text_lower or "samp" in text_lower or "out of stock" in text_lower or "stock" in text_lower:
                reason = "Medication out of stock"
            elif "side effect" in text_lower or "chhakkar" in text_lower or "chakkar" in text_lower or "dizziness" in text_lower or "tras" in text_lower or "vomit" in text_lower or "nausea" in text_lower or "unwell" in text_lower:
                reason = "Side effects / feeling unwell"
            return "MISSED", reason

        return "UNKNOWN", None

    @classmethod
    def parse_vitals_reading_from_speech(cls, vital_type: str, text: str) -> Optional[Tuple[float, Optional[float]]]:
        """
        Extracts numbers from code-mixed speech for vitals (VT-01).
        Supports:
        - "120 over 80", "120 aani 80", "130 aur 85", "120/80"
        - "sugar 140", "pulse 72", "oxygen 97"
        """
        # Find all integer or float numbers
        numbers = re.findall(r"\b\d+(?:\.\d+)?\b", text)
        if not numbers:
            return None

        if vital_type in ["BP", "BP_SYSTOLIC"]:
            if len(numbers) >= 2:
                sys = float(numbers[0])
                dia = float(numbers[1])
                return (sys, dia)
            elif len(numbers) == 1:
                return (float(numbers[0]), None)
        else:
            return (float(numbers[0]), None)
            
        return None
