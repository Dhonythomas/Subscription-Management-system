# Subscription Management System — Design Plan

**Product:** Brightloop Software subscription billing platform

**Core flow:** Product > Plan > Quotation > Subscription > Invoice > Payment > Reports

## 1. Overview

A unified platform that runs the full life of a subscription business: products and plans, quotations, subscriptions, automatic invoicing, payments and revenue reporting. It replaces Brightloop's spreadsheet process with one system that is correct (no missed or double bills), secure (enforced roles) and fast (every page under 2 seconds).

### Architecture choice

Modular monolith with an event-driven core. One codebase and one deployable unit, so it is finishable in a hackathon. Modules communicate only through service functions and domain events. The billing engine runs as a separate worker process, which keeps heavy billing runs away from user-facing requests.

### Design principles

- **Correctness first:** the database enforces billing uniqueness, not just application code.
- **Backend-enforced RBAC:** hiding buttons is never the security layer.
- **Snapshot, don't reference:** invoices copy price, tax and discount at billing time.
- **Every change is traceable:** state changes write an audit row and an outbox event in the same transaction.
- **Read models for speed:** dashboards read pre-aggregated, indexed data.

## 2. System Architecture

```
React App (Vite)
Admin/Staff panel | Customer portal | Finance dashboard
                         |
                    API Layer (REST + JWT + RBAC)
accounts | catalog | plans | subscriptions | billing | payments | discounts | reports
                         |
              PostgreSQL (source of truth, outbox, audit log)
                         |
              Redis (job queue + dashboard cache)

Billing Worker + Scheduler          Outbox Dispatcher
idempotent invoice generation       publishes domain events
                         |
                Email / PDF / n8n
          reset links, invoices, reminders
```

Workers also read and write PostgreSQL and Redis. Events go to the outbox in the same transaction as the change.

| Component | Responsibility | Tech |
|---|---|---|
| React app | Role-based routes: admin/staff panel, customer portal, finance dashboard | React + Vite |
| API | Auth, RBAC, CRUD, state transitions via services | Django + DRF |
| Billing worker | Finds due subscriptions, generates invoices idempotently | Celery beat + worker |
| Outbox dispatcher | Publishes events written in the same transaction as state changes | Worker loop |
| PostgreSQL | Single source of truth, constraints, indexes | Postgres 15+ |
| Redis | Job queue and short-lived dashboard cache | Redis 7 |
| Docker Compose | One command starts every service | `docker compose up` |

## 3. Modules and Boundaries

Each module owns its tables. Other modules may call its service functions or subscribe to its events, never query its tables directly.

| Module | Owns | Key rules |
|---|---|---|
| `accounts` | User, Customer, roles, reset tokens | Unique email; password 9+ chars with upper, lower, special; only admin creates staff |
| `catalog` | Product, Variant, Tax | Variant adds a price delta (e.g. brand Odoo = +560); tax rules set by admin |
| `plans` | Plan and its behaviour flags | Billing period daily/weekly/monthly/yearly; min qty; availability dates; flags auto_close, closable, pausable, renewable |
| `subscriptions` | QuotationTemplate, Subscription, SubscriptionLine | Numbered; state machine; created from templates with validity days |
| `billing` | Invoice, InvoiceLine, billing runs | Generated only from subscriptions; state machine; never billed twice or skipped |
| `payments` | Payment | Method, amount, date, note, against an invoice; invoice auto-marked Paid when fully covered |
| `discounts` | Discount, DiscountUsage | Admin-only; fixed or percent; scope product or subscription; date range; usage limit |
| `reports` | `daily_metrics` read model, dashboard queries | Active subs, revenue, outstanding, overdue, MRR, filters |
| `platform` | AuditLog, OutboxEvent | Append-only; written in the same transaction as the change |

## 4. Data Model

Relationships: User > Customer > Subscription > SubscriptionLine; Subscription > Invoice > InvoiceLine; Invoice > Payment; Product > Variant; Plan, Tax, Discount and QuotationTemplate attach to subscriptions and lines.

| Table | Key columns | Constraints and indexes |
|---|---|---|
| `users` | id, email, password, role (admin/staff/customer) | UNIQUE(email) |
| `customers` | id, user_id, name, billing details | INDEX(user_id) |
| `products` / `variants` | name, type, sales_price, cost_price, notes / attribute, value, price_delta | INDEX(product_id) |
| `plans` | price, period, min_qty, start_date, end_date, auto_close, closable, pausable, renewable | INDEX(period) |
| `subscriptions` | number, customer_id, plan_id, start, expiry, payment_terms, status, next_billing_date | UNIQUE(number); INDEX(status, next_billing_date) |
| `subscription_lines` | product_id, variant_id, qty, unit_price, tax_id, amount | INDEX(subscription_id) |
| `invoices` | number, subscription_id, customer_id, period_start, period_end, subtotal, tax, discount, total, status, due_date | UNIQUE(subscription_id, period_start, period_end); INDEX(status, due_date); INDEX(customer_id) |
| `invoice_lines` | description, qty, unit_price, tax_rate, discount, amount (all snapshotted) | INDEX(invoice_id) |
| `payments` | invoice_id, method, amount, paid_on, note | INDEX(invoice_id, paid_on) |
| `discounts` / `discount_usage` | type, value, min_amount, min_qty, start, end, usage_limit, used_count, scope | INDEX(start, end) |
| `audit_log` / `outbox` | entity, entity_id, from, to, actor, at / event_type, payload, published_at | INDEX(entity, entity_id); INDEX(published_at) |

All money columns use `NUMERIC(12,2)` / `Decimal`. Never floats.

## 5. State Machines

Transitions live in one table of allowed moves, enforced in service code. The API never sets status directly. Every transition writes an audit row and an outbox event.

### Subscription

| From | To | Trigger |
|---|---|---|
| Draft | Quotation | Quote sent to customer |
| Quotation | Confirmed | Customer accepts / staff confirms |
| Confirmed | Active | Start date reached or activated; `next_billing_date` set |
| Active | Closed | Expiry (if plan `auto_close`), or early close (if plan `closable`) |
| Active | Paused | Only if plan `pausable`; billing skipped while paused |
| Active / Closed | Active (renewed) | Only if plan `renewable`; new period starts |

### Invoice

| From | To | Trigger |
|---|---|---|
| Draft | Confirmed | Staff confirms (or auto-confirm on generation) |
| Confirmed | Paid | Sum of payments >= total |
| Draft / Confirmed | Cancelled | Staff cancels; only if no payments recorded |

Overdue is derived, not stored: `status = Confirmed AND due_date < today AND balance > 0`.

## 6. Billing Engine

The hardest and most important part. Runs in the worker process on a schedule (and on demand for demos).

1. Scheduler selects subscriptions with `status = Active` and `next_billing_date <= today` (indexed query).
2. For each one, open a transaction and lock the row (`SELECT ... FOR UPDATE`).
3. Build invoice lines from subscription lines, snapshotting price, tax rate and quantity.
4. Evaluate eligible discounts (dates, min amount/qty, scope, `used_count < limit`) and apply them.
5. Compute taxes from admin-defined rules and totals using `Decimal`.
6. Insert invoice and lines. The `UNIQUE(subscription, period_start, period_end)` constraint rejects duplicates.
7. Increment discount `used_count`, advance `next_billing_date`, write audit row and outbox event (`invoice.created`).
8. Commit. Any failure rolls back the whole subscription; a failed one is logged and retried, others continue.

**Why it cannot double-bill:** row lock plus unique constraint. Running the job twice, or two workers at once, produces the same result. This is demoable live: click "Run billing" twice and show zero new invoices the second time.

**Why it cannot skip:** `next_billing_date` only advances inside the same transaction that creates the invoice. If anything fails, the date stays and the next run picks it up.

## 7. Access Control (RBAC)

| Capability | Admin | Staff | Customer |
|---|---|---|---|
| Create staff accounts | Yes | No | No |
| Manage products, plans, taxes | Yes | View only | No |
| Create discount rules | Yes | No | No |
| Create / edit quotations and subscriptions | Yes | Yes | No |
| Confirm, cancel, send, print invoices | Yes | Yes | No |
| Record payments | Yes | Yes | No |
| Finance dashboard | Yes | Yes (limited) | No |
| View own subscriptions and invoices | Yes | Yes | Own only |

Enforced by permission classes on every endpoint. Customer querysets are always filtered by the logged-in customer's ID, so changing an ID in the URL returns nothing. Auth uses JWT; password reset sends a time-limited, single-use link by email.

## 8. Discounts and Taxes

- Discounts are created by admin only: fixed amount or percentage, min purchase or quantity, start and end dates, usage limit.
- Scope is either specific products (applied to matching lines) or the whole subscription.
- Applied automatically at invoice generation, so nobody has to remember. They stop when expired or when `used_count` reaches the limit.
- Usage count increments atomically in the invoice transaction, so concurrent runs cannot exceed the limit.
- Taxes come from admin-defined rules (percentage per tax, assigned to products or lines) and are snapshotted onto invoice lines.

## 9. Performance Plan (under 2 seconds)

- Indexes: `subscriptions(status, next_billing_date)`, `invoices(status, due_date)`, `invoices(customer_id)`, `payments(invoice_id)`.
- Pagination on every list endpoint; default page size 25.
- Dashboard read model: a `daily_metrics` table updated by events, plus SQL `COUNT`/`SUM` aggregates. No Python loops over rows.
- Redis cache for dashboard summary (30-60 second TTL), invalidated on payment or invoice events.
- `select_related` / `prefetch_related` to avoid N+1 queries; check with query counters in tests.
- Proof: seed 10,000 subscriptions and 30,000 invoices, record endpoint timings, and show them in the demo.

## 10. Finance Dashboard

One screen: active subscriptions, revenue collected, amount outstanding, overdue invoices, plus MRR and ARR. Filters by date range, plan, customer and status. A summary view above a paginated table. Overdue list is sorted by days overdue so staff can chase the oldest first.

## 11. What Makes This Stand Out

- Idempotent billing engine with a live "run twice, nothing changes" demo.
- Transactional outbox: reliable events with no lost messages; n8n or webhooks can plug in later at zero extra cost.
- Append-only audit log doubling as a subscription timeline ("where does this stand").
- Snapshot pricing: old invoices never change when plans or taxes are edited.
- MRR / ARR on the dashboard, directly answering "nobody can say how much recurring revenue we have".
- Docker Compose, seeded demo data, and a clean README so judges can run it in one command.

## 12. Build Order

| Phase | Deliverable | Done when |
|---|---|---|
| 1 | Foundation schema (all modules), constraints, platform audit/outbox, subscription and invoice state-machine services, Docker | Migrations run; outbox/audit tests pass; illegal transitions rejected in tests |
| 2 | Auth, roles, password reset | Three roles log in; permissions enforced on API |
| 3 | Catalog, variants, taxes, plans APIs | Admin can launch a product and plan with flags |
| 4 | Templates and subscriptions APIs and business flow | Quote to Active flow works with audit trail |
| 5 | Billing engine and scheduler | Run twice = no duplicates; invoices fully prefilled |
| 6 | Payments and invoice actions | Record payment; invoice auto-Paid; PDF and email send |
| 7 | Discounts | Auto-applied on next invoice; stops at expiry or limit |
| 8 | Dashboard and read model | All pages under 2s on 10k seeded subscriptions |
| 9 | Seed data, README, demo script | One-command run; 3-minute demo rehearsed |
| 10 | Optional extras | n8n reminders, payment gateway test mode, proration |

## 13. Demo Script (3 minutes)

1. Sign up a customer; show password rules and the customer portal.
2. As admin: create a product with a variant, a plan, and a discount rule.
3. As staff: build a quotation from a template; move it to Active.
4. Click "Run billing": invoices generate with taxes and discount. Click again: nothing duplicates.
5. Record a payment; invoice flips to Paid; show the audit timeline.
6. Open the finance dashboard on 10k seeded subscriptions; show MRR, overdue list and response times.

## 14. Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Scope creep (n8n, gateway, proration) | Treat as bonus only after the core flow works end to end |
| Billing bugs under load | DB unique constraint, row locks, and a concurrency test running two workers |
| Slow dashboard at scale | Read model, indexes, cache, and early load testing with seeded data |
| Role leaks | Permission tests per endpoint, including customer-A-reads-customer-B attempts |
