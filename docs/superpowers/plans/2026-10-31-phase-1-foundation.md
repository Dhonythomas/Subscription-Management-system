# Phase 1 Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver the Phase 1 foundation: the complete core schema, platform audit/outbox layer, subscription and invoice state machines, Docker Compose runtime, and a PostgreSQL-backed test suite.

**Architecture:** Django 5.2 modular monolith under `backend/apps/`, with `platform` owning shared base models, money helpers, audit/outbox services, the outbox dispatcher, and the generic state-transition helper. Phase 1 creates all core models and migrations; later phases add APIs and business services without rewriting the schema.

**Tech Stack:** Python 3.12+ (host 3.13), Django 5.2.18, DRF 3.16.1, psycopg 3.2.13, Celery 5.5.3, Redis client 6.4.0, pytest 8.4.2, pytest-django 4.11.1, PostgreSQL 16, Redis 7, Docker Compose.

**Spec:** `docs/superpowers/specs/2026-10-31-phase-1-foundation-design.md`

## Global Constraints

- Money fields are always `DecimalField(max_digits=12, decimal_places=2)`; never float. One rounding rule: `ROUND_HALF_UP` to two places in `apps.platform.money.quantize_money`.
- Status changes only through service functions. Every transition writes `AuditLog` and `OutboxEvent` in the same transaction.
- Each module owns its tables; cross-module writes go through services/events, never another app's models.
- `AUTH_USER_MODEL = "accounts.User"` must be set before the first migration.
- Django apps live under `backend/apps/`; app labels are `accounts`, `catalog`, `plans`, `subscriptions`, `billing`, `payments`, `discounts`, `reports`, `platform`. This avoids shadowing Python's `platform` stdlib module.
- Required indexes: `subscriptions(status, next_billing_date)`, `invoices(status, due_date)`, `invoices(customer)`, `payments(invoice, paid_on)`, `plans(period)`.
- Tests are written with the code, never skipped or weakened. All tests pass before each commit.
- Commit messages start with `phase-1:`.
- No secrets committed. `.env` is ignored; `.env.example` documents development values.
- `docker compose up` must work from a clean checkout without a manually created `.env`.
- Phase 1 is the schema freeze: create all core models/migrations now. Do not build business APIs, billing logic, payment recording, discount application, report queries, or frontend.

## Review Focus

1. A transition attempted outside a transaction, or with a stale instance, must never leave status, audit, and outbox inconsistent. Owned by Task 4 and Task 8.
2. An illegal transition or unmet plan flag must write nothing and raise `InvalidTransition`. Owned by Task 8 and Task 9.
3. An outbox handler failure must leave the event unpublished, record the error, and allow retry without losing the event. Owned by Task 5.
4. Duplicate invoice periods, duplicate emails, and duplicate subscription numbers must be rejected by the database, not only by application checks. Owned by Tasks 3, 8, and 9.
5. Every money field and calculation must remain `Decimal`; no float path may appear. Owned by Tasks 4, 6, 7, 9, and 10.

---

### Task 1: Repository docs and Phase 1 scope alignment

**Files:**
- Create: `AGENT.md`
- Create: `RULES.md`
- Create: `docs/design.md`
- Create: `docs/platform-contract.md`
- Create: `PROGRESS.md`
- Modify: `README.md`
- Modify: `MODULE_ASSIGNMENTS.md`
- Delete: `backend/src/server.js`
- Delete: `database/schema.sql`
- Delete: `docs/api-contract.md`

**Interfaces:**
- Consumes: the existing `MODULE_ASSIGNMENTS.md`, the parent workspace's `RULES.md`/`AGENT.md`, and the extracted design plan.
- Produces: authoritative repository docs that define Phase 1 as the full foundation schema, platform, state machines, and Docker; a written platform contract other members can code against.

- [ ] **Step 1: Add the product design, rules, and agent instructions**

Create `docs/design.md` from the 5-page `Subscription_System_Design_Plan.pdf`, preserving all sections 1–14 and all concrete values (indexes, state transitions, billing steps, RBAC matrix, performance targets, demo script, risks). Create `RULES.md` with the 16 non-negotiables from the parent workspace. Create `AGENT.md` with the project/stack/architecture instructions, the start/end-of-phase checklists, and this Phase 1 definition:

> Phase 1: foundation schema (all modules), constraints, platform audit/outbox, subscription and invoice state-machine services, Docker. Done when migrations run, `docker compose up` starts clean, outbox/audit tests pass, and illegal transitions are rejected.

Add a “Phase 1 schema freeze” note: all core models/migrations are created in Phase 1; later phases add APIs/services/new migrations and never rewrite the foundation. Add the app layout note: apps live under `backend/apps/`, with app label `platform` to avoid shadowing the stdlib.

- [ ] **Step 2: Write the platform contract**

Create `docs/platform-contract.md` covering: base-model imports; `record_audit`/`emit_event` signatures and the active-transaction requirement; `apply_transition` signature and per-module transition maps; event types (`subscription.status_changed`, `invoice.status_changed`) and payload envelope; handler registration and idempotency expectations; the required index checklist; the money quantization rule; and the rule that business modules never import another module's models for writes.

- [ ] **Step 3: Update `MODULE_ASSIGNMENTS.md`**

Change the Phase 1 map to `Phase 1: Foundation schema (all modules) + platform + state machines -> platform (Tech Lead)`. Expand Module 1 tasks to include the full foundation schema, custom user, audit/outbox, state-machine helper, subscription/invoice services, Docker, and tests. Change Module 5 to state that Phase 4 builds the quotation/subscription business flow and APIs on top of the Phase 1 schema and state-machine foundation, not a duplicate schema. Update the recommended split so Member 1 owns `platform` + foundation + integration (phases 1 and 9). Remove the stale “PDF could not be machine-read” and “all files are 0 bytes” notes.

- [ ] **Step 4: Write the progress log**

Create `PROGRESS.md` with current phase “Phase 1 — Foundation”, status “In progress”, the schema-freeze decision, the local PostgreSQL/WSL verification note, and a verification log placeholder. Do not claim verification that has not happened.

Replace the empty root `README.md` with a short real README: project summary, core flow, stack, current Phase 1 status, and a note that full run instructions follow in Task 11. Do not leave it zero bytes.

- [ ] **Step 5: Remove the empty scaffold placeholders**

Delete the zero-byte `backend/src/server.js`, `database/schema.sql`, and `docs/api-contract.md`. They conflict with the Django stack and Rule 12. Record the removal in `PROGRESS.md`.

- [ ] **Step 6: Verify no tracked zero-byte source placeholders remain**

Run from the worktree root:

```powershell
git ls-files | ForEach-Object { [PSCustomObject]@{ Path = $_; Bytes = (Get-Item -LiteralPath $_).Length } } | Where-Object { $_.Bytes -eq 0 }
```

Expected: no output. Run `git diff --check`; expected: no output.

- [ ] **Step 7: Commit**

```powershell
git add AGENT.md RULES.md docs/design.md docs/platform-contract.md PROGRESS.md MODULE_ASSIGNMENTS.md README.md
git rm backend/src/server.js database/schema.sql docs/api-contract.md
git commit -m "phase-1: align foundation scope and docs"
```

---

### Task 2: Django project scaffold and dependencies

**Files:**
- Create: `backend/manage.py`
- Create: `backend/config/__init__.py`
- Create: `backend/config/settings.py`
- Create: `backend/config/urls.py`
- Create: `backend/config/wsgi.py`
- Create: `backend/config/asgi.py`
- Create: `backend/config/celery.py`
- Create: `backend/requirements.txt`
- Create: `backend/pytest.ini`
- Create: `backend/conftest.py`
- Create: `backend/apps/__init__.py`
- Create: `backend/apps/platform/__init__.py`
- Create: `backend/apps/platform/apps.py`
- Create: `backend/apps/platform/models.py`
- Create: `backend/apps/platform/views.py`
- Create: `backend/apps/platform/migrations/__init__.py`
- Create: `backend/apps/platform/tests/__init__.py`
- Create: `backend/apps/platform/tests/test_health.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `config.settings` with PostgreSQL/Redis/Celery/DRF configuration; `config.celery.app`; a public `GET /health/` returning `{"status": "ok"}`; the `apps.platform` Django app.

- [ ] **Step 1: Pin the dependency set**

Create `backend/requirements.txt`:

```text
Django==5.2.18
djangorestframework==3.16.1
psycopg[binary]==3.2.13
celery[redis]==5.5.3
redis==6.4.0
pytest==8.4.2
pytest-django==4.11.1
```

Create the repo-root virtual environment and install:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
```

Expected: installation completes with no dependency conflicts.

- [ ] **Step 2: Write the failing health test**

Create `backend/apps/platform/tests/test_health.py`:

```python
from django.test import Client


def test_health_endpoint_returns_ok():
    response = Client().get("/health/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 3: Run the test to verify it fails**

From `backend/`:

```powershell
..\.venv\Scripts\python.exe -m pytest apps/platform/tests/test_health.py -q
```

Expected: FAIL because the URL and app do not exist yet.

- [ ] **Step 4: Implement the Django scaffold**

Create `manage.py` with `DJANGO_SETTINGS_MODULE=config.settings`. Create `config/settings.py` with:

- `BASE_DIR = Path(__file__).resolve().parent.parent`
- `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS` from environment with the non-secret development defaults documented in `.env.example`
- PostgreSQL `DATABASES` using `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT`, defaulting to `subscription_db`, `subscription`, `subscription`, `localhost`, `5432`
- `INSTALLED_APPS`: Django admin/auth/contenttypes/sessions/messages/staticfiles, `rest_framework`, `apps.platform.apps.PlatformConfig`
- `MIDDLEWARE`, `ROOT_URLCONF`, `TEMPLATES`, `WSGI_APPLICATION`, `AUTH_PASSWORD_VALIDATORS` (minimum length 9), `LANGUAGE_CODE="en-us"`, `TIME_ZONE="UTC"`, `USE_TZ=True`, `STATIC_URL`, `DEFAULT_AUTO_FIELD`
- `REST_FRAMEWORK` with `DEFAULT_PERMISSION_CLASSES = ["rest_framework.permissions.IsAuthenticated"]`, `DEFAULT_PAGINATION_CLASS = "rest_framework.pagination.PageNumberPagination"`, `PAGE_SIZE = 25`
- `REDIS_URL` from environment, default `redis://localhost:6379/0`
- Celery broker/result backend from `REDIS_URL`, `CELERY_TASK_TRACK_STARTED=True`, `CELERY_TIMEZONE="UTC"`

Create `apps/platform/views.py` with a DRF `@api_view(["GET"])` function `health(request)` decorated with `@permission_classes([AllowAny])`, returning `Response({"status": "ok"})`. Create `config/urls.py` with `path("admin/", admin.site.urls)` and `path("health/", health, name="health")`. Create `config/wsgi.py`, `config/asgi.py`, `config/celery.py`, and `config/__init__.py` using the standard Django/Celery boilerplate.

Create `backend/pytest.ini`:

```ini
[pytest]
DJANGO_SETTINGS_MODULE = config.settings
python_files = tests.py test_*.py *_tests.py
testpaths = apps
addopts = -q
```

Create `backend/conftest.py` empty for now. Create `apps/platform/apps.py` with `PlatformConfig(name="apps.platform", label="platform", default_auto_field="django.db.models.BigAutoField")`.

- [ ] **Step 5: Run the test to verify it passes**

From `backend/`:

```powershell
..\.venv\Scripts\python.exe -m pytest apps/platform/tests/test_health.py -q
..\.venv\Scripts\python.exe manage.py check
```

Expected: 1 passed; `System check identified no issues`.

- [ ] **Step 6: Commit**

```powershell
git add backend
git commit -m "phase-1: scaffold django project"
```

---

### Task 3: Accounts schema and custom user

**Files:**
- Create: `backend/apps/accounts/__init__.py`
- Create: `backend/apps/accounts/apps.py`
- Create: `backend/apps/accounts/models.py`
- Create: `backend/apps/accounts/migrations/__init__.py`
- Create: `backend/apps/accounts/tests/__init__.py`
- Create: `backend/apps/accounts/tests/test_models.py`
- Modify: `backend/apps/platform/models.py`
- Modify: `backend/config/settings.py`
- Modify: `backend/conftest.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `apps.platform.models.TimeStampedModel` and `SoftDeleteModel` (abstract bases); `apps.accounts.models.User`, `Role`, `Customer`; `UserManager.create_user(email, password=None, **extra_fields)`; `AUTH_USER_MODEL = "accounts.User"`. The rest of the platform models arrive in Task 4.

- [ ] **Step 1: Write the failing account tests**

Create `backend/apps/accounts/tests/test_models.py` with:

```python
import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError

from apps.accounts.models import Customer, Role

User = get_user_model()


@pytest.mark.django_db
def test_create_user_hashes_password_and_defaults_to_customer():
    user = User.objects.create_user(email="person@example.com", password="Secret123!")
    assert user.role == Role.CUSTOMER
    assert user.check_password("Secret123!")
    assert user.password != "Secret123!"


@pytest.mark.django_db
def test_email_is_unique():
    User.objects.create_user(email="same@example.com", password="Secret123!")
    with pytest.raises(IntegrityError):
        User.objects.create_user(email="same@example.com", password="Secret123!")


@pytest.mark.django_db
def test_customer_links_to_user():
    user = User.objects.create_user(email="customer@example.com", password="Secret123!")
    customer = Customer.objects.create(user=user, name="Acme Ltd")
    assert customer.user == user
    assert str(customer) == "Acme Ltd"
```

- [ ] **Step 2: Run the tests to verify they fail**

From `backend/`:

```powershell
..\.venv\Scripts\python.exe -m pytest apps/accounts/tests/test_models.py -q
```

Expected: FAIL because the accounts app/models do not exist.

- [ ] **Step 3: Implement the custom user and customer**

Create `apps/accounts/models.py`:

- `Role(models.TextChoices)` with `ADMIN="admin"`, `STAFF="staff"`, `CUSTOMER="customer"`.
- `UserManager(BaseUserManager)` with `create_user(email, password=None, **extra_fields)` normalizing email, requiring email, hashing via `set_password`, and `create_superuser` setting `is_staff`, `is_superuser`, and `role=ADMIN`.
- `User(AbstractBaseUser, PermissionsMixin)` with `email=EmailField(unique=True)`, `role=CharField(max_length=20, choices=Role.choices, default=Role.CUSTOMER)`, `is_staff=BooleanField(default=False)`, `is_active=BooleanField(default=True)`, `date_joined=DateTimeField(default=timezone.now)`, `objects=UserManager()`, `USERNAME_FIELD="email"`, `REQUIRED_FIELDS=[]`, `Meta.db_table="users"`.
- `Customer(TimeStampedModel)` with `user=OneToOneField(settings.AUTH_USER_MODEL, on_delete=CASCADE, related_name="customer")`, `name=CharField(max_length=255)`, `billing_email=EmailField(blank=True)`, `billing_address=TextField(blank=True)`, `billing_phone=CharField(max_length=50, blank=True)`, `Meta.db_table="customers"`, `__str__` returning `name`.

Add `TimeStampedModel` and `SoftDeleteModel` to `apps/platform/models.py` in this task (the platform app already exists from Task 2). `TimeStampedModel` has `created_at=DateTimeField(auto_now_add=True)` and `updated_at=DateTimeField(auto_now=True)`, `abstract=True`. `SoftDeleteModel` adds `is_deleted=BooleanField(default=False)`, `deleted_at=DateTimeField(null=True, blank=True)`, `soft_delete()`, and `restore()`, with `abstract=True`.

Add `apps.accounts.apps.AccountsConfig(name="apps.accounts", label="accounts")` and add it to `INSTALLED_APPS`. Set `AUTH_USER_MODEL = "accounts.User"` before running any migration.

Add a `user` fixture to `backend/conftest.py` for later tests:

```python
import pytest
from apps.accounts.models import Role, User


@pytest.fixture
def user(db):
    return User.objects.create_user(
        email="actor@example.com",
        password="Secret123!",
        role=Role.ADMIN,
    )
```

- [ ] **Step 4: Create and apply the first migration**

From `backend/`:

```powershell
..\.venv\Scripts\python.exe manage.py makemigrations accounts
..\.venv\Scripts\python.exe manage.py migrate
```

Expected: migrations apply; `accounts.0001_initial` exists.

- [ ] **Step 5: Run the tests to verify they pass**

```powershell
..\.venv\Scripts\python.exe -m pytest apps/accounts/tests/test_models.py -q
```

Expected: 3 passed.

- [ ] **Step 6: Commit**

```powershell
git add backend
git commit -m "phase-1: add custom user and customer schema"
```

---

### Task 4: Platform models, audit/outbox services, and money helper

**Files:**
- Modify: `backend/apps/platform/models.py`
- Create: `backend/apps/platform/exceptions.py`
- Create: `backend/apps/platform/services.py`
- Create: `backend/apps/platform/money.py`
- Create: `backend/apps/platform/tests/test_models.py`
- Create: `backend/apps/platform/tests/test_audit_outbox.py`
- Create: `backend/apps/platform/tests/test_money.py`
- Create: `backend/apps/platform/migrations/0001_initial.py`
- Create: `backend/apps/platform/migrations/0002_audit_log_append_only.py`

**Interfaces:**
- Consumes: `accounts.User` via `settings.AUTH_USER_MODEL`.
- Produces:
  - `TimeStampedModel` (abstract, `created_at`, `updated_at`)
  - `SoftDeleteModel` (abstract, `is_deleted`, `deleted_at`, `soft_delete()`, `restore()`)
  - `AuditLog` with fields `entity_type`, `entity_id`, `from_status`, `to_status`, `actor`, `at`, `metadata`
  - `OutboxEvent` with fields `event_type`, `aggregate_type`, `aggregate_id`, `payload`, `created_at`, `published_at`, `attempts`, `last_error`
  - `InvalidTransition`
  - `record_audit(*, entity_type, entity_id, from_status, to_status, actor=None, metadata=None) -> AuditLog`
  - `emit_event(*, event_type, aggregate_type, aggregate_id, payload=None) -> OutboxEvent`
  - `quantize_money(value) -> Decimal`

- [ ] **Step 1: Write the failing platform tests**

Create `backend/apps/platform/tests/test_money.py`:

```python
from decimal import Decimal
import pytest
from apps.platform.money import quantize_money


@pytest.mark.parametrize("raw, expected", [
    ("10.005", "10.01"),
    ("10.004", "10.00"),
    ("0.999", "1.00"),
])
def test_quantize_money_rounds_half_up(raw, expected):
    assert quantize_money(Decimal(raw)) == Decimal(expected)
```

Create `backend/apps/platform/tests/test_models.py` covering `AuditLog`/`OutboxEvent` field metadata and the required indexes. Create `backend/apps/platform/tests/test_audit_outbox.py` covering the active-transaction requirement, rollback atomicity, and append-only guards:

```python
import pytest
from django.db import DatabaseError, transaction
from django.db.transaction import TransactionManagementError

from apps.platform.models import AuditLog, OutboxEvent
from apps.platform.services import emit_event, record_audit


@pytest.mark.django_db(transaction=True)
def test_record_audit_requires_an_atomic_block(user):
    with pytest.raises(TransactionManagementError):
        record_audit(entity_type="test.entity", entity_id="1", from_status="a", to_status="b", actor=user)


@pytest.mark.django_db(transaction=True)
def test_emit_event_requires_an_atomic_block():
    with pytest.raises(TransactionManagementError):
        emit_event(event_type="test.event", aggregate_type="test.entity", aggregate_id="1")


@pytest.mark.django_db
def test_audit_and_outbox_roll_back_together(user):
    with pytest.raises(RuntimeError):
        with transaction.atomic():
            record_audit(entity_type="test.entity", entity_id="1", from_status="a", to_status="b", actor=user)
            emit_event(event_type="test.event", aggregate_type="test.entity", aggregate_id="1")
            raise RuntimeError("force rollback")
    assert AuditLog.objects.count() == 0
    assert OutboxEvent.objects.count() == 0


@pytest.mark.django_db
def test_audit_log_rejects_queryset_update(user):
    with transaction.atomic():
        log = record_audit(entity_type="test.entity", entity_id="1", from_status="a", to_status="b", actor=user)
    with pytest.raises(DatabaseError):
        with transaction.atomic():
            AuditLog.objects.filter(pk=log.pk).update(to_status="c")
```

Also add tests for instance `save()`/`delete()` rejection and `OutboxEvent` default `attempts=0`, `published_at=None`.

- [ ] **Step 2: Run the tests to verify they fail**

From `backend/`:

```powershell
..\.venv\Scripts\python.exe -m pytest apps/platform/tests -q
```

Expected: FAIL because the models, services, and money helper do not exist.

- [ ] **Step 3: Implement the platform models and services**

Add the models and helper signatures above. `record_audit` and `emit_event` must call a shared `ensure_atomic_block()` that raises `TransactionManagementError` when `transaction.get_connection().in_atomic_block` is false. `AuditLog.save()` must raise `ValidationError` when `not self._state.adding`; `AuditLog.delete()` must always raise. `quantize_money` uses `Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)`.

- [ ] **Step 4: Create the migrations and the append-only trigger**

From `backend/`:

```powershell
..\.venv\Scripts\python.exe manage.py makemigrations platform
..\.venv\Scripts\python.exe manage.py migrate
```

Create `0002_audit_log_append_only.py` with `migrations.RunSQL` that creates a PostgreSQL function `prevent_audit_log_mutation()` and a `BEFORE UPDATE OR DELETE` trigger `audit_log_no_update_delete` on `audit_log`; the reverse SQL drops the trigger and function. Run `migrate` again.

- [ ] **Step 5: Run the tests to verify they pass**

```powershell
..\.venv\Scripts\python.exe -m pytest apps/platform/tests -q
```

Expected: all platform tests pass.

- [ ] **Step 6: Commit**

```powershell
git add backend
git commit -m "phase-1: add audit outbox and money platform"
```

---

### Task 5: Outbox dispatcher

**Files:**
- Create: `backend/apps/platform/events.py`
- Create: `backend/apps/platform/tasks.py`
- Create: `backend/apps/platform/management/__init__.py`
- Create: `backend/apps/platform/management/commands/__init__.py`
- Create: `backend/apps/platform/management/commands/dispatch_outbox.py`
- Create: `backend/apps/platform/tests/test_dispatcher.py`
- Modify: `backend/config/celery.py`
- Modify: `backend/config/settings.py`
- Modify: `backend/config/__init__.py`

**Interfaces:**
- Consumes: `OutboxEvent` from Task 4.
- Produces:
  - `register_handler(event_type: str, handler: Callable[[OutboxEvent], None]) -> None`
  - `clear_handlers() -> None`
  - `dispatch_pending(limit: int = 100) -> int`
  - `dispatch_outbox_task(limit: int = 100) -> int`
  - management command `python manage.py dispatch_outbox`

- [ ] **Step 1: Write the failing dispatcher tests**

Create `backend/apps/platform/tests/test_dispatcher.py` with tests that:
- register a handler, emit an event inside `transaction.atomic()`, call `dispatch_pending()`, assert the handler received the event, `published_at` is set, and `attempts == 1`;
- register a handler that raises, call `dispatch_pending()`, assert `published_at is None`, `attempts == 1`, and `last_error` contains the message; then register a successful handler and call again, asserting it publishes;
- emit an event with no registered handler, dispatch, and assert it is marked published and a warning is logged (use `caplog`);
- emit two events, publish one manually, dispatch, and assert only the unpublished one is processed.

Use an autouse fixture that calls `clear_handlers()` before and after each test.

- [ ] **Step 2: Run the tests to verify they fail**

From `backend/`:

```powershell
..\.venv\Scripts\python.exe -m pytest apps/platform/tests/test_dispatcher.py -q
```

Expected: FAIL because the dispatcher does not exist.

- [ ] **Step 3: Implement the dispatcher and Celery wiring**

Implement `dispatch_pending` with one `transaction.atomic()` block: select unpublished events with `select_for_update(skip_locked=True).order_by("created_at")[:limit]`, invoke each registered handler, set `published_at=timezone.now()` and clear `last_error` on success, and on exception record `last_error` and leave `published_at=None`. Always increment `attempts` and save the event. Log a warning when no handler is registered; mark the event published. Add `dispatch_outbox_task` as a Celery `shared_task`, and the management command that calls `dispatch_pending`.

Configure `config/celery.py` with `app = Celery("subscription_management")`, `config_from_object("django.conf:settings", namespace="CELERY")`, and `autodiscover_tasks()`. Import `celery_app` in `config/__init__.py`. Add `CELERY_BEAT_SCHEDULE` for `apps.platform.tasks.dispatch_outbox_task` every 10 seconds.

- [ ] **Step 4: Run the tests to verify they pass**

```powershell
..\.venv\Scripts\python.exe -m pytest apps/platform/tests/test_dispatcher.py -q
```

Expected: all dispatcher tests pass.

- [ ] **Step 5: Commit**

```powershell
git add backend
git commit -m "phase-1: add transactional outbox dispatcher"
```

---

### Task 6: Catalog schema

**Files:**
- Create: `backend/apps/catalog/__init__.py`
- Create: `backend/apps/catalog/apps.py`
- Create: `backend/apps/catalog/models.py`
- Create: `backend/apps/catalog/migrations/__init__.py`
- Create: `backend/apps/catalog/tests/__init__.py`
- Create: `backend/apps/catalog/tests/test_models.py`
- Modify: `backend/config/settings.py`

**Interfaces:**
- Consumes: `apps.platform.models.TimeStampedModel`.
- Produces: `Product`, `Variant`, `Tax` models with `DecimalField(max_digits=12, decimal_places=2)` money fields and a variant price delta.

- [ ] **Step 1: Write the failing catalog tests**

Cover: creating a product with `Decimal("120.00")` sales price and `Decimal("40.00")` cost price; variant `price_delta`; tax `rate`; product `__str__`; and the decimal metadata for every money field. Assert `Product._meta.get_field("sales_price").max_digits == 12` and `decimal_places == 2`.

- [ ] **Step 2: Run the tests to verify they fail**

```powershell
..\.venv\Scripts\python.exe -m pytest apps/catalog/tests -q
```

Expected: FAIL because the app/models do not exist.

- [ ] **Step 3: Implement the catalog models**

Create `Product` (`name`, `type` choices service/goods, `sales_price`, `cost_price`, `notes`, `is_active`), `Variant` (`product` FK, `attribute`, `value`, `price_delta`), and `Tax` (`name`, `rate`, `is_active`). Use `TimeStampedModel`; set `db_table` to `products`, `variants`, `taxes`. Add `CatalogConfig(name="apps.catalog", label="catalog")` and add it to `INSTALLED_APPS`.

- [ ] **Step 4: Create and apply the migration, then run tests**

```powershell
..\.venv\Scripts\python.exe manage.py makemigrations catalog
..\.venv\Scripts\python.exe manage.py migrate
..\.venv\Scripts\python.exe -m pytest apps/catalog/tests -q
```

Expected: migration applies; all catalog tests pass.

- [ ] **Step 5: Commit**

```powershell
git add backend
git commit -m "phase-1: add catalog schema"
```

---

### Task 7: Plans schema

**Files:**
- Create: `backend/apps/plans/__init__.py`
- Create: `backend/apps/plans/apps.py`
- Create: `backend/apps/plans/models.py`
- Create: `backend/apps/plans/migrations/__init__.py`
- Create: `backend/apps/plans/tests/__init__.py`
- Create: `backend/apps/plans/tests/test_models.py`
- Modify: `backend/config/settings.py`

**Interfaces:**
- Consumes: `Product` from Task 6.
- Produces: `Plan` with `product`, `price`, `period`, `min_qty`, `start_date`, `end_date`, `auto_close`, `closable`, `pausable`, `renewable`, `is_active`; index on `period`.

- [ ] **Step 1: Write the failing plan tests**

Cover defaults (`min_qty=1`, flags false), period choices, money decimal metadata, relation to `Product`, and the presence of an index whose fields are `["period"]`.

- [ ] **Step 2: Run the tests to verify they fail**

```powershell
..\.venv\Scripts\python.exe -m pytest apps/plans/tests -q
```

Expected: FAIL because the app/model does not exist.

- [ ] **Step 3: Implement the Plan model**

Create `Plan` with the fields above, `Period` choices daily/weekly/monthly/yearly, `db_table="plans"`, and `Meta.indexes = [models.Index(fields=["period"], name="plan_period_idx")]`. Add `PlansConfig(name="apps.plans", label="plans")` and add it to `INSTALLED_APPS`.

- [ ] **Step 4: Create and apply the migration, then run tests**

```powershell
..\.venv\Scripts\python.exe manage.py makemigrations plans
..\.venv\Scripts\python.exe manage.py migrate
..\.venv\Scripts\python.exe -m pytest apps/plans/tests -q
```

Expected: migration applies; all plan tests pass.

- [ ] **Step 5: Commit**

```powershell
git add backend
git commit -m "phase-1: add plans schema"
```

---

### Task 8: Subscriptions schema and state machine

**Files:**
- Create: `backend/apps/subscriptions/__init__.py`
- Create: `backend/apps/subscriptions/apps.py`
- Create: `backend/apps/subscriptions/models.py`
- Create: `backend/apps/subscriptions/services.py`
- Create: `backend/apps/subscriptions/migrations/__init__.py`
- Create: `backend/apps/subscriptions/tests/__init__.py`
- Create: `backend/apps/subscriptions/tests/test_models.py`
- Create: `backend/apps/subscriptions/tests/test_state_machine.py`
- Modify: `backend/apps/platform/services.py` (add `apply_transition`)
- Modify: `backend/config/settings.py`
- Modify: `backend/conftest.py`

**Interfaces:**
- Consumes: `Customer` (accounts), `Product`/`Variant`/`Tax` (catalog), `Plan` (plans), `apply_transition`, `record_audit`, `emit_event`, `InvalidTransition`.
- Produces:
  - `QuotationTemplate`
  - `Subscription` with `Status` choices and `ALLOWED_TRANSITIONS`
  - `SubscriptionLine`
  - `transition_subscription(subscription, to_status, *, actor=None, reason="", at_expiry=False) -> Subscription`
  - `platform.services.apply_transition(instance, *, to_status, allowed_transitions, actor, event_type, validate=None, metadata=None, extra_update_fields=None) -> Model`

- [ ] **Step 1: Add the generic transition helper test-first**

Add to `backend/apps/platform/tests/test_audit_outbox.py` or a new `test_transitions.py`:

```python
@pytest.mark.django_db
def test_apply_transition_locks_checks_and_writes_audit_and_outbox(user, subscription):
    from apps.platform.services import apply_transition
    from apps.subscriptions.models import Subscription
    from apps.subscriptions.services import transition_subscription

    updated = transition_subscription(subscription, Subscription.Status.QUOTATION, actor=user)
    assert updated.status == Subscription.Status.QUOTATION
    assert AuditLog.objects.filter(entity_type="subscriptions.subscription", entity_id=str(subscription.pk)).count() == 1
    assert OutboxEvent.objects.filter(event_type="subscription.status_changed").count() == 1
```

- [ ] **Step 2: Write the failing subscription model and state-machine tests**

`test_models.py` covers: subscription number uniqueness, required fields, `SubscriptionLine` decimal fields, and the presence of `Index(fields=["status", "next_billing_date"])`.

`test_state_machine.py` covers:
- Draft → Quotation → Confirmed → Active succeeds and writes audit + outbox each time;
- illegal Draft → Active raises `InvalidTransition` and writes nothing;
- Active → Paused fails unless `plan.pausable=True`;
- Active → Closed fails unless `plan.closable=True` or (`at_expiry=True` and `plan.auto_close=True`);
- Closed → Active and Active → Active renewal fail unless `plan.renewable=True`;
- Confirmed → Active sets `next_billing_date` to `start_date` when it is empty;
- reusing a stale subscription instance after a successful transition is rejected because `apply_transition` re-reads and locks the row;
- monkeypatching `apps.platform.services.emit_event` to raise rolls back the status and audit row.

- [ ] **Step 3: Run the tests to verify they fail**

```powershell
..\.venv\Scripts\python.exe -m pytest apps/subscriptions/tests -q
```

Expected: FAIL because the models, services, and helper do not exist.

- [ ] **Step 4: Implement the subscriptions models and services**

Create the models described in the design. `Subscription.Status` values are `draft`, `quotation`, `confirmed`, `active`, `paused`, `closed`. `ALLOWED_TRANSITIONS` is:

```python
{
    Status.DRAFT: {Status.QUOTATION},
    Status.QUOTATION: {Status.CONFIRMED},
    Status.CONFIRMED: {Status.ACTIVE},
    Status.ACTIVE: {Status.PAUSED, Status.CLOSED},
    Status.PAUSED: {Status.ACTIVE},
    Status.CLOSED: {Status.ACTIVE},
}
```

Implement `apply_transition` in `apps/platform/services.py` as described in the platform contract: require an active transaction, lock the row with `select_for_update`, check the allowed map, run the validator, save status and extra fields, record audit and outbox, and return the locked instance. Implement `transition_subscription` with plan-flag validators and the `next_billing_date` rule. Add `SubscriptionsConfig(name="apps.subscriptions", label="subscriptions")` and add it to `INSTALLED_APPS`. Add fixtures for a customer, product, tax, plan, and subscription to `backend/conftest.py`.

- [ ] **Step 5: Create and apply the migration, then run tests**

```powershell
..\.venv\Scripts\python.exe manage.py makemigrations subscriptions
..\.venv\Scripts\python.exe manage.py migrate
..\.venv\Scripts\python.exe -m pytest apps/subscriptions/tests apps/platform/tests -q
```

Expected: all subscription and platform tests pass.

- [ ] **Step 6: Commit**

```powershell
git add backend
git commit -m "phase-1: add subscription state machine"
```

---

### Task 9: Billing schema and invoice state machine

**Files:**
- Create: `backend/apps/billing/__init__.py`
- Create: `backend/apps/billing/apps.py`
- Create: `backend/apps/billing/models.py`
- Create: `backend/apps/billing/services.py`
- Create: `backend/apps/billing/migrations/__init__.py`
- Create: `backend/apps/billing/tests/__init__.py`
- Create: `backend/apps/billing/tests/test_models.py`
- Create: `backend/apps/billing/tests/test_state_machine.py`
- Modify: `backend/config/settings.py`
- Modify: `backend/conftest.py`

**Interfaces:**
- Consumes: `Subscription` (subscriptions), `Customer` (accounts), `apply_transition`, `InvalidTransition`.
- Produces:
  - `Invoice` with `Status` choices and `ALLOWED_TRANSITIONS`
  - `InvoiceLine`
  - `transition_invoice(invoice, to_status, *, actor=None, reason="") -> Invoice`
  - Unique constraint `uniq_invoice_subscription_period` on `(subscription, period_start, period_end)`
  - Indexes `invoice_status_due_idx` and `invoice_customer_idx`

- [ ] **Step 1: Write the failing billing tests**

`test_models.py` covers money decimal metadata, `InvoiceLine` snapshot fields (`description`, `quantity`, `unit_price`, `tax_rate`, `discount`, `amount`), the unique period constraint (creating a second invoice with the same subscription/period raises `IntegrityError`), and the required indexes.

`test_state_machine.py` covers Draft → Confirmed → Paid, Draft → Cancelled, Confirmed → Cancelled, illegal Paid → Cancelled, and audit + outbox creation. Add a fixture for an invoice in `conftest.py`.

- [ ] **Step 2: Run the tests to verify they fail**

```powershell
..\.venv\Scripts\python.exe -m pytest apps/billing/tests -q
```

Expected: FAIL because the app/models do not exist.

- [ ] **Step 3: Implement the billing models and service**

Create `Invoice` and `InvoiceLine` as described. `Invoice.Status` values are `draft`, `confirmed`, `paid`, `cancelled`. `ALLOWED_TRANSITIONS` is:

```python
{
    Status.DRAFT: {Status.CONFIRMED, Status.CANCELLED},
    Status.CONFIRMED: {Status.PAID, Status.CANCELLED},
    Status.PAID: set(),
    Status.CANCELLED: set(),
}
```

Implement `transition_invoice` using `apply_transition`. The payment precondition for Paid and the no-payments precondition for Cancelled are Phase 6 responsibilities; document that in the service docstring. Add `BillingConfig(name="apps.billing", label="billing")` and add it to `INSTALLED_APPS`.

- [ ] **Step 4: Create and apply the migration, then run tests**

```powershell
..\.venv\Scripts\python.exe manage.py makemigrations billing
..\.venv\Scripts\python.exe manage.py migrate
..\.venv\Scripts\python.exe -m pytest apps/billing/tests -q
```

Expected: all billing tests pass.

- [ ] **Step 5: Commit**

```powershell
git add backend
git commit -m "phase-1: add invoice state machine"
```

---

### Task 10: Payments, discounts, and reports schema

**Files:**
- Create: `backend/apps/payments/__init__.py`
- Create: `backend/apps/payments/apps.py`
- Create: `backend/apps/payments/models.py`
- Create: `backend/apps/payments/migrations/__init__.py`
- Create: `backend/apps/payments/tests/__init__.py`
- Create: `backend/apps/payments/tests/test_models.py`
- Create: `backend/apps/discounts/__init__.py`
- Create: `backend/apps/discounts/apps.py`
- Create: `backend/apps/discounts/models.py`
- Create: `backend/apps/discounts/migrations/__init__.py`
- Create: `backend/apps/discounts/tests/__init__.py`
- Create: `backend/apps/discounts/tests/test_models.py`
- Create: `backend/apps/reports/__init__.py`
- Create: `backend/apps/reports/apps.py`
- Create: `backend/apps/reports/models.py`
- Create: `backend/apps/reports/migrations/__init__.py`
- Create: `backend/apps/reports/tests/__init__.py`
- Create: `backend/apps/reports/tests/test_models.py`
- Modify: `backend/config/settings.py`
- Modify: `backend/conftest.py`

**Interfaces:**
- Consumes: `Invoice` (billing), `Subscription` (subscriptions), `Product` (catalog).
- Produces:
  - `Payment` with `invoice`, `method`, `amount`, `paid_on`, `note`; index `(invoice, paid_on)`
  - `Discount` with `type`, `value`, `min_amount`, `min_qty`, `start_date`, `end_date`, `usage_limit`, `used_count`, `scope`, `products`, `is_active`; index `(start_date, end_date)`
  - `DiscountUsage` with `discount`, `subscription`, `invoice`, with unique constraint and index
  - `DailyMetrics` with unique `date`, `active_subscriptions`, `revenue_collected`, `outstanding`, `overdue_invoices`, `mrr`, `arr`

- [ ] **Step 1: Write the failing model tests**

Payments: money decimal metadata, payment creation against an invoice, presence of `Index(fields=["invoice", "paid_on"])`, and `__str__`.
Discounts: fixed/percent type, scope, date range, usage limit, money decimal metadata, `DiscountUsage` uniqueness for the same discount/subscription/invoice, and the date-range index.
Reports: unique `date`, decimal metrics, negative/default values, and `DailyMetrics.__str__`.

- [ ] **Step 2: Run the tests to verify they fail**

```powershell
..\.venv\Scripts\python.exe -m pytest apps/payments/tests apps/discounts/tests apps/reports/tests -q
```

Expected: FAIL because the apps/models do not exist.

- [ ] **Step 3: Implement the models**

Create the models described above. Use `TimeStampedModel` for all of them. Add `PaymentsConfig`, `DiscountsConfig`, and `ReportsConfig` to `INSTALLED_APPS`. Add fixtures for a payment, discount, and daily metric to `conftest.py` if needed.

- [ ] **Step 4: Create and apply the migrations, then run tests**

```powershell
..\.venv\Scripts\python.exe manage.py makemigrations payments discounts reports
..\.venv\Scripts\python.exe manage.py migrate
..\.venv\Scripts\python.exe -m pytest apps/payments/tests apps/discounts/tests apps/reports/tests -q
```

Expected: migrations apply; all tests pass.

- [ ] **Step 5: Commit**

```powershell
git add backend
git commit -m "phase-1: add payment discount and report schema"
```

---

### Task 11: Docker Compose, environment, README, and final docs

**Files:**
- Create: `docker-compose.yml`
- Create: `backend/Dockerfile`
- Create: `backend/.dockerignore`
- Create: `.env.example`
- Modify: `README.md`
- Modify: `PROGRESS.md`
- Modify: `docs/platform-contract.md`
- Modify: `AGENT.md`
- Modify: `MODULE_ASSIGNMENTS.md`

**Interfaces:**
- Consumes: the complete Django project and tests.
- Produces: a clean-checkout runtime with `docker compose up --build`, a documented test command, and accurate project docs.

- [ ] **Step 1: Create the Docker runtime**

Create `backend/Dockerfile` from `python:3.12-slim`, install `requirements.txt`, copy the backend, expose 8000, and default to `python manage.py runserver 0.0.0.0:8000`. Create `backend/.dockerignore` for caches, `.venv`, `.git`, `.env`, and test artifacts.

Create `docker-compose.yml` with services:
- `db`: `postgres:16`, `POSTGRES_DB/USER/PASSWORD` from `${VAR:-default}`, `postgres_data` volume, `pg_isready` healthcheck.
- `redis`: `redis:7`, `redis-cli ping` healthcheck.
- `migrate`: builds `./backend`, command `python manage.py migrate --noinput`, backend environment, depends on healthy `db`.
- `api`: builds `./backend`, command `python manage.py runserver 0.0.0.0:8000`, port `8000:8000`, depends on `migrate` completion and healthy `db`/`redis`, `/health/` healthcheck, bind mount `./backend:/app`.
- `worker`: `celery -A config worker -l info`, depends on `migrate` completion and healthy `db`/`redis`.
- `beat`: `celery -A config beat -l info`, same dependencies.
- Shared environment: `DJANGO_SECRET_KEY` default `dev-insecure-change-me`, `DJANGO_DEBUG=1`, `DJANGO_ALLOWED_HOSTS=*`, `POSTGRES_HOST=db`, `POSTGRES_PORT=5432`, `REDIS_URL=redis://redis:6379/0`.
- `postgres_data` named volume.

Create `.env.example` with local-development values for the same variables, noting that Docker Compose overrides database/Redis hosts.

- [ ] **Step 2: Verify the Compose file and runtime if Docker is available**

If `docker` is available:

```powershell
docker compose config
docker compose up --build -d
Start-Sleep -Seconds 15
(Invoke-WebRequest -UseBasicParsing http://localhost:8000/health/).Content
docker compose run --rm api pytest
docker compose down -v
```

Expected: `{"status": "ok"}`; pytest passes; cleanup succeeds.

If Docker is unavailable, record in `PROGRESS.md` that Compose runtime verification is blocked by the missing Docker Desktop installation. Do not claim it was run. Validate the YAML structurally with a Python YAML parse if a YAML library is already available; otherwise inspect it manually.

- [ ] **Step 3: Verify locally against the WSL PostgreSQL**

From `backend/`:

```powershell
..\.venv\Scripts\python.exe manage.py check
..\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
..\.venv\Scripts\python.exe -m pytest -q
```

Expected: no issues; no missing migrations; all tests pass.

- [ ] **Step 4: Write the README and update the docs**

README must include: project summary, architecture, prerequisites, `docker compose up --build`, `docker compose run --rm api pytest`, local test instructions, current Phase 1 scope, and the Docker-unavailable verification note if applicable. Update `PROGRESS.md` with what was built, commands run, results, and the Docker gap. Update `docs/platform-contract.md` with any final signatures or event types. Re-check `AGENT.md` and `MODULE_ASSIGNMENTS.md` for consistency with the implementation.

- [ ] **Step 5: Commit**

```powershell
git add docker-compose.yml backend/Dockerfile backend/.dockerignore .env.example README.md PROGRESS.md docs AGENT.md MODULE_ASSIGNMENTS.md
git commit -m "phase-1: add docker runtime and docs"
```

---

### Task 12: Final verification and handoff

**Files:**
- Modify: `PROGRESS.md`

**Interfaces:**
- Consumes: all previous tasks.
- Produces: verified Phase 1 branch and an honest handoff report.

- [ ] **Step 1: Run the full verification suite**

From `backend/`:

```powershell
..\.venv\Scripts\python.exe manage.py check
..\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
..\.venv\Scripts\python.exe -m pytest -q
```

From the worktree root:

```powershell
git diff --check
git status --short
git log --oneline -5
```

Expected: all tests pass; no missing migrations; no whitespace errors; clean working tree after the final commit.

- [ ] **Step 2: Check for leftovers and secrets**

Run:

```powershell
git grep -n -E "TODO|FIXME|print\(|pdb|breakpoint\(" -- backend docs README.md AGENT.md MODULE_ASSIGNMENTS.md
git ls-files | Where-Object { $_ -match '(^|/)\.env$' }
```

Expected: no leftover debug statements, TODO/FIXME markers, or committed `.env` files. Intentional `print` in management command output may be documented; prefer logger or no output.

- [ ] **Step 3: Update `PROGRESS.md` with the exact verification results and remaining gaps**

Record the test count, check command results, migration check result, Docker verification status, and any known gaps (for example, Docker Desktop not installed). Do not claim unrun checks.

- [ ] **Step 4: Commit the final state**

```powershell
git add PROGRESS.md
git commit -m "phase-1: verify foundation"
```

- [ ] **Step 5: Handoff**

Provide the branch name, commit range, test command and result, Docker verification status, and a concise list of files created/modified/deleted. Push the branch only after confirming the working tree is clean and the remote is up to date:

```powershell
git fetch origin
git push -u origin phase-1-foundation
```

If the push is rejected or the remote has newer work, stop and report; do not force-push. Merge to `main` only after the branch is reviewed and tests pass on the merged tree.
