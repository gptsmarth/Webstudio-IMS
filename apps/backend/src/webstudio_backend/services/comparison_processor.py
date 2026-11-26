"""Identify exact processor models and extract structured comparison facts."""

import re
from collections.abc import Iterable

from webstudio_backend.api.schemas.comparison import ComparisonSpec

CHIP_MODELS = (
    r"Intel\s+(?:Core\s+)?Ultra\s+[3579]\s+(?:Processor\s+)?\d{3}[A-Z]{0,2}",
    r"Intel\s+Core\s+i[3579]-(?:N\d{3}|\d{4,5}[A-Z]{0,2})",
    r"Intel\s+Core\s+[3579]\s+(?:Processor\s+)?\d{3}[A-Z]{0,2}",
    r"Intel\s+(?:Processor\s+)?N\d{2,3}",
    r"AMD\s+Ryzen\s+(?:AI\s+)?(?:[3579]|Max\+?)(?:\s+PRO)?\s+(?:HX\s+)?\d{3,4}[A-Z]{0,3}",
)
CHIP_PATTERN = re.compile(rf"\b(?:{'|'.join(CHIP_MODELS)})\b(?![-\w])", re.I)
CPU_TOTALS = {
    "CPU cores": r"(?<![\w-])(\d{1,3})\s*(?:-\s*)?(?:physical\s+)?cores?\b",
    "CPU threads": r"(?<![\w-])(\d{1,3})\s*(?:-\s*)?(?:hardware\s+)?threads?\b",
}
INLINE_CPU_FACTS = {
    "CPU max turbo": r"\b(?:up to|max(?:imum)? (?:turbo|boost)|(?:turbo|boost)(?: up to)?)\s+(\d+(?:\.\d+)?\s*(?:GHz|MHz))\b",
    "CPU cache": r"\b(\d+(?:\.\d+)?\s*(?:MB|KB))\s+(?:(?:Intel |AMD )?(?:smart |L[123] )?)cache\b",
}
FACT_PATTERNS = {
    "CPU cores": r"(?:cpu |processor |total )?cores?(?: count)?",
    "CPU threads": r"(?:cpu |processor |total )?threads?(?: count)?",
    "CPU core layout": r"(?:(?:cpu |processor )?core (?:layout|configuration)|[pe]-cores)",
    "CPU max turbo": r"(?:(?:cpu |processor )?(?:max(?:imum)? )?(?:turbo|boost)(?: clock| frequency)?|cpu max clock)",
    "CPU cache": r"(?:cpu |processor |l[123] )?cache",
}


def exact_chip(value: str) -> str | None:
    value = re.sub(r"®|™|\((?:r|tm)\)", "", value, flags=re.I)
    matches = set()
    for match in CHIP_PATTERN.findall(value):
        chip = " ".join(match.casefold().split()).replace(" processor ", " ")
        matches.add(chip.replace("intel ultra ", "intel core ultra ", 1))
    return next(iter(matches)) if len(matches) == 1 else None


def processor_text(specifications: Iterable[ComparisonSpec]) -> str:
    return next(
        (
            spec.detail
            for spec in specifications
            if spec.component.strip().casefold()
            in {"processor", "cpu", "processor model", "cpu model"}
        ),
        "",
    )


def processor_facts(specifications: Iterable[ComparisonSpec]) -> dict[str, str]:
    specs = tuple(specifications)
    processor = processor_text(specs)
    values = {}
    for label, aliases in FACT_PATTERNS.items():
        found = next(
            (
                spec.detail.strip()
                for spec in specs
                if re.fullmatch(aliases, spec.component.strip(), re.I)
            ),
            "",
        )
        if label in CPU_TOTALS:
            total = found if re.fullmatch(r"[1-9]\d{0,2}", found) else None
            if total is None and (match := re.search(CPU_TOTALS[label], found or processor, re.I)):
                total = match[1]
            if total and 0 < int(total) <= 256:
                values[label] = total
        elif found:
            values[label] = found
        elif (pattern := INLINE_CPU_FACTS.get(label)) and (
            match := re.search(pattern, processor, re.I)
        ):
            values[label] = match[1]
    return values


def with_processor_facts(specifications: list[ComparisonSpec]) -> list[ComparisonSpec]:
    facts = processor_facts(specifications)
    labels = {spec.component.casefold() for spec in specifications}
    return [
        *specifications,
        *(
            ComparisonSpec(component=label, detail=value)
            for label, value in facts.items()
            if label.casefold() not in labels
        ),
    ][:60]


def has_cpu_totals(facts: dict[str, str]) -> bool:
    return all(label in facts for label in CPU_TOTALS)


def has_cpu_details(facts: dict[str, str]) -> bool:
    return has_cpu_totals(facts) and all(label in facts for label in INLINE_CPU_FACTS)
