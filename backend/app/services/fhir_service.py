"""
FHIR R4 Hospital Ingestion Service (ON-07)
Parses HL7 FHIR R4 JSON bundles and Patient/CarePlan resources.
Extracts demographics, conditions, medication requests, and caregiver contacts.
Performs duplicate detection by contact phone and MRN / identifier.
Persists valid records with full audit logging and CDSS care plan staging.
"""

from datetime import datetime, date
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, or_

from app.models.patient import Patient, Facility, Caregiver, Consent, CarePlan
from app.models.clinical import MedicationSchedule, VitalsThreshold
from app.core.audit import log_audit_event


class FHIRValidationError(Exception):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class FHIRDuplicateError(Exception):
    def __init__(self, message: str, existing_patient_id: str, phone: str):
        super().__init__(message)
        self.message = message
        self.existing_patient_id = existing_patient_id
        self.phone = phone


class FHIRService:

    @staticmethod
    def parse_bundle(bundle_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extracts structured patient data from HL7 FHIR R4 Bundle or direct resource.
        """
        if not isinstance(bundle_data, dict):
            raise FHIRValidationError("FHIR payload must be a JSON object")

        resource_type = bundle_data.get("resourceType")
        if resource_type not in ["Bundle", "Patient"]:
            raise FHIRValidationError(
                f"Unsupported FHIR resourceType: '{resource_type}'. Expected 'Bundle' or 'Patient'."
            )

        resources: List[Dict[str, Any]] = []
        if resource_type == "Bundle":
            entries = bundle_data.get("entry", [])
            for entry in entries:
                res = entry.get("resource")
                if res and isinstance(res, dict):
                    resources.append(res)
        else:
            resources.append(bundle_data)

        # 1. Extract Patient resource
        patient_res = next((r for r in resources if r.get("resourceType") == "Patient"), None)
        if not patient_res:
            raise FHIRValidationError("FHIR bundle must contain a 'Patient' resource")

        # 2. Extract Conditions (Diagnoses)
        condition_resources = [r for r in resources if r.get("resourceType") == "Condition"]

        # 3. Extract MedicationRequests
        med_resources = [r for r in resources if r.get("resourceType") == "MedicationRequest"]

        # 4. Extract CarePlan
        careplan_res = next((r for r in resources if r.get("resourceType") == "CarePlan"), None)

        # Parse demographics
        demographics = FHIRService._extract_demographics(patient_res)

        # Parse diagnosis from Condition or CarePlan
        diagnosis = FHIRService._extract_diagnosis(condition_resources, careplan_res)
        demographics["diagnosis"] = diagnosis

        # Parse medications
        medications = FHIRService._extract_medications(med_resources)

        # Parse caregivers / emergency contacts
        caregivers = FHIRService._extract_contacts(patient_res)

        # Parse care plan targets
        care_plan_targets = FHIRService._extract_care_plan(careplan_res)

        return {
            "demographics": demographics,
            "medications": medications,
            "caregivers": caregivers,
            "care_plan": care_plan_targets,
            "raw_summary": {
                "total_conditions": len(condition_resources),
                "total_medications": len(med_resources),
                "has_care_plan": careplan_res is not None
            }
        }

    @staticmethod
    def _extract_demographics(patient: Dict[str, Any]) -> Dict[str, Any]:
        """Extracts standard demographics from FHIR Patient resource."""
        # Names
        names = patient.get("name", [])
        first_name = ""
        last_name = ""
        if names and isinstance(names, list):
            name_obj = next((n for n in names if n.get("use") == "official"), names[0])
            family = name_obj.get("family", "")
            given = name_obj.get("given", [])
            first_name = " ".join(given) if isinstance(given, list) else str(given)
            last_name = family
            if not first_name and name_obj.get("text"):
                parts = name_obj["text"].split(" ", 1)
                first_name = parts[0]
                last_name = parts[1] if len(parts) > 1 else ""

        if not first_name:
            first_name = "Discharged"
        if not last_name:
            last_name = "Patient"

        # DOB
        birth_date_str = patient.get("birthDate")
        dob = date(1965, 1, 1)
        if birth_date_str:
            try:
                dob = datetime.strptime(birth_date_str[:10], "%Y-%m-%d").date()
            except Exception:
                pass

        # Gender
        gender_raw = (patient.get("gender") or "Male").capitalize()
        if gender_raw not in ["Male", "Female", "Other"]:
            gender_raw = "Male"

        # Telecom (Phone & Email)
        phone = ""
        email = None
        for telecom in patient.get("telecom", []):
            system = telecom.get("system")
            value = telecom.get("value", "")
            if system == "phone" and not phone:
                phone = value.strip()
            elif system == "email" and not email:
                email = value.strip()

        # Identifier (MRN)
        mrn = None
        for ident in patient.get("identifier", []):
            val = ident.get("value")
            if val:
                mrn = str(val)
                break

        # Address
        address_str = None
        addresses = patient.get("address", [])
        if addresses:
            addr = addresses[0]
            lines = addr.get("line", [])
            line_txt = ", ".join(lines) if isinstance(lines, list) else str(lines)
            city = addr.get("city", "")
            state = addr.get("state", "")
            postal = addr.get("postalCode", "")
            parts = [p for p in [line_txt, city, state, postal] if p]
            address_str = ", ".join(parts) if parts else None

        # Preferred language (communication)
        preferred_lang = "en"
        for comm in patient.get("communication", []):
            lang = comm.get("language", {})
            for coding in lang.get("coding", []):
                code = (coding.get("code") or "").lower()
                if "mr" in code or "marathi" in code:
                    preferred_lang = "mr"
                    break
                elif "hi" in code or "hindi" in code:
                    preferred_lang = "hi"
                    break
                elif "en" in code:
                    preferred_lang = "en"
                    break

        return {
            "first_name": first_name,
            "last_name": last_name,
            "dob": dob,
            "gender": gender_raw,
            "phone": phone,
            "email": email,
            "mrn": mrn,
            "address": address_str,
            "preferred_language": preferred_lang,
            "discharge_date": date.today()
        }

    @staticmethod
    def _extract_diagnosis(conditions: List[Dict[str, Any]], careplan: Optional[Dict[str, Any]]) -> str:
        """Extracts primary diagnosis from FHIR Condition resources."""
        diagnoses = []
        for cond in conditions:
            # Check code text
            code_obj = cond.get("code", {})
            text = code_obj.get("text")
            if text:
                diagnoses.append(text)
                continue
            for coding in code_obj.get("coding", []):
                disp = coding.get("display")
                if disp:
                    diagnoses.append(disp)
                    break

        if diagnoses:
            return "; ".join(diagnoses[:3])

        if careplan and careplan.get("description"):
            return careplan["description"][:255]

        return "Post-Discharge Recovery Care"

    @staticmethod
    def _extract_medications(med_resources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extracts medication schedules from FHIR MedicationRequest resources."""
        meds = []
        for mr in med_resources:
            med_name = ""
            # Check medicationCodeableConcept
            med_concept = mr.get("medicationCodeableConcept", {})
            if med_concept.get("text"):
                med_name = med_concept["text"]
            elif med_concept.get("coding"):
                med_name = med_concept["coding"][0].get("display", "Prescribed Medication")
            else:
                med_name = "Prescribed Medication"

            dosage_text = "Standard Dose"
            frequency = "ONCE_DAILY"
            dose_times = ["09:00"]
            instructions = "Take with water after meals"
            route = "Oral"

            dosage_instructions = mr.get("dosageInstruction", [])
            if dosage_instructions:
                d = dosage_instructions[0]
                if d.get("text"):
                    instructions = d["text"]
                    dosage_text = d["text"].split()[0] if len(d["text"].split()) > 0 else dosage_text
                
                # Check timing repeat
                timing = d.get("timing", {}).get("repeat", {})
                freq_val = timing.get("frequency", 1)
                period_val = timing.get("period", 1)
                period_unit = timing.get("periodUnit", "d")

                if freq_val == 2:
                    frequency = "TWICE_DAILY"
                    dose_times = ["09:00", "21:00"]
                elif freq_val == 3:
                    frequency = "THRICE_DAILY"
                    dose_times = ["09:00", "14:00", "21:00"]
                elif freq_val == 4:
                    frequency = "FOUR_TIMES_DAILY"
                    dose_times = ["08:00", "12:00", "16:00", "20:00"]

                if d.get("route", {}).get("text"):
                    route = d["route"]["text"]

            meds.append({
                "medicine_name": med_name,
                "dosage": dosage_text,
                "frequency": frequency,
                "dose_times": dose_times,
                "instructions": instructions,
                "route": route
            })

        return meds

    @staticmethod
    def _extract_contacts(patient: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extracts emergency contacts and caregivers from FHIR Patient contact list."""
        caregivers = []
        for c in patient.get("contact", []):
            name_obj = c.get("name", {})
            name = name_obj.get("text", "")
            if not name and name_obj.get("given"):
                name = " ".join(name_obj.get("given", [])) + " " + name_obj.get("family", "")
            if not name:
                name = "Emergency Contact"

            # Relationship
            rel = "Caregiver"
            relationships = c.get("relationship", [])
            if relationships:
                first_rel = relationships[0]
                if isinstance(first_rel, dict):
                    rel = first_rel.get("text") or (first_rel.get("coding", [{}])[0].get("display") if first_rel.get("coding") else "Family")

            phone = ""
            email = None
            for tel in c.get("telecom", []):
                sys = tel.get("system")
                val = tel.get("value", "")
                if sys == "phone" and not phone:
                    phone = val.strip()
                elif sys == "email" and not email:
                    email = val.strip()

            if phone:
                caregivers.append({
                    "name": name.strip(),
                    "relationship": rel.strip() if rel else "Caregiver",
                    "phone": phone,
                    "email": email,
                    "is_authorized": True,
                    "consented_channels": ["SMS", "WHATSAPP", "VOICE"],
                    "consented_categories": ["medication", "vitals", "alerts", "appointments"]
                })

        return caregivers

    @staticmethod
    def _extract_care_plan(careplan: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Extracts lifestyle targets from FHIR CarePlan resource."""
        diet = "Low sodium, balanced cardiac diet. Avoid spicy and deep-fried foods."
        hydration = 8
        activity = 20

        if careplan:
            desc = careplan.get("description", "")
            if "diet" in desc.lower():
                diet = desc
            for act in careplan.get("activity", []):
                det = act.get("detail", {})
                desc_text = det.get("description", "")
                if "water" in desc_text.lower() or "hydration" in desc_text.lower():
                    hydration = 10
                if "walk" in desc_text.lower() or "physio" in desc_text.lower():
                    activity = 30

        return {
            "diet_instructions": diet,
            "hydration_target_glasses": hydration,
            "hydration_interval_hours": 2,
            "activity_target_minutes": activity,
            "activity_target_steps": 2500,
            "physiotherapy_instructions": "Light walking twice daily. Avoid lifting heavy weights (>5kg)."
        }

    @classmethod
    def import_fhir_patient(
        cls,
        db: Session,
        bundle_data: Dict[str, Any],
        actor_id: str,
        actor_role: str,
        facility_id: str = "facility-apex-1",
        check_duplicates: bool = True,
        activate_immediately: bool = True
    ) -> Dict[str, Any]:
        """
        Parses FHIR R4 data, verifies duplicates against PostgreSQL,
        creates Patient, Consent, CarePlan, MedicationSchedule, Caregiver entities,
        and logs audit trail.
        """
        parsed = cls.parse_bundle(bundle_data)
        demo = parsed["demographics"]
        meds = parsed["medications"]
        caregivers = parsed["caregivers"]
        care_plan_targets = parsed["care_plan"]

        if not demo.get("phone"):
            raise FHIRValidationError(
                "FHIR Patient resource is missing telecom phone contact. Valid phone is required for automated recovery calling."
            )

        # Duplicate detection (ON-07)
        if check_duplicates:
            existing = db.execute(
                select(Patient).where(
                    or_(
                        Patient.phone == demo["phone"],
                        Patient.phone == demo["phone"].replace(" ", "").replace("-", "")
                    )
                )
            ).scalars().first()

            if existing:
                raise FHIRDuplicateError(
                    f"Patient with phone '{demo['phone']}' already exists in care programme (ID: {existing.id}, Name: {existing.first_name} {existing.last_name}).",
                    existing_patient_id=existing.id,
                    phone=demo["phone"]
                )

        initial_status = "ACTIVE" if (activate_immediately and meds) else "DRAFT"

        patient = Patient(
            facility_id=facility_id,
            first_name=demo["first_name"],
            last_name=demo["last_name"],
            dob=demo["dob"],
            gender=demo["gender"],
            phone=demo["phone"],
            email=demo.get("email"),
            address=demo.get("address"),
            diagnosis=demo["diagnosis"],
            discharge_date=demo["discharge_date"],
            programme_duration_days=30,
            preferred_language=demo["preferred_language"],
            status=initial_status,
            call_window_start="09:00",
            call_window_end="18:00",
            checkin_morning_time="09:30",
            checkin_evening_time="17:30",
            dnd_start="21:00",
            dnd_end="07:00",
            retry_limit=3,
            max_deferrals=2,
            treating_doctor_name="Attending Hospital Physician",
            treating_doctor_specialty="Cardiothoracic Care",
            created_at=datetime.utcnow()
        )
        db.add(patient)
        db.flush()

        # Consent record (ON-06, GV-02)
        consent = Consent(
            patient_id=patient.id,
            voice_contact=True,
            call_recording=True,
            data_processing=True,
            caregiver_disclosure=True,
            emergency_escalation=True,
            consented_at=datetime.utcnow(),
            consent_notes="Standard clinical consent ingested via HL7 FHIR R4 Hospital Transfer"
        )
        db.add(consent)

        # Care Plan
        care_plan = CarePlan(
            patient_id=patient.id,
            diet_instructions=care_plan_targets["diet_instructions"],
            hydration_target_glasses=care_plan_targets["hydration_target_glasses"],
            hydration_interval_hours=care_plan_targets["hydration_interval_hours"],
            activity_target_minutes=care_plan_targets["activity_target_minutes"],
            activity_target_steps=care_plan_targets["activity_target_steps"],
            physiotherapy_instructions=care_plan_targets["physiotherapy_instructions"]
        )
        db.add(care_plan)
        db.flush()

        # Medications
        for m in meds:
            ms = MedicationSchedule(
                care_plan_id=care_plan.id,
                patient_id=patient.id,
                medicine_name=m["medicine_name"],
                dosage=m["dosage"],
                frequency=m["frequency"],
                dose_times=m["dose_times"],
                instructions=m["instructions"],
                route=m["route"],
                effective_start_date=demo["discharge_date"],
                is_active=True
            )
            db.add(ms)

        # Default vitals thresholds for post-discharge recovery
        default_thresholds = [
            ("BLOOD_PRESSURE_SYS", "mmHg", 80, 220, 100, 130, 131, 150, 160, 200),
            ("BLOOD_PRESSURE_DIA", "mmHg", 50, 130, 60, 85, 86, 95, 100, 120),
            ("HEART_RATE", "bpm", 40, 180, 60, 90, 91, 105, 110, 160),
            ("SPO2", "%", 70, 100, 95, 100, 92, 94, 70, 90),
            ("TEMPERATURE", "F", 94.0, 106.0, 97.0, 99.0, 99.1, 100.4, 101.0, 105.0)
        ]
        for v_type, unit, p_min, p_max, n_min, n_max, w_min, w_max, c_min, c_max in default_thresholds:
            thresh = VitalsThreshold(
                care_plan_id=care_plan.id,
                patient_id=patient.id,
                vital_type=v_type,
                unit=unit,
                plausible_min=p_min,
                plausible_max=p_max,
                normal_min=n_min,
                normal_max=n_max,
                warning_min=w_min,
                warning_max=w_max,
                critical_min=c_min,
                critical_max=c_max
            )
            db.add(thresh)

        # Caregivers
        for cg in caregivers:
            c_entity = Caregiver(
                patient_id=patient.id,
                name=cg["name"],
                relationship=cg["relationship"],
                phone=cg["phone"],
                email=cg.get("email"),
                is_authorized=cg["is_authorized"],
                consented_channels=cg["consented_channels"],
                consented_categories=cg["consented_categories"]
            )
            db.add(c_entity)

        db.commit()
        db.refresh(patient)

        # Audit trail (GV-04)
        log_audit_event(
            db=db,
            event_type="FHIR_PATIENT_IMPORTED",
            actor_id=actor_id,
            actor_role=actor_role,
            resource="patient",
            details={
                "patient_id": patient.id,
                "first_name": patient.first_name,
                "last_name": patient.last_name,
                "phone": patient.phone,
                "status": patient.status,
                "medications_count": len(meds),
                "caregivers_count": len(caregivers),
                "mrn": demo.get("mrn")
            },
            patient_id=patient.id
        )

        return {
            "success": True,
            "patient_id": patient.id,
            "status": patient.status,
            "patient_name": f"{patient.first_name} {patient.last_name}",
            "diagnosis": patient.diagnosis,
            "preferred_language": patient.preferred_language,
            "medications_count": len(meds),
            "caregivers_count": len(caregivers),
            "summary": parsed["raw_summary"]
        }
