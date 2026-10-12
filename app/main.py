from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.database.connection import SessionLocal
from app.models.expense import PaymentMethod
from app.integrations import tekjuice_s2s
from app.routes import auth, dashboard, expenses, users, content

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(expenses.router)
app.include_router(dashboard.router)
app.include_router(content.router)

# Tek Juice S2S publication receiver (tekjuice-connector) — the only
# publication path (the legacy M2M route was retired 2026-10-12).
tekjuice_receiver = tekjuice_s2s.build_receiver(settings, SessionLocal)
if tekjuice_receiver is not None:
    app.include_router(tekjuice_s2s.create_router(tekjuice_receiver))


DEFAULT_PAYMENT_METHODS = [
    "Cash",
    "Mobile Money",
    "Bank Transfer",
    "Credit Card",
    "Debit Card",
    "Cheque",
]


@app.on_event("startup")
def seed_payment_methods() -> None:
    """Insert default payment methods if the table is empty."""
    db = SessionLocal()
    try:
        if db.query(PaymentMethod).count() == 0:
            for name in DEFAULT_PAYMENT_METHODS:
                db.add(PaymentMethod(name=name))
            db.commit()
    finally:
        db.close()


@app.on_event("startup")
def register_tekjuice_connector() -> None:
    """Register the S2S receiver with the Tek Juice Data Engine."""
    if tekjuice_receiver is not None:
        tekjuice_s2s.start_connector_handshake(settings, tekjuice_receiver)


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok", "app": settings.APP_NAME}

# Data Engine integration
from app.routes import engine as engine_router
from app.models.content import PublishedContent
from app.database.base import Base
from app.database.connection import engine as db_engine

app.include_router(engine_router.router)

# Auto-create published_content table if it doesn't exist
Base.metadata.create_all(bind=db_engine, tables=[PublishedContent.__table__])
