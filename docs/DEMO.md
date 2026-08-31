# Portfolio demo deployment

A public, read-mostly instance of the app for the portfolio. Same codebase,
separate infrastructure, disposable data.

## Setup (do this later, once the seed script exists)

1. **New Vercel project** from the same repo (or a `demo` branch).
2. **New Neon database** — a throwaway project/branch, not the personal one.
3. **Environment variables** on the demo project:
   ```
   DATABASE_URL        = <demo Neon pooled URL>
   APP_PASSWORD_HASH   = <bcrypt hash of the published demo password>
   JWT_SECRET          = <fresh random value, unrelated to the real instance>
   CRON_SECRET         = <fresh random value>
   DEMO_MODE           = true
   CORS_ORIGINS        = https://<demo-domain>
   FX_API_URL          = https://api.frankfurter.dev
   ```
   Leave `ANTHROPIC_API_KEY` unset — receipt parsing degrades gracefully.
4. **Seed**: run `python -m backend.seed` against the demo database (CI step or
   one-off). Re-seeding should be idempotent or wipe-and-fill.
5. **README**: publish the demo URL and password.

## What `DEMO_MODE=true` does

- `deny_in_demo` dependency → destructive / mutating endpoints return `403`
  (deletes, bulk recategorize, import commit, people settle, cron-less writes).
  Attach `dependencies=[Depends(deny_in_demo)]` as those routes are built.
- `GET /api/meta` returns `demo_mode: true`, `import_enabled: false`.
- Frontend hides the import screen and shows a "Demo" badge; destructive
  buttons are disabled where present.
- Quick-add and normal reads still work, so visitors can click around.

## Seed data bar (Phase 1)

The seed must look like a real semester abroad, not placeholder rows:
- 7 accounts from the spec (Wise BRL/USD, Chase, Amex, Macy's, Cash, Dad's Card).
- ~3–4 months of transactions with realistic merchants (Trader Joe's, MBTA,
  Comcast, CVS, local restaurants/coffee, Amazon, IKEA…).
- A funded-in-BRL → converted-to-USD story with 2 transfers that carry a real
  `fx_cost_usd`.
- Rent as a shared expense split with two roommates, some settled, some not.
- A couple of setup-category purchases (furniture, kitchenware).
- FX rates covering the date range.

See the seeding requirement in `docs/PLAN.md` §9.
