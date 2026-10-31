# Module-Wise Task Breakdown — Subscription Management System

**Project:** Subscription Billing Platform (Brightloop Software)
**Core Flow:** Product > Plan > Quotation > Subscription > Invoice > Payment > Reports
**Stack:** Django 5 + DRF, PostgreSQL, Redis + Celery, React (Vite), Docker Compose
**Source of Truth:** `docs/design.md` (Design Plan), `AGENT.md`, `RULES.md`

---

## Module Inventory

| Module | Django App | Responsibility |
|--------|-----------|----------------|
| **platform** | `platform` | Shared infra: outbox, audit log, domain events, base models, DB discipline |
| **accounts** | `accounts` | Auth, roles (admin/staff/customer), password reset, RBAC |
| **catalog** | `catalog` | Products, variants, taxes |
| **plans** | `plans` | Subscription plans, feature flags |
| **subscriptions** | `subscriptions` | Quotations, subscription lifecycle, state machine, audit trail |
| **billing** | `billing` | Billing engine, scheduler, invoices, idempotency |
| **payments** | `payments` | Payment recording, invoice → Paid, PDF, email |
| **discounts** | `discounts` | Auto-applied discounts, expiry, usage limits |
| **reports** | `reports` | Dashboard, read model, revenue reporting |
| **frontend** | — | React (Vite): admin/staff panel, customer portal, finance dashboard |

---

## Phase Dependency Map (build order — one phase at a time per RULES.md Rule 2)

```
Phase 1: Foundation schema (all modules) + platform + state machines  →  platform (Tech Lead)
Phase 2: Auth + roles                     →  accounts (depends on Phase 1 schema)
Phase 3: Catalog + plans APIs             →  catalog, plans (depends on Phase 1 schema)
Phase 4: Quotations + subscriptions flow  →  subscriptions (depends on Phase 1 schema)
Phase 5: Billing engine + scheduler       →  billing (depends on Phase 1 schema and subscriptions)
Phase 6: Payments + invoice actions       →  payments (depends on Phase 1 schema and billing)
Phase 7: Discounts engine                 →  discounts (depends on Phase 1 schema and billing)
Phase 8: Dashboard + read model           →  reports (depends on billing, payments, discounts)
Phase 9: Seed data + README + demo        →  all (integration)
Phase 10: Optional extras                 →  after phases 1-9 complete
```

**Rule:** Never start Phase N+1 until Phase N is tested, committed, and logged in `PROGRESS.md`.

---

## Module-Wise Task Assignments (Independent Team Members)

### Module 1: `platform` + Foundation Schema (Phase 1)
**Owner:** 1 developer (Tech Lead) — **Must be done first; blocks all other modules**

**Tasks:**
- Set up Django 5 + DRF project with PostgreSQL 16, Redis 7, Celery, and Docker Compose
- Create the full foundation schema in Phase 1: custom user and roles, customers, products/variants/taxes, plans, subscriptions/lines, invoices/lines, payments, discounts/usage, daily metrics
- Create the custom user model before the first migration (`AUTH_USER_MODEL = "accounts.User"`)
- Base models: `TimeStampedModel`, `SoftDeleteModel`, `AuditLog`, `OutboxEvent`
- Platform services: `record_audit`, `emit_event`, `apply_transition`, money quantization, and the outbox dispatcher
- Subscription and invoice state-machine services with a single allowed-transitions table; illegal transitions rejected
- Required indexes: `subscriptions(status, next_billing_date)`, `invoices(status, due_date)`, `invoices(customer)`, `payments(invoice, paid_on)`, `plans(period)`
- Outbox pattern: event publishing in the same transaction as the state change
- Append-only audit enforcement at both model and PostgreSQL trigger level
- `docker compose up` must start the full system from a clean checkout
- `.env.example` committed; no secrets in repo

**Definition of Done:** Migrations run; `docker compose up` starts clean when Docker is available; outbox and audit atomicity tests pass; illegal subscription and invoice transitions are rejected; all required indexes exist. Phase 1 stops at schema, platform infrastructure, and state-machine services: no business API endpoints are built early.

---

### Module 2: `accounts` — Auth & RBAC (Phase 2)
**Owner:** 1 developer (independent once Phase 1 foundation exists)

**Tasks:**
- Use the custom user, `Role`, and `Customer` models created by the Phase 1 schema freeze
- Build email/password login for `admin`, `staff`, and `customer` roles; email remains unique
- Enforce password rules (>8 chars, uppercase, lowercase, special char) with Django default hashers
- Password reset: time-limited, single-use tokens
- Explicit permission class on every endpoint (no open endpoints)
- Only `admin` creates staff, discounts, products, plans, taxes
- Customer querysets filtered by logged-in customer (ID tampering → 404/empty)
- Permission tests: customer-A-reads-customer-B attempt

**Definition of Done:** Three roles log in; permissions enforced; all permission tests pass. Phase 2 adds auth APIs and permissions on top of the Phase 1 schema; it does not recreate the user schema.

---

### Module 3: `catalog` — Products, Variants, Taxes (Phase 3)
**Owner:** 1 developer (independent once Phase 1 foundation exists)

**Tasks:**
- Use the `Product`, `Variant`, and `Tax` models and indexes created by the Phase 1 schema freeze
- Build the admin CRUD APIs for products, variants, and tax rates
- Keep all money as `DecimalField(max_digits=12, decimal_places=2)`; no floats anywhere
- Paginate every list endpoint; use `select_related`/`prefetch_related` to avoid N+1
- Query-count tests on key endpoints

**Definition of Done:** Admin can launch a product with variants and taxes; tests pass. Phase 3 adds APIs and services; it does not rewrite the catalog schema.

---

### Module 4: `plans` — Subscription Plans (Phase 3)
**Owner:** 1 developer (independent once Phase 1 foundation exists; can pair with `catalog`)

**Tasks:**
- Use the `Plan` model (product link, billing interval, price, feature flags, `period` index) created by the Phase 1 schema freeze
- Build the admin plan APIs and validation for flags
- Keep money as `DecimalField(max_digits=12, decimal_places=2)`
- Pagination and query optimization

**Definition of Done:** Admin can create a plan; tests pass. Phase 3 adds APIs and services; it does not rewrite the plans schema.

---

### Module 5: `subscriptions` — Quotations + Subscription Lifecycle (Phase 4)
**Owner:** 1–2 developers (depends on the Phase 1 schema; pairs with `accounts`, `catalog`, `plans`)

**Tasks:**
- Build the quotation template and quote → Active subscription business flow and APIs on top of the Phase 1 `QuotationTemplate`, `Subscription`, `SubscriptionLine`, and state-machine foundation
- Use the Phase 1 subscription state machine; do not duplicate its schema or its allowed-transitions table
- Status changes **only** through service functions (never `obj.status = ...` save)
- Every transition writes `AuditLog` + `OutboxEvent` in the same transaction
- API exposes actions (confirm, cancel, pause, close, renew); never accepts a raw `status` field
- Illegal transitions rejected in tests
- Audit trail on all state changes

**Definition of Done:** Quote to Active flow works; illegal transitions rejected; audit trail verified. Phase 4 adds the quotation/subscription business flow and APIs on top of the Phase 1 schema and state-machine foundation, not a duplicate schema.

---

### Module 6: `billing` — Billing Engine + Invoices (Phase 5)
**Owner:** 1–2 developers (depends on Phase 1 schema and `subscriptions`)

**Tasks:**
- Build the billing engine on the Phase 1 `Invoice` and `InvoiceLine` schema and invoice state machine
- Billing engine runs in separate Celery worker + beat process
- Invoice generation: `UNIQUE(subscription, period_start, period_end)` constraint (never drop/weaken)
- `select_for_update` row lock inside transaction
- `next_billing_date` advances only in same transaction that creates the invoice
- Invoice lines copy price, tax rate, quantity, discount at billing time (snapshot)
- Idempotency: running billing job twice = zero duplicates, zero skipped
- Test proving double-run idempotency

**Definition of Done:** Invoices fully prefilled; double-run creates no duplicates; test passes. Phase 5 adds the billing engine; it does not rewrite the invoice schema.

---

### Module 7: `payments` — Payments + Invoice Actions (Phase 6)
**Owner:** 1 developer (depends on Phase 1 schema and `billing`)

**Tasks:**
- Use the Phase 1 `Payment` schema and `(invoice, paid_on)` index
- Record payment against an invoice
- Invoice auto-transitions to Paid when balance cleared, through the invoice service
- PDF generation and email send on payment/invoice events
- Keep payment amounts as `Decimal`

**Definition of Done:** Payment recorded; invoice auto-Paid; PDF + email verified. Phase 6 adds payment APIs and services; it does not rewrite the payment schema.

---

### Module 8: `discounts` — Discounts (Phase 7)
**Owner:** 1 developer (depends on Phase 1 schema and `billing`)

**Tasks:**
- Use the Phase 1 `Discount` and `DiscountUsage` schema
- Apply eligible discounts automatically on the next invoice
- Stop at expiry date or usage limit
- Usage limit respected under repeat billing runs (test required)

**Definition of Done:** Discounts auto-apply; expiry/limit enforced; test passes. Phase 7 adds the discount engine; it does not rewrite the discount schema.

---

### Module 9: `reports` — Dashboard + Read Model (Phase 8)
**Owner:** 1 developer (depends on Phase 1 schema, `billing`, `payments`, `discounts`)

**Tasks:**
- Use the Phase 1 `DailyMetrics` schema and aggregates
- Build admin/staff panel, customer portal, and finance dashboard read models
- All pages under 2s on 10k seeded subscriptions
- Revenue reporting, including MRR and ARR
- Paginated list endpoints

**Definition of Done:** Dashboard pages load under 2s with 10k subscriptions; tests pass. Phase 8 adds read APIs and aggregation services; it does not rewrite the metrics schema.

---

### Module 10: Frontend — React + Vite (Parallel with backend; integrates per phase)
**Owner:** 1–2 developers

**Tasks:**
- Role-based routes: admin/staff panel, customer portal, finance dashboard
- UI shells for each module as backend phases complete
- Connect to backend APIs as each phase delivers endpoints
- Hiding a button in UI is **never** a security measure (RBAC enforced on backend)

**Definition of Done:** All three portals functional; integrated with backend APIs.

---

### Module 11: Phase 9 — Seed Data, README, Demo (Integration)
**Owner:** All team members (after phases 1–8 complete)

**Tasks:**
- One-command seed data
- README run instructions accurate after every phase
- 3-minute demo script rehearsed

---

## Recommended Team Split (4–6 Members)

| Member | Primary Modules | Phases |
|--------|----------------|--------|
| Member 1 (Tech Lead) | `platform` + foundation + integration | 1, 9 |
| Member 2 | `accounts` | 2 |
| Member 3 | `catalog` + `plans` | 3 |
| Member 4 | `subscriptions` | 4 |
| Member 5 | `billing` + `payments` | 5, 6 |
| Member 6 | `discounts` + `reports` + frontend | 7, 8, frontend |

---

## Critical Integration Points (Sync Required Between Members)

1. **`platform` → all modules:** Outbox/Audit pattern must be agreed before anyone writes state changes.
2. **`accounts` → `subscriptions`:** Role permissions must be in place before subscription actions are exposed.
3. **`catalog`/`plans` → `subscriptions`:** Product/plan schemas must be stable before quotation flow is built.
4. **`subscriptions` → `billing`:** Subscription model and `next_billing_date` must be final before billing engine.
5. **`billing` → `payments`/`discounts`/`reports`:** Invoice schema must be stable before these modules build on it.

---

## Non-Negotiable Rules (from `RULES.md`)

| # | Rule | Summary |
|---|------|---------|
| 1 | Pull first | `git pull --rebase` before reading/changing code; never push --force |
| 2 | Phase by phase | One phase at a time; no stubs or half-built future features |
| 3 | Money is Decimal | `DecimalField(max_digits=12, decimal_places=2)`; never `float` for money |
| 4 | Status via services | Status changes only through service functions; every transition writes `AuditLog` + `OutboxEvent` in same transaction |
| 5 | Billing idempotent | `UNIQUE(subscription, period_start, period_end)`; `select_for_update`; double-run = zero duplicates |
| 6 | Invoices are snapshots | Invoice lines copy price/tax/qty/discount at billing time; never changed by later edits |
| 7 | RBAC on backend | Every endpoint has explicit permission class; customer querysets filtered by logged-in customer |
| 8 | Security basics | Password rules; unique email; time-limited single-use reset links; no secrets in repo |
| 9 | DB discipline | Required indexes; paginated list endpoints; avoid N+1; overdue is derived, never stored |
| 10 | Module boundaries | Each module owns its tables; others call service functions or listen to events |
| 11 | Tests mandatory | No feature complete without tests; illegal transitions, billing idempotency, discount limits, customer isolation, password rules all require proof tests |
| 12 | No fakes | No hardcoded data, mocks, or placeholder logic presented as real; remove unfinished-task markers |
| 13 | Scope control | Main features first; extras (n8n, payment gateway, proration) only after phases 1–9 |
| 14 | Docker must work | `docker compose up` starts full system from clean checkout; README kept accurate |
| 15 | Git hygiene | Commit after every working step; never commit broken code to main; never commit `.env`/secrets |
| 16 | Honest reporting | Say only what you verified by running; show exact errors; list files created/changed/deleted |

---

## Notes

- `docs/design.md` is the source of truth and matches `AGENT.md`. If code and design disagree, stop and ask per `AGENT.md`.
- Phase 1 is the schema freeze. Every module's core models, constraints, and indexes are created there; later phases add APIs, business services, and new migrations without rewriting the foundation.
- Tests must be written alongside code, not afterwards (Rule 11).
- The zero-byte scaffold placeholders were removed in Phase 1 because they conflicted with the Django stack.

Member 1: platform + foundation schema  ← STARTS FIRST (blocks all others)
            │
    ┌───────┴───────┐
Member 2: accounts   Member 3: catalog + plans   (INDEPENDENT, parallel)
            │               │
    └───────┴───────────────┘
            │
Member 4: subscriptions  ← waits for Member 2 + Member 3
            │
    billing → payments → discounts → reports  (sequential, assign as members free up)