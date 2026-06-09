# Application Architecture

This document is the canonical reference for how every API request flows through the system. Every new endpoint, service, or email must follow these patterns.

---

## Request Pipeline

```
HTTP Request
  │
  ├─ JSONContentTypeMiddleware     → 415 if Content-Type ≠ application/json (POST/PUT/PATCH)
  ├─ DRF Throttle                  → 429 when rate limit exceeded
  ├─ Serializer.is_valid()         → 400 on validation failure
  ├─ Service.dispatch()            → atomic business logic; ValueError → 400
  │    └─ transaction.on_commit()  → Celery task (email, external I/O)
  └─ ApiResponse(data, status)
```

---

## Layer 1 — HTTP Request

### Content-Type enforcement

All `POST`, `PUT`, and `PATCH` requests to `/api/` **must** send `Content-Type: application/json`.

The `JSONContentTypeMiddleware` (`cc/utils/middleware.py`) rejects anything else with HTTP **415 Unsupported Media Type**:

```json
{
  "data": {},
  "message": "",
  "errors": ["Content-Type must be application/json."],
  "success": false
}
```

This is enforced globally — no per-view checks needed.

### Rate limiting

DRF's built-in throttling is configured in `REST_FRAMEWORK.DEFAULT_THROTTLE_RATES`:

| Scope  | Limit        | Who uses it                  |
|--------|--------------|------------------------------|
| `anon` | 100 / hour   | Unauthenticated requests     |
| `user` | 1000 / hour  | Authenticated requests       |
| `auth` | 10 / minute  | Register, Login, Verify      |

Authentication endpoints use `AuthRateThrottle` (`cc/utils/throttles.py`), which maps to the `auth` scope:

```python
from cc.utils.throttles import AuthRateThrottle

class RegisterView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AuthRateThrottle]
```

---

## Layer 2 — Serializer

Serializers are the **first point of contact** with request data. They validate and normalize input before anything else runs.

**Rules:**
- Validate only. No DB writes, no side effects, no business logic.
- Field validators (`validate_<field>`) may query the DB to check existence but must not modify it.
- A `400` response is returned immediately if `is_valid()` fails — the service is never called.

```python
serializer = XSerializer(data=request.data)
if not serializer.is_valid():
    return ApiResponse(errors=serializer.errors, success=False, status=400)
```

---

## Layer 3 — Service

Services own all business logic. One class per operation, always in `cc/<app>/services.py`.

```python
class CreateSomethingService:
    def __init__(self, param1: str, param2: str) -> None:
        self.param1 = param1
        self.param2 = param2

    @transaction.atomic
    def dispatch(self) -> Something:
        # DB writes here
        result = Something.objects.create(...)

        # Defer external I/O until after the transaction commits
        transaction.on_commit(lambda: SomeMail(to=result.email, ...).send())

        return result
```

**Rules:**
- Always decorated with `@transaction.atomic`.
- External I/O (email, webhooks, third-party APIs) must go through `transaction.on_commit(lambda: ...)`. This guarantees they only fire if the transaction committed successfully.
- Raise plain Python exceptions (`ValueError`) for domain errors; the view maps them to `ApiResponse`.

Use a service when the operation involves multiple DB writes or needs to be reused across views. Simple reads or single-step writes can stay in the view.

---

## Layer 4 — ApiResponse

All endpoints return `ApiResponse` (`cc/utils/responses.py`), which wraps every response in a consistent envelope:

```json
{
  "data": {},
  "message": "Human-readable description",
  "errors": [],
  "success": true
}
```

```python
# Success
return ApiResponse(data=serializer.data, status=200)

# Validation failure
return ApiResponse(errors=serializer.errors, success=False, status=400)

# Domain error from service
except ValueError as exc:
    return ApiResponse(errors=[str(exc)], success=False, status=400)
```

---

## Layer 5 — Celery (Background Tasks)

All external I/O that is not a DB write must run as a Celery task.

### Configuration

Celery is bootstrapped in `config/celery.py` and loaded via `config/__init__.py`. Settings are in `config/settings/base.py` under the `CELERY_` namespace. The Redis instance (`REDIS_URL`) serves as both broker and result backend.

### Running the worker (development)

```bash
celery -A config.celery worker --loglevel=info
```

### Writing a task

Tasks live in `cc/<app>/tasks.py`. Use `@shared_task` so the task is registered regardless of which Celery app is active:

```python
# cc/users/tasks.py
from celery import shared_task

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def some_background_task(self, user_id: int) -> None:
    try:
        ...
    except Exception as exc:
        raise self.retry(exc=exc) from exc
```

The generic email task (`cc/utils/tasks.send_email_task`) is already provided and used by all email classes.

### Calling a task from a service

Always wrap in `transaction.on_commit` to avoid firing tasks for rolled-back transactions:

```python
@transaction.atomic
def dispatch(self) -> User:
    user = User.objects.create(...)
    transaction.on_commit(lambda: some_background_task.delay(user.id))
    return user
```

**Never call `send_mail()` directly.** Always use an email class (see below).

---

## Layer 6 — Email Classes

Each transactional email is a class in `cc/<app>/emails.py` that extends `BaseEmail` (`cc/utils/emails.py`).

### Defining an email

```python
# cc/users/emails.py
from cc.utils.emails import BaseEmail

class EmailTokenMail(BaseEmail):
    subject = "Your verification code"
    template_name = "users/emails/email_token"  # no extension

    def __init__(self, to: str, token: str, name: str) -> None:
        super().__init__(to=to, token=token, name=name)
```

### Sending

```python
EmailTokenMail(to=user.email, token=token, name=user.name).send()
```

`.send()` dispatches `send_email_task.delay(...)` (Celery), which renders both `.html` and `.txt` template variants and sends via `EmailMultiAlternatives`.

### Templates

Templates live in `cc/<app>/templates/<app>/emails/`. Two files per email:

```
cc/users/templates/users/emails/
  email_token.html   ← HTML variant
  email_token.txt    ← plain-text fallback
```

Context variables are passed via the `__init__` keyword arguments. In the example above, `token` and `name` are available as `{{ token }}` and `{{ name }}` in both templates.

### Adding a new email

1. Create `cc/<app>/emails.py` (or add to the existing one).
2. Subclass `BaseEmail`, set `subject` and `template_name`.
3. Create the two template files (`*.html` and `*.txt`).
4. Call `.send()` from inside a `transaction.on_commit(lambda: ...)` block in the service.

---

## App Layout

```
cc/<appname>/
  models.py
  admin.py
  emails.py          ← transactional email classes
  services.py        ← business logic (one class per operation)
  api/
    serializers.py   ← input validation only
    views.py         ← thin: validate → service → ApiResponse
    permissions.py   ← custom DRF permission classes
  tests/
    factories.py
    test_models.py
    api/
      test_views.py
```

---

## Testing Notes

- Tests use `config.settings.test`, which sets `CELERY_TASK_ALWAYS_EAGER = True` — tasks run synchronously inline, so `mail.outbox` is populated normally.
- Because `pytest-django` wraps each test in a savepoint, `transaction.on_commit` callbacks **do not fire** by default. Tests that need to assert on email delivery should use `@pytest.mark.django_db(transaction=True)` or Django's `TestCase.captureOnCommitCallbacks()`.
- The locmem email backend (`django.core.mail.backends.locmem.EmailBackend`) is active in tests — check `mail.outbox` to assert emails were sent.

---

## Quick Reference

| Concern | Location |
|---------|----------|
| Content-Type middleware | `cc/utils/middleware.py` |
| Rate throttle classes | `cc/utils/throttles.py` |
| Generic email Celery task | `cc/utils/tasks.py` |
| BaseEmail class | `cc/utils/emails.py` |
| ApiResponse | `cc/utils/responses.py` |
| Celery app bootstrap | `config/celery.py` |
| Celery settings | `config/settings/base.py` (CELERY_*) |
| DRF throttle rates | `config/settings/base.py` (REST_FRAMEWORK) |
