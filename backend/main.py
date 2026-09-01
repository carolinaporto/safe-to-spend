from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

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

app = FastAPI(title="safe-to-spend", version="0.1.0")

# CORS is limited to the deployed origin plus localhost (see config.py).
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

_SECURITY_HEADERS = {
    "Strict-Transport-Security": "max-age=63072000; includeSubDomains; preload",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
}


@app.middleware("http")
async def security_headers(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    response = await call_next(request)
    for key, value in _SECURITY_HEADERS.items():
        response.headers.setdefault(key, value)
    return response


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
