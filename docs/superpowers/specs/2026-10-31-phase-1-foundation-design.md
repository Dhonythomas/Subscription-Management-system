# Phase 1 Foundation Design

**Date:** 2026-10-31

**Owner:** Member 1 (Tech Lead / platform)

**Status:** Approved for implementation by delegated decision

**Spec source:** `RULES.md`, `AGENT.md`, `Subscription_System_Design_Plan.pdf`, `MODULE_ASSIGNMENTS.md`

## Intent

Build the foundation every other module depends on, so module owners can add services and APIs without changing the schema, duplicating audit/outbox logic, or hitting a Django custom-user migration trap.

## Goals

1. Complete the core database schema and migrations for every module, including the custom user model.
2. Deliver the `platform` app: timestamped/soft-delete bases, `AuditLog`, `OutboxEvent`, transactional audit/outbox helpers, state-transition helper, and outbox dispatcher.
3. Deliver subscription and invoice state-machine services with illegal-transition tests.
4. Deliver a Docker Compose stack: PostgreSQL, Redis, API, Celery worker, Celery beat, and a one-shot migration service.
5. Deliver a pytest suite that runs against PostgreSQL and proves the invariants that later modules depend on.
6. Make the repository's documents agree on Phase 1: update `AGENT.md` and `MODULE_ASSIGNMENTS.md`, add the product design, rules, progress log, and platform contract.

## Non-goals

- Business API endpoints, serializers, viewsets, or URL routes other than the infrastructure `/health/` endpoint.
- Login, JWT, password reset, RBAC enforcement, or staff/customer portal behaviour (Phase 2).
- Billing engine, invoice generation, payment recording, discount application, report queries, PDFs, emails, or frontend (Phases 5-8).
- Optional n8n, payment gateway, or proration work (Phase 10).
- Building module features ahead of their phase. Phase 1 creates schema and shared services only.

## Constraints

- Django 5.2 + DRF, PostgreSQL 16, Redis 7, Celery, Docker Compose.
- All money is `DecimalField(max_digits=12, decimal_places=2)` / `NUMERIC(12,2)`. No floats. One rounding rule: `ROUND_HALF_UP` to two places, implemented once in `platform/money.py`.
- Status changes only through service functions. Every transition writes `AuditLog` and `OutboxEvent` in the same database transaction.
- Module boundaries: apps live under `backend/apps/<module>/`; app labels remain `accounts`, `catalog`, `plans`, `subscriptions`, `billing`, `payments`, `discounts`, `reports`, `platform`. The nested package avoids shadowing Python's standard-library `platform` module.
- Phase 1 is the schema freeze. Later phases add APIs, services, and new migrations; they do not rewrite committed migrations or the foundation schema.
- Required indexes are created in Phase 1: `subscriptions(status, next_billing_date)`, `invoices(status, due_date)`, `invoices(customer)`, `payments(invoice, paid_on)`, `plans(period)`.
- `docker compose up` must work from a clean checkout without a manually created `.env`. Development defaults are non-secret; `.env.example` documents overrides.
- No secrets, generated artifacts, or `.env` committed.

## Approaches considered

1. **Platform infrastructure only.** Smallest scope and strictly Module 1, but `AGENT.md` Phase 1 would remain incomplete, the custom user would arrive after the first migrations, and required invoice/payment indexes could not be created.
2. **Platform plus subscription foundation.** Satisfies the illegal-transition criterion, but invoice/payment models and their indexes still arrive later, forcing a second schema pass and leaving the custom-user sequencing unresolved.
3. **Full foundation schema plus platform plus state machines (chosen).** Larger Phase 1 and it touches every module's model layer, but it produces one schema freeze, resolves the custom-user trap, creates all required indexes, and unblocks every module owner. It deliberately stops at schema and shared services; no business APIs are built early.

## Decisions

- **Custom user in Phase 1.** `accounts.User` is created before the first migration (`AUTH_USER_MODEL = "accounts.User"`); Phase 2 adds auth endpoints and RBAC on top.
- **Audit log.** Fields: `entity_type`, `entity_id`, `from_status`, `to_status`, `actor` (nullable FK, `SET_NULL`), `at`, `metadata`. Append-only enforced by a model guard and a PostgreSQL trigger. `from`/`to` are named `from_status`/`to_status` because `from` is a Python keyword.
- **Outbox event.** Fields: `event_type`, `aggregate_type`, `aggregate_id`, `payload`, `created_at`, `published_at`, `attempts`, `last_error`. Writes require an active transaction.
- **State transitions.** `platform.services.apply_transition()` locks the row with `select_for_update`, checks an allowed-transitions map, runs an optional validator, saves the status and extra fields, and writes audit and outbox rows in the same transaction. Module services wrap it with their rules.
- **Outbox dispatcher.** `platform.events.dispatch_pending()` locks unpublished events with `skip_locked`, invokes registered handlers, marks success, and records failures for retry. A Celery task and management command call it. Unhandled event types are marked published with a warning; modules must register handlers before emitting an event type.
- **Soft delete.** An abstract `SoftDeleteModel` is provided for future mutable catalog entities, but it is not applied to audit, outbox, invoices, payments, or other financial records. No delete endpoint or policy exists in Phase 1.
- **Health endpoint.** `GET /health/` is public and exists for container health checks. DRF's default permission is `IsAuthenticated`; the health view explicitly allows any.
- **Docker runtime.** Compose services: `db`, `redis`, `migrate`, `api`, `worker`, `beat`. Development credentials/defaults come from compose interpolation; `.env` is optional. The migration service runs once, and the other services wait for it.
- **Placeholder cleanup.** The empty `backend/src/server.js`, `database/schema.sql`, and `docs/api-contract.md` files are removed. They are zero-byte artifacts from the initial scaffold and conflict with the Django stack. `docs/platform-contract.md` replaces the empty API-contract placeholder.
- **Local verification.** PostgreSQL 16 runs in WSL because Docker Desktop is not installed on this machine. Tests run against that real PostgreSQL. Docker Compose configuration is delivered as required, but runtime Docker verification is an explicit gap until Docker Desktop is available.

## Acceptance criteria

- `python manage.py check` passes.
- `python manage.py makemigrations --check --dry-run` reports no missing migrations.
- The full pytest suite passes against PostgreSQL.
- Migrations create the custom user, all core tables, required indexes, and the audit append-only trigger.
- Allowed transitions succeed and write audit + outbox in one transaction; illegal transitions and plan-flag violations write nothing.
- Outbox dispatch calls handlers, marks success, and records failures without losing events.
- `docker compose up` is configured for a clean checkout; if Docker is available, the stack starts and `/health/` responds.
- `AGENT.md`, `MODULE_ASSIGNMENTS.md`, `docs/design.md`, `docs/platform-contract.md`, `PROGRESS.md`, and `README.md` agree on the Phase 1 scope.

## Left to the builder / later phases

- Phase 2: auth endpoints, JWT, password reset, role permissions, customer isolation.
- Phase 3: catalog/plans APIs.
- Phase 4: quotation templates, quote-to-active business flow, subscription APIs.
- Phase 5: billing engine, invoice generation, idempotency, scheduler.
- Phase 6: payments, invoice actions, PDF/email.
- Phase 7: discount application and usage limits.
- Phase 8: dashboard/read model and performance proof.
- Phase 9: seed data, README polish, demo.
- Phase 10: optional extras.
