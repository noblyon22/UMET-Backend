from datetime import datetime, timezone
from sqlalchemy import DateTime, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.database.base import Base

class PublishedContent(Base):
    __tablename__ = "published_content"
    __table_args__ = (UniqueConstraint("page_slug", name="uq_published_content_slug"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    page_slug: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    hero_heading: Mapped[str | None] = mapped_column(Text, nullable=True)
    hero_subheading: Mapped[str | None] = mapped_column(Text, nullable=True)
    body_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta_keywords: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_document_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # GEO/AEO material from Tek Juice (summary, direct answer, FAQ, ...), JSON text.
    discovery: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
