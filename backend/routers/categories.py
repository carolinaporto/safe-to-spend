from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.deps import deny_in_demo, require_auth
from backend.models.category import Category
from backend.models.transaction import Transaction
from backend.schemas.category import CategoryCreate, CategoryOut, CategoryUpdate

router = APIRouter(
    prefix="/api/categories",
    tags=["categories"],
    dependencies=[Depends(require_auth)],
)


def _get_or_404(db: Session, category_id: int) -> Category:
    category = db.get(Category, category_id)
    if category is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "category not found")
    return category


def _would_cycle(db: Session, category_id: int, new_parent_id: int) -> bool:
    """True if making new_parent_id the parent of category_id creates a loop."""
    seen = {category_id}
    cursor: int | None = new_parent_id
    while cursor is not None:
        if cursor in seen:
            return True
        seen.add(cursor)
        parent = db.get(Category, cursor)
        cursor = parent.parent_id if parent else None
    return False


@router.get("", response_model=list[CategoryOut])
def list_categories(
    include_archived: bool = True, db: Session = Depends(get_db)
) -> list[Category]:
    stmt = select(Category).order_by(Category.nature, Category.name)
    if not include_archived:
        stmt = stmt.where(Category.is_archived.is_(False))
    return list(db.execute(stmt).scalars().all())


@router.post("", response_model=CategoryOut, status_code=status.HTTP_201_CREATED)
def create_category(
    body: CategoryCreate, db: Session = Depends(get_db)
) -> Category:
    if body.parent_id is not None:
        _get_or_404(db, body.parent_id)
    category = Category(**body.model_dump())
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@router.patch("/{category_id}", response_model=CategoryOut)
def update_category(
    category_id: int, body: CategoryUpdate, db: Session = Depends(get_db)
) -> Category:
    category = _get_or_404(db, category_id)
    data = body.model_dump(exclude_unset=True)
    new_parent = data.get("parent_id")
    if new_parent is not None and _would_cycle(db, category_id, new_parent):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "that parent would create a category loop",
        )
    for field, value in data.items():
        setattr(category, field, value)
    db.commit()
    db.refresh(category)
    return category


@router.delete(
    "/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(deny_in_demo)],
)
def delete_category(category_id: int, db: Session = Depends(get_db)) -> None:
    category = _get_or_404(db, category_id)
    referenced = db.execute(
        select(Transaction.id)
        .where(Transaction.category_id == category_id)
        .limit(1)
    ).first()
    if referenced is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "category is used by transactions; archive it instead",
        )
    has_children = db.execute(
        select(Category.id).where(Category.parent_id == category_id).limit(1)
    ).first()
    if has_children is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "category has sub-categories"
        )
    db.delete(category)
    db.commit()
