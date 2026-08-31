import datetime as dt

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.deps import require_auth, require_cron_secret
from backend.database import get_db
from backend.schemas.common import ApiModel, RateStr
from backend.services import fx_provider
from backend.services.fx import get_rate, upsert_rate

router = APIRouter(prefix="/api", tags=["fx"])


class RateOut(ApiModel):
    date: dt.date
    base: str
    quote: str
    rate: RateStr


@router.get("/fx/rate", response_model=RateOut, dependencies=[Depends(require_auth)])
def read_rate(
    date: dt.date = Query(default_factory=dt.date.today),
    base: str = Query(min_length=3, max_length=3),
    quote: str = Query(default="USD", min_length=3, max_length=3),
    db: Session = Depends(get_db),
) -> RateOut:
    value = get_rate(db, date, base.upper(), quote.upper())
    if value is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"no {base.upper()}->{quote.upper()} rate on or before {date}",
        )
    return RateOut(date=date, base=base.upper(), quote=quote.upper(), rate=value)


@router.post(
    "/cron/fetch-fx",
    dependencies=[Depends(require_cron_secret)],
    status_code=status.HTTP_200_OK,
)
def fetch_fx(db: Session = Depends(get_db)) -> dict:
    """Daily job (09:00 UTC): store today's USD<->BRL rates."""
    today = dt.date.today()
    try:
        pairs = fx_provider.fetch_usd_brl(today)
    except Exception as exc:  # noqa: BLE001 - provider failure is reported, not raised
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"fx provider unavailable: {exc}",
        )

    for (base, quote), value in pairs.items():
        upsert_rate(db, today, base, quote, value, source="frankfurter")
    db.commit()

    return {
        "date": today.isoformat(),
        "stored": [
            {"base": b, "quote": q, "rate": format(v, "f")}
            for (b, q), v in pairs.items()
        ],
    }
