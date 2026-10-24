import pytest
from app.services.language_service import LanguageService

def test_language_switch_detection():
    """
    LN-03: Allow language change mid-conversation and continue in the new language.
    """
    # Test Marathi switch detection
    assert LanguageService.detect_language_switch_request("मला मराठीत बोलायचे आहे") == "mr"
    assert LanguageService.detect_language_switch_request("Can we please speak in Marathi?") == "mr"
    assert LanguageService.detect_language_switch_request("marathi me bolo") == "mr"

    # Test Hindi switch detection
    assert LanguageService.detect_language_switch_request("हिंदी में बात करो") == "hi"
    assert LanguageService.detect_language_switch_request("Please talk to me in Hindi") == "hi"

    # Test English switch detection
    assert LanguageService.detect_language_switch_request("Let's switch to English please") == "en"

    # Normal text should return None
    assert LanguageService.detect_language_switch_request("Maine dawa le li hai") is None

def test_code_mixed_speech_medication_parsing():
    """
    LN-04: Interpret code-mixed speech (regional language with English drug/clinical terms).
    """
    # 1. Taken confirmation in code-mixed Hindi
    status, reason = LanguageService.parse_code_mixed_medication_response("Maine subah breakfast ke baad Amlodipine le li hai")
    assert status == "TAKEN"

    # 2. Taken confirmation in code-mixed Marathi
    status, reason = LanguageService.parse_code_mixed_medication_response("Ho me sakali Metformin ghetli ahe")
    assert status == "TAKEN"

    # 3. Deferral / Remind me later in Hindi (MD-04)
    status, reason = LanguageService.parse_code_mixed_medication_response("Mujhe thodi der baad me yaad dilana")
    assert status == "DEFERRED"

    # 4. Deferral in Marathi
    status, reason = LanguageService.parse_code_mixed_medication_response("Thodya velani call kara, nantar gheto")
    assert status == "DEFERRED"

    # 5. Missed with side-effect reason
    status, reason = LanguageService.parse_code_mixed_medication_response("Nahi li, goli lene ke baad chakkar aa rahi thi")
    assert status == "MISSED"
    assert "Side effects" in reason

    # 6. Missed with stockout reason
    status, reason = LanguageService.parse_code_mixed_medication_response("Aushadh sampali ahe, stock nahi ahe")
    assert status == "MISSED"
    assert "stock" in reason.lower()

def test_code_mixed_vitals_extraction():
    """
    VT-01, LN-04: Extract BP and SpO2 numbers from conversational multi-language speech.
    """
    # BP: 130 over 85
    bp = LanguageService.parse_vitals_reading_from_speech("BP", "Aaj subah BP 130 aur 85 tha")
    assert bp == (130.0, 85.0)

    # BP: 120/80
    bp2 = LanguageService.parse_vitals_reading_from_speech("BP", "My blood pressure reading is 120 over 80")
    assert bp2 == (120.0, 80.0)

    # SpO2
    spo2 = LanguageService.parse_vitals_reading_from_speech("SPO2", "Oxymeter madhe 97 dakhvat ahe")
    assert spo2 == (97.0, None)
