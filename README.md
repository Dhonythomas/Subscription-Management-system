# Subscription Management System

A subscription billing platform for Brightloop Software. It runs the full life of a subscription business, from products and plans through quotations, subscriptions, automatic invoices, payments, discounts, and revenue reporting.

Core flow: **Product > Plan > Quotation > Subscription > Invoice > Payment > Reports**

## Stack

- Django 5 + Django REST Framework
- React 18 + Vite
- PostgreSQL 16
- Redis 7 + Celery worker and beat
- Docker Compose

## Current status

**Backend phases 1–9 and the React frontend are complete.** The app provides JWT auth and RBAC, catalog and plans, subscriptions, billing, payments, invoice PDFs, discounts, finance reporting, demo seed data, and role-based admin, staff, and customer screens.

## Demo

After migrations:

```bash
docker compose run --rm api python manage.py seed_demo
```

Demo logins:

| Role | Email | Password |
|---|---|---|
| Admin | `admin@example.com` | `DemoPassword123!` |
| Staff | `staff@example.com` | `DemoPassword123!` |
| Customer | `customer@example.com` | `DemoPassword123!` |

Set `DEMO_PASSWORD` to override the demo password. The seed is safe to rerun and creates an active subscription with a paid invoice and refreshed finance metrics.

Demo flow:

1. Log in as admin; list products, plans, and discounts.
2. Log in as staff; list the active subscription and its paid invoice.
3. Download the invoice PDF from `/api/billing/invoices/<id>/pdf/`.
4. Open the finance dashboard at `/api/reports/dashboard/`.
5. Run `python manage.py run_billing` twice; the second run creates no duplicates.

## Prerequisites

- Docker Desktop (for `docker compose up --build`)
- Or Python 3.12+ with PostgreSQL 16 and Redis 7 for local development

## Quick start with Docker

1. Copy the environment example:
   ```bash
   cp .env.example .env
   ```
2. Build and start all services:
   ```bash
   docker compose up --build
   ```
3. Open the app at:
   ```text
   http://localhost:5173
   ```
4. Check the backend health endpoint:
   ```bash
   curl http://localhost:8000/health/
   ```
   Expected response: `{"status": "ok"}`
5. Load demo data:
   ```bash
   docker compose run --rm api python manage.py seed_demo
   ```
6. Run the backend test suite inside the API container:
   ```bash
   docker compose run --rm api pytest
   ```
7. Stop and clean up:
   ```bash
   docker compose down -v
   ```

## Accounts/Auth API

| Method and path | Purpose | Access |
|---|---|---|
| `POST /api/auth/register/` | Register a customer and customer profile | Public |
| `POST /api/auth/login/` | Obtain JWT access and refresh tokens | Public |
| `POST /api/auth/refresh/` | Refresh an access token | Public, valid refresh token required |
| `POST /api/auth/password-reset/` | Request a single-use reset link | Public |
| `POST /api/auth/password-reset-confirm/` | Set a new password using `uidb64` and `token` | Public, valid reset link required |
| `POST /api/accounts/staff/` | Create a staff account | Admin only |
| `GET /api/accounts/me/` | Read the signed-in user's profile | Authenticated |
| `PATCH /api/accounts/me/` | Update customer billing details | Customer only |
| `GET /api/accounts/customers/` | List customers (customers see only themselves) | Authenticated |
| `GET /api/accounts/customers/<id>/` | Read a customer (cross-customer IDs return 404) | Authenticated |

Send the access token as `Authorization: Bearer <access-token>` on protected requests. The initial admin can be created with `createsuperuser`; customer accounts can self-register, and only an admin can create staff accounts. Password reset email links point to `PASSWORD_RESET_FRONTEND_URL` (default `http://localhost:5173/reset-password`); configure it to the deployed client route.

Successful password reset invalidates the user's existing access and refresh tokens; they must log in again. Configure `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, and `EMAIL_USE_TLS` in `.env` for reset emails to deliver. Delivery failures keep the API response generic and are logged without the address or reset token.

## Catalog & Plans API

| Method and path | Purpose | Access |
|---|---|---|
| `/api/catalog/products/` | List, create, read, update, delete products | Admin writes; staff reads |
| `/api/catalog/variants/` | Manage product variants and price deltas | Admin writes; staff reads |
| `/api/catalog/taxes/` | Manage tax names and rates | Admin writes; staff reads |
| `/api/plans/` | List, create, read, update, delete plans | Admin writes; staff reads |

All list endpoints are paginated. Customers cannot access catalog or plan endpoints.

## Subscriptions API

| Method and path | Purpose | Access |
|---|---|---|
| `/api/subscriptions/templates/` | Manage quotation templates | Admin/staff |
| `/api/subscriptions/` | List and create subscriptions | Admin/staff create; customers see own |
| `/api/subscriptions/<id>/` | Read or update a subscription | Admin/staff; customers read own |
| `POST /api/subscriptions/<id>/quotation/` | Move Draft → Quotation | Admin/staff |
| `POST /api/subscriptions/<id>/confirm/` | Move Quotation → Confirmed | Admin/staff |
| `POST /api/subscriptions/<id>/activate/` | Move Confirmed/Paused/Closed → Active | Admin/staff |
| `POST /api/subscriptions/<id>/pause/` | Move Active → Paused | Admin/staff |
| `POST /api/subscriptions/<id>/close/` | Move Active → Closed | Admin/staff |
| `POST /api/subscriptions/<id>/renew/` | Move Closed → Active | Admin/staff |

Status is read-only; lifecycle changes only happen through the action endpoints and are audited.

## Billing

Run due billing on demand:

```bash
python manage.py run_billing
```

Celery Beat also schedules `apps.billing.tasks.run_billing_task` daily. Re-running billing for the same date creates no duplicate invoices; invoice creation and `next_billing_date` advancement are atomic.

## Invoices & Payments API

| Method and path | Purpose | Access |
|---|---|---|
| `GET /api/billing/invoices/` | List invoices | Admin/staff; customers see own |
| `GET /api/billing/invoices/<id>/` | Read an invoice | Admin/staff; customers read own |
| `POST /api/billing/invoices/<id>/confirm/` | Confirm a draft invoice | Admin/staff |
| `POST /api/billing/invoices/<id>/cancel/` | Cancel an unpaid invoice | Admin/staff |
| `GET /api/billing/invoices/<id>/pdf/` | Download the invoice PDF | Admin/staff; customers download own |
| `POST /api/payments/` | Record a payment against a confirmed invoice | Admin/staff |
| `GET /api/payments/` | List payments | Admin/staff |

Partial payments are supported. When total payments reach the invoice total, the invoice automatically becomes Paid. Overpayments and payments against draft, paid, or cancelled invoices are rejected.

## Reports API

| Method and path | Purpose | Access |
|---|---|---|
| `GET /api/reports/dashboard/?date=YYYY-MM-DD` | Finance snapshot for a date | Admin/staff |
| `GET /api/reports/metrics/` | Paginated daily metrics history | Admin/staff |

Refresh metrics with `python manage.py refresh_metrics`; Celery Beat also refreshes them daily. Metrics include active subscriptions, revenue collected, outstanding balance, overdue invoices, MRR, and ARR.

## Discounts

Discounts are applied automatically when invoices are generated. Fixed and percentage discounts can target the whole subscription or selected products, with start/end dates, minimum amount or quantity, and usage limits. Applied discounts are recorded in `discount_usage`; repeat billing runs cannot exceed the limit.

## Frontend development

```bash
cd frontend
npm install
npm run dev
```

Vite serves the app on `http://localhost:5173` and proxies `/api` and `/health` to `http://127.0.0.1:8000`. Production build:

```bash
npm run build
```

The frontend includes login/registration, role-based navigation, finance overview, catalog and plan views, subscription lifecycle actions, invoices with PDF download, payment recording, and the customer profile screen. Backend RBAC remains authoritative.

## Local development and tests (this machine)

PostgreSQL 16 is running in WSL Ubuntu on `127.0.0.1:5432` (database `subscription_db`, user `subscription`). Because the Windows-to-WSL localhost relay can be flaky, tests are run from a Linux virtual environment inside WSL:

```bash
wsl -d Ubuntu -- bash -lc "cd /mnt/c/Users/Thushar/Documents/vs/makeathon/subscription-management-system/backend && /home/thushar/.venvs/subscription/bin/python -m pytest -q"
```

From the backend directory with the Windows virtual environment:

```powershell
..\.venv\Scripts\python.exe manage.py check
..\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
..\.venv\Scripts\python.exe -m pytest -q
```

## Verification notes

- **Docker runtime:** `docker compose up --build -d` completed successfully; migrations ran, the API returned HTTP 200 from `/health/`, and `docker compose run --rm api pytest -q` passed the full suite.
- **No secrets committed:** `.env` is git-ignored; only `.env.example` is tracked.
- **Money:** All money fields use `DecimalField(max_digits=12, decimal_places=2)` with `apps.platform.money.quantize_money` (ROUND_HALF_UP).
- **State changes:** Subscription and invoice transitions go through service functions and write `AuditLog` + `OutboxEvent` in the same transaction.
- **Billing idempotency:** `Invoice` enforces `UNIQUE(subscription, period_start, period_end)` and the billing engine must lock the subscription row with `select_for_update`.

## Documentation

- `docs/design.md` — product design (source of truth)
- `docs/platform-contract.md` — shared interfaces
- `AGENT.md` — working instructions
- `RULES.md` — non-negotiable rules
- `PROGRESS.md` — phase status and verification log
- `MODULE_ASSIGNMENTS.md` — module ownership and phase breakdown
