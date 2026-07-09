"""SQLAlchemy declarative base and model registry.

Every model module must be imported here so Alembic autogenerate and the
metadata registry see the full schema.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


def import_all_models() -> None:
    """Import every model module for metadata registration (used by Alembic)."""
    from app.db import models  # noqa: F401
