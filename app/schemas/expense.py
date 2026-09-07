from datetime import date as date_, datetime

from pydantic import BaseModel, field_validator


# ── Category ────────────────────────────────────────────────────────────────

class CategoryCreate(BaseModel):
    name: str


class CategoryResponse(BaseModel):
    id: int
    name: str
    user_id: int

    model_config = {"from_attributes": True}


# ── Payment Method ───────────────────────────────────────────────────────────

class PaymentMethodResponse(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}


# ── Expense ──────────────────────────────────────────────────────────────────

class ExpenseCreate(BaseModel):
    amount: float
    description: str
    category_id: int
    date: date_
    payment_method_id: int | None = None
    notes: str | None = None

    @field_validator("amount")
    @classmethod
    def amount_must_be_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Amount must be greater than zero")
        return v


class ExpenseUpdate(BaseModel):
    amount: float | None = None
    description: str | None = None
    category_id: int | None = None
    date: date_ | None = None
    payment_method_id: int | None = None
    notes: str | None = None

    @field_validator("amount")
    @classmethod
    def amount_must_be_positive(cls, v: float | None) -> float | None:
        if v is not None and v <= 0:
            raise ValueError("Amount must be greater than zero")
        return v


class ExpenseResponse(BaseModel):
    id: int
    amount: float
    description: str
    date: date_
    notes: str | None
    user_id: int
    category_id: int
    payment_method_id: int | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Income ───────────────────────────────────────────────────────────────────

class IncomeCreate(BaseModel):
    amount: float
    source: str
    description: str | None = None
    date: date_

    @field_validator("amount")
    @classmethod
    def amount_must_be_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Amount must be greater than zero")
        return v


class IncomeUpdate(BaseModel):
    amount: float | None = None
    source: str | None = None
    description: str | None = None
    date: date_ | None = None


class IncomeResponse(BaseModel):
    id: int
    amount: float
    source: str
    description: str | None
    date: date_
    user_id: int
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Budget ───────────────────────────────────────────────────────────────────

class BudgetCreate(BaseModel):
    amount: float
    category_id: int
    month: int
    year: int

    @field_validator("month")
    @classmethod
    def month_must_be_valid(cls, v: int) -> int:
        if not (1 <= v <= 12):
            raise ValueError("Month must be between 1 and 12")
        return v


class BudgetResponse(BaseModel):
    id: int
    amount: float
    category_id: int
    month: int
    year: int
    user_id: int

    model_config = {"from_attributes": True}
