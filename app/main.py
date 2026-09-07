from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.database.connection import SessionLocal
from app.models.expense import PaymentMethod
from app.routes import auth, dashboard, expenses, users

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


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok", "app": settings.APP_NAME}
