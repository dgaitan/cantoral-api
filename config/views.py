from django.db import connection
from django.http import HttpRequest, HttpResponse, JsonResponse

_LANDING_PAGE_HTML = """<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>Cantoral Católico</title>
<style>
  html, body {
    height: 100%;
    margin: 0;
  }
  body {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 2rem;
    box-sizing: border-box;
    background: #1a1410;
    color: #f2ece0;
    font-family: Georgia, "Times New Roman", serif;
  }
  main {
    max-width: 36rem;
    text-align: center;
  }
  blockquote {
    margin: 0 0 1rem;
    font-size: 1.5rem;
    line-height: 1.5;
    font-style: italic;
  }
  cite {
    font-size: 1rem;
    font-style: normal;
    letter-spacing: 0.05em;
    color: #c9a86a;
  }
</style>
</head>
<body>
<main>
  <blockquote>
    &ldquo;En el principio era la Palabra, y la Palabra era Dios&rdquo;
  </blockquote>
  <cite>Juan 1, 1</cite>
</main>
</body>
</html>
"""


def healthcheck(request: HttpRequest) -> JsonResponse:
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
    return JsonResponse({"status": "ok"})


def landing_or_not_found(
    request: HttpRequest,
    exception: Exception | None = None,
) -> HttpResponse:
    """Serve a plain-HTML landing message for non-API, non-JSON requests.

    Django's URL resolver routes here (as handler404) for any path that
    doesn't match a URL pattern. API clients (path under /api/, or an
    Accept header asking for JSON) keep getting a JSON 404 instead.
    """
    accept = request.META.get("HTTP_ACCEPT", "")
    wants_json = request.path.startswith("/api/") or "application/json" in accept
    if wants_json:
        return JsonResponse({"detail": "Not found."}, status=404)
    return HttpResponse(_LANDING_PAGE_HTML, content_type="text/html", status=404)
