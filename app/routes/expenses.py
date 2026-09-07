from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.expense import (
    BudgetCreate,
    BudgetResponse,
    CategoryCreate,
    CategoryResponse,
    ExpenseCreate,
    ExpenseResponse,
    ExpenseUpdate,
    IncomeCreate,
    IncomeResponse,
    IncomeUpdate,
    PaymentMethodResponse,
)
from app.services import expense_service

router = APIRouter(prefix="/api", tags=["Expenses"])


# ── Categories ────────────────────────────────────────────────────────────────

@router.post("/categories", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
def create_category(
    payload: CategoryCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return expense_service.create_category(current_user, payload, db)


@router.get("/categories", response_model=list[CategoryResponse])
def list_categories(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return expense_service.list_categories(current_user, db)


# ── Payment Methods ───────────────────────────────────────────────────────────

@router.get("/payment-methods", response_model=list[PaymentMethodResponse])
def list_payment_methods(db: Session = Depends(get_db)):
    return expense_service.list_payment_methods(db)


# ── Expenses ──────────────────────────────────────────────────────────────────

@router.get("/expenses", response_model=list[ExpenseResponse])
def list_expenses(
    category_id: int | None = Query(default=None),
    payment_method_id: int | None = Query(default=None),
    search: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return expense_service.list_expenses(current_user, db, category_id, payment_method_id, search)


@router.post("/expenses", response_model=ExpenseResponse, status_code=status.HTTP_201_CREATED)
def create_expense(
    payload: ExpenseCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return expense_service.create_expense(current_user, payload, db)


@router.get("/expenses/{expense_id}", response_model=ExpenseResponse)
def get_expense(
    expense_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return expense_service.get_expense(current_user, expense_id, db)


@router.put("/expenses/{expense_id}", response_model=ExpenseResponse)
def update_expense(
    expense_id: int,
    payload: ExpenseUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return expense_service.update_expense(current_user, expense_id, payload, db)


@router.delete("/expenses/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_expense(
    expense_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    expense_service.delete_expense(current_user, expense_id, db)


# ── Income ────────────────────────────────────────────────────────────────────

@router.get("/income", response_model=list[IncomeResponse])
def list_income(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return expense_service.list_income(current_user, db)


@router.post("/income", response_model=IncomeResponse, status_code=status.HTTP_201_CREATED)
def create_income(
    payload: IncomeCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return expense_service.create_income(current_user, payload, db)


@router.get("/income/{income_id}", response_model=IncomeResponse)
def get_income(
    income_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return expense_service.get_income(current_user, income_id, db)


@router.put("/income/{income_id}", response_model=IncomeResponse)
def update_income(
    income_id: int,
    payload: IncomeUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return expense_service.update_income(current_user, income_id, payload, db)


@router.delete("/income/{income_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_income(
    income_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    expense_service.delete_income(current_user, income_id, db)


# ── Budgets ───────────────────────────────────────────────────────────────────

@router.get("/budgets", response_model=list[BudgetResponse])
def list_budgets(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return expense_service.list_budgets(current_user, db)


@router.post("/budgets", response_model=BudgetResponse, status_code=status.HTTP_201_CREATED)
def create_budget(
    payload: BudgetCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return expense_service.create_budget(current_user, payload, db)
