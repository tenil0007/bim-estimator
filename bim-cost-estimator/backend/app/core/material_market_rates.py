"""
Material market reference rates (India-centric)
-----------------------------------------------
Provides per-material unit rates in INR with a live USD/INR spot from the
Frankfurter API (ECB). Import-sensitive materials are blended toward FX
movement; predominantly local materials move less.

These are **reference schedule rates** for transparency next to ML totals — not
a substitute for supplier quotes or BoQ-specific pricing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import httpx

from app.config import get_settings
from app.utils import get_logger

logger = get_logger("material_market_rates")

# Frankfurter moved to api.frankfurter.dev (see https://www.frankfurter.dev/docs/)
FRANKFURTER_LATEST = "https://api.frankfurter.dev/v1/latest"


@dataclass(frozen=True)
class _CatalogEntry:
    category: str
    unit_label: str
    base_inr: float
    """Typical all-India indicative rate (order-of-magnitude for dashboards)."""
    fx_weight: float
    """0 = local-only; 1 = full pass-through vs reference USD/INR (import parity)."""
    keywords: tuple[str, ...]


_CATALOG: tuple[_CatalogEntry, ...] = (
    _CatalogEntry(
        "Ready-mix / structural concrete",
        "per m³",
        7800.0,
        0.12,
        ("concrete", "cement", "rcc", "precast", "shotcrete", "grout"),
    ),
    _CatalogEntry(
        "Reinforcement steel",
        "per kg",
        68.0,
        0.85,
        ("rebar", "reinforcement", "steel bar", "tor", "tmt", "reinforc"),
    ),
    _CatalogEntry(
        "Structural steel sections",
        "per kg",
        72.0,
        0.88,
        ("structural steel", "steel section", "i-section", "beam steel", "column steel"),
    ),
    _CatalogEntry(
        "Masonry / brickwork",
        "per m³",
        5200.0,
        0.08,
        ("brick", "masonry", "block", "aac", "fly ash"),
    ),
    _CatalogEntry(
        "Timber / wood",
        "per m³",
        48000.0,
        0.35,
        ("wood", "timber", "plywood", "lumber", "hardwood"),
    ),
    _CatalogEntry(
        "Glazing",
        "per m²",
        2200.0,
        0.25,
        ("glass", "glazing", "dgu", "window glass", "curtain"),
    ),
    _CatalogEntry(
        "Aluminum / metal cladding",
        "per kg",
        245.0,
        0.55,
        ("aluminum", "aluminium"),
    ),
    _CatalogEntry(
        "Gypsum / drywall",
        "per m²",
        420.0,
        0.1,
        ("gypsum", "drywall", "plasterboard"),
    ),
    _CatalogEntry(
        "UPVC / polymers",
        "per kg",
        185.0,
        0.4,
        ("upvc", "pvc", "polymer", "hdpe"),
    ),
)

_FALLBACK = _CatalogEntry(
    "General building (reference)",
    "per m³ (equiv.)",
    10500.0,
    0.15,
    (),
)


def _normalize(name: str) -> str:
    s = (name or "").lower().strip()
    s = re.sub(r"\s+", " ", s)
    return s


def _match_catalog(raw_name: str) -> _CatalogEntry:
    n = _normalize(raw_name)
    if not n or n == "unknown":
        return _FALLBACK

    for entry in _CATALOG:
        if any(k in n for k in entry.keywords):
            return entry

    if "steel" in n and "concrete" not in n:
        for e in _CATALOG:
            if "Reinforcement" in e.category:
                return e

    return _FALLBACK


def _blend_rate(base_inr: float, fx_weight: float, usd_inr: float, ref_inr: float) -> float:
    """Blend local base with FX movement. fx_weight=1 => full usd_inr/ref ratio."""
    if ref_inr <= 0:
        return base_inr
    ratio = usd_inr / ref_inr
    blended = base_inr * ((1.0 - fx_weight) + fx_weight * ratio)
    return max(round(blended, 2), 0.01)


async def fetch_usd_inr_live() -> tuple[float, str, str]:
    """
    Returns (inr_per_1_usd, rate_date_iso, source_label).
    On failure, returns (reference from settings, '', 'cached_reference').
    """
    settings = get_settings()
    ref = float(settings.material_rate_reference_usd_inr)

    try:
        async with httpx.AsyncClient(timeout=12.0, follow_redirects=True) as client:
            r = await client.get(f"{FRANKFURTER_LATEST}?from=USD&to=INR")
            r.raise_for_status()
            data: dict[str, Any] = r.json()
            inr = float(data["rates"]["INR"])
            d = str(data.get("date") or "")
            return inr, d, "Frankfurter (ECB USD/INR)"
    except Exception as e:
        logger.warning(f"Live USD/INR fetch failed, using reference rate | error={e}")
        return ref, "", "reference_fallback"


async def build_material_unit_rates(
    material_names: list[str],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """
    Build one row per distinct material name from the project, with live FX metadata.
    """
    settings = get_settings()
    ref_usd_inr = float(settings.material_rate_reference_usd_inr)

    usd_inr, rate_date, fx_source = await fetch_usd_inr_live()
    now = datetime.now(timezone.utc).isoformat()

    meta = {
        "usd_inr": round(usd_inr, 4),
        "reference_usd_inr": ref_usd_inr,
        "fx_source": fx_source,
        "fx_rate_date": rate_date or None,
        "fetched_at_utc": now,
    }

    seen: set[str] = set()
    rows: list[dict[str, Any]] = []

    for raw in material_names:
        key = _normalize(raw) or "unknown"
        if key in seen:
            continue
        seen.add(key)

        entry = _match_catalog(raw)
        rate = _blend_rate(entry.base_inr, entry.fx_weight, usd_inr, ref_usd_inr)

        note = (
            f"Indicative {entry.category.lower()}. FX blend weight {entry.fx_weight:.0%} vs "
            f"ref ₹{ref_usd_inr}/USD — import-linked materials move more with USD/INR."
        )

        rows.append(
            {
                "material_name": raw or "Unknown",
                "matched_category": entry.category,
                "unit": entry.unit_label,
                "rate_inr": rate,
                "base_rate_inr": round(entry.base_inr, 2),
                "fx_weight": entry.fx_weight,
                "usd_inr_spot": round(usd_inr, 4),
                "pricing_note": note,
                "as_of_utc": now,
            }
        )

    rows.sort(key=lambda x: (x["matched_category"], x["material_name"]))
    return rows, meta

