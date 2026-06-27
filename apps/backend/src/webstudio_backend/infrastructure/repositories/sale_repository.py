"""Sale persistence repository."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.infrastructure.audit.audit_actor import AuditActor
from webstudio_backend.infrastructure.audit.audit_recorder import AuditRecorder
from webstudio_backend.infrastructure.database.enums import SaleSource
from webstudio_backend.infrastructure.database.models.sale import Sale
from webstudio_backend.infrastructure.database.repositories.base import SqlAlchemyRepository
from webstudio_backend.infrastructure.repositories.exceptions import RequiredFieldError
from webstudio_backend.infrastructure.repositories.validation import normalize_required_name


class SaleRepository(SqlAlchemyRepository[Sale]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Sale)

    async def get_by_inventory_item_id(self, inventory_item_id: uuid.UUID) -> Sale | None:
        statement = select(Sale).where(Sale.inventory_item_id == inventory_item_id)
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def create_manual(
        self,
        *,
        inventory_item_id: uuid.UUID,
        sold_at: datetime,
        invoice_number: str,
        customer_name: str,
        payment_mode: str,
        recorded_by_user_id: int,
        notes: str | None = None,
        actor: AuditActor,
    ) -> Sale:
        normalized_invoice = normalize_required_name(invoice_number)
        normalized_customer = normalize_required_name(customer_name)
        normalized_payment = normalize_required_name(payment_mode)
        if not normalized_invoice:
            raise RequiredFieldError("invoice_number")
        if not normalized_customer:
            raise RequiredFieldError("customer_name")
        if not normalized_payment:
            raise RequiredFieldError("payment_mode")

        sale = await self.add(
            Sale(
                inventory_item_id=inventory_item_id,
                sale_source=SaleSource.MANUAL,
                sold_at=sold_at,
                invoice_number=normalized_invoice,
                customer_name=normalized_customer,
                payment_mode=normalized_payment,
                recorded_by_user_id=recorded_by_user_id,
                notes=notes.strip() if notes else None,
            ),
        )
        await AuditRecorder(self._session).record_sale_create(sale, actor=actor)
        return sale
