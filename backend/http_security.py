"""HTTP-level hardening applied to every API response.

The frontend (static HTML/JS) is served by Vercel and gets its own headers
from ``vercel.json``. This module covers the API: strict headers, a locked-down
CSP (the API never returns HTML), no-store caching so financial payloads are
never written to a shared cache, a request-body size cap, and a coarse
in-memory per-IP rate limit.
"""

import time
from collections import defaultdict, deque

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

from backend.config import get_settings
from backend.services.login_throttle import client_ip

# API responses carry no scripts, styles, images or frames — deny everything.
_API_CSP = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"

_SECURITY_HEADERS = {
    "Strict-Transport-Security": "max-age=63072000; includeSubDomains; preload",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Content-Security-Policy": _API_CSP,
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-site",
    "X-Permitted-Cross-Domain-Policies": "none",
    "Permissions-Policy": (
        "camera=(), microphone=(), geolocation=(), payment=(), usb=(), "
        "accelerometer=(), gyroscope=(), magnetometer=(), interest-cohort=()"
    ),
}

# Request-body caps. Imports carry a CSV; everything else is small JSON.
_MAX_BODY_DEFAULT = 1 * 1024 * 1024  # 1 MiB
_MAX_BODY_UPLOAD = 12 * 1024 * 1024  # 12 MiB
_UPLOAD_PREFIXES = ("/api/imports/",)

# Coarse per-IP rate limit. Best-effort: a warm serverless instance keeps this,
# a cold start resets it — the DB-backed login throttle is the durable layer.
_WINDOW_S = 60.0
_MAX_PER_WINDOW = 150
_MAX_WRITES_PER_WINDOW = 40
_hits: dict[str, deque[float]] = defaultdict(deque)
_writes: dict[str, deque[float]] = defaultdict(deque)
_last_prune = 0.0


def _hit(bucket: dict[str, deque[float]], ip: str, limit: int, now: float) -> bool:
    """Record a hit; return True if the IP is now over ``limit``."""
    q = bucket[ip]
    cutoff = now - _WINDOW_S
    while q and q[0] < cutoff:
        q.popleft()
    q.append(now)
    return len(q) > limit


def _prune(now: float) -> None:
    global _last_prune
    if now - _last_prune < _WINDOW_S:
        return
    _last_prune = now
    cutoff = now - _WINDOW_S
    for bucket in (_hits, _writes):
        for ip in [k for k, q in bucket.items() if not q or q[-1] < cutoff]:
            del bucket[ip]


def _max_body_for(path: str) -> int:
    return (
        _MAX_BODY_UPLOAD
        if any(path.startswith(p) for p in _UPLOAD_PREFIXES)
        else _MAX_BODY_DEFAULT
    )


def _apply_headers(response: Response) -> Response:
    for key, value in _SECURITY_HEADERS.items():
        response.headers.setdefault(key, value)
    response.headers["Cache-Control"] = "no-store"
    response.headers.setdefault("Pragma", "no-cache")
    return response


def _blocked(
    status_code: int, detail: str, *, retry_after: int | None = None
) -> Response:
    resp = JSONResponse(status_code=status_code, content={"detail": detail})
    if retry_after is not None:
        resp.headers["Retry-After"] = str(retry_after)
    return _apply_headers(resp)


def install(app: FastAPI) -> None:
    @app.middleware("http")
    async def _harden(request: Request, call_next):
        now = time.monotonic()
        _prune(now)

        content_length = request.headers.get("content-length")
        if (
            content_length
            and content_length.isdigit()
            and int(content_length) > _max_body_for(request.url.path)
        ):
            return _blocked(413, "Request body too large")

        if request.method != "OPTIONS" and get_settings().rate_limit_enabled:
            ip = client_ip(request)
            over = _hit(_hits, ip, _MAX_PER_WINDOW, now)
            if request.method not in ("GET", "HEAD"):
                over = _hit(_writes, ip, _MAX_WRITES_PER_WINDOW, now) or over
            if over:
                return _blocked(429, "Too many requests", retry_after=60)

        return _apply_headers(await call_next(request))
