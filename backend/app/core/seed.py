from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.patient import Facility, Patient, Caregiver, Consent, CarePlan
from app.models.user import UserProfile
from app.models.clinical import MedicationSchedule, VitalsThreshold, VitalReading, SymptomCheckin, MedicationLog, LifestyleLog
from app.models.knowledge import KnowledgeArticle
from app.models.rules_alert import EscalationRule, Alert, AlertActionLog
from app.models.appointment import Appointment
from app.models.conversation import CallSession, CallTurn
from app.models.progress import DailyProgressScore
from app.core.security import hash_password

def seed_initial_data(db: Session):
    """
    Populates database with initial facility, clinician rules, approved clinical
    knowledge base articles, and sample patients with full care plans and history.
    """
    # 1. Facilities
    fac_stmt = select(Facility).where(Facility.id == "facility-apex-1")
    facility = db.execute(fac_stmt).scalars().first()
    if not facility:
        facility = Facility(
            id="facility-apex-1",
            name="Apex Memorial Hospital & Cardiac Care Centre",
            location="Pune / Mumbai, Maharashtra",
            contact_phone="+912026123456"
        )
        db.add(facility)

    fac2_stmt = select(Facility).where(Facility.id == "facility-metropolis-2")
    facility2 = db.execute(fac2_stmt).scalars().first()
    if not facility2:
        facility2 = Facility(
            id="facility-metropolis-2",
            name="Metropolis Heart & Vascular Institute",
            location="Pune, Maharashtra",
            contact_phone="+912025987654"
        )
        db.add(facility2)
    db.flush()

    # 1.1 Clinical Staff User Profiles (DB-05 Authentication)
    staff_users = [
        UserProfile(
            id="user-neha-101",
            email="dr.neha@apexcare.org",
            full_name="Dr. Neha Kulkarni",
            role="CLINICIAN",
            facility_id="facility-apex-1",
            password_hash=hash_password("Clinician123!"),
            is_active=True
        ),
        UserProfile(
            id="user-admin-1",
            email="admin@apexcare.org",
            full_name="Rajesh Sharma (Admin)",
            role="ADMIN",
            facility_id="facility-apex-1",
            password_hash=hash_password("Admin123!"),
            is_active=True
        ),
        UserProfile(
            id="user-patil-202",
            email="dr.patil@metropolis.org",
            full_name="Dr. Ramesh Patil",
            role="CLINICIAN",
            facility_id="facility-metropolis-2",
            password_hash=hash_password("Clinician123!"),
            is_active=True
        ),
        UserProfile(
            id="user-patient-1",
            email="patient.ramesh@apexcare.org",
            full_name="Ramesh Patil",
            role="PATIENT",
            facility_id="facility-apex-1",
            patient_id="patient-demo-1",
            password_hash=hash_password("Patient123!"),
            is_active=True
        )
    ]
    for su in staff_users:
        existing_su = db.execute(select(UserProfile).where(UserProfile.email == su.email)).scalars().first()
        if not existing_su:
            db.add(su)
    db.flush()

    # 2. Approved Knowledge Base Articles (KQ-01, KQ-04)
    articles = [
        KnowledgeArticle(
            article_code="WOUND-01",
            title="Surgical Wound Care and Dressing Instructions",
            category="WOUND_CARE",
            keywords=["wound", "dressing", "incision", "stitches", "bath", "water", "dressing change"],
            content_en="Keep your surgical dressing clean and dry for the first 5 days. You may take a sponge bath. If you notice any fluid discharge, increasing redness, or unpleasant smell, contact your care team immediately.",
            content_hi="सर्जरी के घाव की पट्टी को पहले 5 दिनों तक सूखा और साफ रखें। आप स्पंज बाथ ले सकते हैं। यदि घाव से पानी या मवाद बहता है या लालिमा बढ़ती है, तो तुरंत डॉक्टर को सूचित करें।",
            content_mr="शस्त्रक्रियेच्या जखमेची पट्टी पहिल्या ५ दिवसांपर्यंत कोरडी आणि स्वच्छ ठेवा. आपण स्पंज बाथ घेऊ शकता. जर जखमेतून पाणी किंवा पू येत असेल किंवा लालसरपणा वाढत असेल तर लगेच डॉक्टरांशी संपर्क साधा.",
            version="v1.0.0",
            is_approved=True
        ),
        KnowledgeArticle(
            article_code="ACTIVITY-01",
            title="Post-Discharge Walking & Physical Activity Guidelines",
            category="ACTIVITY",
            keywords=["walk", "walking", "steps", "stairs", "exercise", "lifting"],
            content_en="Start with gentle indoor walking for 10-15 minutes twice daily. Avoid lifting objects heavier than 5 kg. If you experience dizziness or shortness of breath, sit down immediately and rest.",
            content_hi="दिन में दो बार 10-15 मिनट के लिए घर के अंदर धीमी गति से टहलना शुरू करें। 5 किलोग्राम से अधिक भारी वजन न उठाएँ। यदि चक्कर आए या साँस फूले तो तुरंत बैठकर आराम करें।",
            content_mr="दिवसातून दोनदा १०-१५ मिनिटे घरातच हळू चालायला सुरुवात करा. ५ किलोपेक्षा जास्त वजन उचलू नका. चक्कर आल्यास किंवा धाप लागल्यास लगेच बसा आणि विश्रांती घ्या.",
            version="v1.0.0",
            is_approved=True
        ),
        KnowledgeArticle(
            article_code="DIET-01",
            title="Low-Sodium Heart-Healthy Diet Instructions",
            category="DIET_INFO",
            keywords=["salt", "sodium", "diet", "food", "oil", "spices"],
            content_en="Adhere strictly to your low-sodium diet as prescribed. Limit table salt to less than 1 teaspoon per day. Avoid canned soups, pickles, and processed snacks. Drink small sips of water throughout the day.",
            content_hi="डॉक्टर द्वारा बताई गई कम नमक वाली खुराक का सख्ती से पालन करें। प्रतिदिन एक छोटे चम्मच से कम नमक लें। अचार, पापड़ और डिब्बाबंद खाद्य पदार्थों से परहेज करें।",
            content_mr="डॉक्टरांनी सांगितलेल्या कमी मिठाच्या आहाराचे काटेकोरपणे पालन करा. दररोज १ चमच्यापेक्षा कमी मीठ वापरा. लोणचे, पापड आणि प्रक्रिया केलेले अन्न टाळा. दिवसभरात थोडे-थोडे पाणी प्या.",
            version="v1.0.0",
            is_approved=True
        )
    ]
    for art in articles:
        if not db.execute(select(KnowledgeArticle).where(KnowledgeArticle.article_code == art.article_code)).scalars().first():
            db.add(art)

    # 3. Clinician Escalation Rules (ES-01, ES-08)
    rules = [
        EscalationRule(
            code="RULE_SPO2_CRITICAL",
            name="Critical Oxygen Desaturation Alert",
            category="VITALS",
            severity="CRITICAL",
            condition_json={"metric": "SPO2", "operator": "<", "threshold": 88.0},
            action_json={"emergency_script": True, "notify_caregiver": True, "notify_care_team": True, "sla_minutes": 15}
        ),
        EscalationRule(
            code="RULE_BP_HYPERTENSIVE_CRISIS",
            name="Hypertensive Crisis Threshold",
            category="VITALS",
            severity="CRITICAL",
            condition_json={"metric": "BP_SYSTOLIC", "operator": ">", "threshold": 180.0},
            action_json={"emergency_script": True, "notify_caregiver": True, "notify_care_team": True, "sla_minutes": 15}
        ),
        EscalationRule(
            code="RULE_SYMPTOM_SUSTAINED_BREATHLESSNESS",
            name="Sustained Worsening Breathlessness Pattern",
            category="TREND",
            severity="HIGH",
            condition_json={"symptom": "breathlessness", "trend": "worsened", "consecutive_days": 2},
            action_json={"notify_care_team": True, "sla_minutes": 60}
        ),
        EscalationRule(
            code="RULE_MED_REPEATED_MISS",
            name="Repeated Medication Dose Non-Adherence",
            category="MEDICATION",
            severity="HIGH",
            condition_json={"consecutive_misses": 2},
            action_json={"notify_caregiver": True, "notify_care_team": True, "sla_minutes": 60}
        ),
        EscalationRule(
            code="RULE_COMPOSITE_DECLINE_REVIEW",
            name="Multi-Factor Clinical Pattern Decline",
            category="COMPOSITE_DECLINE",
            severity="HIGH",
            condition_json={"co_occurring_indicators": 2},
            action_json={"notify_care_team": True, "sla_minutes": 60}
        )
    ]
    for rule in rules:
        if not db.execute(select(EscalationRule).where(EscalationRule.code == rule.code)).scalars().first():
            db.add(rule)

    # 4. Sample Patient 1 (Mr. Ramesh Patil - Marathi/English)
    p1_stmt = select(Patient).where(Patient.id == "patient-demo-1")
    p1 = db.execute(p1_stmt).scalars().first()
    if not p1:
        p1 = Patient(
            id="patient-demo-1",
            facility_id="facility-apex-1",
            first_name="Ramesh",
            last_name="Patil",
            dob=date(1956, 4, 12),
            gender="Male",
            phone="+919820011223",
            email="ramesh.patil@example.com",
            address="Flat 402, Shivneri Heights, Pune",
            emergency_contact_phone="+919820099887",
            diagnosis="Post-Coronary Artery Bypass Graft (CABG)",
            discharge_date=date.today() - timedelta(days=5),
            programme_duration_days=30,
            preferred_language="mr",
            status="ACTIVE",
            call_window_start="09:00",
            call_window_end="19:00",
            checkin_morning_time="09:30",
            checkin_evening_time="18:30",
            dnd_start="21:00",
            dnd_end="08:00",
            retry_limit=3,
            max_deferrals=2,
            treating_doctor_name="Dr. V. Kulkarni",
            treating_doctor_phone="+919822000001",
            treating_doctor_specialty="Senior Cardiothoracic Surgeon"
        )
        db.add(p1)
        db.flush()

        cg1 = Caregiver(
            patient_id=p1.id,
            name="Sneha Patil (Daughter)",
            relationship="Daughter",
            phone="+919820099887",
            email="sneha.patil@example.com",
            is_authorized=True,
            consented_channels=["SMS", "WHATSAPP", "VOICE"],
            consented_categories=["medication", "vitals", "alerts", "appointments"]
        )
        db.add(cg1)

        c1 = Consent(
            patient_id=p1.id,
            voice_contact=True,
            call_recording=True,
            data_processing=True,
            caregiver_disclosure=True,
            emergency_escalation=True,
            consented_at=datetime.utcnow() - timedelta(days=5),
            consent_notes="Explicit written and audio consent recorded at discharge."
        )
        db.add(c1)

        cp1 = CarePlan(
            patient_id=p1.id,
            version=1,
            is_active=True,
            diet_instructions="Low-sodium cardiac diet. Restrict fluid to 1.8 liters per day.",
            hydration_target_glasses=8,
            hydration_interval_hours=2,
            activity_target_minutes=20,
            activity_target_steps=2000,
            physiotherapy_instructions="Deep breathing exercises 3 times daily with spirometer."
        )
        db.add(cp1)
        db.flush()

        med1 = MedicationSchedule(
            care_plan_id=cp1.id,
            patient_id=p1.id,
            medicine_name="Amlodipine Besylate",
            dosage="5mg",
            frequency="Once daily",
            dose_times=["09:00"],
            instructions="Take in morning after breakfast with water",
            route="Oral",
            effective_start_date=date.today() - timedelta(days=5),
            is_active=True
        )
        med2 = MedicationSchedule(
            care_plan_id=cp1.id,
            patient_id=p1.id,
            medicine_name="Metoprolol Succinate",
            dosage="25mg",
            frequency="Twice daily",
            dose_times=["09:00", "21:00"],
            instructions="Take with meals",
            route="Oral",
            effective_start_date=date.today() - timedelta(days=5),
            is_active=True
        )
        db.add_all([med1, med2])

        vt1 = VitalsThreshold(
            care_plan_id=cp1.id,
            patient_id=p1.id,
            vital_type="SPO2",
            unit="%",
            plausible_min=50.0,
            plausible_max=100.0,
            normal_min=94.0,
            normal_max=100.0,
            warning_min=90.0,
            warning_max=93.0,
            critical_min=88.0,
            critical_max=None
        )
        vt2 = VitalsThreshold(
            care_plan_id=cp1.id,
            patient_id=p1.id,
            vital_type="BP_SYSTOLIC",
            unit="mmHg",
            plausible_min=50.0,
            plausible_max=260.0,
            normal_min=100.0,
            normal_max=135.0,
            warning_min=136.0,
            warning_max=160.0,
            critical_min=85.0,
            critical_max=175.0
        )
        db.add_all([vt1, vt2])

        appt1 = Appointment(
            patient_id=p1.id,
            appointment_type="DOCTOR_FOLLOWUP",
            scheduled_time=datetime.utcnow() + timedelta(days=2, hours=3),
            doctor_facility_name="Dr. V. Kulkarni (Apex Memorial)",
            location="Room 304, OPD Building, Apex Memorial Hospital",
            preparation_instructions="Bring latest ECG report and daily BP chart. Fasting not required.",
            status="SCHEDULED"
        )
        db.add(appt1)

        reading1 = VitalReading(
            patient_id=p1.id,
            vital_type="SPO2",
            value=96.0,
            unit="%",
            status="NORMAL",
            voice_confirmed=True,
            recorded_at=datetime.utcnow() - timedelta(days=1)
        )
        reading2 = VitalReading(
            patient_id=p1.id,
            vital_type="BP_SYSTOLIC",
            value=128.0,
            secondary_value=82.0,
            unit="mmHg",
            status="NORMAL",
            voice_confirmed=True,
            recorded_at=datetime.utcnow() - timedelta(days=1)
        )
        db.add_all([reading1, reading2])

        score1 = DailyProgressScore(
            patient_id=p1.id,
            score_date=date.today() - timedelta(days=1),
            medication_score=100.0,
            checkin_score=90.0,
            hydration_score=85.0,
            activity_score=80.0,
            overall_score=91.0,
            is_declining=False,
            declining_indicators=[],
            calculation_breakdown={"weights": {"medication": 0.4, "symptoms": 0.25, "hydration": 0.15, "activity": 0.2}}
        )
        db.add(score1)

    # 5. Sample Patient 2 (Smt. Sunita Devi - Hindi)
    p2_stmt = select(Patient).where(Patient.id == "patient-demo-2")
    p2 = db.execute(p2_stmt).scalars().first()
    if not p2:
        p2 = Patient(
            id="patient-demo-2",
            facility_id="facility-apex-1",
            first_name="Sunita",
            last_name="Devi",
            dob=date(1962, 8, 20),
            gender="Female",
            phone="+919811223344",
            email="sunita.devi@example.com",
            address="Sector 14, Navi Mumbai",
            emergency_contact_phone="+919811229900",
            diagnosis="Total Knee Arthroplasty (Right Knee)",
            discharge_date=date.today() - timedelta(days=3),
            programme_duration_days=45,
            preferred_language="hi",
            status="ACTIVE",
            treating_doctor_name="Dr. Anil Deshmukh",
            treating_doctor_specialty="Senior Orthopaedic Surgeon"
        )
        db.add(p2)
        db.flush()

        cg2 = Caregiver(
            patient_id=p2.id,
            name="Amit Kumar (Son)",
            relationship="Son",
            phone="+919811229900",
            is_authorized=True,
            consented_channels=["SMS", "WHATSAPP"]
        )
        db.add(cg2)

        c2 = Consent(
            patient_id=p2.id,
            voice_contact=True,
            call_recording=True,
            data_processing=True,
            caregiver_disclosure=True,
            emergency_escalation=True,
            consented_at=datetime.utcnow() - timedelta(days=3)
        )
        db.add(c2)

        cp2 = CarePlan(
            patient_id=p2.id,
            version=1,
            is_active=True,
            diet_instructions="Diabetic renal diet, low sugar.",
            hydration_target_glasses=8,
            activity_target_minutes=15,
            physiotherapy_instructions="Quad sets and ankle pumps 10 reps each."
        )
        db.add(cp2)
        db.flush()

        alert2 = Alert(
            patient_id=p2.id,
            rule_code="RULE_SYMPTOM_WORSENING_PAIN",
            severity="HIGH",
            title="Worsening Surgical Knee Pain (Score: 7/10)",
            description="Patient reported knee pain increased from 4/10 to 7/10 with difficulty in physiotherapy quad sets.",
            supporting_data={"pain_level": 7, "symptom": "knee_pain", "trend": "worsened"},
            status="OPEN",
            sla_due_at=datetime.utcnow() + timedelta(minutes=45)
        )
        db.add(alert2)

    # 6. Cross-Facility Patient (Metropolis Facility for Multi-Tenancy Testing)
    p3_stmt = select(Patient).where(Patient.id == "patient-metro-201")
    p3 = db.execute(p3_stmt).scalars().first()
    if not p3:
        p3 = Patient(
            id="patient-metro-201",
            facility_id="facility-metropolis-2",
            first_name="Kishore",
            last_name="Kumar",
            dob=date(1968, 11, 5),
            gender="Male",
            phone="+919833445566",
            email="kishore.kumar@example.com",
            address="Kothrud, Pune",
            emergency_contact_phone="+919833440011",
            diagnosis="Post-Aortic Valve Replacement",
            discharge_date=date.today() - timedelta(days=2),
            programme_duration_days=30,
            preferred_language="en",
            status="ACTIVE",
            treating_doctor_name="Dr. Ramesh Patil",
            treating_doctor_specialty="Cardiologist"
        )
        db.add(p3)
        db.flush()

        c3 = Consent(
            patient_id=p3.id,
            voice_contact=True,
            call_recording=True,
            data_processing=True,
            caregiver_disclosure=True,
            emergency_escalation=True,
            consented_at=datetime.utcnow() - timedelta(days=2)
        )
        db.add(c3)

    db.commit()
