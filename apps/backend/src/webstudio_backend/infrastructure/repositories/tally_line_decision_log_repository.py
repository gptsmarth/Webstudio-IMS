"""Tally line decision log repository."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.infrastructure.database.models.tally_line_decision_log import (
    TallyLineDecisionLog,
)
from webstudio_backend.infrastructure.database.repositories.base import SqlAlchemyRepository


class TallyLineDecisionLogRepository(SqlAlchemyRepository[TallyLineDecisionLog]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, TallyLineDecisionLog)

    async def record(
        self,
        *,
        invoice_id: int,
        line_id: int | None,
        voucher_guid: str,
        line_index: int,
        serial_source: str | None,
        extracted_serial: str | None,
        normalized_serial: str | None,
        inventory_item_id: uuid.UUID | None,
        match_result: str,
        decision: str,
        reason: str | None,
    ) -> TallyLineDecisionLog:
        return await self.add(
            TallyLineDecisionLog(
                tally_processed_invoice_id=invoice_id,
                tally_processed_invoice_line_id=line_id,
                tally_voucher_guid=voucher_guid,
                line_index=line_index,
                serial_source=serial_source,
                extracted_serial=extracted_serial,
                normalized_serial=normalized_serial,
                inventory_item_id=inventory_item_id,
                match_result=match_result,
                decision=decision,
                reason=reason,
            ),
        )
