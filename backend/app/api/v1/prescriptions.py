import os
import uuid
import shutil
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import select, desc
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import get_current_user, AuthUser, UserRole, require_roles, verify_patient_access
from app.core.audit import log_audit_event, log_config_audit
from app.models.patient import Patient, CarePlan
from app.models.prescription import PrescriptionUpload
from app.models.clinical import MedicationSchedule
from app.services.ocr_service import PrescriptionOCRService

router = APIRouter(prefix="/prescriptions", tags=["Prescription OCR & Verification"])

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "uploads", "prescriptions")
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg"}
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024 # 10MB

class VerifiedMedicationItem(BaseModel):
    medicine_name: str
    dosage: str
    frequency: str = "Once daily"
    dose_times: List[str] = ["09:00"]
    instructions: Optional[str] = "Take after food with water"
    route: str = "Oral"
    duration: Optional[str] = "30 days"

class VerifyPrescriptionRequest(BaseModel):
    verified_medications: List[VerifiedMedicationItem]
    clinician_notes: Optional[str] = None

@router.post("/upload")
async def upload_prescription(
    patient_id: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_roles([UserRole.CLINICIAN, UserRole.ADMIN]))
):
    """
    Phase 4: Doctor uploads prescription (PDF or image).
    Applies free local OCR, extracts draft medication details, and holds for doctor verification.
    """
    patient = db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found.")
    verify_patient_access(patient_id, current_user, patient.facility_id)

    # 1. Validate file extension and MIME type
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format '{ext}'. Supported formats: PDF, PNG, JPG, JPEG."
        )

    # 2. Save securely to local non-public directory
    safe_filename = f"{uuid.uuid4().hex}{ext}"
    target_path = os.path.join(UPLOAD_DIR, safe_filename)

    with open(target_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    file_size = os.path.getsize(target_path)
    if file_size > MAX_FILE_SIZE_BYTES:
        os.remove(target_path)
        raise HTTPException(status_code=400, detail="File size exceeds maximum 10MB limit.")

    # 3. Perform Free Local OCR
    raw_ocr_text = PrescriptionOCRService.extract_text_from_file(target_path, file.content_type or "")
    extracted_meds = PrescriptionOCRService.parse_prescription_text(raw_ocr_text)

    # 4. Save to Database
    prescription = PrescriptionUpload(
        patient_id=patient_id,
        clinician_id=current_user.id,
        filename=file.filename,
        file_path=target_path,
        file_size=file_size,
        mime_type=file.content_type or "application/octet-stream",
        status="OCR_PROCESSED",
        raw_ocr_text=raw_ocr_text,
        extracted_medications=extracted_meds,
        created_at=datetime.utcnow()
    )
    db.add(prescription)
    db.commit()
    db.refresh(prescription)

    log_audit_event(
        db=db,
        event_type="PRESCRIPTION_UPLOADED_AND_OCR_EXTRACTED",
        actor_id=current_user.id,
        actor_role=current_user.role.value,
        resource="prescription_upload",
        details={
            "prescription_id": prescription.id,
            "filename": file.filename,
            "medications_found": len(extracted_meds)
        },
        patient_id=patient_id
    )

    return {
        "id": prescription.id,
        "patient_id": patient_id,
        "filename": prescription.filename,
        "status": prescription.status,
        "raw_ocr_text": prescription.raw_ocr_text,
        "extracted_medications": prescription.extracted_medications,
        "created_at": prescription.created_at.isoformat()
    }

@router.get("/patient/{patient_id}")
def list_prescriptions_for_patient(
    patient_id: str,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user)
):
    patient = db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found.")
    verify_patient_access(patient_id, current_user, patient.facility_id)

    prescriptions = db.execute(
        select(PrescriptionUpload).where(PrescriptionUpload.patient_id == patient_id)
        .order_by(desc(PrescriptionUpload.created_at))
    ).scalars().all()

    return [
        {
            "id": p.id,
            "filename": p.filename,
            "file_size": p.file_size,
            "status": p.status,
            "raw_ocr_text": p.raw_ocr_text,
            "extracted_medications": p.extracted_medications,
            "verified_medications": p.verified_medications,
            "clinician_notes": p.clinician_notes,
            "verified_by": p.verified_by,
            "verified_at": p.verified_at.isoformat() if p.verified_at else None,
            "created_at": p.created_at.isoformat()
        }
        for p in prescriptions
    ]

@router.get("/{prescription_id}/file")
def download_prescription_file(
    prescription_id: str,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user)
):
    """
    Secure file streaming endpoint. Zero public URLs (Phase 4 & 9).
    """
    p = db.get(PrescriptionUpload, prescription_id)
    if not p:
        raise HTTPException(status_code=404, detail="Prescription record not found.")

    patient = db.get(Patient, p.patient_id)
    verify_patient_access(p.patient_id, current_user, patient.facility_id if patient else None)

    if not os.path.exists(p.file_path):
        raise HTTPException(status_code=404, detail="File on disk not found.")

    return FileResponse(
        path=p.file_path,
        media_type=p.mime_type,
        filename=p.filename
    )

@router.post("/{prescription_id}/verify")
def verify_and_approve_prescription(
    prescription_id: str,
    req: VerifyPrescriptionRequest,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_roles([UserRole.CLINICIAN, UserRole.ADMIN]))
):
    """
    Phase 4: Mandatory doctor verification step.
    Doctor approves corrected medication details, which activates MedicationSchedule.
    """
    p = db.get(PrescriptionUpload, prescription_id)
    if not p:
        raise HTTPException(status_code=404, detail="Prescription record not found.")

    patient = db.get(Patient, p.patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found.")
    verify_patient_access(p.patient_id, current_user, patient.facility_id)

    # 1. Update PrescriptionUpload status
    p.status = "VERIFIED"
    p.verified_medications = [m.dict() for m in req.verified_medications]
    p.clinician_notes = req.clinician_notes
    p.verified_by = current_user.name
    p.verified_at = datetime.utcnow()

    # 2. Find or create CarePlan
    care_plan = db.execute(
        select(CarePlan).where(CarePlan.patient_id == p.patient_id, CarePlan.is_active == True)
    ).scalars().first()
    if not care_plan:
        care_plan = CarePlan(
            patient_id=p.patient_id,
            version=1,
            is_active=True
        )
        db.add(care_plan)
        db.flush()

    # 3. Create active MedicationSchedule records from approved details
    created_schedules = []
    for med in req.verified_medications:
        ms = MedicationSchedule(
            care_plan_id=care_plan.id,
            patient_id=p.patient_id,
            medicine_name=med.medicine_name,
            dosage=med.dosage,
            frequency=med.frequency,
            dose_times=med.dose_times,
            instructions=med.instructions,
            route=med.route,
            effective_start_date=date.today(),
            is_active=True
        )
        db.add(ms)
        created_schedules.append(ms)

    db.commit()

    log_audit_event(
        db=db,
        event_type="PRESCRIPTION_VERIFIED_AND_MEDICATIONS_SCHEDULED",
        actor_id=current_user.id,
        actor_role=current_user.role.value,
        resource="prescription_upload",
        details={
            "prescription_id": p.id,
            "scheduled_count": len(created_schedules),
            "doctor": current_user.name
        },
        patient_id=p.patient_id
    )

    return {
        "message": f"Prescription approved. {len(created_schedules)} active medication schedules generated.",
        "prescription_id": p.id,
        "status": "VERIFIED",
        "verified_at": p.verified_at.isoformat(),
        "schedules_created": len(created_schedules)
    }
