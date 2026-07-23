from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class GuessRequest(BaseModel):
    menu_ids: list[str] = Field(min_length=1, max_length=20)

    @model_validator(mode="after")
    def unique_menu_ids(self) -> "GuessRequest":
        if len(set(self.menu_ids)) != len(self.menu_ids):
            raise ValueError("menu_ids must not contain duplicates")
        return self


class AdminMenuUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    category_name: str | None = Field(default=None, min_length=1, max_length=80)
    rank: int | None = Field(default=None, ge=1)
    display_order: int | None = Field(default=None, ge=0)
    is_active: bool | None = None
    answered: bool | None = None


class AdminMenuCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    category_name: str = Field(min_length=1, max_length=80)
    rank: int = Field(ge=1)
    display_order: int = Field(default=0, ge=0)
    answered: bool = False
