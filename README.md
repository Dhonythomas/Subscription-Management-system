# Subscription Management System

A subscription billing platform for Brightloop Software. It runs the full life of a subscription business, from products and plans through quotations, subscriptions, automatic invoices, payments, discounts, and revenue reporting.

Core flow: **Product > Plan > Quotation > Subscription > Invoice > Payment > Reports**

## Stack

- Django 5 + Django REST Framework
- PostgreSQL 16
- Redis 7 + Celery worker and beat
- React (Vite) frontend, delivered in later phases
- Docker Compose

## Current status

**Phase 1 — Foundation is in progress.** The build is creating the complete core schema, the custom user model, the platform audit/outbox layer, the subscription and invoice state machines, required database indexes, and the Docker Compose runtime. Later phases add APIs and business workflows on top of that schema freeze.

Full setup and run instructions are finalized in Phase 1 Task 11. Until then, the repository is not yet a runnable application.

## Design

- `docs/design.md` — product design and source of truth
- `docs/platform-contract.md` — interfaces shared across modules
- `AGENT.md` — working instructions for contributors and AI agents
- `RULES.md` — non-negotiable engineering rules
- `PROGRESS.md` — phase status and verification log
