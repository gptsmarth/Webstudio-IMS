"""Purchase Import Queue repository (additive feature)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from webstudio_backend.infrastructure.database.enums import TallyPurchaseStatus
from webstudio_backend.infrastructure.database.models.tally_purchase_voucher import (
    TallyPurchaseVoucher,
)


class TallyPurchaseRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_voucher_by_guid(
        self, company_sync_id: int, guid: str
    ) -> TallyPurchaseVoucher | None:
        statement = (
            select(TallyPurchaseVoucher)
            .where(
                TallyPurchaseVoucher.tally_company_sync_id == company_sync_id,
                TallyPurchaseVoucher.tally_voucher_guid == guid,
            )
            .options(selectinload(TallyPurchaseVoucher.lines))
        )
        result = await self._session.execute(statement)
        return result.scalars().first()

    async def add_voucher(self, voucher: TallyPurchaseVoucher) -> TallyPurchaseVoucher:
        self._session.add(voucher)
        await self._session.flush()
        return voucher

    async def get_voucher(self, voucher_id: int) -> TallyPurchaseVoucher | None:
        statement = (
            select(TallyPurchaseVoucher)
            .where(TallyPurchaseVoucher.id == voucher_id)
            .options(selectinload(TallyPurchaseVoucher.lines))
        )
        result = await self._session.execute(statement)
        return result.scalars().first()

    async def list_vouchers(
        self,
        *,
        status: TallyPurchaseStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[TallyPurchaseVoucher], int]:
        base = select(TallyPurchaseVoucher)
        if status is not None:
            base = base.where(TallyPurchaseVoucher.status == status)

        count_stmt = select(func.count()).select_from(base.subquery())
        total = int((await self._session.execute(count_stmt)).scalar_one())

        statement = (
            base.options(selectinload(TallyPurchaseVoucher.lines))
            .order_by(
                TallyPurchaseVoucher.voucher_date.desc().nullslast(),
                TallyPurchaseVoucher.id.desc(),
            )
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(statement)
        return list(result.scalars().all()), total

    async def touch_last_seen(self, voucher: TallyPurchaseVoucher) -> None:
        voucher.last_seen_at = datetime.now(UTC)
        await self._session.flush()

    def recompute_status(self, voucher: TallyPurchaseVoucher) -> TallyPurchaseStatus:
        """Derive queue status from per-line import flags."""
        if not voucher.lines:
            voucher.status = TallyPurchaseStatus.PENDING
            return voucher.status
        imported = [line.imported for line in voucher.lines]
        if all(imported):
            voucher.status = TallyPurchaseStatus.IMPORTED
        elif any(imported):
            voucher.status = TallyPurchaseStatus.PARTIALLY_IMPORTED
        else:
            voucher.status = TallyPurchaseStatus.PENDING
        return voucher.status

    async def mark_group_imported(
        self,
        voucher: TallyPurchaseVoucher,
        *,
        group_key: str,
        product_model_id: uuid.UUID,
    ) -> None:
        now = datetime.now(UTC)
        for line in voucher.lines:
            if line.group_key == group_key:
                line.imported = True
                line.product_model_id = product_model_id
                line.imported_at = now
        self.recompute_status(voucher)
        await self._session.flush()
