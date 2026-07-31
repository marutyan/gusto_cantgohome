from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GameSummaryRecord:
    answered_count: int
    total_count: int
    hit_ranks: tuple[int, ...]
    updated_at: str | None


@dataclass(frozen=True, slots=True)
class PublicMenuRecord:
    category_id: int
    category_name: str
    menu_id: str
    name: str
    rank: int
    guessed_at: str | None


@dataclass(frozen=True, slots=True)
class GuessMenuRecord:
    menu_id: str
    name: str
    rank: int


@dataclass(frozen=True, slots=True)
class AdminCategoryRecord:
    category_id: int
    name: str
    display_order: int


@dataclass(frozen=True, slots=True)
class AdminMenuRecord:
    menu_id: str
    name: str
    rank: int
    display_order: int
    is_active: bool
    category_name: str
    guessed_at: str | None


@dataclass(frozen=True, slots=True)
class MenuRankRecord:
    menu_id: str
    rank: int
