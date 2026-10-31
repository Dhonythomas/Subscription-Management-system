# Module 2 Auth and RBAC Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the Accounts module to the approved Phase 2 design: JWT auth, customer signup, password reset, staff administration, customer profiles, and backend-enforced ownership permissions.

**Architecture:** Keep auth and account behavior in the existing Django `accounts` app. Use SimpleJWT with custom role/email/customer claims; keep account creation and reset logic in services; serializers validate request data; explicit DRF permissions and queryset scoping enforce RBAC. Do not change the frozen Phase 1 schema.

**Tech Stack:** Django 5.2, Django REST Framework, `djangorestframework-simplejwt==5.3.1`, PostgreSQL 16, pytest/pytest-django.

**Spec:** `docs/superpowers/specs/2026-10-31-module-2-auth-rbac-design.md`; project constraints in `AGENT.md`, `RULES.md`, and `docs/design.md`.

## Global Constraints

- Do not modify Phase 1 models or committed migrations.
- JWT access lifetime is 30 minutes; refresh lifetime is 1 day; rotate refresh tokens; blacklist-after-rotation is false.
- Default API permission is `IsAuthenticated`; public auth endpoints explicitly declare `AllowAny`; `/health/` remains open.
- Three roles are `admin`, `staff`, and `customer`; customers cannot grant themselves staff/admin roles.
- Passwords must be longer than 8 characters and include uppercase, lowercase, and a special character; use Django password hashers.
- Password reset remains generic to prevent account enumeration, time-limited, and single-use.
- Never return password hashes, log credentials/tokens, weaken tests, or change unrelated modules.
- Every list endpoint is paginated; use `select_related` and prove query behavior where applicable.

## Review Focus

- Missing, malformed, expired, or wrong-role credentials must not grant access; test JWT-protected access with real bearer tokens.
- Signup and staff creation must not accept elevated roles or leave orphaned user/customer records; test role tampering and atomic signup.
- Password reset must not reveal whether an email exists, accept weak passwords, or permit expired/replayed tokens; test each case.
- Customer A must never see or mutate Customer B's record, including through a changed URL ID; test 404 isolation.
- Non-customer profile updates and attempts to patch identity/role fields must be rejected; test both.

---

### Task 1: JWT login, claims, and refresh

**Files:**
- Modify: `backend/requirements.txt`
- Modify: `backend/config/settings.py`
- Modify: `backend/config/urls.py`
- Modify: `backend/apps/accounts/serializers.py`
- Modify: `backend/apps/accounts/views.py`
- Modify: `backend/apps/accounts/urls.py`
- Create: `backend/apps/accounts/auth_urls.py`
- Test: `backend/apps/accounts/tests/test_api.py`

**Interfaces:**
- Produce `RoleTokenObtainPairSerializer.get_token(user)` with `role`, `email`, and `customer_id` claims.
- Produce `POST /api/auth/login/` and `POST /api/auth/refresh/` returning SimpleJWT access/refresh token responses.
- Protected endpoints authenticate using `JWTAuthentication`; unauthenticated requests default to denied.

- [ ] Write tests for admin/staff/customer login, custom claims, bad credentials, refresh, and a real bearer-token request to a protected endpoint.
- [ ] Run those tests and confirm the missing JWT routes/authentication fail.
- [ ] Add SimpleJWT at the exact pinned version, settings, claim serializer, login/refresh views, and `/api/auth/` routing; remove DB-token auth from the API configuration.
- [ ] Run the focused tests and confirm all pass.
- [ ] Commit as `phase-2: add jwt authentication`.

### Task 2: Public customer registration

**Files:**
- Modify: `backend/apps/accounts/serializers.py`
- Modify: `backend/apps/accounts/services.py`
- Modify: `backend/apps/accounts/views.py`
- Modify: `backend/apps/accounts/urls.py`
- Modify: `backend/apps/accounts/auth_urls.py`
- Test: `backend/apps/accounts/tests/test_api.py`

**Interfaces:**
- Produce `create_customer_account(*, email, password, name, billing_address="", billing_phone="", billing_email="") -> User`, atomically creating a `Role.CUSTOMER` user and linked `Customer`.
- Produce `POST /api/auth/register/` with `AllowAny`, returning HTTP 201, access/refresh tokens, and profile data.

- [ ] Write tests for valid registration, customer role and linked record, returned JWT claims, duplicate email, weak password, and attempts to submit role/admin fields.
- [ ] Run focused tests and confirm registration is absent/fails.
- [ ] Implement registration through the service and serializer; accept no caller-supplied role or privilege fields.
- [ ] Run focused tests and confirm all pass.
- [ ] Commit as `phase-2: add customer registration`.

### Task 3: Time-limited, single-use password reset

**Files:**
- Modify: `backend/apps/accounts/serializers.py`
- Modify: `backend/apps/accounts/services.py`
- Modify: `backend/apps/accounts/views.py`
- Modify: `backend/apps/accounts/urls.py`
- Test: `backend/apps/accounts/tests/test_api.py`

**Interfaces:**
- Produce `POST /api/auth/password-reset/` and `POST /api/auth/password-reset-confirm/` using `uidb64`, `token`, and `new_password`.
- Reset request always returns the same public response; confirmation validates the Django token, password policy, and user. The reset token is single-use; JWT access tokens remain valid until their configured expiry.

- [ ] Write tests for existing/nonexistent emails returning the same response, valid reset, invalid UID/token, expired token, weak password, and replay rejection.
- [ ] Run focused tests and confirm missing edge cases fail.
- [ ] Implement reset flow with Django's time-limited `default_token_generator`, generic email behavior, and password-change token invalidation.
- [ ] Run focused tests and confirm all pass.
- [ ] Commit as `phase-2: complete password reset flow`.

### Task 4: Admin-only staff creation and role permissions

**Files:**
- Modify: `backend/apps/accounts/permissions.py`
- Modify: `backend/apps/accounts/serializers.py`
- Modify: `backend/apps/accounts/services.py`
- Modify: `backend/apps/accounts/views.py`
- Modify: `backend/apps/accounts/urls.py`
- Modify: `backend/apps/accounts/permissions.py`
- Test: `backend/apps/accounts/tests/test_api.py`

**Interfaces:**
- Produce `POST /api/accounts/staff/`, requiring `IsAdmin`, accepting only email/password, and always creating an active `Role.STAFF` user with `is_staff=True`.
- Produce role permission classes `IsAdmin`, `IsStaff`, `IsCustomer`, and `IsStaffOrAdmin`; Task 5 adds `IsCustomerOwnerOrStaffAdmin`.
- No public or customer path can create elevated accounts.

- [ ] Write tests proving admin success, staff/customer/anonymous denial, invalid password rejection, and resistance to role/is_superuser field injection.
- [ ] Run focused tests and confirm required route/permission cases fail.
- [ ] Implement the narrow staff endpoint and remove/restrict generic managed-user creation that can create unrelated user roles.
- [ ] Run focused tests and confirm all pass.
- [ ] Commit as `phase-2: restrict staff account creation`.

### Task 5: Customer profile and ownership-safe customer reads

**Files:**
- Modify: `backend/apps/accounts/permissions.py`
- Modify: `backend/apps/accounts/serializers.py`
- Modify: `backend/apps/accounts/views.py`
- Modify: `backend/apps/accounts/urls.py`
- Create: `backend/apps/accounts/mixins.py`
- Test: `backend/apps/accounts/tests/test_api.py`

**Interfaces:**
- Produce `GET/PATCH /api/accounts/me/`; GET includes user and customer billing profile, while PATCH is customer-only and updates only `name`, `billing_email`, `billing_address`, and `billing_phone`.
- Produce `CustomerQuerySetMixin` with configurable owner lookup (`user` or `customer__user`) and `IsCustomerOwnerOrStaffAdmin` object permission.
- Customer list/detail reads are read-only; customer querysets include only the caller's own customer record, while staff/admin can read all.

- [ ] Write tests for customer profile reads/updates, staff/admin update denial, protected-field rejection, own customer detail, cross-customer 404, and staff/admin access to both records.
- [ ] Add pagination/query-count assertions for customer list queries and run the focused tests.
- [ ] Implement profile serialization and scoped read-only customer endpoints with explicit permissions and `select_related("user")`.
- [ ] Run focused tests and confirm all pass.
- [ ] Commit as `phase-2: add customer profile and isolation`.

### Task 6: Full Phase 2 verification and handoff

**Files:**
- Modify: `PROGRESS.md`
- Modify only if needed for accurate commands: `README.md`

**Interfaces:**
- No schema/migration changes. All auth routes, RBAC behavior, and completion evidence are documented accurately.

- [ ] Run Accounts tests, the full pytest suite, `manage.py check`, and `makemigrations --check --dry-run` against PostgreSQL.
- [ ] Run Docker Compose build/up, API tests, and `/health/` verification if Docker Engine is available; otherwise report the exact blocker.
- [ ] Review `git diff --check`, inspect changes, search for secrets/debug prints/TODOs, and verify no `.env` is committed.
- [ ] Update `PROGRESS.md` with tested Phase 2 status and known limitations.
- [ ] Commit as `phase-2: verify auth and rbac` and leave the branch clean.
