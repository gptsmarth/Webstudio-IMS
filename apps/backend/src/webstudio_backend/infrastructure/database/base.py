"""SQLAlchemy declarative base and metadata configuration."""

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

from webstudio_backend.infrastructure.database.constants import DATABASE_SCHEMA

NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = MetaData(
    naming_convention=NAMING_CONVENTION,
    schema=DATABASE_SCHEMA,
)


class Base(DeclarativeBase):
    """Declarative base for all ORM models in the `webstudio` schema."""

    metadata = metadata
