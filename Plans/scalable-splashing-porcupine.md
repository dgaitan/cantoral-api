# Plan: API-Only Django Setup with JWT, Ruff, Typed Python, and CLAUDE.md

## Context

The project was bootstrapped with Cookiecutter Django, which includes a full frontend stack (templates, crispy forms, allauth UI flows, djLint, etc.). The goal is to strip it down to a clean, typed, API-only backend using DRF + JWT, two named PostgreSQL databases, and Ruff as the sole linter/formatter. The CLAUDE.md will document the resulting architecture for future sessions.

---

## Step 1 — Update `pyproject.toml`

### Remove (frontend / irrelevant packages)
- `collectfasta` — static file acceleration, no frontend
- `crispy-bootstrap5` — Bootstrap forms
- `django-allauth[mfa]` — replaced by simplejwt direct auth
- `django-anymail[sendgrid]` — email delivery (no email flows needed for API auth)
- `django-crispy-forms` — forms library
- `django-storages[s3]` — S3 media (no file uploads in scope)
- `pillow` — image processing

### Add (production)
- `djangorestframework-simplejwt` — JWT auth for DRF

### Remove (dev)
- `djlint` — HTML template linter (no templates)
- `sphinx`, `sphinx-autobuild` — docs generator
- `werkzeug[watchdog]` — Werkzeug dev server (standard `runserver` is fine)

### Fix pytest table name (bug in current config)
`[tool.pytest]` → `[tool.pytest.ini_options]` (pytest ignores the wrong section name)

### Remove `[tool.djlint]` section entirely

---

## Step 2 — Update `config/settings/base.py`

### INSTALLED_APPS — remove
- `crispy_forms`, `crispy_bootstrap5`
- `allauth`, `allauth.account`, `allauth.mfa`, `allauth.socialaccount`
- `rest_framework.authtoken` (replaced by simplejwt)
- `django.forms` (form renderer, not needed without templates)

### INSTALLED_APPS — add
- `rest_framework_simplejwt`
- `rest_framework_simplejwt.token_blacklist` (for refresh token rotation)

### MIDDLEWARE — remove
- `allauth.account.middleware.AccountMiddleware`

### REST_FRAMEWORK — replace
```python
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}
```

### Add SIMPLE_JWT block
```python
from datetime import timedelta
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}
```

### Database — rename and add test DB
```python
DATABASES = {
    "default": env.db("DATABASE_URL", default="postgres:///cantoral"),
}
DATABASES["default"]["ATOMIC_REQUESTS"] = True
DATABASES["default"]["TEST"] = {"NAME": "cantoral_tests"}
```

### Remove
- `CRISPY_*` settings
- `FORM_RENDERER`
- `LOGIN_REDIRECT_URL`, `LOGIN_URL`
- `ACCOUNT_*`, `SOCIALACCOUNT_*` allauth settings
- `STATICFILES_DIRS` (keep `STATIC_ROOT` and `STATIC_URL` for admin)
- `MEDIA_ROOT`, `MEDIA_URL`

---

## Step 3 — Update `config/urls.py`

Remove:
- Home and about template views
- `users/` frontend URL include
- `accounts/` allauth include
- `/api/auth-token/` (DRF token auth)

Add:
```python
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenVerifyView

path("api/auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
path("api/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
path("api/auth/token/verify/", TokenVerifyView.as_view(), name="token_verify"),
```

Keep: `admin/`, `api/` (DRF router), `api/schema/`, `api/docs/`

---

## Step 4 — Clean up `cc/users/`

### Delete
- `views.py` — template-based views (UserRedirectView, UserUpdateView, UserDetailView)
- `forms.py` — allauth signup forms and admin form
- `adapters.py` — allauth adapters
- `context_processors.py` — allauth context processor
- `urls.py` — no frontend URL patterns remain
- `templates/` directory entirely

### Modify `cc/users/api/serializers.py`
Add `CustomTokenObtainPairSerializer` so simplejwt accepts `email` instead of `username`:
```python
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = User.EMAIL_FIELD
```

Wire it in `SIMPLE_JWT` settings: `"TOKEN_OBTAIN_SERIALIZER": "cc.users.api.serializers.CustomTokenObtainPairSerializer"`

### Keep
- `models.py`, `managers.py`, `admin.py`, `apps.py`
- `api/views.py`, `api/serializers.py` (update)
- `tests/` (update to remove allauth-dependent tests)
- `migrations/`

---

## Step 5 — Update `config/api_router.py`

Remove the auth-token endpoint registration (it moves to urls.py as JWT endpoints). Keep `UserViewSet` registration.

---

## Step 6 — Update `config/settings/local.py`

Remove `django-extensions` from INSTALLED_APPS (package is being removed). Keep `debug_toolbar` — useful for inspecting API queries.

---

## Step 7 — Update `.pre-commit-config.yaml`

Remove the two `djlint` hooks (`djlint-reformat-django`, `djlint-django`). Keep `ruff-check`, `ruff-format`, `django-upgrade`, and standard hooks.

---

## Step 8 — Update `cc/users/tests/`

Remove tests that depend on allauth forms/adapters/views (test_forms.py, test_views.py template tests, test_urls.py). Keep and update:
- `tests/test_models.py`
- `tests/test_managers.py`
- `tests/api/test_views.py` — add JWT auth tests (token obtain, refresh, protected endpoint)

Update `conftest.py` to remove allauth-specific fixture setup.

---

## Step 9 — Create `CLAUDE.md`

Document:

```
# CLAUDE.md

## Commands
uv run python manage.py runserver            # dev server
uv run pytest                                # all tests
uv run pytest cc/users/tests/test_models.py  # single file
uv run pytest -k test_name                  # single test by name
uv run coverage run -m pytest && uv run coverage html
uv run ruff check .                          # lint
uv run ruff check --fix .                   # lint + autofix
uv run ruff format .                         # format
uv run mypy cc                               # type check

## Architecture
- API-only Django 6 project, no frontend templates (admin UI only)
- DRF + drf-spectacular for REST API and OpenAPI schema
- JWT auth via djangorestframework-simplejwt (Bearer tokens)
  - POST /api/auth/token/         → obtain access + refresh tokens
  - POST /api/auth/token/refresh/ → rotate refresh token
  - POST /api/auth/token/verify/  → verify token validity
- Custom User model (cc.users.User): email-based login, no username field
  - CustomTokenObtainPairSerializer wires simplejwt to accept "email" field
- Two PostgreSQL databases:
  - "cantoral"       → DATABASE_URL=postgres:///cantoral (main)
  - "cantoral_tests" → used automatically by pytest (TEST.NAME in settings)
- Settings layered: base.py ← local.py / test.py / production.py

## Adding a new app
1. Create: cc/<appname>/models.py, api/serializers.py, api/views.py, tests/
2. Register in LOCAL_APPS in config/settings/base.py
3. Register router in config/api_router.py

## Type checking
- mypy + django-stubs + drf-stubs enforce typed Python
- All new models, serializers, and views must be fully annotated
- Migrations excluded from mypy

## Test patterns
- Factories in cc/<app>/tests/factories.py (factory-boy)
- Use pytest fixtures, not unittest.TestCase
- Test DB is "cantoral_tests" — created/destroyed automatically by pytest-django
```

---

## Verification

1. `uv sync` — installs updated dependencies without errors
2. `uv run python manage.py migrate` — migrations apply cleanly
3. `uv run pytest` — test suite passes against `cantoral_tests` DB
4. `uv run ruff check .` — zero lint errors
5. `uv run mypy cc` — zero type errors
6. `curl -X POST http://localhost:8000/api/auth/token/ -d '{"email":"...","password":"..."}' -H "Content-Type: application/json"` — returns `access` + `refresh` tokens
7. `curl -H "Authorization: Bearer <token>" http://localhost:8000/api/users/me/` — returns user data
