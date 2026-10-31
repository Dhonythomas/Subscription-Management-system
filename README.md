# Subscription Management System

A subscription billing platform for Brightloop Software. It runs the full life of a subscription business, from products and plans through quotations, subscriptions, automatic invoices, payments, discounts, and revenue reporting.

Core flow: **Product > Plan > Quotation > Subscription > Invoice > Payment > Reports**

## Stack

- Django 5 + Django REST Framework
- PostgreSQL 16
- Redis 7 + Celery worker and beat
- Docker Compose

## Current status

**Phase 1 — Foundation** is complete. The repository now contains the full foundation schema, the custom user model, the platform audit/outbox layer, the subscription and invoice state machines, all required database indexes, the outbox dispatcher, and the Docker Compose runtime.

Later phases add APIs and business workflows on top of this schema freeze.

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
3. Check the health endpoint:
   ```bash
   curl http://localhost:8000/health/
   ```
   Expected response: `{"status": "ok"}`
4. Run the test suite inside the API container:
   ```bash
   docker compose run --rm api pytest
   ```
5. Stop and clean up:
   ```bash
   docker compose down -v
   ```

## Local development and tests (this machine)

PostgreSQL 16 is running in WSL Ubuntu on `127.0.0.1:5432` (database `subscription_db`, user `subscription`). Because the Windows-to-WSL localhost relay can be flaky, tests are run from a Linux virtual environment inside WSL:

```bash
wsl -d Ubuntu -- bash -lc "cd /mnt/c/Users/Thushar/Documents/vs/makeathon/subscription-management-system/.worktrees/phase-1-foundation/backend && /home/thushar/.venvs/subscription/bin/python -m pytest -q"
```

From the backend directory with the Windows virtual environment:

```powershell
..\.venv\Scripts\python.exe manage.py check
..\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
..\.venv\Scripts\python.exe -m pytest -q
```

## Verification notes

- **Docker runtime:** Docker Desktop is not installed on this machine, so `docker compose up` runtime verification was not executed. The Compose file, Dockerfile, `.dockerignore`, and `.env.example` were created and structurally validated with PyYAML. All migrations and tests were verified against PostgreSQL 16 in WSL.
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
