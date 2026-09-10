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
        else:
            # Default ("All") queue means "still open" — ignored vouchers are
            # tombstoned and fully-imported ones are done, so both are hidden
            # here and only reachable via their own status filter.
            base = base.where(
                TallyPurchaseVoucher.status.not_in(
                    (TallyPurchaseStatus.IGNORED, TallyPurchaseStatus.IMPORTED)
                )
            )

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

    async def ignore_voucher(self, voucher: TallyPurchaseVoucher) -> None:
        """Tombstone a voucher so it disappears from the queue and is never
        re-fetched (the sync upsert only touches ``last_seen`` for known GUIDs)."""
        voucher.status = TallyPurchaseStatus.IGNORED
        voucher.last_seen_at = datetime.now(UTC)
        await self._session.flush()

    async def close_voucher(self, voucher: TallyPurchaseVoucher) -> None:
        """Manually mark a voucher Imported, permanently, regardless of which
        line groups were actually brought into inventory. Terminal — see the
        early-return for IMPORTED in ``recompute_status``."""
        voucher.status = TallyPurchaseStatus.IMPORTED
        voucher.last_seen_at = datetime.now(UTC)
        await self._session.flush()

    async def count_existing_guids(self, company_sync_id: int, guids: list[str]) -> int:
        """How many of the given voucher GUIDs already exist for this company."""
        if not guids:
            return 0
        statement = select(func.count()).where(
            TallyPurchaseVoucher.tally_company_sync_id == company_sync_id,
            TallyPurchaseVoucher.tally_voucher_guid.in_(set(guids)),
        )
        return int((await self._session.execute(statement)).scalar_one())

    def recompute_status(self, voucher: TallyPurchaseVoucher) -> TallyPurchaseStatus:
        """Derive queue status from per-line import flags."""
        # Ignored and manually-closed-Imported are terminal, user-set states —
        # never auto-override them from line-level import flags.
        if voucher.status in (TallyPurchaseStatus.IGNORED, TallyPurchaseStatus.IMPORTED):
            return voucher.status
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
