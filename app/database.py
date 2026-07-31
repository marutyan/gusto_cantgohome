"""Compatibility facade for the persistence safety boundary."""

from app.persistence.connections import connect, read_connection, transaction
from app.persistence.integrity import check_database
from app.persistence.migrations import MIGRATION_DIR, migrate

__all__ = [
    "MIGRATION_DIR",
    "check_database",
    "connect",
    "migrate",
    "read_connection",
    "transaction",
]
