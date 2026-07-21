"""Purchase Import Queue business logic (additive feature).

Inventory is NEVER auto-created. Import happens only via ``import_group`` after
explicit user approval, and runs entirely inside the request transaction so a
failure rolls everything back (no partial inventory).
"""

from __future__ import annotations

import json
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.api.schemas.purchase import (
    AccessoryMatch,
    MatchAccessoryResponse,
    MatchedModel,
    MatchModelResponse,
    PurchaseIgnoreResponse,
    PurchaseImportRequest,
    PurchaseImportResponse,
    PurchaseModelGroup,
    PurchaseQueueItem,
    PurchaseSerialCell,
    PurchaseTaxBreakdown,
    PurchaseVoucherDetail,
)
from webstudio_backend.core.exceptions import AppError
from webstudio_backend.infrastructure.audit.audit_actor import AuditActor
from webstudio_backend.infrastructure.database.enums import (
    InventorySource,
    ProductCategory,
    ProductModelStatus,
    TallyPurchaseStatus,
)
from webstudio_backend.infrastructure.database.models.tally_purchase_line import TallyPurchaseLine
from webstudio_backend.infrastructure.database.models.tally_purchase_voucher import (
    TallyPurchaseVoucher,
)
from webstudio_backend.infrastructure.repositories.brand_repository import BrandRepository
from webstudio_backend.infrastructure.repositories.inventory_item_repository import (
    InventoryItemRepository,
)
from webstudio_backend.infrastructure.repositories.product_model_repository import (
    ProductModelRepository,
)
from webstudio_backend.infrastructure.repositories.tally_purchase_repository import (
    TallyPurchaseRepository,
)
from webstudio_backend.integrations.tally.purchase_normalization import (
    ACCESSORY_AUTO_SELECT_SCORE,
    ACCESSORY_SUGGEST_SCORE,
    accessory_match_score,
    models_partial_match,
    normalize_model_number,
)
from webstudio_backend.integrations.tally.quantity import parse_tally_quantity
from webstudio_backend.services.inventory_service import InventoryService
from webstudio_backend.services.product_image_jobs import schedule_product_image_resolve


def _parse_quantity(raw: str | None) -> int:
    return parse_tally_quantity(raw, default=0)


def _decode_serials(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        return []
    if not isinstance(data, list):
        return []
    return [str(item).strip() for item in data if str(item).strip()]


class PurchaseImportService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._purchase = TallyPurchaseRepository(session)
        self._brands = BrandRepository(session)
        self._models = ProductModelRepository(session)
        self._inventory_repo = InventoryItemRepository(session)
        self._inventory = InventoryService(session)

    # ---- Queue reads -------------------------------------------------------

    @staticmethod
    def _taxes(voucher: TallyPurchaseVoucher) -> PurchaseTaxBreakdown:
        return PurchaseTaxBreakdown(
            subtotal=voucher.subtotal,
            discount_amount=voucher.discount_amount,
            round_off=voucher.round_off,
            cgst_amount=voucher.cgst_amount,
            sgst_amount=voucher.sgst_amount,
            igst_amount=voucher.igst_amount,
            cess_amount=voucher.cess_amount,
            grand_total=voucher.grand_total,
        )

    @staticmethod
    def _grouped_lines(
        voucher: TallyPurchaseVoucher,
    ) -> dict[str, list[TallyPurchaseLine]]:
        groups: dict[str, list[TallyPurchaseLine]] = {}
        for line in voucher.lines:
            groups.setdefault(line.group_key, []).append(line)
        return groups

    async def list_queue(
        self, *, status: str | None, limit: int, offset: int
    ) -> list[PurchaseQueueItem]:
        status_enum = None
        if status:
            try:
                status_enum = TallyPurchaseStatus(status)
            except ValueError as exc:
                raise AppError(
                    "VALIDATION_ERROR", "Invalid status filter.", status_code=422
                ) from exc
        vouchers, _total = await self._purchase.list_vouchers(
            status=status_enum, limit=limit, offset=offset
        )
        items: list[PurchaseQueueItem] = []
        for voucher in vouchers:
            groups = self._grouped_lines(voucher)
            imported = sum(1 for lines in groups.values() if all(line.imported for line in lines))
            items.append(
                PurchaseQueueItem(
                    id=voucher.id,
                    supplier_name=voucher.supplier_name,
                    voucher_date=voucher.voucher_date,
                    voucher_number=voucher.tally_voucher_number,
                    invoice_number=voucher.printed_invoice_number,
                    reference_number=voucher.reference_number,
                    voucher_guid=voucher.tally_voucher_guid,
                    voucher_type=voucher.voucher_type,
                    grand_total=voucher.grand_total,
                    taxes=self._taxes(voucher),
                    status=voucher.status.value,
                    group_count=len(groups),
                    imported_group_count=imported,
                    pending_group_count=len(groups) - imported,
                )
            )
        return items

    async def _require_voucher(self, voucher_id: int) -> TallyPurchaseVoucher:
        voucher = await self._purchase.get_voucher(voucher_id)
        if voucher is None:
            raise AppError("NOT_FOUND", "Purchase voucher not found.", status_code=404)
        return voucher

    async def get_detail(self, voucher_id: int) -> PurchaseVoucherDetail:
        voucher = await self._require_voucher(voucher_id)
        groups: list[PurchaseModelGroup] = []
        for group_key, lines in self._grouped_lines(voucher).items():
            ordered = sorted(lines, key=lambda line: line.line_index)
            serials: list[str] = []
            for line in ordered:
                serials.extend(_decode_serials(line.serials_json))
            quantity = sum(_parse_quantity(line.quantity) for line in ordered)
            if quantity == 0:
                quantity = len(serials)
            # Pad empty slots so the UI can collect one serial per billed unit.
            while len(serials) < quantity:
                serials.append("")
            cells = await self._build_serial_cells(serials)
            line_total = next(
                (line.line_total for line in ordered if line.line_total is not None), None
            )
            imported = all(line.imported for line in ordered)
            product_model_id = next(
                (line.product_model_id for line in ordered if line.product_model_id is not None),
                None,
            )
            groups.append(
                PurchaseModelGroup(
                    group_key=group_key,
                    stock_item_name=ordered[0].stock_item_name,
                    quantity=quantity,
                    serial_source=ordered[0].serial_source,
                    serials=cells,
                    line_total=line_total,
                    imported=imported,
                    product_model_id=product_model_id,
                    duplicate_count=sum(1 for cell in cells if cell.is_duplicate),
                )
            )
        return PurchaseVoucherDetail(
            id=voucher.id,
            supplier_name=voucher.supplier_name,
            voucher_date=voucher.voucher_date,
            voucher_number=voucher.tally_voucher_number,
            invoice_number=voucher.printed_invoice_number,
            reference_number=voucher.reference_number,
            voucher_guid=voucher.tally_voucher_guid,
            voucher_type=voucher.voucher_type,
            narration=voucher.narration,
            taxes=self._taxes(voucher),
            grand_total=voucher.grand_total,
            status=voucher.status.value,
            groups=groups,
        )

    async def _build_serial_cells(self, serials: list[str]) -> list[PurchaseSerialCell]:
        cells: list[PurchaseSerialCell] = []
        for serial in serials:
            trimmed = serial.strip()
            if not trimmed:
                cells.append(PurchaseSerialCell(serial_number="", is_duplicate=False))
                continue
            matches = await self._inventory_repo.find_all_by_serial_number(trimmed)
            existing = matches[0] if matches else None
            cells.append(
                PurchaseSerialCell(
                    serial_number=trimmed,
                    is_duplicate=bool(matches),
                    existing_status=existing.status.value if existing else None,
                )
            )
        return cells

    # ---- Model matching ----------------------------------------------------

    async def match_model(self, brand_id: int, raw_model: str) -> MatchModelResponse:
        brand = await self._brands.get_by_id(brand_id)
        if brand is None:
            raise AppError("NOT_FOUND", "Brand not found.", status_code=404)
        normalized = normalize_model_number(
            raw_model, brand_name=brand.name, brand_short_name=brand.short_name
        )
        models = await self._models.list_all_for_brand(brand_id)
        exact: list[MatchedModel] = []
        partial: list[MatchedModel] = []
        for model in models:
            candidate = normalize_model_number(
                model.model_number, brand_name=brand.name, brand_short_name=brand.short_name
            )
            if not candidate:
                continue
            if candidate == normalized:
                kind = "exact"
            elif models_partial_match(
                raw_model,
                model.model_number,
                brand_name=brand.name,
                brand_short_name=brand.short_name,
            ):
                # e.g. Tally "S3407QA-KP027WS" vs IMS "S3407QA-KP027WS(S3407QA)".
                kind = "partial"
            else:
                continue
            entry = MatchedModel(
                id=model.id,
                model_number=model.model_number,
                model_name=model.model_name,
                category=model.category.value,
                is_active=model.status == ProductModelStatus.ACTIVE,
                match_kind=kind,
            )
            (exact if kind == "exact" else partial).append(entry)
        # Exact matches first so the UI lists them above the looser suggestions.
        matches = exact + partial
        # Auto-select ONLY a single unambiguous exact active match. Partial
        # matches are surfaced as suggestions but the operator must confirm
        # (or create a new model), so a suffix mismatch never silently reuses
        # the wrong catalogue entry.
        auto = None
        active_exact = [m for m in exact if m.is_active]
        if len(active_exact) == 1:
            auto = active_exact[0].id
        return MatchModelResponse(
            normalized_model_number=normalized,
            matches=matches,
            auto_selected_model_id=auto,
        )

    async def match_accessory(self, brand_id: int, query: str) -> MatchAccessoryResponse:
        """Fuzzy-search brand accessories by part number / model number / name.

        Unlike ``match_model`` (deterministic exact match for laptops), accessory
        lookup tolerates the loose free-text names Tally emits, e.g. matching
        "ASUS MD102 SILENT" to a catalogue accessory stored as "MD102".
        """
        brand = await self._brands.get_by_id(brand_id)
        if brand is None:
            raise AppError("NOT_FOUND", "Brand not found.", status_code=404)
        normalized = normalize_model_number(
            query, brand_name=brand.name, brand_short_name=brand.short_name
        )
        models = await self._models.list_all_for_brand(brand_id)
        scored: list[tuple[float, AccessoryMatch]] = []
        for model in models:
            if model.category != ProductCategory.ACCESSORY:
                continue
            score = accessory_match_score(
                query,
                candidate_model_number=model.model_number,
                candidate_part_number=model.part_number,
                candidate_model_name=model.model_name,
                brand_name=brand.name,
                brand_short_name=brand.short_name,
            )
            if score < ACCESSORY_SUGGEST_SCORE:
                continue
            scored.append(
                (
                    score,
                    AccessoryMatch(
                        id=model.id,
                        model_number=model.model_number,
                        model_name=model.model_name,
                        part_number=model.part_number,
                        accessory_kind=model.accessory_kind.value if model.accessory_kind else None,
                        category=model.category.value,
                        is_active=model.status == ProductModelStatus.ACTIVE,
                        score=score,
                    ),
                )
            )
        scored.sort(key=lambda item: item[0], reverse=True)
        matches = [match for _score, match in scored]

        # Auto-select only when the single best active candidate is confident and
        # unambiguous (clearly ahead of the runner-up).
        auto = None
        active = [(score, match) for score, match in scored if match.is_active]
        if active:
            top_score, top_match = active[0]
            runner_up = active[1][0] if len(active) > 1 else 0.0
            if top_score >= ACCESSORY_AUTO_SELECT_SCORE and (top_score - runner_up) >= 0.1:
                auto = top_match.id
        return MatchAccessoryResponse(
            normalized_query=normalized,
            matches=matches,
            auto_selected_model_id=auto,
        )

    # ---- Import (transactional) -------------------------------------------

    async def ignore_voucher(self, voucher_id: int) -> PurchaseIgnoreResponse:
        """Dismiss a fetched purchase voucher from the review queue.

        Tombstoned (status=ignored, row retained) so the same Tally voucher is
        not re-fetched on the next sync. Fully imported vouchers cannot be
        ignored (nothing left to dismiss)."""
        voucher = await self._require_voucher(voucher_id)
        if voucher.status == TallyPurchaseStatus.IGNORED:
            return PurchaseIgnoreResponse(voucher_id=voucher.id, status=voucher.status.value)
        if voucher.status == TallyPurchaseStatus.IMPORTED:
            raise AppError(
                "ALREADY_IMPORTED",
                "This purchase is already fully imported and cannot be ignored.",
                status_code=409,
            )
        await self._purchase.ignore_voucher(voucher)
        return PurchaseIgnoreResponse(voucher_id=voucher.id, status=voucher.status.value)

    async def import_group(
        self, request: PurchaseImportRequest, *, actor: AuditActor
    ) -> PurchaseImportResponse:
        voucher = await self._require_voucher(request.voucher_id)
        group_lines = [line for line in voucher.lines if line.group_key == request.group_key]
        if not group_lines:
            raise AppError("NOT_FOUND", "Model group not found on voucher.", status_code=404)
        if all(line.imported for line in group_lines):
            raise AppError(
                "ALREADY_IMPORTED",
                "This model group has already been imported.",
                status_code=409,
            )

        brand = await self._brands.get_by_id(request.brand_id)
        if brand is None or not brand.is_active:
            raise AppError("VALIDATION_ERROR", "Brand is not available.", status_code=422)

        serials = [s.strip() for s in request.serial_numbers if s.strip()]
        if not serials:
            raise AppError(
                "VALIDATION_ERROR",
                "At least one serial number is required before import.",
                status_code=422,
            )

        # Quantity == number of serials (unique).
        seen: set[str] = set()
        duplicates_in_request = []
        for serial in serials:
            key = serial.lower()
            if key in seen:
                duplicates_in_request.append(serial)
            seen.add(key)
        if duplicates_in_request:
            raise AppError(
                "VALIDATION_ERROR",
                f"Duplicate serials in request: {', '.join(sorted(set(duplicates_in_request)))}",
                status_code=422,
            )

        # Duplicate-in-IMS guard (never overwrite / duplicate). EAN-as-serial
        # brands intentionally share serials across units, so the whole-IMS
        # duplicate scan only applies to unique-serial brands.
        skipped_serials: list[str] = []
        if not brand.allow_duplicate_serials:
            existing_serials: list[str] = []
            for serial in serials:
                if await self._inventory_repo.find_all_by_serial_number(serial):
                    existing_serials.append(serial)
            if existing_serials:
                if not request.skip_existing_serials:
                    raise AppError(
                        "SERIAL_NUMBER_DUPLICATE",
                        f"Serial(s) already exist in IMS: {', '.join(existing_serials)}",
                        status_code=409,
                    )
                # Partial import: units already in IMS are reported back as
                # skipped ("already added") and only the new ones are created.
                skipped_serials = existing_serials
                existing_keys = {serial.lower() for serial in existing_serials}
                serials = [serial for serial in serials if serial.lower() not in existing_keys]

        if not serials and request.mode == "new":
            raise AppError(
                "VALIDATION_ERROR",
                "All serial numbers already exist in IMS — select the existing "
                "model instead of creating a new one.",
                status_code=422,
            )

        existing_model = request.mode == "existing"
        model_id: uuid.UUID
        newly_created_model = False
        if existing_model:
            if request.product_model_id is None:
                raise AppError("VALIDATION_ERROR", "product_model_id is required.", status_code=422)
            model = await self._models.get_by_id(request.product_model_id)
            if model is None:
                raise AppError("NOT_FOUND", "Product model not found.", status_code=404)
            if model.brand_id != request.brand_id:
                raise AppError(
                    "VALIDATION_ERROR",
                    "Selected model does not belong to the chosen brand.",
                    status_code=422,
                )
            if model.status != ProductModelStatus.ACTIVE:
                raise AppError(
                    "PRODUCT_MODEL_ARCHIVED", "Product model is not active.", status_code=422
                )
            model_id = model.id
        else:
            if request.new_product_model is None:
                raise AppError(
                    "VALIDATION_ERROR", "new_product_model is required.", status_code=422
                )
            body = request.new_product_model
            if body.brand_id != request.brand_id:
                raise AppError(
                    "VALIDATION_ERROR",
                    "New model brand must match the selected brand.",
                    status_code=422,
                )
            try:
                created = await self._models.create(
                    brand_id=body.brand_id,
                    category=body.category,
                    accessory_kind=body.accessory_kind,
                    part_number=body.part_number,
                    model_number=body.model_number,
                    model_name=body.model_name,
                    cpu=body.cpu,
                    gpu=body.gpu,
                    ram_gb=body.ram_gb,
                    storage_value=body.storage_value,
                    storage_unit=body.storage_unit,
                    storage_type=body.storage_type,
                    status=body.status,
                    display=body.display,
                    color_options=body.color_options,
                    product_image_url=body.product_image_url,
                    search_aliases=body.search_aliases,
                    notes=body.notes,
                    purchase_price=body.purchase_price,
                    selling_price=body.selling_price,
                    actor=actor,
                )
            except Exception as exc:  # noqa: BLE001
                raise AppError("VALIDATION_ERROR", str(exc), status_code=409) from exc
            model_id = created.id
            newly_created_model = not created.product_image_url

        # Create one inventory item per serial (all TALLY_PURCHASE sourced).
        imported = 0
        for serial in serials:
            try:
                await self._inventory.create_item(
                    serial_number=serial,
                    product_model_id=model_id,
                    color=request.color,
                    current_location_id=request.current_location_id,
                    status=request.status,
                    purchase_date=voucher.voucher_date,
                    purchase_price=request.purchase_price,
                    inventory_source=InventorySource.TALLY_PURCHASE,
                    actor=actor,
                )
            except Exception as exc:  # noqa: BLE001 — rollback whole import
                raise AppError("VALIDATION_ERROR", str(exc), status_code=422) from exc
            imported += 1

        await self._purchase.mark_group_imported(
            voucher, group_key=request.group_key, product_model_id=model_id
        )

        if newly_created_model:
            # Background image discovery — never blocks the import commit.
            schedule_product_image_resolve(model_id)

        return PurchaseImportResponse(
            product_model_id=model_id,
            imported_count=imported,
            voucher_status=voucher.status.value,
            group_key=request.group_key,
            existing_model=existing_model,
            skipped_count=len(skipped_serials),
            skipped_serials=skipped_serials,
        )
