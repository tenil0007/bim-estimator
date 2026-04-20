"""
Custom Validators
-----------------
Validation utilities for BIM data, model inputs, and API parameters.
"""

from typing import Optional


def validate_element_type(element_type: str) -> bool:
    """Validate IFC element type against supported types."""
    SUPPORTED_TYPES = {
        "IfcWall", "IfcSlab", "IfcBeam", "IfcColumn",
        "IfcDoor", "IfcWindow", "IfcRoof", "IfcStair",
        "IfcRailing", "IfcCurtainWall", "IfcFooting",
        "IfcPile", "IfcPlate", "IfcMember"
    }
    return element_type in SUPPORTED_TYPES


def validate_material(material: str) -> bool:
    """Validate material name against known construction materials."""
    KNOWN_MATERIALS = {
        "Concrete", "Reinforced Concrete", "Steel", "Structural Steel",
        "Brick", "Timber", "Glass", "Aluminum", "Stone",
        "Masonry", "Precast Concrete", "Composite",
        "Gypsum", "Plywood", "Cement Mortar"
    }
    return material in KNOWN_MATERIALS


def validate_quantity(value: float, quantity_type: str) -> bool:
    """Validate that a quantity value is physically reasonable."""
    RANGES = {
        "area": (0.01, 10000.0),      # m²
        "volume": (0.001, 5000.0),     # m³
        "length": (0.01, 500.0),       # m
        "weight": (0.1, 500000.0),     # kg
        "thickness": (0.001, 5.0),     # m
    }
    min_val, max_val = RANGES.get(quantity_type, (0, float("inf")))
    return min_val <= value <= max_val


def validate_model_type(model_type: str) -> bool:
    """Validate ML model type selection."""
    return model_type in {"random_forest", "xgboost"}
