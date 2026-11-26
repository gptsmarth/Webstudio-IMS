"""Persistent cache of verified external laptop research."""

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from webstudio_backend.infrastructure.database.base import Base


class LaptopComparisonCache(Base):
    __tablename__ = "laptop_comparison_cache"
    __table_args__ = (Index("ix_laptop_comparison_cache_expiry", "expires_at"),)

    normalized_brand: Mapped[str] = mapped_column(String(80), primary_key=True)
    normalized_model: Mapped[str] = mapped_column(String(160), primary_key=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
