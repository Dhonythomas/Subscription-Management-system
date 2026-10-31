# RULES.md - Non-Negotiables

These rules apply to every AI agent and every contributor on **subscription-management-system**. They are not suggestions. If a task would break a rule, stop, say which rule, and ask the user before continuing.

---

## 1. Pull first, always

**Before reading, changing or modifying any code, the repository `subscription-management-system` must be pulled and up to date.** No exceptions, including "small" edits, new sessions, and resumed sessions.

Required routine, every session and before every new task:

```bash
cd subscription-management-system
git status                      # working tree must be understood; do not discard others' changes
git fetch origin
git pull --rebase origin <current-branch>
git log -3 --oneline            # confirm you are on the latest commit
```

- If the pull fails or conflicts, stop and report. Do not edit code on top of a stale or conflicted tree.
- If there are uncommitted local changes you did not make, ask the user before pulling over them.
- After finishing work, pull again before pushing, so you never overwrite newer work.
- Never `git push --force` to a shared branch. Never rewrite published history.

## 2. Build phase by phase, never all at once

- Follow the phase order in `AGENT.md`. One phase at a time.
- Do not begin the next phase until the current one is tested, committed and logged in `PROGRESS.md`.
- Do not scaffold future phases "for convenience". No stubs, empty modules, or half-built features from later phases.
- If asked to build everything at once, decline and propose the next single phase.

## 3. Money is Decimal

- All money fields: `DecimalField(max_digits=12, decimal_places=2)` / `NUMERIC(12,2)`.
- Never use `float` for money, anywhere: models, serializers, calculations, tests, seed data.
- Rounding happens in one place, with one documented rule.

## 4. Status changes only through service functions

- Subscription and invoice statuses change only via service functions that check the allowed-transitions table.
- Never assign `obj.status = ...` and save outside those services.
- The API never accepts a raw `status` field to set state; it exposes actions (confirm, cancel, close, pause, etc.).
- Every transition writes an `AuditLog` row and an `OutboxEvent` in the **same database transaction**.

## 5. Billing must be idempotent

- `UNIQUE(subscription, period_start, period_end)` on invoices stays in place. Never drop or weaken it.
- Invoice generation locks the subscription row (`select_for_update`) inside a transaction.
- `next_billing_date` advances only in the same transaction that creates the invoice.
- Running the billing job twice, or with two workers at once, must create zero duplicates and skip nothing. A test must prove this.

## 6. Invoices are snapshots

- Invoice lines copy price, tax rate, quantity and discount at billing time.
- Editing a plan, product, tax or discount later must never change an existing invoice.

## 7. RBAC is enforced on the backend

- Every endpoint has an explicit permission class. No endpoint is open by accident.
- Roles: `admin`, `staff`, `customer`. Only admin creates staff, discounts, products, plans and taxes.
- Customer querysets are always filtered by the logged-in customer. Changing an ID in a URL must return nothing or 404.
- Hiding a button in the UI is never a security measure.
- Every endpoint needs at least one permission test, including a customer-A-reads-customer-B attempt where relevant.

## 8. Security basics

- Passwords: more than eight characters, with an uppercase letter, a lowercase letter and a special character. Hashed with Django's default hashers.
- Email is unique per account.
- Password reset links are time-limited and single-use.
- No secrets in the repo. Use `.env` (git-ignored) and commit a `.env.example`.
- Never log passwords, tokens or full card/payment details.

## 9. Database discipline

- Never edit a migration that has already been committed and pulled by others. Add a new migration.
- Required indexes stay: `subscriptions(status, next_billing_date)`, `invoices(status, due_date)`, `invoices(customer)`, `payments(invoice, paid_on)`.
- Every list endpoint is paginated.
- Avoid N+1 queries: use `select_related` / `prefetch_related` and check with a query-count test on key endpoints.
- Overdue is derived (`status=Confirmed AND due_date < today AND balance > 0`), never stored.

## 10. Module boundaries

- Each module owns its tables. Other modules call its service functions or listen to its events. They never query its tables or import its models directly for writes.
- Business logic lives in services, not in views or serializers.

## 11. Tests are mandatory

- No feature is complete without tests written alongside it.
- All tests must pass before commit. Never delete, skip or weaken a test to make it pass. If a test is wrong, say so and explain before changing it.
- Required proof tests: illegal state transitions are rejected; billing twice creates no duplicates; discount usage limit is respected under repeat runs; customers cannot read each other's data; password rules are enforced.

## 12. No fakes, no silent shortcuts

- No hardcoded data, mock responses or placeholder logic presented as real functionality.
- Leftover unfinished-task markers, commented-out code and debug prints are removed or reported at the end of each phase.
- Do not silently change requirements. If the brief or design must change, say so and get approval.

## 13. Scope control

- Main features first. Extras (n8n, payment gateway, proration) only after phases 1-9 are done.
- Do not add libraries or services not in the design without asking.
- Do not refactor unrelated code while working on a task.

## 14. Docker must always work

- `docker compose up` starts the full system from a clean checkout.
- Keep `README.md` run instructions accurate after every phase.

## 15. Git hygiene

- Commit after every working step or phase with a clear message: `phase-N: summary`.
- Never commit broken code to the main branch. Work on a branch if the phase is large.
- Never commit `.env`, secrets, build artifacts or large generated files.

## 16. Honest reporting

- Say only what you verified by running it. "Should work" is not "works".
- If something fails, show the exact error. Do not hide it or work around it quietly.
- At the end of every task, list files created, changed and deleted, tests run and their result, and anything incomplete.

---

### Quick pre-flight (read before every task)

1. Did I pull the repo? (Rule 1)
2. Am I working on only the current phase? (Rule 2)
3. Will I run tests before saying it is done? (Rule 11)
4. Does my change respect money, status, billing and RBAC rules? (Rules 3-7)
