# Nob Expense Tracker — Backend

A personal finance management REST API built with **FastAPI**, **SQLAlchemy**, and **PostgreSQL**.

## Features

- **Authentication** — JWT-based register / login / logout / profile
- **Expenses** — Full CRUD with search, filter by category and payment method
- **Income** — Track all income sources
- **Categories** — Per-user custom categories
- **Payment Methods** — Cash, Mobile Money, Bank Card, etc.
- **Budgets** — Monthly category budgets with over-budget detection
- **Dashboard** — All-time summary, monthly breakdown, category breakdown, budget status

## Project Structure

```
app/
├── core/           # Config and security (JWT, hashing)
├── database/       # SQLAlchemy engine, session, Base
├── models/         # ORM models (User, Expense, Income, Category, Budget)
├── schemas/        # Pydantic request/response schemas
├── routes/         # FastAPI routers
├── services/       # Business logic
└── dependencies/   # Reusable FastAPI dependencies (auth guard)
```

## Getting Started

### 1. Clone the repository

```bash
git clone <repo-url>
cd expense-tracker-backend
```

### 2. Create and activate a virtual environment

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
cp .env.example .env
# Edit .env with your database credentials and secret key
```

### 5. Run database migrations

```bash
alembic upgrade head
```

### 6. Start the development server

```bash
uvicorn app.main:app --reload
```

API docs are available at [http://localhost:8000/docs](http://localhost:8000/docs).

## API Overview

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Register a new user |
| POST | `/api/auth/login` | Log in, receive JWT |
| POST | `/api/auth/logout` | Log out (client discards token) |
| GET | `/api/auth/me` | Get current user |
| GET/PATCH | `/api/users/me` | View / update profile |
| POST | `/api/users/me/change-password` | Change password |
| GET/POST | `/api/expenses` | List / create expenses |
| GET/PUT/DELETE | `/api/expenses/{id}` | Read / update / delete expense |
| GET/POST | `/api/income` | List / create income records |
| GET/PUT/DELETE | `/api/income/{id}` | Read / update / delete income |
| GET/POST | `/api/categories` | List / create categories |
| GET | `/api/payment-methods` | List payment methods |
| GET/POST | `/api/budgets` | List / create budgets |
| GET | `/api/dashboard/summary` | All-time financial summary |
| GET | `/api/dashboard/monthly` | Monthly income vs expenses |
| GET | `/api/dashboard/categories` | Spending by category |
| GET | `/api/dashboard/budgets` | Budget vs actual for a month |

## Running with Docker

```bash
docker build -t nob-expense-tracker .
docker run -p 8000:8000 --env-file .env nob-expense-tracker
```

## Development Phases

| Phase | Focus |
|-------|-------|
| 1 | Foundation — FastAPI + PostgreSQL + SQLAlchemy |
| 2 | Authentication — JWT, protected routes |
| 3 | Core Finance — Expenses, income, categories |
| 4 | Dashboard — Summaries and calculations |
| 5 | Advanced — Budgets, analytics, notifications |
| 6 | Production — Tests, Docker, deployment |

## Environment Variables

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection string |
| `SECRET_KEY` | JWT signing secret |
| `ALGORITHM` | JWT algorithm (default: `HS256`) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token lifetime (default: `30`) |
| `CORS_ORIGINS` | Allowed frontend origins |
