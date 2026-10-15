from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, exists, not_
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.content import PublishedContent
from app.models.tekjuice_publication import TekJuicePublication

router = APIRouter(prefix="/api/content", tags=["Published Content"])

# A Tek Juice article whose publications are all withdrawn is no longer on the
# site. Content Tek Juice never published (UMET's own pages) is unaffected.
_withdrawn = and_(
    exists().where(TekJuicePublication.resource_id == PublishedContent.id),
    not_(exists().where(and_(TekJuicePublication.resource_id == PublishedContent.id,
                             TekJuicePublication.status == "published"))),
)

@router.get("/{page_slug}")
def get_published_content(
    page_slug: str,
    db: Session = Depends(get_db),
):
    content = (
        db.query(PublishedContent)
        .filter(PublishedContent.page_slug == page_slug, not_(_withdrawn))
        .first()
    )

    if content is None:
        raise HTTPException(status_code=404, detail="Published content not found")

    return {
        "page_slug": content.page_slug,
        "title": content.title,
        "hero_heading": content.hero_heading,
        "hero_subheading": content.hero_subheading,
        "body_content": content.body_content,
        "meta_description": content.meta_description,
        "meta_keywords": content.meta_keywords,
        "published_at": content.published_at,
        "updated_at": content.updated_at,
    }

@router.get("")
def list_published_content(
    db: Session = Depends(get_db),
):
    contents = (
        db.query(PublishedContent)
        .filter(not_(_withdrawn))
        .order_by(PublishedContent.published_at.desc())
        .all()
    )

    return [
        {
            "page_slug": content.page_slug,
            "title": content.title,
            "hero_heading": content.hero_heading,
            "hero_subheading": content.hero_subheading,
            "meta_description": content.meta_description,
            "published_at": content.published_at,
            "updated_at": content.updated_at,
        }
        for content in contents
    ]
