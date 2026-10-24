from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class KnowledgeArticleCreate(BaseModel):
    article_code: str
    title: str
    category: str # WOUND_CARE, ACTIVITY, RECOVERY, DIET_INFO, DISCHARGE
    keywords: List[str] = []
    content_en: str
    content_hi: str
    content_mr: str
    version: str = "v1.0.0"
    approved_by: str = "Clinical Governance Committee"

class KnowledgeArticleResponse(BaseModel):
    id: str
    article_code: str
    title: str
    category: str
    keywords: List[str]
    content_en: str
    content_hi: str
    content_mr: str
    version: str
    is_approved: bool
    approved_by: str
    approved_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True

class KnowledgeQueryRequest(BaseModel):
    patient_id: Optional[str] = None
    query: str
    language: str = "en" # en, hi, mr
    call_session_id: Optional[str] = None

class KnowledgeQueryResponse(BaseModel):
    answered: bool
    answer: str
    article_code: Optional[str] = None
    article_version: Optional[str] = None
    routed_to: Optional[str] = None
    category: Optional[str] = None

class DeclinedQueryResponse(BaseModel):
    id: str
    patient_id: Optional[str] = None
    query_text: str
    query_type: str
    routed_to: str
    standard_response_delivered: Optional[str] = None
    logged_at: datetime

    class Config:
        from_attributes = True
