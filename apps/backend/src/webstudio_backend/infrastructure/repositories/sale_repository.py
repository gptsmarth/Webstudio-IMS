"""Sale persistence repository."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.infrastructure.audit.audit_actor import AuditActor
from webstudio_backend.infrastructure.audit.audit_recorder import AuditRecorder
from webstudio_backend.infrastructure.database.enums import AuditSource, SaleSource
from webstudio_backend.infrastructure.database.models.sale import Sale
from webstudio_backend.infrastructure.database.repositories.base import SqlAlchemyRepository
from webstudio_backend.infrastructure.repositories.exceptions import RequiredFieldError
from webstudio_backend.infrastructure.repositories.validation import normalize_required_name
from webstudio_backend.services.sale_snapshot import SaleProductSnapshot


class SaleRepository(SqlAlchemyRepository[Sale]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Sale)

    async def get_by_inventory_item_id(self, inventory_item_id: uuid.UUID) -> Sale | None:
        statement = select(Sale).where(
            Sale.inventory_item_id == inventory_item_id,
            Sale.cancelled_at.is_(None),
        )
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
        sale_amount: float | None = None,
        snapshot: SaleProductSnapshot | None = None,
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

        sale = Sale(
            inventory_item_id=inventory_item_id,
            sale_source=SaleSource.MANUAL,
            sold_at=sold_at,
            invoice_number=normalized_invoice,
            customer_name=normalized_customer,
            payment_mode=normalized_payment,
            recorded_by_user_id=recorded_by_user_id,
            notes=notes.strip() if notes else None,
            sale_amount=sale_amount,
        )
        if snapshot is not None:
            snapshot.apply_to(sale)
        sale = await self.add(sale)
        await AuditRecorder(self._session).record_sale_create(sale, actor=actor)
        return sale

    async def create_tally(
        self,
        *,
        inventory_item_id: uuid.UUID,
        sold_at: datetime,
        printed_invoice_number: str,
        internal_voucher_number: str,
        customer_name: str | None,
        payment_mode: str | None,
        tally_company_name: str,
        tally_voucher_guid: str,
        tally_master_id: str | None,
        tally_voucher_type: str,
        mapped_location_id: int | None,
        notes: str | None = None,
        idempotency_key: str,
        snapshot: SaleProductSnapshot | None = None,
        sale_amount: float | None = None,
        sale_amount_excluding_gst: float | None = None,
    ) -> Sale:
        sale = Sale(
            inventory_item_id=inventory_item_id,
            sale_source=SaleSource.TALLY,
            sold_at=sold_at,
            invoice_number=printed_invoice_number,
            printed_invoice_number=printed_invoice_number,
            customer_name=customer_name,
            payment_mode=payment_mode,
            recorded_by_user_id=None,
            tally_company_name=tally_company_name,
            tally_voucher_number=internal_voucher_number,
            tally_voucher_guid=tally_voucher_guid,
            tally_master_id=tally_master_id,
            tally_voucher_type=tally_voucher_type,
            mapped_location_id=mapped_location_id,
            notes=notes,
            idempotency_key=idempotency_key,
            sale_amount=sale_amount,
            sale_amount_excluding_gst=sale_amount_excluding_gst,
        )
        if snapshot is not None:
            snapshot.apply_to(sale)
        sale = await self.add(sale)
        actor = AuditActor.system(display_name="Tally Sync", role="system")
        await AuditRecorder(self._session).record_sale_create(
            sale,
            actor=actor,
            source=AuditSource.TALLY_SYNC,
        )
        return sale
