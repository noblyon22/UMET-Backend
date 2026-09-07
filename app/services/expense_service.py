from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.expense import Budget, Category, Expense, Income, PaymentMethod
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


# ── Categories ────────────────────────────────────────────────────────────────

def create_category(user: User, payload: CategoryCreate, db: Session) -> CategoryResponse:
    category = Category(name=payload.name, user_id=user.id)
    db.add(category)
    db.commit()
    db.refresh(category)
    return CategoryResponse.model_validate(category)


def list_categories(user: User, db: Session) -> list[CategoryResponse]:
    categories = db.query(Category).filter(Category.user_id == user.id).all()
    return [CategoryResponse.model_validate(c) for c in categories]


# ── Payment Methods ───────────────────────────────────────────────────────────

def list_payment_methods(db: Session) -> list[PaymentMethodResponse]:
    methods = db.query(PaymentMethod).all()
    return [PaymentMethodResponse.model_validate(m) for m in methods]


# ── Expenses ─────────────────────────────────────────────────────────────────

def create_expense(user: User, payload: ExpenseCreate, db: Session) -> ExpenseResponse:
    category = db.query(Category).filter(
        Category.id == payload.category_id, Category.user_id == user.id
    ).first()
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    expense = Expense(
        amount=payload.amount,
        description=payload.description,
        category_id=payload.category_id,
        date=payload.date,
        payment_method_id=payload.payment_method_id,
        notes=payload.notes,
        user_id=user.id,
    )
    db.add(expense)
    db.commit()
    db.refresh(expense)
    return ExpenseResponse.model_validate(expense)


def list_expenses(
    user: User,
    db: Session,
    category_id: int | None = None,
    payment_method_id: int | None = None,
    search: str | None = None,
) -> list[ExpenseResponse]:
    query = db.query(Expense).filter(Expense.user_id == user.id)
    if category_id:
        query = query.filter(Expense.category_id == category_id)
    if payment_method_id:
        query = query.filter(Expense.payment_method_id == payment_method_id)
    if search:
        query = query.filter(Expense.description.ilike(f"%{search}%"))
    expenses = query.order_by(Expense.date.desc()).all()
    return [ExpenseResponse.model_validate(e) for e in expenses]


def get_expense(user: User, expense_id: int, db: Session) -> ExpenseResponse:
    expense = db.query(Expense).filter(
        Expense.id == expense_id, Expense.user_id == user.id
    ).first()
    if not expense:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found")
    return ExpenseResponse.model_validate(expense)


def update_expense(user: User, expense_id: int, payload: ExpenseUpdate, db: Session) -> ExpenseResponse:
    expense = db.query(Expense).filter(
        Expense.id == expense_id, Expense.user_id == user.id
    ).first()
    if not expense:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found")

    if payload.category_id is not None:
        category = db.query(Category).filter(
            Category.id == payload.category_id, Category.user_id == user.id
        ).first()
        if not category:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(expense, field, value)

    db.commit()
    db.refresh(expense)
    return ExpenseResponse.model_validate(expense)


def delete_expense(user: User, expense_id: int, db: Session) -> None:
    expense = db.query(Expense).filter(
        Expense.id == expense_id, Expense.user_id == user.id
    ).first()
    if not expense:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found")
    db.delete(expense)
    db.commit()


# ── Income ────────────────────────────────────────────────────────────────────

def create_income(user: User, payload: IncomeCreate, db: Session) -> IncomeResponse:
    income = Income(
        amount=payload.amount,
        source=payload.source,
        description=payload.description,
        date=payload.date,
        user_id=user.id,
    )
    db.add(income)
    db.commit()
    db.refresh(income)
    return IncomeResponse.model_validate(income)


def list_income(user: User, db: Session) -> list[IncomeResponse]:
    records = db.query(Income).filter(Income.user_id == user.id).order_by(Income.date.desc()).all()
    return [IncomeResponse.model_validate(r) for r in records]


def get_income(user: User, income_id: int, db: Session) -> IncomeResponse:
    record = db.query(Income).filter(Income.id == income_id, Income.user_id == user.id).first()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Income record not found")
    return IncomeResponse.model_validate(record)


def update_income(user: User, income_id: int, payload: IncomeUpdate, db: Session) -> IncomeResponse:
    record = db.query(Income).filter(Income.id == income_id, Income.user_id == user.id).first()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Income record not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(record, field, value)
    db.commit()
    db.refresh(record)
    return IncomeResponse.model_validate(record)


def delete_income(user: User, income_id: int, db: Session) -> None:
    record = db.query(Income).filter(Income.id == income_id, Income.user_id == user.id).first()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Income record not found")
    db.delete(record)
    db.commit()


# ── Budgets ───────────────────────────────────────────────────────────────────

def create_budget(user: User, payload: BudgetCreate, db: Session) -> BudgetResponse:
    category = db.query(Category).filter(
        Category.id == payload.category_id, Category.user_id == user.id
    ).first()
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    budget = Budget(
        amount=payload.amount,
        category_id=payload.category_id,
        month=payload.month,
        year=payload.year,
        user_id=user.id,
    )
    db.add(budget)
    db.commit()
    db.refresh(budget)
    return BudgetResponse.model_validate(budget)


def list_budgets(user: User, db: Session) -> list[BudgetResponse]:
    budgets = db.query(Budget).filter(Budget.user_id == user.id).all()
    return [BudgetResponse.model_validate(b) for b in budgets]
