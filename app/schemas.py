from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class GuessRequest(BaseModel):
    menu_ids: list[str] = Field(min_length=1, max_length=20)

    @model_validator(mode="after")
    def unique_menu_ids(self) -> "GuessRequest":
        if len(set(self.menu_ids)) != len(self.menu_ids):
            raise ValueError("menu_ids must not contain duplicates")
        return self
