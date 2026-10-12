"""Tek Juice S2S publication receiver for UMET.

Mounts the ``tekjuice-connector`` publication receiver over UMET's existing
content model:

- ``PublishedContent`` holds the page (``page_slug`` is the content identity).
- ``TekJuicePublication`` is the ledger that ties each page to the Tek Juice
  execution and idempotency key that last wrote it. Pages without a published
  ledger entry are not managed by Tek Juice and are never overwritten.

Content and ledger are written in one transaction, so a redelivered request is
recognised by its idempotency key and replayed instead of written twice.
"""

from __future__ import annotations

import logging
import threading
from datetime import datetime, timezone
from typing import Callable, Optional

from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from app.models.content import PublishedContent
from app.models.tekjuice_publication import TekJuicePublication
from tekjuice_connector.publication import (
    ContentStoreError,
    DuplicateSlugError,
    PublicationContent,
    PublicationReceiver,
    StoredContent,
)

logger = logging.getLogger(__name__)

S2S_PUBLISH_PATH = "/api/integrations/tekjuice/s2s/publish"


class UMETContentStore:
    """``ContentStore`` over UMET's PublishedContent + TekJuicePublication."""

    def __init__(
        self,
        session_factory: Callable[[], Session],
        *,
        public_base_url: str,
        website_id: str,
    ) -> None:
        self._session_factory = session_factory
        self._base = public_base_url.rstrip("/")
        self._website_id = website_id

    # ── Lookups ──────────────────────────────────────────────────────────

    def public_url(self, slug: str) -> str:
        return f"{self._base}/{slug.strip('/')}"

    def _stored(self, content: PublishedContent, ledger: TekJuicePublication) -> StoredContent:
        return StoredContent(
            resource_id=str(content.id),
            slug=content.page_slug,
            execution_id=ledger.execution_id,
            idempotency_key=ledger.idempotency_key,
            content_hash=ledger.content_hash or "",
            published_url=ledger.published_url or self.public_url(content.page_slug),
        )

    @staticmethod
    def _latest_ledger(db: Session, resource_id: int) -> Optional[TekJuicePublication]:
        return (
            db.query(TekJuicePublication)
            .filter(
                TekJuicePublication.resource_id == resource_id,
                TekJuicePublication.status == "published",
            )
            .order_by(TekJuicePublication.updated_at.desc(), TekJuicePublication.id.desc())
            .first()
        )

    def find_by_slug(self, slug: str) -> Optional[StoredContent]:
        with self._session_factory() as db:
            content = (
                db.query(PublishedContent)
                .filter(PublishedContent.page_slug == slug)
                .first()
            )
            if content is None:
                return None
            ledger = self._latest_ledger(db, content.id)
            if ledger is None:
                # Not written by Tek Juice: never managed by the receiver.
                return None
            return self._stored(content, ledger)

    def find_by_idempotency_key(self, idempotency_key: str) -> Optional[StoredContent]:
        with self._session_factory() as db:
            ledger = (
                db.query(TekJuicePublication)
                .filter(
                    TekJuicePublication.idempotency_key == idempotency_key,
                    TekJuicePublication.status == "published",
                )
                .first()
            )
            if ledger is None or ledger.resource_id is None:
                return None
            content = db.get(PublishedContent, ledger.resource_id)
            if content is None:
                return None
            return self._stored(content, ledger)

    # ── Writes ───────────────────────────────────────────────────────────

    @staticmethod
    def _apply(target: PublishedContent, content: PublicationContent, execution_id: str) -> None:
        now = datetime.now(timezone.utc)
        target.title = content.title
        target.hero_heading = content.title
        target.hero_subheading = content.excerpt
        target.body_content = content.body
        target.meta_description = content.meta_description
        target.meta_keywords = ", ".join(content.meta_keywords)
        target.source_document_id = execution_id
        target.updated_at = now

    def _record_ledger(
        self,
        db: Session,
        *,
        content_row: PublishedContent,
        content: PublicationContent,
        action: str,
        execution_id: str,
        idempotency_key: str,
    ) -> None:
        # One ledger row per execution (unique execution_id): a regenerated
        # publication for the same execution updates its row in place.
        ledger = (
            db.query(TekJuicePublication)
            .filter(TekJuicePublication.execution_id == execution_id)
            .first()
        )
        if ledger is None:
            ledger = TekJuicePublication(execution_id=execution_id)
            db.add(ledger)
        ledger.idempotency_key = idempotency_key
        ledger.website_id = self._website_id
        ledger.action_type = action
        ledger.resource_id = content_row.id
        ledger.published_url = self.public_url(content_row.page_slug)
        ledger.content_hash = content.content_hash()
        ledger.status = "published"
        ledger.error = None
        ledger.updated_at = datetime.now(timezone.utc)

    def create(
        self,
        content: PublicationContent,
        *,
        execution_id: str,
        idempotency_key: str,
    ) -> StoredContent:
        with self._session_factory() as db:
            try:
                row = PublishedContent(
                    page_slug=content.slug,
                    published_at=datetime.now(timezone.utc),
                )
                self._apply(row, content, execution_id)
                db.add(row)
                db.flush()
                self._record_ledger(
                    db,
                    content_row=row,
                    content=content,
                    action="create",
                    execution_id=execution_id,
                    idempotency_key=idempotency_key,
                )
                db.commit()
            except IntegrityError as exc:
                db.rollback()
                raise DuplicateSlugError(
                    f"Content slug already exists: {content.slug}"
                ) from exc
            except OperationalError as exc:
                db.rollback()
                raise ContentStoreError("UMET content database unavailable") from exc
        stored = self.find_by_slug(content.slug)
        if stored is None:
            raise ContentStoreError("Created content could not be read back")
        return stored

    def update(
        self,
        existing: StoredContent,
        content: PublicationContent,
        *,
        execution_id: str,
        idempotency_key: str,
    ) -> StoredContent:
        with self._session_factory() as db:
            try:
                row = db.get(PublishedContent, int(existing.resource_id))
                if row is None:
                    raise ContentStoreError("Content disappeared during update")
                self._apply(row, content, execution_id)
                self._record_ledger(
                    db,
                    content_row=row,
                    content=content,
                    action="update",
                    execution_id=execution_id,
                    idempotency_key=idempotency_key,
                )
                db.commit()
            except OperationalError as exc:
                db.rollback()
                raise ContentStoreError("UMET content database unavailable") from exc
        stored = self.find_by_slug(existing.slug)
        if stored is None:
            raise ContentStoreError("Updated content could not be read back")
        return stored


def build_receiver(settings, session_factory) -> Optional[PublicationReceiver]:
    """Return the receiver, or None when S2S is not configured."""
    if not (settings.TEKJUICE_WEBSITE_ID and settings.TEKJUICE_RECEIVER_SECRET):
        return None
    store = UMETContentStore(
        session_factory,
        public_base_url=settings.PUBLIC_URL,
        website_id=settings.TEKJUICE_WEBSITE_ID,
    )
    return PublicationReceiver(
        store=store,
        website_id=settings.TEKJUICE_WEBSITE_ID,
        receiver_secret=settings.TEKJUICE_RECEIVER_SECRET,
    )


def create_router(receiver: PublicationReceiver):
    from tekjuice_connector.adapters.fastapi import create_router as connector_router

    return connector_router(receiver, path=S2S_PUBLISH_PATH)


def public_content_url(settings) -> str:
    """Anonymous URL serving published content (GET /api/content/{slug}).

    UMET pages are rendered in the browser from this API, so it is the public
    proof that published content is served.
    """
    return settings.TEKJUICE_PUBLIC_CONTENT_URL or (
        settings.PUBLIC_URL.rstrip("/") + "/api/content/{slug}"
    )


def start_connector_handshake(settings, receiver: PublicationReceiver) -> Optional[threading.Thread]:
    """Register the receiver with the Data Engine in the background.

    Runs off the request path: the Data Engine verifies the receiver by
    calling it back, so the handshake must not block application startup.
    """
    required = (
        settings.TEKJUICE_CONNECTOR_KEY,
        settings.TEKJUICE_DATA_ENGINE_URL,
        settings.TEKJUICE_PUBLICATION_ENDPOINT_URL,
    )
    if not all(required):
        logger.info("Tek Juice connector handshake not configured; skipping")
        return None

    def _connect() -> None:
        from tekjuice_connector import PublicationRegistration, TekJuiceConnector

        try:
            connector = TekJuiceConnector(
                website_id=settings.TEKJUICE_WEBSITE_ID,
                connector_key=settings.TEKJUICE_CONNECTOR_KEY,
                data_engine_url=settings.TEKJUICE_DATA_ENGINE_URL,
                publication=PublicationRegistration.from_receiver(
                    receiver,
                    endpoint_url=settings.TEKJUICE_PUBLICATION_ENDPOINT_URL,
                    framework="fastapi",
                    public_content_url=public_content_url(settings),
                ),
            )
            result = connector.connect()
            logger.info(
                "Tek Juice connector handshake: onboarding=%s publication=%s ready=%s next=%s",
                result.onboarding_status,
                result.publication_status,
                result.ready,
                result.next_action,
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("Tek Juice connector handshake failed: %s", exc)

    thread = threading.Thread(target=_connect, name="tekjuice-handshake", daemon=True)
    thread.start()
    return thread
