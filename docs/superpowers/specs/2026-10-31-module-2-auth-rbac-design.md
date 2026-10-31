# Design Document: Module 2 (Phase 2) — Auth, Roles & RBAC

**Document Path:** `docs/superpowers/specs/2026-10-31-module-2-auth-rbac-design.md`  
**Date:** 2026-10-31  
**Project:** Brightloop Software — Subscription Management System  
**Module:** `accounts` (Phase 2)  
**Status:** Approved for Implementation Planning

---

## 1. Intent and Why

Brightloop Software requires a secure, role-separated backend to manage subscriptions, billing, and customer self-service. Authentication and authorization must be strictly enforced at the API layer, replacing spreadsheet operations with verified permissions for three roles:
- **Admin**: Full control across catalog, plans, discounts, taxes, staff accounts, and finance reporting.
- **Staff**: Operational duties: creating quotations/subscriptions, managing invoices, and recording payments. Cannot create other staff or configure catalog/plans/taxes/discounts.
- **Customer**: Access strictly confined to their own subscriptions, invoices, and profile. Cannot view or mutate any other customer's data or administrative resources.

Hiding UI buttons is explicitly not security (Rule 7). The backend must be the authoritative barrier.

---

## 2. Goals, Non-Goals, and Anti-Goals

### Goals
- Implement JWT-based authentication (`POST /api/auth/login/`, `POST /api/auth/refresh/`) compatible with the custom `accounts.User` model from Phase 1.
- Provide public customer self-registration (`POST /api/auth/register/`) to satisfy Demo Script Step 1 ("Sign up a customer; show password rules and the customer portal").
- Enforce strict password validation rules (>8 chars, at least 1 uppercase, 1 lowercase, 1 special character) across user creation, registration, and password resets.
- Implement time-limited, single-use password reset endpoints (`POST /api/auth/password-reset/` and `POST /api/auth/password-reset-confirm/`).
- Enforce explicit DRF permission classes (`IsAdmin`, `IsStaff`, `IsCustomer`, `IsStaffOrAdmin`, `IsCustomerOwnerOrStaffAdmin`) across all endpoints with zero open endpoints by default.
- Implement admin-only staff creation (`POST /api/accounts/staff/`).
- Provide an authenticated profile endpoint (`GET /api/accounts/me/` and `PATCH /api/accounts/me/`) allowing customers to read and update their billing details.
- Provide a customer detail endpoint (`GET /api/accounts/customers/<int:pk>/`) with queryset filtering so Customer A attempting to access Customer B's URL receives a 404 (Rule 7 proof).
- Provide comprehensive test coverage for all auth and RBAC requirements.

### Non-Goals
- Modifying Phase 1 database schema or existing migrations for `User` and `Customer`.
- Implementing frontend UI pages (Frontend is tracked under Module 10).
- Building Phase 3+ endpoints (catalog, plans, subscriptions, billing, etc.).

### Anti-Goals
- Permitting endpoints without explicit permission classes.
- Permitting customer accounts to be granted staff or admin privileges.
- Permitting arbitrary password formats or weak credentials.
- Storing or logging plain-text passwords or tokens (Rule 8).

---

## 3. Constraints

- **RULES.md Compliance:**
  - Rule 1: Working tree is clean and up to date.
  - Rule 2: Strictly phase-by-phase; no Phase 3+ stubs or logic.
  - Rule 7: Backend-enforced RBAC. Every endpoint has an explicit permission class. Customer querysets always filtered by logged-in customer ID.
  - Rule 8: Security basics. Passwords >8 characters with uppercase, lowercase, special character. Hashed with Django defaults. Unique email. Password reset time-limited and single-use. No secrets in repo.
  - Rule 11: Mandatory proof tests for illegal role access, customer isolation, and password validation.
  - Rule 13: Scope control.

---

## 4. Approaches Considered

### Approach 1: DRF with `djangorestframework-simplejwt` (Selected)
- Add `djangorestframework-simplejwt` to `requirements.txt`.
- Configure `rest_framework_simplejwt.authentication.JWTAuthentication` as the default authentication class in `settings.py`.
- Custom JWT serializer embedding user role, email, and customer ID in claims.
- Standard token refresh and claims handling.
- **Why Chosen:** Aligns directly with `docs/design.md` ("REST + JWT + RBAC"), robust, industry standard, well-tested, and secure.

### Approach 2: Custom Token Authentication with PyJWT
- Manually encode/decode JWTs in custom middleware and authentication classes.
- **Rejected:** High maintenance overhead, prone to token validation bugs, and reinvents what `simplejwt` provides out of the box.

### Approach 3: Built-in DRF Database Tokens
- Use Django's `authtoken` table.
- **Rejected:** Conflicts with the explicit architectural contract in `docs/design.md` requiring JWT.

---

## 5. Architectural and Technical Specification

### 5.1 Dependencies & Settings
- Add `djangorestframework-simplejwt==5.3.1` to `backend/requirements.txt`.
- Update `backend/config/settings.py`:
  - Add `'rest_framework_simplejwt'` to `INSTALLED_APPS`.
  - Configure `REST_FRAMEWORK` with `DEFAULT_AUTHENTICATION_CLASSES`:
    `'rest_framework_simplejwt.authentication.JWTAuthentication'`.
  - Set `DEFAULT_PERMISSION_CLASSES` to `['rest_framework.permissions.IsAuthenticated']`.
  - Configure `SIMPLE_JWT`:
    - `ACCESS_TOKEN_LIFETIME`: 30 minutes
    - `REFRESH_TOKEN_LIFETIME`: 1 day
    - `ROTATE_REFRESH_TOKENS`: True
    - `BLACKLIST_AFTER_ROTATION`: False
  - Configure `AUTH_PASSWORD_VALIDATORS` with custom validator:
    `apps.accounts.validators.ComplexPasswordValidator`.

### 5.2 Password Validation
- Create `apps/accounts/validators.py`:
  - `ComplexPasswordValidator`:
    - Minimum length: 9 characters (`>8` chars per Rule 8).
    - Regex checks: at least 1 uppercase (`[A-Z]`), at least 1 lowercase (`[a-z]`), at least 1 special character (`[!@#$%^&*(),.?":{}|<>]`).
    - Raises `django.core.exceptions.ValidationError` with descriptive messages.

### 5.3 Permissions Framework & Queryset Scoping
- Create `apps/accounts/permissions.py`:
  - `IsAdmin`: Checks `request.user.is_authenticated and request.user.role == Role.ADMIN`.
  - `IsStaff`: Checks `request.user.is_authenticated and request.user.role == Role.STAFF`.
  - `IsCustomer`: Checks `request.user.is_authenticated and request.user.role == Role.CUSTOMER`.
  - `IsStaffOrAdmin`: Checks `request.user.is_authenticated and request.user.role in (Role.ADMIN, Role.STAFF)`.
  - `IsCustomerOwnerOrStaffAdmin`: Object-level permission checking whether the object belongs to the authenticated customer or caller is staff/admin.
- Create `apps/accounts/mixins.py`:
  - `CustomerQuerySetMixin`: Configurable mixin that filters querysets by `customer.user == request.user` (or `user == request.user` if querying `Customer` directly). When a customer requests an object outside their ownership, returns 404. Staff and Admin see the full queryset.

### 5.4 Endpoints & Views
- In `apps/accounts/urls.py` mounted at `/api/auth/` and `/api/accounts/`:
  1. `POST /api/auth/register/` (AllowAny):
     - Input: `{"email": "...", "password": "...", "name": "...", "billing_address": "...", "billing_phone": "..."}`
     - Validates password via `ComplexPasswordValidator`.
     - Atomically creates `User(role=Role.CUSTOMER)` and linked `Customer`.
     - Returns JWT tokens (`access`, `refresh`) and user profile data (201 Created).
  2. `POST /api/auth/login/` (AllowAny):
     - Input: `{"email": "...", "password": "..."}`
     - Validates credentials via custom `TokenObtainPairSerializer`.
     - Output: `{"access": "...", "refresh": "...", "user": {"id": 1, "email": "...", "role": "admin", "customer_id": ...}}`
  3. `POST /api/auth/refresh/` (AllowAny):
     - Standard `TokenRefreshView`.
  4. `POST /api/auth/password-reset/` (AllowAny):
     - Input: `{"email": "..."}`
     - Generates token with `django.contrib.auth.tokens.default_token_generator` and `urlsafe_base64_encode`.
     - Dispatches reset link email (in dev/test, uses Django mail outbox / console).
     - Response: Generic success message (to prevent email enumeration).
  5. `POST /api/auth/password-reset-confirm/` (AllowAny):
     - Input: `{"uidb64": "...", "token": "...", "new_password": "..."}`
     - Decodes `uidb64`, fetches user, validates token via `default_token_generator.check_token()`.
     - Validates password via `validate_password()`.
     - Sets password with `user.set_password()` and saves.
     - Automatically invalidates token on change (single-use guarantee).
  6. `POST /api/accounts/staff/` (IsAdmin):
     - Input: `{"email": "...", "password": "..."}`
     - Validates password and unique email.
     - Creates `User` with `role=Role.STAFF`, `is_staff=True`.
     - Output: Created staff user details (201 Created).
  7. `GET /api/accounts/me/` & `PATCH /api/accounts/me/` (IsAuthenticated):
     - `GET`: Returns current user details and customer profile if role is customer.
     - `PATCH`: Allows customer to update billing details (`name`, `billing_address`, `billing_phone`, `billing_email`). Non-customer users cannot edit customer fields.
  8. `GET /api/accounts/customers/<int:pk>/` (IsAuthenticated + CustomerQuerySetMixin):
     - Staff/Admin can view any customer.
     - Customer callers are scoped strictly to their own `Customer.id`. Tampering with ID (e.g. Customer A requesting Customer B's PK) returns 404 Not Found.

### 5.5 URL Routing
- Update `backend/config/urls.py` to route `/api/auth/` and `/api/accounts/` to `apps.accounts.urls`.
- Keep existing `/health/` endpoint open for container healthchecks.

---

## 6. Test Plan (Mandatory Proof Tests per Rule 11)

1. **Password Validation Tests:**
   - Test password with <9 chars (rejected).
   - Test password missing uppercase (rejected).
   - Test password missing lowercase (rejected).
   - Test password missing special char (rejected).
   - Test valid password (accepted).
2. **Registration & Login Tests:**
   - Public customer signup creates both User and Customer records and returns JWT tokens.
   - Admin login returns valid JWT with role claim `admin`.
   - Staff login returns valid JWT with role claim `staff`.
   - Customer login returns valid JWT with role claim `customer`.
   - Invalid password or email returns 401 Unauthorized.
   - Token refresh successfully yields new access token.
3. **RBAC & Permission Tests:**
   - Admin can create staff account via `/api/accounts/staff/` (201).
   - Staff caller to `/api/accounts/staff/` is rejected with 403 Forbidden.
   - Customer caller to `/api/accounts/staff/` is rejected with 403 Forbidden.
   - Unauthenticated caller to `/api/accounts/staff/` is rejected with 401 Unauthorized.
4. **Customer Isolation Tests (Rule 7 Proof):**
   - Customer A authenticated via JWT can retrieve `/api/accounts/customers/<pk_A>/`.
   - Customer A attempting to retrieve `/api/accounts/customers/<pk_B>/` returns **404 Not Found** (ID tampering blocked).
   - Staff and Admin can retrieve both `<pk_A>` and `<pk_B>`.
5. **Customer Profile Updates:**
   - Customer can update their billing information via `PATCH /api/accounts/me/`.
   - Attempting to update restricted fields (e.g. `role`, `is_staff`, `is_superuser`) is ignored/forbidden.
6. **Password Reset Tests (Rule 8 Proof):**
   - Password reset request generates valid single-use token for user.
   - Password reset confirm with valid token successfully updates password.
   - Reusing the same reset token is rejected (single-use proof).
   - Calling confirm with invalid/expired token or weak password is rejected.
