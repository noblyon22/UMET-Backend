import hmac
import hashlib
import os
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.models.content import PublishedContent

router = APIRouter(prefix="/api/engine", tags=["Data Engine"])

WEBHOOK_SECRET = os.getenv("DATA_ENGINE_WEBHOOK_SECRET", "")

def verify_signature(secret: str, body: bytes, signature: str) -> bool:
    if not secret:
        return True  # skip verification if no secret configured
    expected = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)

@router.post("/publish")
async def receive_published_content(request: Request, db: Session = Depends(get_db)):
    body = await request.body()
    signature = request.headers.get("X-Signature-256", "")

    if WEBHOOK_SECRET and not verify_signature(WEBHOOK_SECRET, body, signature):
        raise HTTPException(status_code=401, detail="Invalid signature")

    payload = await request.json()

    # Extract fields from Data Engine publish payload
    page_slug = payload.get("page_slug") or payload.get("url", "").rstrip("/").split("/")[-1] or "home"
    title = payload.get("title")
    hero_heading = payload.get("hero_heading") or payload.get("h1")
    hero_subheading = payload.get("hero_subheading") or payload.get("subtitle")
    body_content = payload.get("body_content") or payload.get("content")
    meta_description = payload.get("meta_description")
    meta_keywords = payload.get("meta_keywords")
    source_document_id = str(payload.get("document_id", ""))

    # Upsert — update if exists, insert if new
    existing = db.query(PublishedContent).filter_by(page_slug=page_slug).first()
    if existing:
        existing.title = title or existing.title
        existing.hero_heading = hero_heading or existing.hero_heading
        existing.hero_subheading = hero_subheading or existing.hero_subheading
        existing.body_content = body_content or existing.body_content
        existing.meta_description = meta_description or existing.meta_description
        existing.meta_keywords = meta_keywords or existing.meta_keywords
        existing.source_document_id = source_document_id or existing.source_document_id
    else:
        db.add(PublishedContent(
            page_slug=page_slug,
            title=title,
            hero_heading=hero_heading,
            hero_subheading=hero_subheading,
            body_content=body_content,
            meta_description=meta_description,
            meta_keywords=meta_keywords,
            source_document_id=source_document_id,
        ))

    db.commit()
    return {"status": "received", "page_slug": page_slug}

@router.get("/content/{page_slug}")
def get_published_content(page_slug: str, db: Session = Depends(get_db)):
    content = db.query(PublishedContent).filter_by(page_slug=page_slug).first()
    if not content:
        return {"page_slug": page_slug, "content": None}
    return {
        "page_slug": content.page_slug,
        "title": content.title,
        "hero_heading": content.hero_heading,
        "hero_subheading": content.hero_subheading,
        "body_content": content.body_content,
        "meta_description": content.meta_description,
        "meta_keywords": content.meta_keywords,
        "published_at": content.published_at.isoformat(),
    }

@router.get("/content")
def list_published_content(db: Session = Depends(get_db)):
    items = db.query(PublishedContent).order_by(PublishedContent.updated_at.desc()).all()
    return [{"page_slug": i.page_slug, "title": i.title, "published_at": i.published_at.isoformat()} for i in items]
