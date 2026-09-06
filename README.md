# safe-to-spend

[![CI](https://github.com/carolinaporto/safe-to-spend/actions/workflows/ci.yml/badge.svg)](https://github.com/carolinaporto/safe-to-spend/actions/workflows/ci.yml)

**Personal finance for an academic year abroad.**

A web app I built to manage my money during my academic year at Harvard. As an international student, my finances sit across two currencies and several institutions — funds in BRL that get converted to USD, accounts at Wise and Chase, three credit cards, rent split with two roommates — and no off-the-shelf budgeting app handles that well. This one does.

The home screen answers a single question: **how much can I spend today, given what has to last until May?**

<!-- ![Dashboard](docs/screenshot-dashboard.png) -->

---

## Features

- **Multi-currency ledger.** Every transaction stores its original amount, currency, FX rate, and USD equivalent. Reporting is in USD; history stays true. Rates pulled daily from the ECB.
- **FX cost tracking.** Each conversion is compared against the market rate that day, exposing the real cost of a transfer — spread included, not just the advertised fee.
- **Runway and daily allowance.** Knows the end date of the year, upcoming committed costs, and the reserve. Derives a monthly ceiling and a daily safe-to-spend figure. One-off setup costs are excluded from the burn-rate average.
- **Shared expenses.** Rent is paid in full but only my share counts as spending; the rest are receivables until roommates settle.
- **Statement import.** Chase, Amex, and Wise CSVs are parsed, deduplicated, and auto-categorized by a rule engine that learns from manual corrections. Optional receipt parsing via the Anthropic API for cryptic merchant names.
- **Accrual and cash views.** Card purchases count as spending on the purchase date; balance projections account for open statements and due dates.

---

## Stack

| Layer | Choice |
|---|---|
| Frontend | React 18, TypeScript, Vite |
| Styling | styled-components |
| Icons | [Phosphor Icons](https://phosphoricons.com/) |
| Charts | Recharts |
| Data | TanStack Query, TanStack Table |
| Forms | React Hook Form + Zod |
| Backend | FastAPI (Python 3.12), Pydantic v2 |
| ORM | SQLAlchemy 2.0, Alembic |
| Database | PostgreSQL (Neon) |
| Hosting | Vercel — static frontend + FastAPI Python Function |

---

## Design notes

**Postgres over a document store.** Money needs exact decimals, and every report here is a `GROUP BY` with joins. Transfers span two rows and must commit atomically.

**No floats touch money.** `NUMERIC(14,2)` for amounts, `NUMERIC(18,8)` for rates, `Decimal` in Python, serialized as strings so JavaScript never rounds a balance.

**FX cost is derived, never posted.** A conversion writes two ledger legs, which alone leave both balances correct — posting an extra fee row would double-count the loss. The cost lives on the transfer record and feeds its own report.

**One row equals one movement in one account.** Balances are computed as `opening_balance + Σ(in) − Σ(out)`, never stored in a field that can drift.

**All financial arithmetic lives in the backend.** Dashboard endpoints return values already computed in USD. The frontend draws; it does not calculate.

Full schema and business rules: [`docs/PLAN.md`](docs/PLAN.md).

---

## Running locally

```bash
git clone https://github.com/<user>/safe-to-spend.git
cd safe-to-spend

# Database — Neon in production; Postgres via Docker for local dev
docker compose up -d db

# Backend (Python 3.12 — see .python-version)
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"                # runtime deps + pytest/ruff/pip-audit
cp .env.example .env          # DATABASE_URL is pre-filled for the Docker DB
python -m backend.scripts.hash_password "your-password"   # paste into APP_PASSWORD_HASH
alembic upgrade head
python -m backend.seed                # realistic fake data (dev / demo)
uvicorn backend.main:app --reload

# Frontend
cd frontend && cp .env.example .env && npm install && npm run dev
```

Backend on `:8000`, frontend on `:5173`. Environment variables are documented in `.env.example`.

To use the app for real, start from an empty ledger instead of the seed:

```bash
python -m backend.reset              # wipes accounts/transactions/budgets/…
```

Then add your accounts and academic-year plan in **Settings**. Don't run
`backend.seed` again afterwards — it would erase your data and refill fakes.

---

## Testing

```bash
createdb -h localhost -U sts safe_to_spend_test   # once; or via psql
pytest              # needs the Docker DB running
ruff check backend tests alembic
alembic check       # migrations match the models
```

The test fixtures `TRUNCATE` every table between tests, so they run against a
**separate** database whose name ends in `_test` (`safe_to_spend_test` by
default; `conftest.py` derives it from `DATABASE_URL` and refuses to run
against anything else). Your real data in `safe_to_spend` is never touched by
`pytest`. Take a dump before anything risky: `scripts/db_backup.sh`.

Covers the parts where a bug means a wrong number on screen: currency conversion and rounding, transfer legs balancing, FX cost computation, shared-expense math, balance reconstruction, runway and budget math, import deduplication, and the exclusion of transfers and reimbursements from category spending. CI runs all of the above plus the frontend build on every push.

---

## Deploy

Vercel (static frontend + FastAPI Python Function) with a Neon Postgres. Full
runbook in [`docs/DEPLOY.md`](docs/DEPLOY.md); the security model and the
env-var checklist are in [`SECURITY.md`](SECURITY.md).

---

## Roadmap

- [x] Multi-currency ledger, accounts, categories, daily FX rates
- [x] Budgets, runway, projection chart
- [x] CSV import with deduplication and merchant rules
- [x] Shared expenses and credit card statements
- [ ] Installable PWA with offline quick-add

---

## Notes on development

The architecture, data model, and financial rules in this project are mine —
including the decisions documented above and in `docs/PLAN.md`. Implementation
was done with Claude Code, working from that specification.

--- 

## License

MIT
