"""
Quantity Takeoff (QTO) Module
------------------------------
Computes construction quantities from extracted BIM element data.
Maps element quantities to cost database rates for estimation.
Follows Indian Standard (IS) measurement conventions.
"""

import json
from pathlib import Path
from typing import Optional
from app.utils import get_logger
from app.config import get_settings

logger = get_logger("quantity_takeoff")


def compute_qto(elements: list[dict]) -> list[dict]:
    """
    Compute quantity takeoff for all elements.
    Enriches element data with computed quantities and unit mappings.

    Args:
        elements: List of BIM element dictionaries

    Returns:
        Enriched element list with QTO fields
    """
    rates = _load_cost_rates()
    enriched = []

    for elem in elements:
        elem = _compute_element_qto(elem, rates)
        enriched.append(elem)

    logger.info(f"QTO computed for {len(enriched)} elements")
    return enriched


def _compute_element_qto(element: dict, rates: dict) -> dict:
    """Compute QTO for a single element based on its type."""
    ifc_type = element.get("ifc_type", "")
    material = element.get("material", "Unknown")

    # Get applicable rate
    rate_info = _get_rate_for_element(ifc_type, material, rates)

    # Determine primary quantity for cost calculation
    primary_qty, primary_unit = _get_primary_quantity(element, ifc_type)

    element["primary_quantity"] = primary_qty
    element["primary_unit"] = primary_unit
    element["unit_rate"] = rate_info.get("unit_rate", 0)
    element["rate_unit"] = rate_info.get("rate_unit", "per m³")
    element["labor_rate_per_hour"] = rate_info.get("labor_rate_per_hour", 250)
    element["labor_productivity"] = rate_info.get("labor_productivity", 1.0)  # m³/hr or m²/hr

    # Compute estimated cost from QTO
    if primary_qty and element["unit_rate"]:
        element["qto_estimated_cost"] = round(primary_qty * element["unit_rate"], 2)
    else:
        element["qto_estimated_cost"] = 0.0

    # Compute estimated labor hours
    if primary_qty and element["labor_productivity"] > 0:
        element["estimated_labor_hours"] = round(primary_qty / element["labor_productivity"], 2)
    else:
        element["estimated_labor_hours"] = 0.0

    return element


def _get_primary_quantity(element: dict, ifc_type: str) -> tuple:
    """Determine the primary quantity and unit for cost calculation."""
    volume = element.get("volume", 0) or 0
    area = element.get("area", 0) or 0
    length = element.get("length", 0) or 0

    # Volume-based types (concrete work)
    if ifc_type in ("IfcColumn", "IfcBeam", "IfcFooting", "IfcStair"):
        return (volume, "m³")

    # Area-based OR volume-based
    if ifc_type in ("IfcSlab", "IfcRoof"):
        if volume > 0:
            return (volume, "m³")
        return (area, "m²")

    # Walls: volume for concrete, area for brick
    if ifc_type == "IfcWall":
        material = element.get("material", "")
        if "Concrete" in material:
            return (volume, "m³") if volume > 0 else (area, "m²")
        return (area, "m²")

    # Count-based types
    if ifc_type in ("IfcDoor", "IfcWindow"):
        return (area, "m²")

    # Length-based
    if ifc_type == "IfcRailing":
        return (length, "m")

    # Fallback to volume > area > length
    if volume > 0:
        return (volume, "m³")
    elif area > 0:
        return (area, "m²")
    elif length > 0:
        return (length, "m")
    return (1.0, "nos")


def _get_rate_for_element(ifc_type: str, material: str, rates: dict) -> dict:
    """Look up cost rate from the rate database."""
    # Try specific match first
    key = f"{ifc_type}_{material}".replace(" ", "_")
    if key in rates:
        return rates[key]

    # Try element type match
    if ifc_type in rates:
        return rates[ifc_type]

    # Default rates (INR)
    return _get_default_rate(ifc_type, material)


def _get_default_rate(ifc_type: str, material: str) -> dict:
    """Default Indian construction rates (INR) when database lookup fails."""
    DEFAULT_RATES = {
        "IfcColumn": {"unit_rate": 12500, "rate_unit": "per m³", "labor_rate_per_hour": 350, "labor_productivity": 0.8},
        "IfcBeam": {"unit_rate": 11000, "rate_unit": "per m³", "labor_rate_per_hour": 350, "labor_productivity": 0.7},
        "IfcSlab": {"unit_rate": 10000, "rate_unit": "per m³", "labor_rate_per_hour": 300, "labor_productivity": 1.2},
        "IfcWall": {"unit_rate": 4500, "rate_unit": "per m²", "labor_rate_per_hour": 250, "labor_productivity": 2.5},
        "IfcFooting": {"unit_rate": 9500, "rate_unit": "per m³", "labor_rate_per_hour": 300, "labor_productivity": 1.0},
        "IfcDoor": {"unit_rate": 8500, "rate_unit": "per m²", "labor_rate_per_hour": 400, "labor_productivity": 0.3},
        "IfcWindow": {"unit_rate": 12000, "rate_unit": "per m²", "labor_rate_per_hour": 400, "labor_productivity": 0.25},
        "IfcStair": {"unit_rate": 15000, "rate_unit": "per m³", "labor_rate_per_hour": 400, "labor_productivity": 0.5},
        "IfcRoof": {"unit_rate": 11000, "rate_unit": "per m³", "labor_rate_per_hour": 350, "labor_productivity": 0.9},
        "IfcRailing": {"unit_rate": 3500, "rate_unit": "per m", "labor_rate_per_hour": 300, "labor_productivity": 1.5},
        "IfcCurtainWall": {"unit_rate": 18000, "rate_unit": "per m²", "labor_rate_per_hour": 500, "labor_productivity": 0.4},
    }

    rate = DEFAULT_RATES.get(ifc_type, {
        "unit_rate": 5000, "rate_unit": "per m²",
        "labor_rate_per_hour": 250, "labor_productivity": 1.0,
    })

    # Material adjustments
    if "Steel" in material or "Structural Steel" in material:
        rate["unit_rate"] = int(rate["unit_rate"] * 1.8)
        rate["labor_productivity"] *= 0.7
    elif "Precast" in material:
        rate["unit_rate"] = int(rate["unit_rate"] * 1.3)
        rate["labor_productivity"] *= 1.5  # Faster installation

    return rate


def _load_cost_rates() -> dict:
    """Load cost rate database from JSON file."""
    settings = get_settings()
    rate_file = settings.data_dir / "cost_database" / "rates.json"

    if rate_file.exists():
        try:
            with open(rate_file, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load rates.json | error={e}")

    logger.info("Using default built-in rates (rates.json not found)")
    return {}
