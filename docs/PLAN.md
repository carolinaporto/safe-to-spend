# safe-to-spend — Technical Specification

Personal finance web app for an academic year abroad. Money sits in two currencies (BRL and USD) across multiple institutions. The app tracks every movement, normalizes reporting to USD, exposes the real cost of currency conversion, splits shared expenses, and computes how much can safely be spent per month and per day until a fixed end date.

---

## 1. Stack

| Layer | Choice |
|---|---|
| Frontend | React 18 + TypeScript + Vite |
| Styling | **styled-components** (no Tailwind, no CSS frameworks, no component libraries) |
| Icons | **@phosphor-icons/react** |
| Charts | Recharts |
| Data fetching | TanStack Query |
| Tables | TanStack Table |
| Forms | React Hook Form + Zod |
| Backend | FastAPI (Python 3.12) + Pydantic v2 |
| ORM | SQLAlchemy 2.0 + Alembic |
| Database | PostgreSQL (Neon) |
| Hosting | Vercel — static frontend + FastAPI as a Python Function |
| Scheduled jobs | Vercel Cron |

### Styling rules

- All styling through `styled-components`. No utility classes, no inline style objects, no third-party UI kits.
- A single `frontend/src/theme.ts` defines colors, spacing scale, radii, typography, and shadows. Every styled component reads from the theme — no hardcoded hex values or pixel values outside the theme.
- `ThemeProvider` wraps the app root. `createGlobalStyle` handles reset and base typography.
- Semantic color tokens required: `success`, `warning`, `danger` (traffic-light states), plus per-category colors resolved from the theme.
- Recharts components receive colors as props from the theme, not via CSS.

### Icon rules

- Icons come from `@phosphor-icons/react` only.
- One weight across the entire app, set once via `IconContext.Provider` at the root. Use `duotone`.
- No inline SVGs, no icon fonts, no other icon packages.

### Deployment structure

```
/
├── api/index.py          # Vercel entrypoint, exposes the FastAPI app
├── backend/              # routers, models, services, importers
├── frontend/             # React app (Vite)
├── docs/PLAN.md
├── requirements.txt
└── vercel.json           # /api/* → Python function; everything else → SPA
```

Serverless constraints that must be respected:
- Use the Neon **pooled** connection string and `poolclass=NullPool` in SQLAlchemy.
- No in-memory caches or global state that must survive between requests.
- Nothing written to `/tmp` that needs to persist.
- All secrets via environment variables.

---

## 2. Core invariants

These are not optional and apply everywhere in the codebase.

1. Money is `NUMERIC(14,2)`. FX rates are `NUMERIC(18,8)`. Python uses `Decimal`. **No `float` ever touches a monetary value**, including in JSON responses — serialize `Decimal` as string.
2. Rounding is `ROUND_HALF_UP` to 2 decimal places.
3. Every transaction stores original amount, original currency, FX rate applied, and USD equivalent. Conversion happens in the backend at write time and is persisted.
4. One row in `transactions` = one movement in one account. A transfer produces **two** rows linked by `transfer_group_id`.
5. Account balance is always computed as `opening_balance + Σ(in) − Σ(out)`. Never a stored mutable field.
6. All financial arithmetic lives in the backend. Dashboard endpoints return values already computed in USD. The frontend renders only.
7. Transfers never appear in category spending reports.
8. Reported spending for a shared expense = `amount_usd − Σ(shares belonging to other people)`. Enforced server-side.

---

## 3. Data model

### `accounts`
```
id, name, institution, kind (checking|savings|credit_card|cash|external),
currency (USD|BRL), opening_balance NUMERIC(14,2), opening_date,
statement_day INT NULL, due_day INT NULL,
color, icon, is_active, sort_order
```
Seed: Wise BRL, Wise USD, Chase Checking, Amex, Macy's, Cash, Dad's Card (`external`).

`external` accounts appear in category spending but are excluded from net worth and runway.

### `categories`
```
id, name, parent_id NULL,
nature (essential|discretionary|setup|fee|income),
icon, color, is_archived
```
Seed:
- **essential**: Rent, Groceries, Utilities, Transport, Health/Insurance, Phone/Internet, Academic materials, Laundry
- **discretionary**: Restaurants, Bars, Coffee, Clothing, Entertainment, Travel, Subscriptions, Gifts
- **setup**: Furniture, Kitchenware, Bedding, Deposit, Electronics
- **fee**: Transfer fee, FX spread, Bank fee, Foreign transaction fee
- **income**: Funding, Roommate reimbursement, Work, Scholarship, Refund

### `transactions`
```
id, date DATE, account_id FK,
direction (in|out),
kind (expense|income|transfer|adjustment),
amount NUMERIC(14,2),              -- positive, in the account currency
currency,
fx_rate_to_usd NUMERIC(18,8),      -- 1.0 when already USD
amount_usd NUMERIC(14,2),
category_id FK NULL,
merchant_raw TEXT NULL, merchant_clean TEXT NULL,
description, notes,
paid_by_person_id FK NULL,
is_shared BOOL, is_reimbursable BOOL, excluded_from_my_budget BOOL,
transfer_group_id UUID NULL, recurring_id FK NULL,
source (manual|csv|api), external_id TEXT NULL, import_batch_id FK NULL,
needs_review BOOL DEFAULT false,
tags TEXT[], receipt_url NULL,
created_at, updated_at
```
Indexes: `(date)`, `(account_id, date)`, `(category_id, date)`, `(transfer_group_id)`, partial unique on `(account_id, external_id)`.

### `transfers`
Metadata for a conversion; the two ledger legs live in `transactions`.
```
id, date, from_account_id, to_account_id,
amount_out NUMERIC, currency_out, amount_in NUMERIC, currency_in,
explicit_fee NUMERIC NULL, explicit_fee_currency NULL,
effective_rate NUMERIC(18,8), market_rate NUMERIC(18,8),
fx_cost_usd NUMERIC(14,2), provider, notes
```

### `fx_rates`
```
date, base, quote, rate NUMERIC(18,8), source
PRIMARY KEY (date, base, quote)
```

### `people`
```
id, name, role (me|roommate|parent|other), notes
```

### `expense_shares`
```
id, transaction_id FK, person_id FK,
share_amount_usd NUMERIC(14,2), settled BOOL, settled_transaction_id FK NULL
```

### `budgets`
```
id, month DATE (first of month), category_id FK NULL, amount_usd, rollover BOOL
```
`category_id NULL` means the global monthly ceiling.

### `recurring_rules`
```
id, name, account_id, category_id, amount, currency,
frequency (monthly|weekly|yearly), day_of_month,
start_date, end_date, auto_create BOOL, last_generated_date
```

### `merchant_rules`
```
id, pattern TEXT, match_type (contains|regex),
category_id, merchant_clean, priority INT, hit_count INT
```

### `plan_config`
Single row.
```
academic_year_start, academic_year_end,
emergency_reserve_usd, committed_costs JSONB
```

### `import_batches`
```
id, account_id, filename, row_count, imported_count, duplicate_count, created_at
```

---

## 4. Business logic

### 4.1 Currency conversion
- BRL amounts convert to USD using the `fx_rates` entry for the transaction date; fall back to the most recent prior rate.
- Rate source: Frankfurter (`https://api.frankfurter.dev`), ECB data, no API key. Fallback: `open.er-api.com`.
- Daily cron at 09:00 UTC stores USD↔BRL.
- If rate lookup fails, persist using the last known rate and set `needs_review = true`.

### 4.2 FX cost on transfers
Given R$5,000 out and $890 in:
```
effective_rate  = 890 / 5000
market_rate     = fx_rates[date]
theoretical_usd = 5000 * market_rate
fx_cost_usd     = theoretical_usd - 890
```
Do **not** create an expense row for this cost. The two ledger legs already leave both balances correct; an extra row would double-count. `fx_cost_usd` is stored on the `transfers` record and surfaced in a dedicated FX report, separate from consumption spending.

`explicit_fee` records a fee the provider displayed separately. It is already contained within `fx_cost_usd`.

### 4.3 Shared expenses
1. Log the full expense with `is_shared = true`.
2. Create `expense_shares` rows for each other person. My own share is implicit.
3. Reported spending uses `amount_usd − Σ(other people's shares)`.
4. The unsettled remainder is a receivable.
5. When settled, create a linked `income` transaction and set `settled = true` plus `settled_transaction_id`.

### 4.4 External account purchases
When `account.kind = 'external'`, the entry form asks for treatment:
- **Gift** → counts in category spending, `excluded_from_my_budget = true`, no effect on balances or runway.
- **I owe it back** → creates a liability against that person, shown in "I owe", deducted from available funds.

### 4.5 Runway and safe-to-spend
```
net_worth_usd     = Σ balances of owned accounts (BRL converted at today's rate)
                    + receivables from other people
                    − open credit card statements
                    − liabilities owed

available         = net_worth_usd − emergency_reserve − future_committed_costs
                    − future_recurring_costs

future_recurring_costs = Σ not-yet-generated occurrences of expense recurring
                    rules from today to academic_year_end, at each rule's
                    current amount (income rules ignored). Editing a rule's
                    amount re-prices the reservation.

months_remaining  = fractional months between today and academic_year_end
monthly_ceiling   = available / months_remaining

mtd_spend         = Σ expenses this month
                    (excluding setup category, recurring-rule transactions,
                    transfers, and other people's shares)
remaining_month   = monthly_ceiling − mtd_spend
daily_allowance   = remaining_month / days_remaining_in_month
```
Rules:
- `daily_allowance` is the primary number on the home screen.
- Traffic light: green if projected month-end spend is under the ceiling, warning up to 110%, danger above.
- `setup` category spending is excluded from the monthly pace calculation but still deducted from `available`.
- Recurring bills are reserved from `available` up front, so their generated transactions are excluded from the monthly pace and from the trailing burn rate (no double counting).
- Expected future income is never counted in `available` — recurring rules flagged `is_income` are ignored by `future_recurring_costs`.

### 4.6 Credit cards
Category spending uses accrual (purchase date). Balance projection and runway use cash (due date), with open statements already deducted from net worth. The cards panel shows current balance, closed statement, due date, and an alert within 5 days of the due date.

---

## 5. Data import

**CSV first.** Per-institution parsers in `backend/importers/` (`chase.py`, `amex.py`, `wise.py`, `generic.py`) mapping to a shared schema. The Wise export contains multiple currencies, so the parser must read currency per row.

- **Deduplication**: hash of `(account_id, date, amount, merchant_raw)` plus `external_id` when present. Duplicates are reported, not inserted.
- **Preview before commit**: show what will be imported, what is duplicate, what is uncategorized. Only write on confirmation.
- **Rule engine**: `merchant_rules` applies category and clean name by `contains` or regex, ordered by priority. After a manual categorization of a new `merchant_raw`, offer to create a rule.
- **Review inbox**: queue of `needs_review = true` with fast keyboard/touch editing.

Optional: a "paste receipt text" field that sends the text to the Anthropic API and returns `{merchant, category, amount, date}` as JSON to prefill the form. Requires `ANTHROPIC_API_KEY`; feature degrades gracefully when absent.

---

## 6. Screens

**Home / Dashboard** — Hero showing the daily allowance with traffic light and month progress bar. Cards for net worth, monthly ceiling, month-to-date spend, runway in days. Projection line chart of balance to `academic_year_end` with committed costs marked and the zero-crossing point if any. Category donut for the month. Stacked bars of spend per month by nature (essential / discretionary / setup). Account balances with BRL and USD side by side. Alerts for due statements, overdue receivables, exceeded categories, unreviewed transactions.

**Transactions** — Table with filters (date range, account, category, currency, nature, free text), inline editing, multi-select bulk recategorization, CSV export.

**Quick add** — Short mobile-first form: amount → currency → account → category → date (defaults to today) → save. Must be completable in under 10 seconds on a phone.

**Transfers** — Form for money out of account A into account B. Displays effective rate, market rate, and cost. History with cumulative FX cost chart and effective rate by provider.

**Budget** — Monthly ceiling per category with consumption bars. Copy from previous month. Optional rollover.

**People** — Balance per person (owed to me, owed by me). "Mark as settled" generates the linked transaction.

**Income** — Funding entries in BRL, total received, amount already converted, amount still in BRL, cumulative FX cost against the total.

**Settings** — Accounts, categories, merchant rules, recurring rules, academic year dates, emergency reserve, committed costs.

---

## 7. API

```
POST   /api/auth/login

GET    /api/accounts                      + POST, PATCH, DELETE
GET    /api/categories                    + POST, PATCH, DELETE

GET    /api/transactions                  ?from&to&account&category&kind&q&page
POST   /api/transactions
PATCH  /api/transactions/{id}
DELETE /api/transactions/{id}
POST   /api/transactions/bulk-categorize

POST   /api/transfers                     creates both legs, computes cost
GET    /api/transfers
GET    /api/transfers/summary

POST   /api/imports/preview               CSV upload, diff without writing
POST   /api/imports/commit
GET    /api/imports/review-queue

GET    /api/dashboard/overview            net worth, ceiling, MTD, daily allowance
GET    /api/dashboard/by-category         ?from&to&group=month
GET    /api/dashboard/cashflow
GET    /api/dashboard/projection
GET    /api/dashboard/balances

GET    /api/budgets/{month}               + PUT
GET    /api/people/balances
POST   /api/people/{id}/settle

GET    /api/fx/rate?date&base&quote
POST   /api/cron/fetch-fx                 guarded by CRON_SECRET header
```

Authentication: single-user password login returning a JWT. Password stored as a bcrypt hash in `APP_PASSWORD_HASH`. All routes except `/api/auth/login` and the cron endpoint require a valid token. CORS restricted to the deployed origin.

---

## 8. Execution phases

Each phase ends with a working deployment. Do not start a phase with the previous one broken.

**Phase 0 — Foundation**
Monorepo structure, Vercel config, Neon connection, SQLAlchemy + Alembic, health check, password login with JWT, theme and `ThemeProvider`, Phosphor `IconContext`, app shell with navigation.

**Phase 1 — Usable MVP**
Accounts, categories, manual transactions with multi-currency, daily FX fetch, account balances, transactions table with filters and inline editing, quick add screen.
*Done when: all spending can be recorded and balances are correct.*

**Phase 2 — Intelligence**
Monthly budgets, runway, daily allowance, full dashboard with all charts, projection to end of year.
*Done when: the home screen correctly answers how much can be spent today.*

**Phase 3 — Import**
CSV upload with Chase/Amex/Wise parsers, deduplication, preview, merchant rules, review inbox.

**Phase 4 — Real life**
Shared expenses and settlements, external account handling, credit card statements and due dates, recurring rules, income screen, cumulative FX cost report.

**Phase 5 — Optional**
Installable PWA with offline quick add, receipt parsing via Anthropic API, email alerts.

**Phase 6 — Bank connections**
Live transaction sync for Chase via Teller. (Wise personal API can no longer
serve statements under PSD2 — it stays on CSV import.)
Full design, data model and runbook in [`CONNECTIONS.md`](CONNECTIONS.md).

---

## 9. Testing

`pytest`, written alongside the logic. Required coverage:

- Currency conversion with `Decimal`, including rounding behavior.
- A transfer creates exactly two legs, balances reconcile, `fx_cost_usd` is correct.
- Shared expense reporting equals amount minus other people's shares.
- Account balance equals opening plus inflows minus outflows against seeded data.
- Re-importing the same CSV inserts nothing.
- Runway calculation with committed costs and reserve.
- Transfers and reimbursements are absent from category spending reports.

Also required: a seed script with realistic fake data, `DATE` columns without timezone for ledger entries, and a weekly export job producing a JSON/CSV backup.

---

## 10. Environment variables

```
DATABASE_URL          # Neon pooled connection string
APP_PASSWORD_HASH     # bcrypt hash of the single-user password
JWT_SECRET
CRON_SECRET
FX_API_URL
ANTHROPIC_API_KEY     # optional, receipt parsing
VITE_API_BASE_URL
```

Provide `.env.example` with all keys and empty values.
