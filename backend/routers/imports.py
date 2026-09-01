import json

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.deps import deny_in_demo, require_auth
from backend.importers import PARSER_NAMES, ParseError
from backend.models.account import Account
from backend.models.transaction import Transaction
from backend.schemas.imports import (
    CommitOut,
    PreviewOut,
    PreviewRowOut,
    ReviewQueueItem,
    ReviewQueueOut,
)
from backend.services.imports import build_preview, commit_import

router = APIRouter(
    prefix="/api/imports", tags=["imports"], dependencies=[Depends(require_auth)]
)

_MAX_BYTES = 5 * 1024 * 1024


def _account_or_422(db: Session, account_id: int) -> Account:
    account = db.get(Account, account_id)
    if account is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "unknown account_id"
        )
    return account


def _validate_parser(parser: str | None) -> str | None:
    if parser and parser not in PARSER_NAMES:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"parser must be one of {PARSER_NAMES}",
        )
    return parser or None


async def _read(file: UploadFile) -> bytes:
    content = await file.read()
    if len(content) > _MAX_BYTES:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "file too large (5 MB max)"
        )
    return content


@router.post("/preview", response_model=PreviewOut)
async def preview(
    account_id: int = Form(...),
    parser: str | None = Form(default=None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> PreviewOut:
    account = _account_or_422(db, account_id)
    content = await _read(file)
    try:
        result = build_preview(
            db, account, file.filename or "upload.csv", content,
            _validate_parser(parser),
        )
    except ParseError as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, f"could not parse: {exc}"
        ) from exc
    return PreviewOut(
        parser=result.parser,
        account_id=result.account_id,
        filename=result.filename,
        rows=[PreviewRowOut.model_validate(r) for r in result.rows],
        summary=result.summary,
    )


@router.post(
    "/commit", response_model=CommitOut, dependencies=[Depends(deny_in_demo)]
)
async def commit(
    account_id: int = Form(...),
    parser: str | None = Form(default=None),
    overrides: str = Form(default="{}"),
    skip: str = Form(default="[]"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> CommitOut:
    account = _account_or_422(db, account_id)
    content = await _read(file)
    try:
        override_map = {str(k): v for k, v in json.loads(overrides).items()}
        skip_set = {str(k) for k in json.loads(skip)}
    except (json.JSONDecodeError, AttributeError) as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "overrides/skip must be JSON",
        ) from exc

    try:
        batch = commit_import(
            db, account, file.filename or "upload.csv", content,
            _validate_parser(parser),
            overrides=override_map,
            skip=skip_set,
        )
    except ParseError as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, f"could not parse: {exc}"
        ) from exc

    return CommitOut(
        batch_id=batch.id,
        parser=batch.parser,
        filename=batch.filename,
        row_count=batch.row_count,
        imported_count=batch.imported_count,
        duplicate_count=batch.duplicate_count,
    )


@router.get("/review-queue", response_model=ReviewQueueOut)
def review_queue(
    limit: int = 200, db: Session = Depends(get_db)
) -> ReviewQueueOut:
    stmt = (
        select(Transaction)
        .where(Transaction.needs_review.is_(True))
        .order_by(Transaction.date.desc(), Transaction.id.desc())
    )
    total = db.scalar(
        select(func.count()).select_from(stmt.subquery())
    ) or 0
    rows = db.execute(stmt.limit(limit)).scalars().all()
    return ReviewQueueOut(
        items=[
            ReviewQueueItem(
                id=t.id,
                date=t.date,
                account_id=t.account_id,
                amount=t.amount,
                currency=t.currency,
                amount_usd=t.amount_usd,
                merchant_raw=t.merchant_raw,
                merchant_clean=t.merchant_clean,
                description=t.description,
                category_id=t.category_id,
                direction=t.direction.value,
                kind=t.kind.value,
                source=t.source.value,
            )
            for t in rows
        ],
        total=total,
    )
