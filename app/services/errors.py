"""Compatibility facade for domain errors."""

from app.domain.errors import MenuNotFoundError, RankConflictError

__all__ = ["MenuNotFoundError", "RankConflictError"]
