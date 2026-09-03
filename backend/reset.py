"""Empty the ledger. No fake data — run this once to start entering your own.

    ALLOW_DESTRUCTIVE=1 python -m backend.reset

Wipes: accounts, categories, people, transactions, fx_rates, budgets,
plan_config. Leaves auth state (login attempts) alone.

Do NOT run `python -m backend.seed` afterwards — it would refill the
database with fake data and erase what you entered.
"""

import os

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from backend.database import SessionLocal, engine
from backend.models import LEDGER_MODELS
from backend.services.runway import default_plan_config


def guard_destructive(action: str) -> None:
    """Refuse to run a data-destroying CLI unless it is unambiguously intended.

    Two locks: ``ALLOW_DESTRUCTIVE=1`` in the environment, and typing the exact
    target database name at the prompt. Used by ``backend.reset`` and the
    ``backend.seed`` entrypoint — never in the request path.
    """
    db_name = engine.url.database or "?"
    if os.environ.get("ALLOW_DESTRUCTIVE") != "1":
        raise SystemExit(
            f"{action} refused. This DESTROYS all data in '{db_name}'.\n"
            "Re-run with ALLOW_DESTRUCTIVE=1 if you are sure."
        )
    typed = input(
        f"About to {action} — every row in database '{db_name}' is deleted.\n"
        f"Type the database name to confirm: "
    )
    if typed.strip() != db_name:
        raise SystemExit("Name did not match. Aborted.")


def wipe_ledger(db: Session) -> None:
    for model in LEDGER_MODELS:
        db.execute(delete(model))
    db.flush()


def reset() -> dict[str, int]:
    db = SessionLocal()
    try:
        removed = {
            model.__tablename__: db.scalar(
                select(func.count()).select_from(model)
            )
            for model in LEDGER_MODELS
        }
        wipe_ledger(db)
        # Keep the plan_config singleton so the dashboard has a window to work
        # with; the user edits it in Settings.
        db.add(default_plan_config())
        db.commit()
        return removed
    finally:
        db.close()


def main() -> None:
    guard_destructive("wipe the ledger")
    for table, count in reset().items():
        print(f"{table:>13}: removed {count}")
    print("\nDone. Add your accounts and plan in Settings, then import statements.")


if __name__ == "__main__":
    main()
