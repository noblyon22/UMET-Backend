"""Test configuration: UMET on a throwaway SQLite database with S2S enabled."""

import os
import tempfile

_DB_DIR = tempfile.mkdtemp(prefix="umet-tests-")

os.environ.setdefault("DATABASE_URL", f"sqlite:///{_DB_DIR}/umet.db")
os.environ.setdefault("SECRET_KEY", "umet-test-secret-key")
os.environ.setdefault("PUBLIC_URL", "https://ultimatemove.co.uk")
os.environ.setdefault("TEKJUICE_WEBSITE_ID", "d930b609-a3e7-4a8a-826f-ffbe05fac939")
os.environ.setdefault("TEKJUICE_RECEIVER_SECRET", "umet-test-receiver-secret-" + "u" * 32)
