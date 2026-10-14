from datetime import datetime, timezone

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class TekJuiceSiteOverride(Base):
    """Approved site changes from Tek Juice (connector site.changes): head
    metadata overrides and redirects for a site path, as JSON."""

    __tablename__ = "tekjuice_site_overrides"

    path: Mapped[str] = mapped_column(String(300), primary_key=True)
    data: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
