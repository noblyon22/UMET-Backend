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
             title="Moving Cost Guide", body="<p>Plan every cost.</p>", discovery=None):
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
    if discovery:
        content["discovery"] = discovery  # not part of the content hash
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
    assert body["capabilities"] == ["ai.entity", "ai.feed", "ai.indexnow", "ai.llms_txt", "ai.markdown", "ai.robots", "publish.create",
                                    "publish.discovery", "publish.update", "publish.verify",
                                    "seo.prerender", "seo.sitemap"]
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


# ── Search discoverability (seo.prerender / seo.sitemap) ────────────────────

SHELL = ('<!doctype html><html><head><title>UMET — Ultimate Move Expense Tracker</title>'
         '<meta name="description" content="Shell" /><script type="module" src="/assets/app.js"></script>'
         '</head><body><div id="root"></div></body></html>')
SEO = "/api/integrations/tekjuice/seo"


@pytest.fixture
def shell(monkeypatch):
    import app.main as main
    monkeypatch.setattr(main.tekjuice_seo, "_shell", lambda: SHELL)


def test_receiver_advertises_discoverability():
    import app.main as main
    assert {"seo.prerender", "seo.sitemap"} <= set(main.tekjuice_receiver.capabilities)


def test_published_article_is_served_prerendered(client, shell):
    assert _post(client, _payload()).status_code == 200
    page = client.get(f"{SEO}/page/moving-cost-guide")
    assert page.status_code == 200
    assert page.headers["content-type"].startswith("text/html")
    html = page.text
    title = _page("moving-cost-guide").title
    assert f"<title>{title}</title>" in html
    assert "UMET — Ultimate Move Expense Tracker" not in html.split("</head>")[0].split("<title>")[1]
    assert '<link rel="canonical" href="https://ultimatemove.co.uk/moving-cost-guide" />' in html
    assert '<div id="root"><article><h1>' in html
    assert '<script type="module" src="/assets/app.js"></script>' in html


def test_umet_pages_and_unknown_paths_are_not_prerendered(client, shell):
    db = SessionLocal()
    db.add(PublishedContent(page_slug="home", title="UMET home", body_content="Native"))
    db.commit()
    db.close()
    assert client.get(f"{SEO}/page/home").status_code == 404       # UMET's own CMS page
    assert client.get(f"{SEO}/page/dashboard").status_code == 404  # app route


def test_sitemap_lists_public_pages_and_articles(client, shell):
    _post(client, _payload())
    sitemap = client.get(f"{SEO}/sitemap.xml")
    assert sitemap.status_code == 200
    assert "<loc>https://ultimatemove.co.uk/</loc>" in sitemap.text
    assert "<loc>https://ultimatemove.co.uk/features</loc>" in sitemap.text
    assert "<loc>https://ultimatemove.co.uk/moving-cost-guide</loc><lastmod>" in sitemap.text
    assert "/dashboard" not in sitemap.text


# ── AI answer engines (publish.discovery, ai.*) ─────────────────────────────

DISCOVERY = {
    "summary": "Plan every moving cost before the day.",
    "key_takeaways": ["List fixed costs first"],
    "direct_answer": "Write down every cost and track it as you spend.",
    "faq": [{"question": "How do I track costs?", "answer": "Log each expense in UMET."}],
    "entities": ["UMET"],
}


def test_discovery_is_stored_and_rendered_on_the_canonical_url(client, shell):
    import json
    import re
    assert _post(client, _payload(discovery=DISCOVERY)).status_code == 200
    assert json.loads(_page("moving-cost-guide").discovery)["direct_answer"] == DISCOVERY["direct_answer"]
    html = client.get(f"{SEO}/page/moving-cost-guide").text
    data = {d["@type"]: d for d in (json.loads(m) for m in re.findall(
        r'<script type="application/ld\+json">(.*?)</script>', html, re.S))}
    assert data["Article"]["url"] == "https://ultimatemove.co.uk/moving-cost-guide"
    assert data["Article"]["publisher"]["name"] == "UMET"
    assert data["FAQPage"]["mainEntity"][0]["name"] == "How do I track costs?"
    assert '<p id="tj-answer">Write down every cost' in html


def test_ai_outputs_name_the_canonical_url(client, shell):
    _post(client, _payload(discovery=DISCOVERY))
    url = "https://ultimatemove.co.uk/moving-cost-guide"
    md = client.get(f"{SEO}/markdown/moving-cost-guide")
    assert md.status_code == 200 and f"canonical: {url}" in md.text
    assert md.headers["link"] == f'<{url}>; rel="canonical"'
    assert client.get(f"{SEO}/markdown/dashboard").status_code == 404
    llms = client.get(f"{SEO}/llms.txt").text
    assert llms.startswith("# UMET\n\n> UMET is an expense tracker")
    assert f"({url})" in llms
    assert url in client.get(f"{SEO}/llms-full.txt").text
    assert client.get(f"{SEO}/feed.json").json()["items"][0]["url"] == url
    robots = client.get(f"{SEO}/robots.txt").text
    assert "User-agent: GPTBot\nAllow: /" in robots and "Disallow: /dashboard$" in robots
    assert "Sitemap: https://ultimatemove.co.uk/sitemap.xml" in robots


def test_content_column_is_added_to_existing_databases():
    from sqlalchemy import inspect, text
    from app.integrations.tekjuice_s2s import ensure_content_columns
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE published_content DROP COLUMN discovery"))
    ensure_content_columns(engine)
    ensure_content_columns(engine)  # idempotent
    assert "discovery" in {c["name"] for c in inspect(engine).get_columns("published_content")}


def test_indexnow_key_file_is_served(client):
    from tekjuice_connector.publication import indexnow_key
    key = indexnow_key(SECRET)
    response = client.get(f"{SEO}/indexnow/{key}")
    assert response.status_code == 200 and response.text == key
    assert client.get(f"{SEO}/indexnow/{'0' * 32}").status_code == 404


def test_verified_business_facts_are_served(client, shell):
    entity = {"name": "UMET", "website": "https://ultimatemove.co.uk/", "product_type": "Expense Tracker",
              "products": ["UMET"]}
    assert _post(client, _payload(discovery={**DISCOVERY, "entity": entity})).status_code == 200
    import json
    import re
    response = client.get(f"{SEO}/entity.json")
    assert response.status_code == 200 and response.json()["facts"]["name"] == "UMET"
    html = client.get(f"{SEO}/page/moving-cost-guide").text
    types = [json.loads(m)["@type"] for m in re.findall(
        r'<script type="application/ld\+json">(.*?)</script>', html, re.S)]
    assert "Organization" in types and "Product" in types
