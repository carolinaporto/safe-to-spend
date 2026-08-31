from pydantic import BaseModel, Field

from backend.models.enums import CategoryNature
from backend.schemas.common import ApiModel


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    parent_id: int | None = None
    nature: CategoryNature
    icon: str = Field(default="", max_length=40)
    color: str = Field(default="", max_length=16)


class CategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    parent_id: int | None = None
    nature: CategoryNature | None = None
    icon: str | None = Field(default=None, max_length=40)
    color: str | None = Field(default=None, max_length=16)
    is_archived: bool | None = None


class CategoryOut(ApiModel):
    id: int
    name: str
    parent_id: int | None
    nature: CategoryNature
    icon: str
    color: str
    is_archived: bool
