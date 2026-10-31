# Progress Log

## Current phase

**Phase 2 — Auth, Roles & RBAC**

**Status:** In Progress (Design Approved)

## Phase 1 scope decision

Phase 1 is the full foundation schema plus the platform layer, not platform infrastructure alone. It creates the core models and migrations for every module, including the custom user, subscription and invoice state machines, required indexes, audit/outbox infrastructure, and Docker Compose runtime. This is the **schema freeze**: later phases add APIs, business services, and new migrations, but they do not rewrite the foundation schema.

## Verification environment

- Local development and test verification use PostgreSQL 16 running in WSL Ubuntu on `127.0.0.1:5432` (database `subscription_db`, role `subscription`). Tests are run from a Linux virtual environment inside WSL (`/home/thushar/.venvs/subscription`) because the Windows-to-WSL localhost relay is unreliable on this machine.
- Docker Desktop is not installed on this machine, so `docker compose up` runtime verification is blocked until it is available. The Compose configuration, Dockerfile, `.dockerignore`, and `.env.example` were created and structurally validated with PyYAML.
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
