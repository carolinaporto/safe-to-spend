from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend import http_security
from backend.config import get_settings
from backend.logging_config import configure_logging
from backend.routers import (
    accounts,
    auth,
    backup,
    budgets,
    categories,
    dashboard,
    fx,
    health,
    imports,
    income,
    merchant_rules,
    meta,
    people,
    plan_config,
    recurring_rules,
    transactions,
    transfers,
)

configure_logging()
settings = get_settings()

app = FastAPI(
    title="safe-to-spend",
    version="0.1.0",
    # Don't publish interactive docs or the schema — it just maps the attack
    # surface for a single-user private app.
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

# Order matters: the hardening middleware is added last, so it runs first
# (outermost) and its headers land on every response, including CORS pre-flight.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
http_security.install(app)


app.include_router(health.router)
app.include_router(meta.router)
app.include_router(auth.router)
app.include_router(fx.router)
app.include_router(accounts.router)
app.include_router(categories.router)
app.include_router(transactions.router)
app.include_router(dashboard.router)
app.include_router(budgets.router)
app.include_router(plan_config.router)
app.include_router(merchant_rules.router)
app.include_router(imports.router)
app.include_router(transfers.router)
app.include_router(people.router)
app.include_router(recurring_rules.router)
app.include_router(income.router)
app.include_router(backup.router)
