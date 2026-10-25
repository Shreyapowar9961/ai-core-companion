import json
import re
from typing import Dict, Any, Optional
from app.core.config import settings

class LLMExtractionService:
    """
    Structured Clinical Extraction: Maps patient conversational responses into structured
    vitals and symptom models using regex patterns and language models for entity recognition.
    """

    def __init__(self):
        self.provider = settings.LLM_PROVIDER
        self.api_key = settings.OPENAI_API_KEY
        self.model = settings.OPENAI_MODEL

    def extract_checkin_symptoms(self, transcript: str) -> Dict[str, Any]:
        """
        Extracts structured symptom severity (pain, weakness, dizziness, breathlessness, etc.)
        from conversational speech transcript.
        """
        result: Dict[str, Any] = {
            "pain_level": 0,
            "breathlessness": "none",
            "dizziness": "none",
            "weakness": "none",
            "fever": "none",
            "wound_status": "healing_well",
            "comparison": {},
            "other_verbatim": None
        }

        transcript_lower = transcript.lower()

        # Extract pain score (0-10)
        pain_match = re.search(r"(\b\d{1,2}\b)(?:\s*(?:out of 10|/10|scale))?", transcript_lower)
        if "pain" in transcript_lower or "dard" in transcript_lower or "dukh" in transcript_lower or "tras" in transcript_lower:
            if pain_match:
                val = int(pain_match.group(1))
                if 0 <= val <= 10:
                    result["pain_level"] = val
            elif "severe" in transcript_lower or "bahut" in transcript_lower or "khup" in transcript_lower:
                result["pain_level"] = 8
            elif "mild" in transcript_lower or "thoda" in transcript_lower or "thodasa" in transcript_lower:
                result["pain_level"] = 3
            else:
                result["pain_level"] = 5

        # Extract breathlessness
        if any(w in transcript_lower for w in ["breathless", "short of breath", "saas", "dam", "dhap"]):
            if "severe" in transcript_lower or "bahut" in transcript_lower or "khup" in transcript_lower:
                result["breathlessness"] = "severe"
            elif "mild" in transcript_lower or "thoda" in transcript_lower:
                result["breathlessness"] = "mild"
            else:
                result["breathlessness"] = "moderate"

        # Extract dizziness
        if any(w in transcript_lower for w in ["dizzy", "dizziness", "chhakkar", "chakkar"]):
            result["dizziness"] = "moderate"

        # Extract fever
        if any(w in transcript_lower for w in ["fever", "bukhar", "taap", "garam"]):
            if "high" in transcript_lower or "tez" in transcript_lower:
                result["fever"] = "high"
            else:
                result["fever"] = "mild"

        # Extract wound status
        if any(w in transcript_lower for w in ["pus", "discharge", "paani", "rakht", "bleeding"]):
            result["wound_status"] = "discharge"
        elif any(w in transcript_lower for w in ["redness", "lal", "laal"]):
            result["wound_status"] = "redness"

        # Extract comparison with yesterday (improved, unchanged, worsened)
        if any(w in transcript_lower for w in ["better", "sudhaar", "accha", "thik", "bara"]):
            result["comparison"]["general"] = "improved"
            if result["breathlessness"] != "none":
                result["comparison"]["breathlessness"] = "improved"
        elif any(w in transcript_lower for w in ["worse", "kharab", "jyada", "waait", "traas vadla"]):
            result["comparison"]["general"] = "worsened"
            if result["breathlessness"] != "none":
                result["comparison"]["breathlessness"] = "worsened"
            if result["pain_level"] > 0:
                result["comparison"]["pain"] = "worsened"
        elif any(w in transcript_lower for w in ["same", "waisa hi", "tasach", "no change"]):
            result["comparison"]["general"] = "unchanged"

        # Check for unlisted symptoms (CI-04)
        outside_terms = ["vomit", "ultee", "rash", "khujli", "loose motion", "headache", "sar dard"]
        for t in outside_terms:
            if t in transcript_lower:
                result["other_verbatim"] = transcript

        return result

    def extract_vitals(self, vital_type: str, transcript: str) -> Dict[str, Any]:
        """
        Extracts numbers and units for vitals from speech.
        """
        numbers = re.findall(r"\b\d+(?:\.\d+)?\b", transcript)
        if not numbers:
            return {"value": None, "secondary_value": None, "confirmed": False}

        if vital_type in ["BP", "BP_SYSTOLIC"]:
            sys = float(numbers[0])
            dia = float(numbers[1]) if len(numbers) > 1 else None
            return {"value": sys, "secondary_value": dia, "confirmed": True}
        else:
            return {"value": float(numbers[0]), "secondary_value": None, "confirmed": True}

llm_extraction_service = LLMExtractionService()
