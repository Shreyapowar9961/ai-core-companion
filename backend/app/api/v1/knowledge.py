from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select, or_
from typing import List
from datetime import datetime

from app.core.database import get_db
from app.core.security import get_current_user, AuthUser, UserRole, require_roles
from app.models.knowledge import KnowledgeArticle, DeclinedQueryLog
from app.schemas.knowledge import (
    KnowledgeArticleCreate, KnowledgeArticleResponse,
    KnowledgeQueryRequest, KnowledgeQueryResponse, DeclinedQueryResponse
)
from app.core.audit import log_audit_event, log_config_audit

router = APIRouter(prefix="/knowledge", tags=["Approved Knowledge & Guardrails"])

@router.post("/articles", response_model=KnowledgeArticleResponse, status_code=status.HTTP_201_CREATED)
def create_approved_article(
    req: KnowledgeArticleCreate,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_roles([UserRole.CLINICIAN, UserRole.ADMIN]))
):
    article = KnowledgeArticle(
        article_code=req.article_code,
        title=req.title,
        category=req.category,
        keywords=req.keywords,
        content_en=req.content_en,
        content_hi=req.content_hi,
        content_mr=req.content_mr,
        version=req.version,
        is_approved=True,
        approved_by=req.approved_by,
        approved_at=datetime.utcnow()
    )
    db.add(article)
    db.commit()
    db.refresh(article)

    log_config_audit(
        db=db,
        config_type="CONTENT",
        item_id=article.id,
        changed_by=current_user.id,
        new_value={"code": article.article_code, "version": article.version, "title": article.title},
        change_reason="Approved clinical documentation added"
    )

    return article

@router.get("/articles", response_model=List[KnowledgeArticleResponse])
def list_approved_articles(
    category: str = None,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user)
):
    stmt = select(KnowledgeArticle).where(KnowledgeArticle.is_approved == True)
    if category:
        stmt = stmt.where(KnowledgeArticle.category == category)
    return db.execute(stmt).scalars().all()

@router.post("/query", response_model=KnowledgeQueryResponse)
def query_knowledge_base(
    req: KnowledgeQueryRequest,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user)
):
    query_lower = req.query.lower()

    # 1. Guardrail: Route Diagnosis / Prognosis / Dosage (KQ-03, MD-07)
    clinical_decision_terms = [
        "what is my diagnosis", "will i survive", "prognosis", "cure me", "is it cancer",
        "change dosage", "stop medication", "can i take double", "what dose", "prescribe"
    ]
    if any(term in query_lower for term in clinical_decision_terms):
        q_type = "DOSAGE" if ("dose" in query_lower or "medication" in query_lower) else "DIAGNOSIS"
        declined_entry = DeclinedQueryLog(
            patient_id=req.patient_id,
            call_session_id=req.call_session_id,
            query_text=req.query,
            query_type=q_type,
            routed_to="TREATING_DOCTOR",
            standard_response_delivered="I cannot make clinical diagnoses or suggest dosage changes. I have routed your query to your doctor."
        )
        db.add(declined_entry)
        db.commit()

        if req.language == "hi":
            msg = "मैं चिकित्सा निदान या दवा की खुराक में बदलाव पर सलाह नहीं दे सकता। मैंने यह प्रश्न आपके डॉक्टर को भेज दिया है।"
        elif req.language == "mr":
            msg = "मी वैद्यकीय निदान किंवा औषधांच्या प्रमाणात बदल करण्याचा सल्ला देऊ शकत नाही. मी हा प्रश्न तुमच्या डॉक्टरांकडे पाठवला आहे."
        else:
            msg = "I cannot determine diagnoses or suggest medication changes. I have routed your query to your clinician."

        return KnowledgeQueryResponse(
            answered=False,
            answer=msg,
            routed_to="TREATING_DOCTOR"
        )

    # 2. Search approved content library (KQ-01, KQ-04)
    stmt = select(KnowledgeArticle).where(KnowledgeArticle.is_approved == True)
    articles = db.execute(stmt).scalars().all()

    matched_article: KnowledgeArticle = None
    for art in articles:
        if any(kw.lower() in query_lower for kw in art.keywords) or art.title.lower() in query_lower:
            matched_article = art
            break

    if matched_article:
        if req.language == "hi":
            answer = matched_article.content_hi
        elif req.language == "mr":
            answer = matched_article.content_mr
        else:
            answer = matched_article.content_en

        return KnowledgeQueryResponse(
            answered=True,
            answer=answer,
            article_code=matched_article.article_code,
            article_version=matched_article.version,
            category=matched_article.category
        )

    # 3. Not in approved documentation: State plainly unavailable, GENERATE NOTHING (KQ-02, KQ-05)
    declined_entry = DeclinedQueryLog(
        patient_id=req.patient_id,
        call_session_id=req.call_session_id,
        query_text=req.query,
        query_type="UNKNOWN_TOPIC",
        routed_to="CARE_TEAM_INBOX",
        standard_response_delivered="Information not available in approved documentation. Offered routing to care team."
    )
    db.add(declined_entry)
    db.commit()

    if req.language == "hi":
        unavail_msg = "यह जानकारी वर्तमान अनुमोदित दिशानिर्देशों में उपलब्ध नहीं है। क्या आप चाहते हैं कि मैं आपकी केयर टीम से संपर्क करूँ?"
    elif req.language == "mr":
        unavail_msg = "ही माहिती सध्याच्या मान्यताप्राप्त वैद्यकीय माहितीत उपलब्ध नाही. आपण डॉक्टरांच्या टीमशी संपर्क साधू इच्छिता का?"
    else:
        unavail_msg = "That information is not available in your approved discharge plan. Would you like me to connect you with your care team?"

    return KnowledgeQueryResponse(
        answered=False,
        answer=unavail_msg,
        routed_to="CARE_TEAM_INBOX"
    )

@router.get("/declined-queries", response_model=List[DeclinedQueryResponse])
def list_declined_queries(
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_roles([UserRole.CLINICIAN, UserRole.ADMIN]))
):
    stmt = select(DeclinedQueryLog).order_by(DeclinedQueryLog.logged_at.desc()).limit(100)
    return db.execute(stmt).scalars().all()
