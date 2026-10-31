# AGENT.md

Instructions for any AI coding agent working on **subscription-management-system**.

Read this file and `RULES.md` fully before doing anything. `RULES.md` is non-negotiable and overrides everything else, including the user's convenience requests, unless the user explicitly says to break a specific rule.

## Project

A subscription billing platform for a fictional company, Brightloop Software. It runs the full life of a subscription business: products and plans, quotations, subscriptions, automatic invoicing, payments, discounts and revenue reporting.

Core flow: **Product > Plan > Quotation > Subscription > Invoice > Payment > Reports**

Source of truth for design: `docs/design.md` (the Design Plan). If code and the design disagree, stop and ask.

## Stack

- Backend: Django 5 + Django REST Framework
- Database: PostgreSQL 16
- Queue and cache: Redis 7, with Celery (worker + beat)
- Frontend: React (Vite), role-based routes: admin/staff panel, customer portal, finance dashboard
- Runtime: Docker Compose (`docker compose up` must always work)

If the stack was changed by the user, they will say so here: `STACK_OVERRIDE: none`

## Architecture in one paragraph

Modular monolith with an event-driven core. One Django app per module: `accounts`, `catalog`, `plans`, `subscriptions`, `billing`, `payments`, `discounts`, `reports`, `platform`. Modules talk only through service functions and domain events, never through each other's tables. The billing engine runs in a separate worker process. State changes write an audit row and an outbox event in the same transaction.

Django apps live under `backend/apps/<module>/`. App labels remain `accounts`, `catalog`, `plans`, `subscriptions`, `billing`, `payments`, `discounts`, `reports`, and `platform`. The nested package avoids shadowing Python's standard-library `platform` module.

`platform` owns the shared base models, money quantization, audit/outbox helpers, the generic transition helper, and the outbox dispatcher. Business modules own their own tables and expose services instead of letting another module write their models directly.

## Start-of-session checklist (do this every time)

1. Run the pull routine from `RULES.md` rule 1. Do not skip it.
2. Read `docs/design.md`, `RULES.md`, and `PROGRESS.md`.
3. Identify the current phase from `PROGRESS.md`. Work on that phase only.
4. State the phase and the plan in a few lines before writing code.
5. Confirm tests currently pass before changing anything: `docker compose run --rm api pytest`. If Docker is unavailable in the local environment, run the same suite against the configured PostgreSQL instance and record that fact honestly.

## Phases (build in this order, one at a time)

| Phase | Deliverable | Done when |
|---|---|---|
| 1 | Foundation schema (all modules), constraints, platform audit/outbox, subscription and invoice state-machine services, Docker | Migrations run; `docker compose up` starts clean; outbox/audit tests pass; illegal transitions are rejected |
| 2 | Auth, roles, password reset | Three roles log in; permissions enforced on the API |
| 3 | Catalog, variants, taxes, plans APIs and business services | Admin can launch a product and plan with flags |
| 4 | Quotation templates and subscriptions APIs and business flow | Quote to Active flow works with audit trail |
| 5 | Billing engine and scheduler | Run twice = no duplicates; invoices fully prefilled |
| 6 | Payments and invoice actions | Record payment; invoice auto-Paid; PDF and email send |
| 7 | Discounts engine | Auto-applied on next invoice; stops at expiry or limit |
| 8 | Dashboard and read model | All pages under 2s on 10k seeded subscriptions |
| 9 | Seed data, README, demo script | One-command run; 3-minute demo rehearsed |
| 10 | Optional extras (n8n, payment gateway, proration) | Only after phases 1-9 are complete |

Phase 1 is the **foundation schema and platform** phase. All core models and migrations are created in Phase 1, including the custom user, subscription and invoice state machines, and the required indexes. Later phases add APIs, business services, and new migrations; they never rewrite committed migrations or the foundation schema. This is the **Phase 1 schema freeze**.

Never start phase N+1 until phase N is complete, tested, committed and recorded in `PROGRESS.md`. Never build multiple phases in one go, even if asked casually. If the user asks for "everything", push back and propose the next single phase.

## How to work inside a phase

- Work in small steps. After each meaningful step, run the tests.
- Write tests together with the code, not afterwards.
- Prefer boring, readable code over clever code.
- Follow existing patterns in the repo before inventing new ones.
- If a requirement is ambiguous, ask one focused question instead of guessing.
- If something in the brief seems wrong or risky, say so plainly before proceeding.
- Keep money as `Decimal` and use the one shared quantization rule.
- Change statuses only through service functions, and keep audit plus outbox writes in the same transaction.

## End-of-phase checklist

1. All tests pass (paste the summary line in your report).
2. Run the app via Docker and confirm it starts clean.
3. Search for leftovers: unfinished-task markers, mocks, hardcoded values, commented-out code. Remove or list them honestly.
4. Update `PROGRESS.md` (what was done, what was verified, known gaps).
5. Commit with a clear message: `phase-N: short summary`.
6. Report back: what was built, how it was verified, what is not done. Do not claim "done" for anything you did not run.

## Reporting rules

- Be direct. No sugarcoating, no padding.
- Never say something works unless you ran it and saw it work.
- If a test fails or you are stuck, say so and show the exact error.
- List every file you created, changed or deleted.

## Files in this repo that matter

- `AGENT.md` (this file): how to work
- `RULES.md`: non-negotiable rules
- `docs/design.md`: the design plan, source of truth
- `docs/platform-contract.md`: interfaces other modules code against
- `PROGRESS.md`: current phase and history
- `README.md`: run instructions (kept current)
