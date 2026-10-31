# Progress Log

## Current phase

**Phase 7 — Automatic Discounts**

**Status:** Complete

## Phase 1 scope decision

Phase 1 is the full foundation schema plus the platform layer, not platform infrastructure alone. It creates the core models and migrations for every module, including the custom user, subscription and invoice state machines, required indexes, audit/outbox infrastructure, and Docker Compose runtime. This is the **schema freeze**: later phases add APIs, business services, and new migrations, but they do not rewrite the foundation schema.

## Verification environment

- Local development and test verification use PostgreSQL 16 running in WSL Ubuntu on `127.0.0.1:5432` (database `subscription_db`, role `subscription`). Tests are run from a Linux virtual environment inside WSL (`/home/thushar/.venvs/subscription`) because the Windows-to-WSL localhost relay is unreliable on this machine.
- Docker Desktop is installed. Phase 2 Docker Compose build, migrations, API tests, and `/health/` have now been verified in the isolated worktree.
- No verification is claimed for a command that has not been run.

## Verification log

| Date | Task | Command | Result |
|---|---|---|---|
| 2026-10-31 | Task 1: docs and scope alignment | `git diff --check HEAD^ HEAD` | OK |
| 2026-10-31 | Task 2: Django scaffold and health test | `wsl -d Ubuntu -- bash .../run-tests.sh` | OK (1 test) |
| 2026-10-31 | Task 3: custom user and customer schema | `wsl -d Ubuntu -- bash .../run-tests.sh` | OK (4 tests) |
| 2026-10-31 | Task 4: audit/outbox/money + trigger | `wsl -d Ubuntu -- bash .../run-tests.sh` | OK (20 tests) |
| 2026-10-31 | Task 5: transactional outbox dispatcher | `wsl -d Ubuntu -- bash .../run-tests.sh` | OK (24 tests) |
| 2026-10-31 | Task 6: catalog schema | `wsl -d Ubuntu -- bash .../run-tests.sh` | OK (26 tests) |
| 2026-10-31 | Task 7: plans schema | `wsl -d Ubuntu -- bash .../run-tests.sh` | OK (28 tests) |
| 2026-10-31 | Task 8: subscription state machine | `wsl -d Ubuntu -- bash .../run-tests.sh` | OK (40 tests) |
| 2026-10-31 | Task 9: invoice state machine | `wsl -d Ubuntu -- bash .../run-tests.sh` | OK (48 tests) |
| 2026-10-31 | Task 10: payments/discounts/reports schema | `wsl -d Ubuntu -- bash .../run-tests.sh` | OK (52 tests) |
| 2026-10-31 | Task 11: docker runtime and docs | `python -c "import yaml; yaml.safe_load(open('docker-compose.yml')); print('yaml_ok')"`; `manage.py check`; `manage.py makemigrations --check --dry-run`; `wsl -d Ubuntu -- bash .../run-tests.sh` | OK (52 tests); Docker Compose not executed (not installed) |
| 2026-10-31 | Phase 2 design: Auth, Roles & RBAC | Subagent builder review + design spec | Approved |
| 2026-10-31 | Task 12: final verification and handoff | `git diff --check`; `git status --short`; `git log --oneline -6`; `git grep` for TODO/FIXME; no `.env` committed | Working tree clean; 52 tests passed; no missing migrations; Docker not verified |

## Task 1 notes

- Removed the zero-byte scaffold placeholders `backend/src/server.js`, `database/schema.sql`, and `docs/api-contract.md`; they conflict with the Django stack.
- Added the product design, non-negotiable rules, agent instructions, platform contract, and this progress log.
- Updated `MODULE_ASSIGNMENTS.md` so every module owner sees the same Phase 1 definition.

## Phase 1 deliverables

- Django 5 project with all nine modules and required apps configured
- Custom user model (`accounts.User`) with roles, unique email, and `AUTH_USER_MODEL`
- Complete foundation schema: products/variants/taxes, plans, quotations/subscriptions/lines, invoices/lines, payments, discounts/usage, daily metrics
- Platform: `TimeStampedModel`, `SoftDeleteModel`, `AuditLog` (append-only, model + PostgreSQL trigger), `OutboxEvent`, `record_audit`, `emit_event`, `apply_transition`, `quantize_money`, `InvalidTransition`
- Subscription and invoice state machines enforced through services
- Transactional outbox dispatcher with Celery task, management command, and beat schedule
- Required indexes and `UNIQUE(subscription, period_start, period_end)` on invoices
- Docker Compose (db, redis, migrate, api, worker, beat), Dockerfile, `.dockerignore`, `.env.example`
- Tests passing against PostgreSQL 16 in WSL

## Phase 2 implementation

- SimpleJWT email/password login and refresh for admin, staff, and customer roles; access tokens last 30 minutes and refresh tokens last one day, with role/email/customer ID claims
- Public customer signup that atomically creates a customer account and linked profile
- Django password validation requiring more than eight characters, uppercase, lowercase, and one special character from the approved set
- Generic, time-limited, single-use password reset email and confirmation endpoints; delivery failures keep the public response generic, and changing the password invalidates existing access and refresh JWTs
- SMTP backend, host, port, credentials, and TLS are configurable through environment variables; no mail credentials are committed
- Admin-only staff creation; staff/customer/unauthenticated callers are denied, and role escalation fields are rejected
- Authenticated `/me/` profile reads; customers can update only their own billing details
- Read-only customer list/detail APIs with queryset scoping, 404 on cross-customer ID tampering, and staff/admin visibility
- Explicit role permissions; paginated, `select_related("user")` customer listing
- No Phase 1 model or migration changes

## Phase 2 verification

| Date | Task | Command | Result |
|---|---|---|---|
| 2026-10-31 | Phase 2 full suite (WSL PostgreSQL 16) | `wsl -d Ubuntu -- bash -lc "cd .../phase-2-auth-rbac/backend && /home/thushar/.venvs/subscription/bin/python -m pytest -q"` | 103 passed |
| 2026-10-31 | Phase 2 Django/migration checks | `manage.py check`; `manage.py makemigrations --check --dry-run` | No issues; no changes detected |
| 2026-10-31 | Phase 2 Docker runtime | `docker compose config`; `docker compose up --build -d`; `docker compose run --rm api pytest -q`; `curl http://localhost:8000/health/` | Build and migrations succeeded; 103 tests passed; health returned HTTP 200 `{"status":"ok"}`; containers healthy |

### Earlier attempts (superseded by the successful verification above)

| Date | Task | Command | Result |
|---|---|---|---|
| 2026-10-31 | Phase 2 syntax and Django checks | `python -m compileall -q backend/apps/accounts backend/config`; `python backend/manage.py check` | OK |
| 2026-10-31 | Migration consistency | `python backend/manage.py makemigrations --check --dry-run` | No changes detected; PostgreSQL connection timed out while checking history |
| 2026-10-31 | Accounts API tests | `python -m pytest --ds=test_sqlite_settings --nomigrations backend/apps/accounts/tests -q` | 15 passed against temporary SQLite configuration |
| 2026-10-31 | Full regression attempt | `python -m pytest --ds=test_sqlite_settings --nomigrations -q` | 64 passed, 1 baseline PostgreSQL-trigger test failed because SQLite does not enforce the audit trigger |
| 2026-10-31 | PostgreSQL test suite | `python -m pytest backend/apps/accounts/tests -q` | Blocked: PostgreSQL connection timed out; Docker daemon unavailable |

## Phase 3 implementation

- Admin CRUD for products, variants, taxes, and plans
- Staff read-only access; customer and anonymous access denied
- Decimal money fields and validation for non-negative prices, tax rates, quantity, and plan dates
- Paginated list endpoints with `select_related` for variant and plan products
- No schema or migration changes

## Phase 3 verification

| Date | Task | Command | Result |
|---|---|---|---|
| 2026-10-31 | Phase 3 API tests | `python -m pytest apps/catalog/tests/test_api.py apps/plans/tests/test_api.py -q` | 12 passed |
| 2026-10-31 | Full suite (WSL PostgreSQL 16) | `python -m pytest -q` | 115 passed |
| 2026-10-31 | Django/migration checks | `manage.py check`; `manage.py makemigrations --check --dry-run` | No issues; no changes detected |

## Phase 4 implementation

- Quotation template APIs for admin and staff
- Subscription APIs with nested line creation and editing while draft or quotation
- Lifecycle actions for quotation, confirmation, activation, pause, close, and renewal
- All status changes use the existing transition service and preserve audit/outbox atomicity
- Customers can list and read only their own subscriptions; only admin/staff can create or act
- Validation for subscription dates, active plans, positive quantities, non-negative amounts, and variant/product consistency
- No schema or migration changes

## Phase 4 verification

| Date | Task | Command | Result |
|---|---|---|---|
| 2026-10-31 | Phase 4 API tests | `python -m pytest apps/subscriptions/tests/test_api.py -q` | 8 passed |
| 2026-10-31 | Full suite (WSL PostgreSQL 16) | `python -m pytest -q` | 123 passed |
| 2026-10-31 | Django/migration checks | `manage.py check`; `manage.py makemigrations --check --dry-run` | No issues; no changes detected |

## Phase 5 implementation

- Idempotent invoice generation for active subscriptions due on or before the billing date
- Per-subscription row lock inside a transaction; the existing unique invoice-period constraint remains intact
- Invoice lines snapshot product/variant description, quantity, unit price, tax rate, discount, and amount
- Totals use `Decimal` and the shared money quantizer
- `next_billing_date` advances in the same transaction that creates the invoice
- `invoice.created` event written to the outbox in that transaction
- Celery daily task and `run_billing` management command for scheduled or on-demand runs
- Double-run test proves a second run creates no duplicate invoices
- No schema or migration changes

## Phase 5 verification

| Date | Task | Command | Result |
|---|---|---|---|
| 2026-10-31 | Billing engine tests | `python -m pytest apps/billing/tests/test_billing_engine.py -q` | 5 passed |
| 2026-10-31 | Full suite (WSL PostgreSQL 16) | `python -m pytest -q` | 128 passed |
| 2026-10-31 | Django/migration checks | `manage.py check`; `manage.py makemigrations --check --dry-run` | No issues; no changes detected |

## Phase 6 implementation

- Invoice list/detail APIs with customer ownership isolation
- Admin/staff invoice confirmation and cancellation actions through the invoice service
- Admin/staff payment recording against confirmed invoices only
- Partial payments supported; overpayment and payment against draft/paid/cancelled invoices rejected
- Invoice automatically transitions to Paid when payments clear the balance, with audit and outbox atomicity
- `payment.recorded` outbox event for every payment
- Staff can list and retrieve payments; customers cannot record or list payments
- Invoice PDF download for staff/admin and the owning customer
- No schema or migration changes

## Phase 6 verification

| Date | Task | Command | Result |
|---|---|---|---|
| 2026-10-31 | Payments and invoice API tests | `python -m pytest apps/payments/tests/test_api.py -q` | 8 passed |
| 2026-10-31 | Invoice PDF tests | `python -m pytest apps/billing/tests/test_pdf.py -q` | 2 passed |
| 2026-10-31 | Full suite (WSL PostgreSQL 16) | `python -m pytest -q` | 138 passed |
| 2026-10-31 | Django/migration checks | `manage.py check`; `manage.py makemigrations --check --dry-run` | No issues; no changes detected |

## Phase 7 implementation

- Eligible discounts apply automatically during invoice generation
- Fixed and percentage discounts for whole subscriptions or selected products
- Minimum amount and minimum quantity rules
- Active date-window enforcement
- Usage limits enforced with row locks and persisted `DiscountUsage`
- Discounts are allocated to invoice lines and reduce taxable totals
- Discounted usage survives repeat billing runs without exceeding the limit
- No schema or migration changes

## Phase 7 verification

| Date | Task | Command | Result |
|---|---|---|---|
| 2026-10-31 | Discount engine tests | `python -m pytest apps/discounts/tests/test_engine.py -q` | 4 passed |
| 2026-10-31 | Full suite (WSL PostgreSQL 16) | `python -m pytest -q` | 142 passed |
| 2026-10-31 | Django/migration checks | `manage.py check`; `manage.py makemigrations --check --dry-run` | No issues; no changes detected |

Payment receipt email remains deferred. Phase 8 (dashboard and reports) is next.
