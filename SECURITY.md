# Security

A single-user personal-finance app. The whole threat model is: **nobody but
the owner should ever see the numbers.**

## What protects the data

| Layer | Where |
|---|---|
| Single-user auth — bcrypt password hash, no password stored | `backend/security.py`, `backend/routers/auth.py` |
| Every `/api/*` data route requires a valid JWT; cron routes require `CRON_SECRET` | router `dependencies=[...]` |
| JWT: HS256, 48 h lifetime, `iss` / `aud` / `ver` all verified; bump `TOKEN_VERSION` to revoke every token | `backend/security.py` |
| Login brute-force throttle — per-IP lockout + a global circuit breaker, DB-backed | `backend/services/login_throttle.py` |
| Strict security headers + locked-down CSP on the API | `backend/http_security.py` |
| `Cache-Control: no-store` on every API response — financial payloads never hit a shared or on-disk cache | `backend/http_security.py` |
| Request-body size cap (1 MiB; 12 MiB for imports) | `backend/http_security.py` |
| Coarse in-memory per-IP rate limit on the API | `backend/http_security.py` |
| CSP + security headers on the static frontend | `vercel.json` → `headers` |
| No interactive API docs / OpenAPI schema published | `backend/main.py` |
| CORS restricted to the configured origin + localhost, nothing else | `backend/config.py` |
| Secrets never logged (redaction filter); request bodies and amounts never logged | `backend/logging_config.py` |
| No raw SQL / string-built queries; no `dangerouslySetInnerHTML` / `eval` in the frontend | — |
| `pip-audit` + `npm audit` run in CI | `.github/workflows/ci.yml` |

## Deployment checklist

Set these on the Vercel project (Environment Variables):

- [ ] `APP_PASSWORD_HASH` — hash of a **long, unique** passphrase. Not reused anywhere.
- [ ] `JWT_SECRET` — ≥ 32 chars, from `secrets.token_urlsafe(32)`. **Different** from the dev value.
- [ ] `CRON_SECRET` — same generator, its own value.
- [ ] `TRUST_PROXY_HEADERS=true` (Vercel is the trusted proxy).
- [ ] `RATE_LIMIT_ENABLED=true`.
- [ ] `CORS_ORIGINS` — exactly the deployed frontend URL.
- [ ] `VITE_API_BASE_URL` — **empty** (same-origin `/api`).
- [ ] `DEMO_MODE` unset / `false`.
- [ ] Neon: restrict database access, rotate the connection string if it was ever pasted somewhere shared.
- [ ] Enable Vercel's platform attack protection / firewall if available on the plan — it's the outer DDoS layer the in-app rate limiter can't be.

## If something leaks

- **JWT possibly stolen** (shared device, XSS): change `TOKEN_VERSION` → redeploy. Every existing token is now rejected; you log in again.
- **`JWT_SECRET` leaked**: rotate it → redeploy (also invalidates all tokens).
- **Password leaked**: regenerate `APP_PASSWORD_HASH` with a new passphrase → redeploy.
- **`DATABASE_URL` leaked**: rotate it in Neon immediately.

## Local data safety

`pytest` truncates every table. It is hard-wired to a database whose name ends
in `_test` (`conftest.py` rewrites `DATABASE_URL` and a fixture refuses
otherwise), so it can never touch your real `safe_to_spend`.

`backend.reset` and `backend.seed` **do** hit whatever `DATABASE_URL` points at.
They now refuse to run without `ALLOW_DESTRUCTIVE=1` **and** typing the target
database name. Take a dump first anyway: `scripts/db_backup.sh`.

## Known accepted risk

- The JWT lives in `localStorage`, so a successful XSS could read it. Mitigated
  by the strict CSP (no third-party or inline scripts) and the short token
  lifetime. Moving to an httpOnly cookie + CSRF tokens is a possible future step.
