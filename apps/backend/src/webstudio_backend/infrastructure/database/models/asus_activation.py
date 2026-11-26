"""ASUS activation programme rules, expiring files and credit receipts."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    LargeBinary,
    Numeric,
    String,
    Text,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from webstudio_backend.infrastructure.database.base import Base
from webstudio_backend.infrastructure.database.constants import DATABASE_SCHEMA


class AsusActivationScheme(Base):
    __tablename__ = "asus_activation_schemes"

    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    date_from: Mapped[date] = mapped_column(Date(), index=True)
    date_to: Mapped[date] = mapped_column(Date())
    filename: Mapped[str] = mapped_column(String(255))
    digest: Mapped[str] = mapped_column(String(64))
    rules: Mapped[dict[str, dict]] = mapped_column(JSONB)
    created_by: Mapped[int] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revision: Mapped[int] = mapped_column(Integer, server_default="0")
    rate_overrides: Mapped[dict[str, list[dict]]] = mapped_column(JSONB, server_default="{}")
    history: Mapped[list[dict]] = mapped_column(JSONB, server_default="[]")


class AsusActivationWorkbook(Base):
    __tablename__ = "asus_activation_workbooks"

    scheme_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey(f"{DATABASE_SCHEMA}.asus_activation_schemes.id", ondelete="CASCADE"),
        primary_key=True,
    )
    content: Mapped[bytes] = mapped_column(LargeBinary)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class AsusActivationReceipt(Base):
    __tablename__ = "asus_activation_receipts"

    sale_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(f"{DATABASE_SCHEMA}.sales.id"),
        primary_key=True,
        autoincrement=False,
    )
    scheme_id: Mapped[UUID] = mapped_column(
        Uuid(), ForeignKey(f"{DATABASE_SCHEMA}.asus_activation_schemes.id")
    )
    expected_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    source: Mapped[str] = mapped_column(String(10))
    filename: Mapped[str | None] = mapped_column(String(255))
    digest: Mapped[str | None] = mapped_column(String(64))
    release_date: Mapped[date | None] = mapped_column(Date())
    receipt_scheme: Mapped[str | None] = mapped_column(String(500))
    application_no: Mapped[str | None] = mapped_column(String(128))
    record_note: Mapped[str] = mapped_column(Text())
    recorded_by: Mapped[int] = mapped_column(BigInteger)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    resolution_note: Mapped[str | None] = mapped_column(Text())
    resolved_by: Mapped[int | None] = mapped_column(BigInteger)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_expected_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    scheme_snapshot: Mapped[dict | None] = mapped_column(JSONB)


class AsusActivationCNOverride(Base):
    __tablename__ = "asus_activation_cn_overrides"

    sale_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey(f"{DATABASE_SCHEMA}.sales.id"), primary_key=True, autoincrement=False
    )
    amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    note: Mapped[str] = mapped_column(Text())
    updated_by: Mapped[int] = mapped_column(BigInteger)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
