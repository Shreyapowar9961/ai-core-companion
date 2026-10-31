import re
import os
from typing import Dict, Any, List
from PIL import Image
import pytesseract
import pypdf

class PrescriptionOCRService:
    """
    Strictly ₹0 local prescription OCR and extraction engine.
    Uses local Tesseract OCR and PyPDF. Zero paid APIs or external network calls.
    """

    # Common cardiovascular and post-discharge medications dictionary
    MED_PATTERNS = [
        r"\b(Aspirin|Ecosprin)\b",
        r"\b(Atorvastatin|Atorva|Lipitor)\b",
        r"\b(Rosuvastatin|Rosuvas)\b",
        r"\b(Metoprolol|Betaloc|Metocard)\b",
        r"\b(Bisoprolol|Concor)\b",
        r"\b(Clopidogrel|Plavix|Clopivas)\b",
        r"\b(Ticagrelor|Brilinta)\b",
        r"\b(Ramipril|Cardace)\b",
        r"\b(Telmisartan|Telma)\b",
        r"\b(Furosemide|Lasix)\b",
        r"\b(Torsemide|Dytor)\b",
        r"\b(Amlodipine|Amlong)\b",
        r"\b(Pantoprazole|Pan-40|Pantocid)\b",
        r"\b(Omeprazole|Omez)\b",
        r"\b(Paracetamol|Dolo|Calpol)\b",
        r"\b(Augmentin|Amoxicillin)\b",
        r"\b(Cefixime|Taxim-O)\b",
        r"\b(Tramadol|Ultracet)\b"
    ]

    @classmethod
    def extract_text_from_file(cls, file_path: str, mime_type: str) -> str:
        """
        Extracts raw text from local image or PDF file.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Prescription file not found at {file_path}")

        extracted_text = ""
        try:
            if "pdf" in mime_type.lower() or file_path.lower().endswith(".pdf"):
                reader = pypdf.PdfReader(file_path)
                for page in reader.pages:
                    extracted_text += (page.extract_text() or "") + "\n"
                # If PDF is scanned image and has no text stream, attempt pytesseract on rendered pages if available
                if not extracted_text.strip():
                    extracted_text = "Scanned PDF document. Requires manual visual confirmation."
            else:
                # Image file: PNG, JPG, JPEG
                img = Image.open(file_path)
                extracted_text = pytesseract.image_to_string(img)
        except Exception as e:
            extracted_text = f"OCR process notice: {str(e)}"

        return extracted_text.strip()

    @classmethod
    def parse_prescription_text(cls, raw_text: str) -> List[Dict[str, Any]]:
        """
        Parses raw OCR text into structured draft medication objects.
        Marks all fields as UNVERIFIED pending clinician confirmation (Phase 4).
        """
        medications: List[Dict[str, Any]] = []
        if not raw_text:
            return medications

        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]

        for line in lines:
            # Check for recognized medication names
            matched_med = None
            for pat in cls.MED_PATTERNS:
                m = re.search(pat, line, re.IGNORECASE)
                if m:
                    matched_med = m.group(1).capitalize()
                    break

            # Or generic "Tab" / "Cap" line match
            if not matched_med:
                generic_m = re.search(r"\b(?:Tab|Cap|Tablet|Capsule|Inj)\.?\s+([A-Za-z0-9\-]+)", line, re.IGNORECASE)
                if generic_m:
                    matched_med = generic_m.group(1).capitalize()

            if matched_med:
                # Extract dosage
                dose_match = re.search(r"(\d+(?:\.\d+)?\s*(?:mg|mcg|g|ml|tablets?|caps?))", line, re.IGNORECASE)
                dosage = dose_match.group(1) if dose_match else "1 tablet"

                # Extract frequency
                freq = "Once daily"
                times = ["09:00"]
                if re.search(r"\b(?:BD|BID|Twice daily|1-0-1|1\s*-\s*0\s*-\s*1)\b", line, re.IGNORECASE):
                    freq = "Twice daily"
                    times = ["09:00", "20:00"]
                elif re.search(r"\b(?:TDS|TID|Thrice daily|1-1-1|1\s*-\s*1\s*-\s*1)\b", line, re.IGNORECASE):
                    freq = "Thrice daily"
                    times = ["09:00", "14:00", "20:00"]
                elif re.search(r"\b(?:HS|Night|Bedtime|0-0-1)\b", line, re.IGNORECASE):
                    freq = "Once daily at bedtime"
                    times = ["21:00"]
                elif re.search(r"\b(?:PRN|SOS|As needed)\b", line, re.IGNORECASE):
                    freq = "As needed (SOS)"
                    times = []

                # Extract timing / food instruction
                instructions = "Take after food with water"
                if re.search(r"\b(?:Before food|Empty stomach|AC)\b", line, re.IGNORECASE):
                    instructions = "Take 30 minutes before breakfast on an empty stomach"
                elif re.search(r"\b(?:Bedtime|Night)\b", line, re.IGNORECASE):
                    instructions = "Take after dinner before sleeping"

                # Extract duration
                duration_m = re.search(r"(\d+\s*(?:days?|weeks?|months?))", line, re.IGNORECASE)
                duration = duration_m.group(1) if duration_m else "30 days"

                medications.append({
                    "medicine_name": matched_med,
                    "dosage": dosage,
                    "frequency": freq,
                    "dose_times": times,
                    "instructions": instructions,
                    "duration": duration,
                    "route": "Oral",
                    "status": "UNVERIFIED", # Explicitly unverified until doctor approval
                    "needs_review": True
                })

        # Deduplicate by medicine name
        unique_meds = []
        seen = set()
        for med in medications:
            name_key = med["medicine_name"].lower()
            if name_key not in seen:
                seen.add(name_key)
                unique_meds.append(med)

        return unique_meds
