"""Normalize numerical units for comparable analysis."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class NormalizedValue:
    value: float
    unit: str
    notes: str = ""


_SCALE = {
    "thousand": 1e3,
    "k": 1e3,
    "million": 1e6,
    "mn": 1e6,
    "m": 1e6,
    "billion": 1e9,
    "bn": 1e9,
    "b": 1e9,
    "crore": 1e7,
    "lakh": 1e5,
}


def parse_numeric(raw: float | str | int | None) -> float | None:
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return float(raw)
    text = str(raw).strip().replace(",", "")
    text = text.replace("%", "")
    # Handle $5.2B style
    m = re.match(r"^[\$₹]?\s*(-?\d+(?:\.\d+)?)\s*([kKmMbB])?$", text)
    if m:
        val = float(m.group(1))
        suf = (m.group(2) or "").lower()
        if suf == "k":
            val *= 1e3
        elif suf == "m":
            val *= 1e6
        elif suf == "b":
            val *= 1e9
        return val
    try:
        return float(text)
    except ValueError:
        return None


def normalize_value(value: float, unit: str | None) -> NormalizedValue:
    """
    Convert magnitude words into a base unit where possible.

    Examples:
      5.2, "billion USD" -> 5.2e9, "USD"
      5000, "million USD" -> 5e9, "USD"
      35, "%" -> 35, "percent"
    """
    unit_l = (unit or "").strip().lower()
    if not unit_l:
        return NormalizedValue(value=value, unit="", notes="")

    if "%" in unit_l or "percent" in unit_l or "pct" in unit_l:
        return NormalizedValue(value=value, unit="percent", notes="Normalized percentage unit.")

    # Detect scale word in unit
    scale = 1.0
    notes = ""
    base_unit = unit_l
    for word, factor in _SCALE.items():
        # Prefer longer words first — already unordered; check whole tokens
        if re.search(rf"\b{re.escape(word)}\b", unit_l):
            scale = factor
            notes = f"Scaled by {word} ({factor:g})."
            base_unit = re.sub(rf"\b{re.escape(word)}\b", "", unit_l).strip()
            break

    # Currency / vehicles cleanup
    base_unit = base_unit.replace("usd", "USD").replace("us$", "USD").replace("$", "USD")
    base_unit = re.sub(r"\s+", " ", base_unit).strip(" /-")
    if not base_unit:
        base_unit = "units"

    return NormalizedValue(value=value * scale, unit=base_unit or "units", notes=notes)


def units_compatible(a: str | None, b: str | None) -> bool:
    na = normalize_value(1.0, a).unit.lower()
    nb = normalize_value(1.0, b).unit.lower()
    if not na or not nb:
        return True
    if na == nb:
        return True
    # percent aliases
    if {na, nb} <= {"percent", "%", "pct"}:
        return True
    return False
