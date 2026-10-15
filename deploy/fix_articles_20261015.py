"""One-off content fixes from the 2026-10-15 indexing audit.

1. /transaction-logging-manual-entry-and-import-with-umet: the CTA linked to
   /signup (404; the app route is /register), the body ended in a truncated
   JSON-LD block shown as text, and it claimed CSV export, which UMET does
   not have.
2. /export-your-moving-expenses-with-umet-seamless-csv-data-management: the
   whole article is about CSV export. Its Tek Juice publications are marked
   "withdrawn", so the page returns 404 and leaves the sitemap, the hub and
   /api/content. The row itself is kept (reversible: set status back to
   "published").

Dry run by default; --apply writes. Run inside the backend container:
    docker exec -i -w /app expense-tracker python - [--apply] < deploy/fix_articles_20261015.py
The original rows are printed as JSON first: keep that output as the backup.
"""

import json
import os
import sys

from sqlalchemy import create_engine, text

APPLY = "--apply" in sys.argv
FIX_SLUG = "transaction-logging-manual-entry-and-import-with-umet"
WITHDRAW_SLUG = "export-your-moving-expenses-with-umet-seamless-csv-data-management"

EDITS = [
    ("*   **Data Export:** You can export your expenses and income as CSV at any time "
     "from your account settings, giving you full control over your data.\n", ""),
    ("(https://ultimatemove.co.uk/signup)", "(https://ultimatemove.co.uk/register)"),
    ("### Can I export my data?\nYes — you can export your expenses and income as CSV "
     "at any time from your account settings.\n\n", ""),
]
JSON_HEADING = "## Structured Data"


def fixed_body(body: str) -> str:
    for old, new in EDITS:
        if body.count(old) != 1:
            raise SystemExit(f"Edit does not match exactly once ({body.count(old)}): {old[:60]!r}")
        body = body.replace(old, new)
    if body.count(JSON_HEADING) != 1:
        raise SystemExit(f"{JSON_HEADING!r} found {body.count(JSON_HEADING)} times")
    body = body[: body.index(JSON_HEADING)].rstrip() + "\n"
    for leftover in ('"@context"', "/signup", "CSV"):
        if leftover in body:
            raise SystemExit(f"{leftover!r} still in the body")
    return body


engine = create_engine(os.environ["DATABASE_URL"])
with engine.begin() as db:
    row = db.execute(text("select id, body_content from published_content where page_slug = :s"),
                     {"s": FIX_SLUG}).one()
    target = db.execute(text("select id from published_content where page_slug = :s"),
                        {"s": WITHDRAW_SLUG}).scalar_one()
    ledger = db.execute(text("select id, execution_id, status from tekjuice_publications "
                             "where resource_id = :r order by id"), {"r": target}).mappings().all()
    print("BACKUP " + json.dumps({"published_content": {"id": row.id, "page_slug": FIX_SLUG,
                                                         "body_content": row.body_content},
                                  "withdraw": {"resource_id": target,
                                               "ledger": [dict(r) for r in ledger]}}))

    new_body = fixed_body(row.body_content)
    print(f"{FIX_SLUG}: {len(row.body_content)} -> {len(new_body)} chars; ends with: {new_body[-120:]!r}")
    published = [r for r in ledger if r["status"] == "published"]
    print(f"{WITHDRAW_SLUG}: {len(published)} published ledger row(s) -> withdrawn")
    if not published:
        raise SystemExit("Nothing to withdraw (no published ledger rows)")

    if not APPLY:
        print("Dry run: nothing written. Re-run with --apply.")
        raise SystemExit(0)
    db.execute(text("update published_content set body_content = :b, updated_at = now() where id = :i"),
               {"b": new_body, "i": row.id})
    db.execute(text("update tekjuice_publications set status = 'withdrawn', updated_at = now() "
                    "where resource_id = :r and status = 'published'"), {"r": target})
    print("Applied.")
