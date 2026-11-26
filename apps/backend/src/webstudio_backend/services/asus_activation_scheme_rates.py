"""Date-effective model rates for ASUS activation schemes."""

from datetime import date, timedelta

from webstudio_backend.infrastructure.database.models.asus_activation import AsusActivationScheme

DAY = timedelta(days=1)


def rate_at(scheme: AsusActivationScheme, model: str, sold: date) -> dict | None:
    key = sold.isoformat()
    for row in scheme.rate_overrides.get(model, []):
        if row["date_from"] <= key <= row["date_to"]:
            return row["rate"]
    return scheme.rules.get(model)


def windows(scheme: AsusActivationScheme, model: str) -> list[tuple[date, date, dict | None]]:
    start, end = scheme.date_from, scheme.date_to
    edges = {start, end + DAY}
    for row in scheme.rate_overrides.get(model, []):
        first, last = date.fromisoformat(row["date_from"]), date.fromisoformat(row["date_to"])
        if first <= end and last >= start:
            edges.update((max(start, first), min(end, last) + DAY))
    ordered = sorted(edges)
    return [
        (a, b - DAY, rate_at(scheme, model, a)) for a, b in zip(ordered, ordered[1:], strict=False)
    ]


def window(start: date, end: date, rate: dict) -> dict:
    return {"date_from": start.isoformat(), "date_to": end.isoformat(), "rate": rate}


def overlay(rows: list[dict], start: date, end: date, rate: dict) -> list[dict]:
    result = [window(start, end, rate)]
    for row in rows:
        first, last = date.fromisoformat(row["date_from"]), date.fromisoformat(row["date_to"])
        if last < start or first > end:
            result.append(row)
            continue
        if first < start:
            result.append(window(first, start - DAY, row["rate"]))
        if last > end:
            result.append(window(end + DAY, last, row["rate"]))
    return sorted(result, key=lambda row: row["date_from"])
