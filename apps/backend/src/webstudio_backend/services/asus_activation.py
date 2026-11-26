"""ASUS activation projections and guarded receipt writes."""

from __future__ import annotations

import hashlib
import json
import unicodedata
from collections import Counter, defaultdict
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.core.exceptions import AppError
from webstudio_backend.infrastructure.database.enums import ProductCategory
from webstudio_backend.infrastructure.database.models.asus_activation import (
    AsusActivationReceipt,
    AsusActivationScheme,
    AsusActivationWorkbook,
)
from webstudio_backend.infrastructure.database.models.sale import Sale
from webstudio_backend.infrastructure.repositories.report_repository import ReportRepository
from webstudio_backend.infrastructure.repositories.tally_processed_invoice_repository import (
    TallyProcessedInvoiceRepository,
)
from webstudio_backend.integrations.tally.xml_parser import normalize_serial
from webstudio_backend.services.asus_activation_workbooks import (
    invalid,
    model_key,
    money,
    scheme_code,
)
from webstudio_backend.services.asus_weekly_report_service import INDIA_TIME, AsusSaleUnitPrices

# Serialize imports and settlement changes without acquiring any Tally/sales write lock.
_ACTIVATION_WRITE_LOCK = 59286512
_ZERO = Decimal("0.00")


def local_today() -> date:
    return datetime.now(INDIA_TIME).date()


def month_dates(month: str) -> tuple[date, date]:
    try:
        start = date.fromisoformat(month + "-01")
        next_month = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
    except (ValueError, OverflowError) as exc:
        raise invalid("Select a valid month in YYYY-MM format.") from exc
    return start, next_month - timedelta(days=1)


def _str_money(amount) -> str | None:
    return f"{amount:.2f}" if amount is not None else None


def workbook_file_name(filename: str | None) -> str:
    base = (
        unicodedata.normalize("NFKC", filename or "activation.xlsx")
        .replace("\\", "/")
        .split("/")[-1]
    )
    return "".join(char for char in base if char.isprintable())[:255] or "activation.xlsx"


async def purge_activation_workbooks(session: AsyncSession) -> None:
    await session.execute(
        delete(AsusActivationWorkbook).where(AsusActivationWorkbook.expires_at <= datetime.now(UTC))
    )


class AsusActivationService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self._reports = ReportRepository(session)

    async def lock(self) -> None:
        await self.session.execute(select(func.pg_advisory_xact_lock(_ACTIVATION_WRITE_LOCK)))

    async def upload_scheme(self, start, end, filename, content, rules, actor_id) -> dict:
        if start > end or end > date.max - timedelta(days=6):
            raise invalid(
                "Select an inclusive range with the start date on or before the end date."
            )
        await self.lock()
        await purge_activation_workbooks(self.session)
        digest = hashlib.sha256(content).hexdigest()
        existing = await self.session.scalar(
            select(AsusActivationScheme).where(
                AsusActivationScheme.date_from <= end, AsusActivationScheme.date_to >= start
            )
        )
        if existing:
            if (existing.date_from, existing.date_to, existing.digest) == (start, end, digest):
                return await self._import_result(existing)
            raise AppError(
                "VALIDATION_ERROR",
                f"The selected dates overlap the uploaded scheme for {existing.date_from} to {existing.date_to}.",
                409,
            )
        now = datetime.now(UTC)
        scheme = AsusActivationScheme(
            id=uuid4(),
            date_from=start,
            date_to=end,
            filename=workbook_file_name(filename),
            digest=digest,
            rules=rules,
            created_by=actor_id,
            created_at=now,
        )
        self.session.add(scheme)
        await self.session.flush()
        # Keep five full calendar days after the final sale date.
        expires = datetime.combine(end + timedelta(days=6), time.min, tzinfo=INDIA_TIME)
        if now < expires:
            self.session.add(
                AsusActivationWorkbook(scheme_id=scheme.id, content=content, expires_at=expires)
            )
        return await self._import_result(scheme)

    async def _import_result(self, scheme: AsusActivationScheme) -> dict:
        sales = await self.claims(schemes=[scheme], include_prices=False)
        return {
            **self._scheme_metadata(scheme),
            "matched_sale_count": sum(not sale["cancelled"] for sale in sales),
        }

    async def schemes(self) -> list[AsusActivationScheme]:
        result = await self.session.scalars(
            select(AsusActivationScheme).order_by(AsusActivationScheme.date_from)
        )
        return list(result)

    @staticmethod
    def _scheme_metadata(scheme: AsusActivationScheme) -> dict:
        return {
            "id": str(scheme.id),
            "date_from": str(scheme.date_from),
            "date_to": str(scheme.date_to),
            "filename": scheme.filename,
            "rule_count": len(scheme.rules),
        }

    async def dashboard(self, month: str | None) -> dict:
        today = local_today()
        selected_month = month or today.strftime("%Y-%m")
        schemes = await self.schemes()
        claims = await self.claims(selected_month, schemes=schemes)
        counts = Counter(claim["status"] for claim in claims)
        total_expected = sum((Decimal(claim["expected_amount"]) for claim in claims), _ZERO)
        pending = sum(
            (Decimal(claim["expected_amount"]) for claim in claims if claim["status"] == "pending"),
            _ZERO,
        )
        received = sum(
            (
                Decimal(claim["received_amount"])
                for claim in claims
                if claim["received_amount"] is not None
            ),
            _ZERO,
        )
        return {
            "month": selected_month,
            "today": str(today),
            "active_scheme": next(
                (self._scheme_metadata(s) for s in schemes if s.date_from <= today <= s.date_to),
                None,
            ),
            "latest_scheme": self._scheme_metadata(schemes[-1]) if schemes else None,
            "schemes": [self._scheme_metadata(s) for s in schemes],
            "claims": claims,
            "counts": dict(counts),
            "totals": {
                "expected": str(total_expected),
                "pending": str(pending),
                "received": str(received),
            },
        }

    async def claims(
        self,
        month: str | None = None,
        *,
        serials: set[str] | None = None,
        include_prices: bool = True,
        schemes: list[AsusActivationScheme] | None = None,
    ) -> list[dict]:
        bounds = month_dates(month) if month else None
        schemes = await self.schemes() if schemes is None else schemes
        ranges = [
            s for s in schemes if not bounds or s.date_from <= bounds[1] and s.date_to >= bounds[0]
        ]
        if not ranges or serials == set():
            return []
        start, end = ranges[0].date_from, ranges[-1].date_to
        if bounds:
            start, end = max(start, bounds[0]), min(end, bounds[1])
        records = await self._reports.list_asus_weekly_sales(
            datetime.combine(start, time.min, tzinfo=INDIA_TIME),
            datetime.combine(end, time.max, tzinfo=INDIA_TIME),
            serials=serials,
            include_cancelled=True,
        )
        if not records:
            return []
        receipts = await self.session.scalars(
            select(AsusActivationReceipt)
            .join(AsusActivationScheme)
            .where(AsusActivationScheme.date_from <= end, AsusActivationScheme.date_to >= start)
        )
        by_sale = {receipt.sale_id: receipt for receipt in receipts}
        prices = AsusSaleUnitPrices(TallyProcessedInvoiceRepository(self.session))
        claims = []
        for record in records:
            sale = record.sale
            receipt = by_sale.get(sale.id)
            if (
                record.category == ProductCategory.ACCESSORY
                or sale.cancelled_at
                and receipt is None
            ):
                continue
            sold = sale.sold_at.astimezone(INDIA_TIME).date()
            scheme = next((s for s in ranges if s.date_from <= sold <= s.date_to), None)
            sku = model_key(record.model_number)
            serial = (record.serial_number or "").strip()
            if not scheme or not serial or sku not in scheme.rules:
                continue
            rule = scheme.rules[sku]
            expected = receipt.expected_amount if receipt else Decimal(rule["cn"])
            variance = receipt.amount - expected if receipt else None
            status = "pending"
            if receipt:
                status = "discrepancy" if variance and receipt.resolved_at is None else "received"
            price = await prices.resolve(sale, serial) if include_prices else None
            claims.append(
                {
                    "sale_id": sale.id,
                    "sold_on": str(sold),
                    "serial": serial,
                    "model": sku,
                    "invoice": sale.printed_invoice_number or sale.invoice_number,
                    "customer": sale.customer_name,
                    "unit_price": _str_money(price),
                    "supported_srp": rule["srp"],
                    "expected_amount": str(expected),
                    "scheme_id": str(scheme.id),
                    "date_from": str(scheme.date_from),
                    "date_to": str(scheme.date_to),
                    "scheme_filename": scheme.filename,
                    "scheme_code": rule["scheme_code"],
                    "source_sheet": rule["sheet"],
                    "program_period": rule.get("program_period"),
                    "cancelled": sale.cancelled_at is not None,
                    "status": status,
                    "received_amount": _str_money(receipt.amount) if receipt else None,
                    "variance": _str_money(variance),
                    "receipt_source": receipt.source if receipt else None,
                    "receipt_filename": receipt.filename if receipt else None,
                    "receipt_scheme": receipt.receipt_scheme if receipt else None,
                    "application_no": receipt.application_no if receipt else None,
                    "release_date": (
                        str(receipt.release_date) if receipt and receipt.release_date else None
                    ),
                    "record_note": receipt.record_note if receipt else None,
                    "recorded_at": receipt.recorded_at.isoformat() if receipt else None,
                    "resolution_note": receipt.resolution_note if receipt else None,
                    "resolved_at": (
                        receipt.resolved_at.isoformat() if receipt and receipt.resolved_at else None
                    ),
                    **(
                        {"receipt_digest": receipt.digest if receipt else None}
                        if not include_prices
                        else {}
                    ),
                }
            )
        return list(reversed(claims))

    async def record_manual(
        self, sale_id: int, action: str, raw_amount, note: str, actor_id: int
    ) -> dict:
        await self.lock()
        sale = await self.session.get(Sale, sale_id)
        if not sale:
            raise AppError("NOT_FOUND", "Activation claim not found.", 404)
        month = sale.sold_at.astimezone(INDIA_TIME).strftime("%Y-%m")
        claim = next(
            (c for c in await self.claims(month, include_prices=False) if c["sale_id"] == sale_id),
            None,
        )
        if not claim or claim["cancelled"]:
            raise AppError("NOT_FOUND", "Active activation claim not found.", 404)
        if action == "resolve":
            if claim["status"] != "discrepancy":
                raise AppError(
                    "VALIDATION_ERROR", "This claim has no unresolved amount discrepancy.", 409
                )
            if not note:
                raise invalid("Enter a note explaining how the discrepancy was resolved.")
            receipt = await self.session.get(AsusActivationReceipt, sale_id)
            receipt.resolved_at = datetime.now(UTC)
            receipt.resolved_by = actor_id
            receipt.resolution_note = note
        else:
            if claim["status"] != "pending":
                raise AppError("VALIDATION_ERROR", "This claim already has a receipt.", 409)
            try:
                amount = money(raw_amount)
            except ValueError as exc:
                raise invalid(str(exc)) from exc
            self._record(claim, amount, actor_id, note=note)
        await self.session.flush()
        return next(c for c in await self.claims(month) if c["sale_id"] == sale_id)

    def _record(
        self,
        claim: dict,
        amount: Decimal,
        actor_id: int,
        *,
        note: str = "",
        row=None,
        filename=None,
    ) -> None:
        self.session.add(
            AsusActivationReceipt(
                sale_id=claim["sale_id"],
                scheme_id=UUID(claim["scheme_id"]),
                expected_amount=Decimal(claim["expected_amount"]),
                amount=amount,
                source="excel" if row else "manual",
                filename=filename,
                digest=row["digest"] if row else None,
                release_date=date.fromisoformat(row["release_date"]) if row else None,
                receipt_scheme=(row["scheme"] or None) if row else None,
                application_no=(row["application_no"] or None) if row else None,
                record_note=note,
                recorded_by=actor_id,
                recorded_at=datetime.now(UTC),
            )
        )

    async def reconcile(
        self,
        rows: list[dict],
        content: bytes,
        filename: str | None,
        actor_id: int,
        preview_id: str | None,
    ) -> dict:
        if preview_id is not None:
            await self.lock()
        claims = await self.claims(serials={row["serial"] for row in rows}, include_prices=False)
        preview = self._plan_receipts(rows, claims)
        filename = workbook_file_name(filename)
        token = hashlib.sha256(
            content + json.dumps([filename, preview], sort_keys=True).encode()
        ).hexdigest()
        if preview_id is not None:
            if token != preview_id:
                raise AppError(
                    "VALIDATION_ERROR",
                    "The workbook or matching claims changed. Preview the file again before confirming.",
                    409,
                )
            by_sale = {c["sale_id"]: c for c in claims}
            for row in preview:
                if row["outcome"] in ("receive", "discrepancy"):
                    self._record(
                        by_sale[row["sale_id"]],
                        Decimal(row["amount"]),
                        actor_id,
                        row=row,
                        filename=filename,
                    )
        counts = Counter(row["outcome"] for row in preview)
        posted = {
            outcome: sum(
                (Decimal(row["amount"]) for row in preview if row["outcome"] == outcome), _ZERO
            )
            for outcome in ("receive", "discrepancy")
        }
        return {
            "preview_id": token,
            "filename": filename,
            "confirmed": preview_id is not None,
            "rows": preview,
            "counts": dict(counts),
            "received_total": str(posted["receive"]),
            "discrepancy_total": str(posted["discrepancy"]),
            "receivable_total": str(sum(posted.values(), _ZERO)),
        }

    @staticmethod
    def _plan_receipts(rows: list[dict], claims: list[dict]) -> list[dict]:
        by_unit = defaultdict(list)
        for claim in claims:
            by_unit[(normalize_serial(claim["serial"]), claim["model"])].append(claim)
        seen = set()
        preview = []
        for row in rows:
            planned = {
                **row,
                "outcome": "unmatched",
                "sale_id": None,
                "expected_amount": None,
                "variance": None,
            }
            preview.append(planned)
            if row["digest"] in seen:
                planned["outcome"] = "duplicate"
                continue
            seen.add(row["digest"])
            code = scheme_code(row["scheme"])
            candidates = [
                c
                for c in by_unit[(row["serial"], row["model"])]
                if c["sold_on"] <= row["release_date"]
                and not c["cancelled"]
                and (not code or not c["scheme_code"] or code == c["scheme_code"])
            ]
            if code:
                exact = [c for c in candidates if c["scheme_code"] == code]
                candidates = exact or candidates
            if len(candidates) != 1:
                if candidates:
                    planned["outcome"] = "ambiguous"
                continue
            candidate = candidates[0]
            variance = Decimal(row["amount"]) - Decimal(candidate["expected_amount"])
            planned.update(
                sale_id=candidate["sale_id"],
                expected_amount=candidate["expected_amount"],
                variance=str(variance),
                sold_on=candidate["sold_on"],
                invoice=candidate["invoice"],
                date_from=candidate["date_from"],
                date_to=candidate["date_to"],
            )
            if candidate["status"] != "pending":
                planned["outcome"] = (
                    "duplicate"
                    if candidate["receipt_digest"] == row["digest"]
                    else "already_recorded"
                )
            else:
                planned["outcome"] = "discrepancy" if variance else "receive"
        repeated = Counter(
            p["sale_id"] for p in preview if p["outcome"] in ("receive", "discrepancy")
        )
        for row in preview:
            if repeated[row["sale_id"]] > 1 and row["outcome"] in ("receive", "discrepancy"):
                row["outcome"] = "ambiguous"
        return preview
