import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Boolean, DateTime, JSON, ForeignKey, Text
from app.core.database import Base

def gen_uuid():
    return str(uuid.uuid4())

class KnowledgeArticle(Base):
    __tablename__ = "knowledge_articles"
    
    id = Column(String(64), primary_key=True, default=gen_uuid)
    article_code = Column(String(64), unique=True, index=True)
    title = Column(String(255), nullable=False)
    # WOUND_CARE, ACTIVITY, RECOVERY, DIET_INFO, DISCHARGE (KQ-01)
    category = Column(String(64), nullable=False)
    keywords = Column(JSON, default=list)
    
    # Multilingual approved clinical documentation (LN-05, KQ-01)
    content_en = Column(Text, nullable=False)
    content_hi = Column(Text, nullable=False)
    content_mr = Column(Text, nullable=False)
    
    # Versioning & Clinical Governance (KQ-04)
    version = Column(String(32), default="v1.0.0", nullable=False)
    is_approved = Column(Boolean, default=True)
    approved_by = Column(String(128), default="Clinical Governance Committee")
    approved_at = Column(DateTime, default=datetime.utcnow)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class DeclinedQueryLog(Base):
    __tablename__ = "declined_query_logs"
    
    id = Column(String(64), primary_key=True, default=gen_uuid)
    patient_id = Column(String(64), ForeignKey("patients.id"), nullable=True, index=True)
    call_session_id = Column(String(64), ForeignKey("call_sessions.id"), nullable=True)
    
    query_text = Column(Text, nullable=False) # (KQ-05: Content-gap analysis)
    # DIAGNOSIS, DOSAGE, PROGNOSIS, UNKNOWN_TOPIC (KQ-02, KQ-03, MD-07)
    query_type = Column(String(64), nullable=False)
    routed_to = Column(String(128), default="CARE_TEAM_ESCALATION_QUEUE") # (KQ-03)
    standard_response_delivered = Column(Text, nullable=True)
    
    logged_at = Column(DateTime, default=datetime.utcnow, index=True)
