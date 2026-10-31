# Platform Contract

This document defines the interfaces the `platform` app provides to every other module. Treat these signatures, event names, and invariants as the contract. Other modules may import these helpers; they must not reimplement the transaction, audit, outbox, or transition behaviour.

## Base models

```python
from apps.platform.models import TimeStampedModel, SoftDeleteModel
```

- `TimeStampedModel` is abstract and adds `created_at` (`auto_now_add=True`) and `updated_at` (`auto_now=True`).
- `SoftDeleteModel` is abstract, extends `TimeStampedModel`, and adds `is_deleted`, `deleted_at`, `soft_delete()`, and `restore()`.
- Soft deletion is for future mutable catalog entities only. Do not apply it to audit, outbox, invoices, payments, or other financial records.

## Money

```python
from apps.platform.money import quantize_money

quantize_money(Decimal("10.005"))  # Decimal("10.01")
```

- All money columns are `DecimalField(max_digits=12, decimal_places=2)` / `NUMERIC(12,2)`.
- `quantize_money` is the single rounding rule: `ROUND_HALF_UP` to two decimal places.
- Never convert money through `float`. Accept `Decimal`, integer, or numeric string, and return `Decimal`.

## Audit and outbox writes

```python
from apps.platform.services import record_audit, emit_event

record_audit(
    *,
    entity_type: str,
    entity_id: str,
    from_status: str,
    to_status: str,
    actor=None,
    metadata: dict | None = None,
) -> AuditLog

emit_event(
    *,
    event_type: str,
    aggregate_type: str,
    aggregate_id: str,
    payload: dict | None = None,
) -> OutboxEvent
```

- Both helpers require an active database transaction. Outside `transaction.atomic()` they raise `django.db.transaction.TransactionManagementError`.
- `record_audit` and `emit_event` participate in the caller's transaction. If the caller rolls back, both rows disappear.
- `AuditLog` is append-only. The model rejects update/delete, and a PostgreSQL trigger blocks `UPDATE`/`DELETE` at the database level.
- Use stable entity names: `subscriptions.subscription`, `billing.invoice`, and similar `app.model` values.
- `entity_id` and `aggregate_id` are stored as strings so integers and UUIDs share one interface.

## State transitions

```python
from apps.platform.services import apply_transition

apply_transition(
    instance,
    *,
    to_status: str,
    allowed_transitions: Mapping[str, set[str]],
    actor=None,
    event_type: str,
    validate: Callable[[Model], None] | None = None,
    metadata: dict | None = None,
    extra_update_fields: dict | None = None,
) -> Model
```

`apply_transition`:

1. Requires an active transaction.
2. Re-reads the row with `select_for_update()` using the instance primary key, so a stale in-memory instance cannot skip a transition.
3. Rejects a move that is not in the supplied allowed-transitions map with `InvalidTransition`.
4. Runs `validate(locked_instance)` if supplied; a raised `InvalidTransition` aborts before any write.
5. Saves the new status and any `extra_update_fields`.
6. Writes `AuditLog` and `OutboxEvent` in the same transaction.
7. Returns the locked, updated instance.

Module services must wrap this helper and own their business rules. Views and serializers never assign `status` directly.

### Subscription map

```python
{
    "draft": {"quotation"},
    "quotation": {"confirmed"},
    "confirmed": {"active"},
    "active": {"paused", "closed"},
    "paused": {"active"},
    "closed": {"active"},  # renewal only when the plan is renewable
}
```

### Invoice map

```python
{
    "draft": {"confirmed", "cancelled"},
    "confirmed": {"paid", "cancelled"},
    "paid": set(),
    "cancelled": set(),
}
```

## Domain events

Phase 1 emits these event types:

| Event type | Aggregate type | Emitted when |
|---|---|---|
| `subscription.status_changed` | `subscriptions.subscription` | A subscription transition is committed |
| `invoice.status_changed` | `billing.invoice` | An invoice transition is committed |

The event payload envelope is JSON-serialisable and includes:

```json
{
  "aggregate_type": "subscriptions.subscription",
  "aggregate_id": "42",
  "from_status": "draft",
  "to_status": "quotation",
  "actor_id": 7,
  "reason": "quote sent",
  "occurred_at": "2026-10-31T10:15:00+00:00"
}
```

`actor_id` is `null` for system transitions. `reason` is `null` or an empty string when no reason was supplied.

## Outbox dispatcher

```python
from apps.platform.events import (
    register_handler,
    clear_handlers,
    dispatch_pending,
)

register_handler("subscription.status_changed", my_handler)
dispatch_pending(limit=100)
```

- A handler receives the `OutboxEvent` instance and returns normally on success.
- Handlers must be idempotent. The dispatcher provides at-least-once delivery, not exactly-once side effects. Use `event.id`, aggregate IDs, or an external idempotency key before repeating an external action.
- Handlers are registered during app startup or in module `AppConfig.ready()`.
- `dispatch_pending` locks unpublished rows with `select_for_update(skip_locked=True)`, so two workers do not process the same event at the same time.
- On success it sets `published_at` and clears `last_error`. On failure it increments `attempts`, stores `last_error`, and leaves `published_at` null for retry.
- An event type with no registered handler is logged as a warning and marked published; modules must register handlers before emitting a type they rely on.
- `apps.platform.tasks.dispatch_outbox_task` is the Celery entry point. `python manage.py dispatch_outbox` is the manual entry point.

## Required indexes and constraints

These exist in the Phase 1 migrations and must not be dropped or weakened:

- `UNIQUE(users.email)`
- `UNIQUE(subscriptions.number)`
- `UNIQUE(invoices.subscription, invoices.period_start, invoices.period_end)`
- `INDEX(subscriptions.status, subscriptions.next_billing_date)`
- `INDEX(invoices.status, invoices.due_date)`
- `INDEX(invoices.customer)`
- `INDEX(payments.invoice, payments.paid_on)`
- `INDEX(plans.period)`
- `INDEX(audit_log.entity_type, audit_log.entity_id)`
- `INDEX(outbox_event.published_at)`

## Module boundary rules

- Each app owns its tables and migrations.
- Another module may read data through a service function or a domain event.
- Another module must not write, update, or delete another app's models directly.
- Foreign keys may use Django string references such as `"accounts.Customer"` to avoid import cycles. That does not grant write permission.
- Business logic belongs in services, not views, serializers, or model `save()` overrides.
- Every endpoint has an explicit permission class; no endpoint is open by accident. The Phase 1 `/health/` endpoint is the sole intentional exception because container health checks need it.

## Verification contract

A module is not complete until these pass from `backend/`:

```powershell
..\.venv\Scripts\python.exe manage.py check
..\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
..\.venv\Scripts\python.exe -m pytest -q
```

The suite runs against PostgreSQL. Docker Compose is the supported team runtime; see `README.md` for the current run instructions.
