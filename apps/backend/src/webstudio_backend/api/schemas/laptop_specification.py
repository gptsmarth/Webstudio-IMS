"""Supplemental public hardware facts stored on a product model."""

import re

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

_HARDWARE_LABEL = re.compile(
    r"(?:processor|cpu|core|cores|threads|cache|ram|memory|storage|ssd|hdd|nvme|"
    r"graphics|gpu|vram|display|screen|panel|refresh|brightness|resolution|"
    r"battery|charging|charger|power adapter|weight|dimensions|physical design|color|colour|"
    r"connectivity|wireless|wi[ -]?fi|bluetooth|network|ports?|usb|thunderbolt|hdmi|"
    r"camera|webcam|audio|speakers?|microphone|keyboard|security|fingerprint|touchpad|"
    r"operating system|os|warranty|npu)\b",
    re.I,
)
_PRIVATE_LABEL = re.compile(
    r"\b(?:password|token|api key|credential|supplier|cost|margin|serial)\b", re.I
)
_UNKNOWN = re.compile(
    r"^(?:unknown|unavailable|not (?:available|verified|specified|published)|n/a|none|null|[-—])(?:\b|$)",
    re.I,
)
MAX_DETAILED_SPECIFICATIONS = 48


def documented_detail(value: str) -> bool:
    return bool(value.strip() and not _UNKNOWN.match(value.strip()))


class LaptopSpecification(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    component: str = Field(min_length=1, max_length=90)
    detail: str = Field(min_length=1, max_length=1000)

    @field_validator("component")
    @classmethod
    def hardware_label(cls, label: str) -> str:
        if (
            not _HARDWARE_LABEL.match(label)
            or _PRIVATE_LABEL.search(label)
            or not label.isprintable()
        ):
            raise ValueError("Enter a public hardware specification label.")
        return label


def detailed_specifications(facts: object) -> list[LaptopSpecification]:
    if not isinstance(facts, dict):
        return []
    specs = {}
    for label, value in facts.items():
        if not isinstance(label, str) or not isinstance(value, str):
            continue
        value = " ".join(value.split())
        if not documented_detail(value):
            continue
        try:
            spec = LaptopSpecification(component=label, detail=value)
        except ValidationError:
            continue
        specs.setdefault(spec.component.casefold(), spec)
        if len(specs) == MAX_DETAILED_SPECIFICATIONS:
            break
    return list(specs.values())
