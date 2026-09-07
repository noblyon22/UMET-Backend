from sqlalchemy import extract, func
from sqlalchemy.orm import Session

from app.models.expense import Budget, Category, Expense, Income
from app.models.user import User


def get_summary(user: User, db: Session) -> dict:
    total_income = db.query(func.sum(Income.amount)).filter(Income.user_id == user.id).scalar() or 0.0
    total_expenses = db.query(func.sum(Expense.amount)).filter(Expense.user_id == user.id).scalar() or 0.0
    total_budgets = db.query(func.count(Budget.id)).filter(Budget.user_id == user.id).scalar() or 0

    return {
        "total_income": total_income,
        "total_expenses": total_expenses,
        "net_balance": total_income - total_expenses,
        "total_budgets": total_budgets,
    }


def get_monthly_summary(user: User, year: int, month: int, db: Session) -> dict:
    monthly_income = (
        db.query(func.sum(Income.amount))
        .filter(
            Income.user_id == user.id,
            extract("year", Income.date) == year,
            extract("month", Income.date) == month,
        )
        .scalar()
        or 0.0
    )

    monthly_expenses = (
        db.query(func.sum(Expense.amount))
        .filter(
            Expense.user_id == user.id,
            extract("year", Expense.date) == year,
            extract("month", Expense.date) == month,
        )
        .scalar()
        or 0.0
    )

    return {
        "year": year,
        "month": month,
        "total_income": monthly_income,
        "total_expenses": monthly_expenses,
        "net_balance": monthly_income - monthly_expenses,
        "data": [],
    }


def get_category_breakdown(user: User, db: Session) -> list[dict]:
    rows = (
        db.query(Category.id, Category.name, func.sum(Expense.amount).label("total"))
        .join(Expense, Expense.category_id == Category.id)
        .filter(Expense.user_id == user.id)
        .group_by(Category.id, Category.name)
        .order_by(func.sum(Expense.amount).desc())
        .all()
    )

    grand_total = sum(r.total for r in rows) or 1  # avoid zero division
    return [
        {
            "category_id": r.id,
            "category_name": r.name,
            "total": r.total,
            "percentage": round((r.total / grand_total) * 100, 2),
        }
        for r in rows
    ]


def get_budget_status(user: User, year: int, month: int, db: Session) -> list[dict]:
    budgets = (
        db.query(Budget)
        .filter(Budget.user_id == user.id, Budget.year == year, Budget.month == month)
        .all()
    )

    result = []
    for budget in budgets:
        spent = (
            db.query(func.sum(Expense.amount))
            .filter(
                Expense.user_id == user.id,
                Expense.category_id == budget.category_id,
                extract("year", Expense.date) == year,
                extract("month", Expense.date) == month,
            )
            .scalar()
            or 0.0
        )

        category = db.get(Category, budget.category_id)
        budgeted = budget.amount
        percentage_used = round((spent / budgeted) * 100, 2) if budgeted > 0 else 0.0
        result.append(
            {
                "budget_id": budget.id,
                "category_id": budget.category_id,
                "category_name": category.name if category else str(budget.category_id),
                "budgeted": budgeted,
                "spent": spent,
                "remaining": budgeted - spent,
                "percentage_used": percentage_used,
            }
        )

    return result
