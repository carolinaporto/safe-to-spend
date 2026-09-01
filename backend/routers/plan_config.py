from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.deps import require_auth
from backend.schemas.plan_config import PlanConfigOut, PlanConfigUpdate
from backend.services.runway import get_plan_config

router = APIRouter(
    prefix="/api/plan-config",
    tags=["plan-config"],
    dependencies=[Depends(require_auth)],
)


@router.get("", response_model=PlanConfigOut)
def read_plan_config(db: Session = Depends(get_db)) -> PlanConfigOut:
    config = get_plan_config(db)
    db.commit()
    return PlanConfigOut.model_validate(config)


@router.put("", response_model=PlanConfigOut)
def update_plan_config(
    body: PlanConfigUpdate, db: Session = Depends(get_db)
) -> PlanConfigOut:
    config = get_plan_config(db)
    data = body.model_dump(exclude_unset=True)

    if "academic_year_start" in data:
        config.academic_year_start = data["academic_year_start"]
    if "academic_year_end" in data:
        config.academic_year_end = data["academic_year_end"]
    if "emergency_reserve_usd" in data:
        config.emergency_reserve_usd = data["emergency_reserve_usd"]
    if body.committed_costs is not None:
        # Store as plain JSON-serialisable dicts (strings for money/dates).
        config.committed_costs = [
            cost.model_dump(mode="json") for cost in body.committed_costs
        ]

    db.commit()
    db.refresh(config)
    return PlanConfigOut.model_validate(config)
