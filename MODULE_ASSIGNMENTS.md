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
Phase 1: Schema + state machine services  →  platform, subscriptions (foundation)
Phase 2: Auth + roles                     →  accounts (depends on platform)
Phase 3: Catalog + plans                  →  catalog, plans (depends on platform)
Phase 4: Quotations + subscriptions       →  subscriptions (depends on catalog, plans, accounts)
Phase 5: Billing engine + scheduler       →  billing (depends on subscriptions)
Phase 6: Payments                         →  payments (depends on billing)
Phase 7: Discounts                        →  discounts (depends on billing)
Phase 8: Dashboard + read model           →  reports (depends on billing, payments, discounts)
Phase 9: Seed data + README + demo        →  all (integration)
Phase 10: Optional extras                 →  after phases 1-9 complete
```

**Rule:** Never start Phase N+1 until Phase N is tested, committed, and logged in `PROGRESS.md`.

---

## Module-Wise Task Assignments (Independent Team Members)

### Module 1: `platform` — Shared Foundation (Phase 1)
**Owner:** 1 developer (Tech Lead) — **Must be done first; blocks all other modules**

**Tasks:**
- Set up Django 5 + DRF project with PostgreSQL, Redis, Celery, Docker Compose
- Base models: `AuditLog`, `OutboxEvent`, abstract timestamped/soft-delete base
- Required indexes: `subscriptions(status, next_billing_date)`, `invoices(status, due_date)`, `invoices(customer)`, `payments(invoice, paid_on)`
- Outbox pattern: event publishing in same transaction as state change
- `docker compose up` must start the full system from a clean checkout
- `.env.example` committed; no secrets in repo

**Definition of Done:** Migrations run; `docker compose up` starts clean; outbox + audit pattern verified with tests.

---

### Module 2: `accounts` — Auth & RBAC (Phase 2)
**Owner:** 1 developer (independent once `platform` exists)

**Tasks:**
- Custom user model with `role` field (`admin`, `staff`, `customer`)
- Email unique; password rules (>8 chars, uppercase, lowercase, special char); Django default hashers
- Login for all three roles
- Password reset: time-limited, single-use tokens
- Explicit permission class on every endpoint (no open endpoints)
- Only `admin` creates staff, discounts, products, plans, taxes
- Customer querysets filtered by logged-in customer (ID tampering → 404/empty)
- Permission tests: customer-A-reads-customer-B attempt

**Definition of Done:** Three roles log in; permissions enforced; all permission tests pass.

---

### Module 3: `catalog` — Products, Variants, Taxes (Phase 3)
**Owner:** 1 developer (independent once `platform` exists)

**Tasks:**
- Product model, variants, tax rates
- Money: `DecimalField(max_digits=12, decimal_places=2)` only; no floats anywhere
- Admin can create/edit products, variants, taxes
- API endpoints paginated; `select_related`/`prefetch_related` to avoid N+1
- Query-count tests on key endpoints

**Definition of Done:** Admin can launch a product with variants and taxes; tests pass.

---

### Module 4: `plans` — Subscription Plans (Phase 3)
**Owner:** 1 developer (independent once `platform` exists; can pair with `catalog`)

**Tasks:**
- Plan model linked to product, billing interval, price, feature flags
- Admin can launch a plan with flags
- Money as `DecimalField(max_digits=12, decimal_places=2)`
- Pagination and query optimization

**Definition of Done:** Admin can create a plan; tests pass.

---

### Module 5: `subscriptions` — Quotations + Subscription Lifecycle (Phase 4)
**Owner:** 1–2 developers (depends on `accounts`, `catalog`, `plans`)

**Tasks:**
- Quotation template model; quote → Active subscription flow
- Subscription state machine with allowed-transitions table
- Status changes **only** through service functions (never `obj.status = ...` save)
- Every transition writes `AuditLog` + `OutboxEvent` in the same transaction
- API exposes actions (confirm, cancel, pause, close); never accepts raw `status` field
- Illegal transitions rejected in tests
- Audit trail on all state changes

**Definition of Done:** Quote to Active flow works; illegal transitions rejected; audit trail verified.

---

### Module 6: `billing` — Billing Engine + Invoices (Phase 5)
**Owner:** 1–2 developers (depends on `subscriptions`)

**Tasks:**
- Billing engine runs in separate Celery worker + beat process
- Invoice generation: `UNIQUE(subscription, period_start, period_end)` constraint (never drop/weaken)
- `select_for_update` row lock inside transaction
- `next_billing_date` advances only in same transaction that creates the invoice
- Invoice lines copy price, tax rate, quantity, discount at billing time (snapshot)
- Idempotency: running billing job twice = zero duplicates, zero skipped
- Test proving double-run idempotency

**Definition of Done:** Invoices fully prefilled; double-run creates no duplicates; test passes.

---

### Module 7: `payments` — Payments + Invoice Actions (Phase 6)
**Owner:** 1 developer (depends on `billing`)

**Tasks:**
- Record payment against an invoice
- Invoice auto-transitions to Paid when balance cleared
- PDF generation and email send on payment/invoice events
- Payment model with index on `(invoice, paid_on)`

**Definition of Done:** Payment recorded; invoice auto-Paid; PDF + email verified.

---

### Module 8: `discounts` — Discounts (Phase 7)
**Owner:** 1 developer (depends on `billing`)

**Tasks:**
- Discount model; auto-applied on next invoice
- Stops at expiry date or usage limit
- Usage limit respected under repeat billing runs (test required)

**Definition of Done:** Discounts auto-apply; expiry/limit enforced; test passes.

---

### Module 9: `reports` — Dashboard + Read Model (Phase 8)
**Owner:** 1 developer (depends on `billing`, `payments`, `discounts`)

**Tasks:**
- Admin/staff panel, customer portal, finance dashboard read models
- All pages under 2s on 10k seeded subscriptions
- Revenue reporting
- Paginated list endpoints

**Definition of Done:** Dashboard pages load under 2s with 10k subscriptions; tests pass.

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
| Member 1 (Tech Lead) | `platform` + integration | 1, 9 |
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
| 12 | No fakes | No hardcoded data, mocks, or placeholder logic presented as real; remove TODOs/FIXMEs |
| 13 | Scope control | Main features first; extras (n8n, payment gateway, proration) only after phases 1–9 |
| 14 | Docker must work | `docker compose up` starts full system from clean checkout; README kept accurate |
| 15 | Git hygiene | Commit after every working step; never commit broken code to main; never commit `.env`/secrets |
| 16 | Honest reporting | Say only what you verified by running; show exact errors; list files created/changed/deleted |

---

## Notes

- The PDF `Subscription_System_Design_Plan.pdf` could not be machine-read in this session. Confirm that `docs/design.md` exists and matches `AGENT.md`. If code and design disagree, stop and ask per `AGENT.md`.
- All workspace source files are currently 0 bytes (greenfield scaffold). No existing code to preserve.
- Tests must be written alongside code, not afterwards (Rule 11).



Member 1: platform  ← STARTS FIRST (blocks all others)
            │
    ┌───────┴───────┐
Member 2: accounts   Member 3: catalog + plans   (INDEPENDENT, parallel)
            │               │
    └───────┴───────────────┘
            │
Member 4: subscriptions  ← waits for Member 2 + Member 3
            │
    billing → payments → discounts → reports  (sequential, assign as members free up)