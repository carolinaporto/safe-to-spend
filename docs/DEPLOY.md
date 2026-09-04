# Deploy (Vercel + Neon)

The app runs as a Vercel project: the static frontend plus one FastAPI Python
Function (`api/index.py`). The database is a Neon Postgres, **separate** from
the local `safe_to_spend`.

Do these in order.

## 1. Neon database

1. Create a Neon project (region close to you). One database, e.g. `safe_to_spend`.
2. Copy the **pooled** connection string (the host contains `-pooler`). It looks like:
   `postgresql://user:pass@ep-xxx-pooler.region.aws.neon.tech/safe_to_spend?sslmode=require`
3. Run the migrations against it from your machine — needs a throwaway JWT secret
   just so config validation passes:

   ```
   DATABASE_URL='<neon pooled url>' \
   JWT_SECRET='0000000000000000000000000000000000' \
   .venv/bin/alembic upgrade head
   ```

## 2. Your data — keep it or start fresh?

Your real accounts/transactions are only in the **local** Postgres.

**Start fresh:** skip this step. After the first deploy, add your accounts +
plan in Settings, then import statements.

**Bring it over** — schema from the migrations (step 1), then data only, so
nothing depends on Neon accepting a raw `pg_dump` of the whole DB:

```
# after step 1's `alembic upgrade head` has run against Neon:
docker exec -i safe-to-spend-db \
  pg_dump -U sts -d safe_to_spend --data-only --no-owner \
          --exclude-table=alembic_version \
| docker exec -i safe-to-spend-db psql '<neon pooled url>'
```

Then check it landed:

```
docker exec -i safe-to-spend-db psql '<neon pooled url>' \
  -c "select count(*) from transactions; select count(*) from accounts;"
```

## 3. Secrets

Generate three independent values:

```
python -c "import secrets; print(secrets.token_urlsafe(32))"   # x3
```

- `JWT_SECRET` — one of them. **Not** the value in your local `.env`.
- `CRON_SECRET` — another.
- `APP_PASSWORD_HASH` — `python -m backend.scripts.hash_password "a long unique passphrase"`

## 4. Vercel project

1. Import the GitHub repo `carolinaporto/safe-to-spend` into Vercel. It picks up
   `vercel.json` automatically (build command, Python function, rewrites, crons).
2. **Environment Variables** (Production):

   | Key | Value |
   |---|---|
   | `DATABASE_URL` | the Neon **pooled** URL |
   | `APP_PASSWORD_HASH` | the bcrypt hash from step 3 |
   | `JWT_SECRET` | step 3, ≥ 32 chars |
   | `CRON_SECRET` | step 3 |
   | `TRUST_PROXY_HEADERS` | `true` |
   | `RATE_LIMIT_ENABLED` | `true` |
   | `CORS_ORIGINS` | your deployed URL, e.g. `https://safe-to-spend.vercel.app` |

   **Do not set** `VITE_API_BASE_URL` (must stay empty so the app talks to its
   own origin), `DEMO_MODE`, or `TOKEN_VERSION`.

3. Deploy. If the URL isn't final yet, deploy once, note the real URL, set
   `CORS_ORIGINS` to it, redeploy.

## 5. After the first deploy

- Open the URL, log in with the passphrase from step 3.
- If you started fresh: Settings → add accounts, set the Plan, import statements.
- **Crons** (fetch-fx daily, generate-recurring daily, backup weekly) run
  automatically — confirm they appear under the project's *Cron Jobs* tab.
- Turn on Vercel's attack/firewall protection if your plan has it — it's the
  outer DDoS layer.

## Redeploys

Push to `main` → Vercel builds and deploys. CI (GitHub Actions) runs tests +
`pip-audit` + `npm audit` on every push.

Schema changes: after merging a migration, run `alembic upgrade head` against
the Neon URL (same command as step 1) — Vercel does not migrate on deploy.

## If a secret leaks

See `SECURITY.md` → "If something leaks". Fastest kill switch for a stolen
token: set `TOKEN_VERSION=2` in Vercel env and redeploy.
