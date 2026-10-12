"""UMET S2S receiver: the tekjuice-connector receiver over UMET's content model."""

from __future__ import annotations

import hashlib
import os
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.database.base import Base
from app.database.connection import SessionLocal, engine
from app.integrations.tekjuice_s2s import S2S_PUBLISH_PATH
from app.main import app
from app.models.content import PublishedContent
from app.models.tekjuice_publication import TekJuicePublication

WEBSITE_ID = os.environ["TEKJUICE_WEBSITE_ID"]
SECRET = os.environ["TEKJUICE_RECEIVER_SECRET"]
AUTH = {"Authorization": f"Bearer {SECRET}", "X-TekJuice-Contract-Version": "1.0"}
M2M_PATH = "/api/integrations/tekjuice/publish"


@pytest.fixture(autouse=True)
def database():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield


@pytest.fixture
def client():
    return TestClient(app)


def _payload(*, action="create", slug="moving-cost-guide", execution_id="exec-1",
             title="Moving Cost Guide", body="<p>Plan every cost.</p>"):
    content = {
        "title": title,
        "body": body,
        "slug": slug,
        "excerpt": "Plan every cost.",
        "meta_description": "A guide to moving costs.",
        "meta_keywords": ["moving costs", "budget"],
    }
    canonical = "\n".join([title, body, slug, content["excerpt"],
                           content["meta_description"], ",".join(content["meta_keywords"])])
    digest = hashlib.sha256(canonical.encode()).hexdigest()
    return {
        "contract_version": "1.0",
        "execution_id": execution_id,
        "website_id": WEBSITE_ID,
        "action": action,
        "idempotency_key": f"tekjuice:{WEBSITE_ID}:{execution_id}:{action}:{digest}",
        "content": content,
        "metadata": {"content_strategy_id": None, "opportunity_id": None, "content_hash": digest},
    }


def _post(client, payload, headers=AUTH):
    return client.post(S2S_PUBLISH_PATH, json=payload, headers=headers)


def _page(slug):
    with SessionLocal() as db:
        return db.query(PublishedContent).filter_by(page_slug=slug).first()


def _ledger():
    with SessionLocal() as db:
        return db.query(TekJuicePublication).order_by(TekJuicePublication.id).all()


def test_only_the_s2s_route_receives_publications(client):
    assert client.post(S2S_PUBLISH_PATH, json={}).status_code == 401
    # The legacy M2M route is retired.
    assert client.post(M2M_PATH, json={}).status_code == 404


def test_create_persists_page_and_ledger(client):
    response = _post(client, _payload())

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "published"
    assert body["action_performed"] == "created"
    assert body["published_url"] == "https://ultimatemove.co.uk/moving-cost-guide"
    page = _page("moving-cost-guide")
    assert page.title == "Moving Cost Guide"
    assert page.body_content == "<p>Plan every cost.</p>"
    assert page.meta_keywords == "moving costs, budget"
    assert page.source_document_id == "exec-1"
    assert body["resource_id"] == str(page.id)
    [ledger] = _ledger()
    assert ledger.execution_id == "exec-1"
    assert ledger.status == "published"
    assert ledger.content_hash == body["content_hash"]


def test_redelivery_is_replayed(client):
    first = _post(client, _payload())
    second = _post(client, _payload())

    assert second.json()["replayed"] is True
    assert second.json()["resource_id"] == first.json()["resource_id"]
    assert len(_ledger()) == 1


def test_regenerated_content_for_same_execution_updates_in_place(client):
    _post(client, _payload())
    response = _post(client, _payload(body="<p>Regenerated.</p>"))

    assert response.status_code == 200
    assert response.json()["action_performed"] == "updated"
    assert _page("moving-cost-guide").body_content == "<p>Regenerated.</p>"
    assert len(_ledger()) == 1  # same execution, same ledger row


def test_duplicate_slug_from_other_execution_is_409(client):
    _post(client, _payload(slug="introduction"))
    response = _post(client, _payload(slug="introduction", execution_id="exec-2", title="Other"))

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "duplicate_slug"
    assert _page("introduction").title == "Moving Cost Guide"


def test_update_of_existing_tek_juice_page(client):
    created = _post(client, _payload()).json()
    response = _post(client, _payload(action="update", execution_id="exec-2", title="Moving Costs 2026"))

    assert response.status_code == 200
    assert response.json()["resource_id"] == created["resource_id"]
    assert _page("moving-cost-guide").title == "Moving Costs 2026"
    assert [row.execution_id for row in _ledger()] == ["exec-1", "exec-2"]


def test_page_not_written_by_tek_juice_is_never_overwritten(client):
    with SessionLocal() as db:
        db.add(PublishedContent(page_slug="about", title="About UMET", body_content="<p>Ours.</p>"))
        db.commit()

    update = _post(client, _payload(action="update", slug="about"))
    create = _post(client, _payload(slug="about"))

    assert update.status_code == 404
    assert create.status_code == 409
    assert _page("about").body_content == "<p>Ours.</p>"


def test_m2m_era_content_and_history_survive_and_remain_updatable(client):
    """Content published through the legacy M2M route keeps its ledger history
    and can be updated through S2S."""
    # History exactly as the retired M2M route stored it: page + ledger row.
    with SessionLocal() as db:
        page = PublishedContent(page_slug="legacy-guide", title="Legacy Guide",
                                body_content="<p>v1</p>", source_document_id="m2m-exec")
        db.add(page)
        db.flush()
        db.add(TekJuicePublication(
            execution_id="m2m-exec", idempotency_key="m2m-key", website_id=WEBSITE_ID,
            action_type="create", resource_id=page.id,
            published_url="https://ultimatemove.co.uk/legacy-guide",
            content_hash="0" * 64, status="published",
        ))
        db.commit()
        legacy_id = str(page.id)

    response = _post(client, _payload(action="update", slug="legacy-guide",
                                      execution_id="s2s-exec", title="Legacy Guide, updated"))

    assert response.status_code == 200, response.text
    assert response.json()["resource_id"] == legacy_id
    page = _page("legacy-guide")
    assert page.title == "Legacy Guide, updated"
    history = {row.execution_id: row for row in _ledger()}
    assert history["m2m-exec"].action_type == "create"
    assert history["s2s-exec"].action_type == "update"


def test_verify_is_a_dry_run(client):
    publication = _payload(slug="tekjuice-verification-abc", execution_id="verify-1")
    response = _post(client, {
        "contract_version": "1.0", "action": "verify", "website_id": WEBSITE_ID,
        "challenge": "c-123", "dry_run": True, "publication": publication,
    })

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "verified"
    assert body["challenge"] == "c-123"
    assert body["persisted"] is False
    assert body["capabilities"] == ["publish.create", "publish.update", "publish.verify"]
    assert body["would_publish_url"] == "https://ultimatemove.co.uk/tekjuice-verification-abc"
    assert _page("tekjuice-verification-abc") is None
    assert _ledger() == []


@pytest.mark.parametrize(
    "headers",
    [{}, {"Authorization": "Bearer umet-test-legacy-m2m-secret"}, {"Authorization": "Bearer wrong" + "x" * 40}],  # noqa: E501
)
def test_s2s_rejects_other_credentials_including_m2m_secret(client, headers):
    response = _post(client, _payload(), headers=headers)
    assert response.status_code == 401
    assert _page("moving-cost-guide") is None


def test_other_website_is_rejected(client):
    payload = _payload()
    payload["website_id"] = "another-website"
    assert _post(client, payload).status_code == 403


def test_public_content_url_points_at_the_anonymous_content_api(client):
    from app.core.config import settings
    from app.integrations.tekjuice_s2s import public_content_url

    template = public_content_url(settings)
    assert template == "https://ultimatemove.co.uk/api/content/{slug}"

    _post(client, _payload())
    path = "/" + template.split("/", 3)[3].replace("{slug}", "moving-cost-guide")
    response = client.get(path)  # anonymous: no credentials
    assert response.status_code == 200
    assert response.json()["title"] == "Moving Cost Guide"
