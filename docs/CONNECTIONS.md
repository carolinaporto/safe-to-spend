# Bank connections (live sync)

Pull transactions straight from the bank instead of exporting CSVs. This is a
fleshed-out version of the "Wise API sync / Plaid" line in `PLAN.md` Phase 5.

- **Wise** — direct, using a personal API token. One token covers **every
  currency balance** (BRL and USD live under the same personal profile).
- **Chase** — no public personal API. Goes through **Teller** (`teller.io`),
  which has an official OAuth connection to Chase and a free development tier.

Everything is **read-only**. Nothing here can move money.

---

## 1. How each provider works

### Wise

Base URL `https://api.transferwise.com` (sandbox: `https://api.sandbox.transferwise.tech`).
Auth: `Authorization: Bearer <WISE_API_TOKEN>`.

Sync steps:

1. `GET /v1/profiles` → find the entry with `"type": "personal"`, keep its `id`.
2. `GET /v4/profiles/{profileId}/balances?types=STANDARD` → one entry per
   currency you hold (`{ id, currency, amount }`). BRL and USD are just two
   rows here — **same profile, same token, same code path, loop over them.**
3. For each balance, fetch the statement:
   `GET /v1/profiles/{profileId}/balance-statements/{balanceId}/statement.json`
   `?currency={CUR}&intervalStart={ISO}&intervalEnd={ISO}&type=COMPACT`
   (max interval 12 months; we pull a rolling ~40-day window each run).

**SCA signing.** The statement endpoint is protected by Strong Customer
Authentication. First call returns `403` with a header `x-2fa-approval: <ott>`.
Sign that one-time token — `base64( RSA-SHA256(privateKey, ott) )` — and retry
with headers `x-2fa-approval: <ott>` and `X-Signature: <sig>`. The public half
of the key is registered once in the Wise UI. `/v1/profiles` and `/v4/.../balances`
do **not** need signing.

Each statement transaction carries a stable `referenceNumber` (e.g.
`CARD-1234567`, `TRANSFER-2332273711`) → our `Transaction.external_id`.
It also has `date`, `amount {value, currency}`, `totalFees`, `runningBalance`,
and `details {type, description, merchant {name, category}}`.

### Chase → Teller

Base URL `https://api.teller.io`. Every request uses **mutual TLS**: a client
certificate + private key issued from the Teller dashboard. Per-enrollment auth
is HTTP Basic with the enrollment's `access_token` as the username, empty
password.

- The connection itself is made in the browser by **Teller Connect**
  (`https://cdn.teller.io/connect/connect.js`): the user logs into Chase in a
  popup, the widget hands our frontend an `access_token` + `enrollment.id`,
  which we POST to the backend and store (encrypted).
- `GET /accounts` → accounts under that enrollment.
- `GET /accounts/{id}/transactions?count=N&from_id=<cursor>` → newest-first,
  each with a stable `id`, `date`, `description`, `amount` (string, signed),
  `status` (`posted` / `pending`), `details {category, counterparty}`.
- **Pending rows**: a pending transaction's `id` is not stable; only reconcile
  on `posted`. Keep pending rows out of the ledger or mark them clearly.
- **Re-auth**: when Chase forces a re-login, calls return `401` with
  `error.code` like `enrollment.disconnected`. The UI must re-run Teller
  Connect in reconnect mode for that `enrollment.id`.

CSP delta (frontend, `vercel.json` + `backend/http_security.py`): Connect needs
`script-src https://cdn.teller.io` and `frame-src https://teller.io`. Scope to
exactly that — confirm against Teller's docs at implementation time.

---

## 2. Architecture

Reuse everything the CSV importer already built: `Transaction.source`,
`Transaction.external_id`, the partial unique index
`(account_id, external_id) WHERE external_id IS NOT NULL`, `convert_to_usd`,
the merchant-rule / categorization pipeline, and the review queue.

**Refactor first.** Extract the "one parsed row → `Transaction` (FX applied,
merchant rules, `needs_review` when uncategorized, dedupe by content key /
external id)" logic out of `backend/services/imports.py` into a shared
`backend/services/ingest.py`. CSV commit and both bank adapters then call it.

### New tables / columns (one Alembic migration)

- `bank_connections`: `id`, `provider` (`wise` | `teller`), `status`
  (`active` | `needs_reauth` | `disabled`), `external_ref` (Wise `profileId` /
  Teller `enrollment.id`), `access_token_encrypted` (text, null for Wise —
  its token lives in env), `institution_name`, `created_at`, `last_synced_at`,
  `last_error`.
- `accounts`: `+ connection_id` (FK, nullable), `+ external_account_id` (text,
  nullable), unique `(connection_id, external_account_id)`. Manual accounts
  leave both null.
- `enums.TransactionSource`: add `wise`, `teller` (keep `api`, `manual`, `csv`).

### Adapters

`backend/services/connections/wise.py` and `.../teller.py`, each exposing
`fetch_transactions(connection, since) -> list[ExternalRow]` and, for Teller,
`list_accounts(...)`. `ExternalRow` is the same shape `ingest.py` consumes.

### Sync

- `POST /api/cron/sync-banks` (`require_cron_secret`) — iterate `active`
  connections, fetch since `last_synced_at` minus a small overlap, upsert by
  `external_id`, then set `last_synced_at`; on auth failure set
  `status = needs_reauth`; on anything else record `last_error`.
- `POST /api/connections/{id}/sync` (`require_auth`, `deny_in_demo`) — the
  "Sync now" button, one connection.
- `vercel.json` cron: `{ "path": "/api/cron/sync-banks", "schedule": "0 */6 * * *" }`.

### Frontend

New **Connections** card in Settings:

- Wise: shows configured / last sync / **Sync now**; lists its currency
  balances with the app Account each maps to.
- **Connect a bank (Chase)** → Teller Connect → POST enrollment to
  `/api/connections/teller` → account-mapping step (pick/create an Account per
  discovered external account).
- Per connection: status badge, last synced, **Sync now**, **Reconnect**
  (when `needs_reauth`), **Remove** (keeps already-imported transactions).

### Secrets

| Env var | Where | Notes |
|---|---|---|
| `WISE_API_TOKEN` | Vercel env only | personal token — powerful, never in DB, never logged |
| `WISE_PRIVATE_KEY` | Vercel env only | PEM contents; public half registered in Wise UI |
| `TELLER_APPLICATION_ID` | Vercel env | |
| `TELLER_ENVIRONMENT` | Vercel env | `development` to start |
| `TELLER_CERT` / `TELLER_KEY` | Vercel env | PEM; written to `/tmp` on cold start for the mTLS client |
| `APP_ENCRYPTION_KEY` | Vercel env only | Fernet key; encrypts Teller `access_token` at rest in Neon |

New dependency: `cryptography` (Fernet for token storage + RSA-SHA256 for Wise
signing). All outbound calls go through a pinned `httpx` client with short
timeouts and a response-size cap, matching `http_security.py`.

### Effect on the runway math

None. External rows run through the same `ingest` pipeline → same categories,
same `needs_review`, same review queue on the Import page. Balances stay
computed, recurring-generated rows stay out of the burn rate. Opening balances
remain manual (optionally seedable from the provider's running balance).

---

## 3. Phases

**6a — Plumbing + Wise.** Migration, `ingest.py` refactor, Wise adapter
(profiles / balances / statement + SCA signing), sync cron + endpoint, Fernet
util, Connections UI (Wise status + Sync now + balance→Account mapping). Tests:
signature generation, statement parsing from a saved fixture, idempotent
re-sync.

**6b — Chase via Teller.** mTLS `httpx` client, Teller adapter (accounts +
paginated transactions), Teller Connect widget, CSP delta, `/api/connections/teller`
create + reconnect, encrypted token storage, `needs_reauth` UI, pending/posted
handling. Tests: transaction parsing + sign convention per account type,
reconnect path.

**6c — Polish.** Match against pre-existing CSV rows when `external_id` is
absent (date + amount + fuzzy merchant), one-time deep backfill, per-connection
error surfacing, "remove keeps transactions" semantics.

---

## 4. One-time manual setup

### Wise

1. wise.com (web, personal account) → **Settings → API tokens** → create a
   token, copy it.
2. Generate a keypair locally:
   ```
   openssl genrsa -out wise_private.pem 2048
   openssl rsa -pubout -in wise_private.pem -out wise_public.pem
   ```
3. wise.com → **Settings → Manage public keys** → add `wise_public.pem`.
4. Put `WISE_API_TOKEN` and `WISE_PRIVATE_KEY` (contents of
   `wise_private.pem`) in Vercel env (Production + Preview).

BRL and USD need nothing extra — same token, both balances.

### Teller

1. teller.io → sign up → **Dashboard → create an Application**. Note the
   Application ID.
2. **Dashboard → Certificates** → generate → download `certificate.pem` and
   `private_key.pem`.
3. Set env: `TELLER_APPLICATION_ID`, `TELLER_ENVIRONMENT=development`,
   `TELLER_CERT` (cert PEM), `TELLER_KEY` (key PEM).
4. After deploy: app → **Settings → Connections → Connect Chase** → log into
   Chase in the Teller popup → select accounts.

### Shared

```
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```
→ `APP_ENCRYPTION_KEY` in Vercel env (Production + Preview).
