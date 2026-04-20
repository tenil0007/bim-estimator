"""
Synthetic BIM Data Generator
-----------------------------
Generates realistic construction BIM data for development and testing
when real IFC files are not available. Data mirrors actual L&T project
characteristics: Indian construction standards, real materials, proper
element dimensions, and spatial hierarchy.

This module is used as a FALLBACK when IfcOpenShell is not installed
or when no IFC file is provided. In production, real IFC parsing is preferred.
"""

import uuid
import random
import numpy as np
from typing import Optional
from app.utils import get_logger

logger = get_logger("synthetic_data")

# ─── Realistic Construction Parameters (Indian Standards / L&T) ─────

BUILDINGS = ["Tower A", "Tower B", "Main Block", "Annexe Building"]

STOREYS = {
    "Foundation": -3.0,
    "Basement 2": -6.0,
    "Basement 1": -3.0,
    "Ground Floor": 0.0,
    "First Floor": 3.5,
    "Second Floor": 7.0,
    "Third Floor": 10.5,
    "Fourth Floor": 14.0,
    "Fifth Floor": 17.5,
    "Sixth Floor": 21.0,
    "Seventh Floor": 24.5,
    "Eighth Floor": 28.0,
    "Terrace": 31.5,
}

# Element configurations with realistic Indian construction parameters
ELEMENT_CONFIGS = {
    "IfcColumn": {
        "materials": [
            ("Reinforced Concrete", "M40", 0.55),
            ("Reinforced Concrete", "M30", 0.30),
            ("Structural Steel", "Fe500", 0.15),
        ],
        "count_per_storey": (8, 20),
        "dimensions": {
            "length": (0.3, 0.9),     # cross-section (m)
            "width": (0.3, 0.9),
            "height": (3.0, 4.5),      # storey height
            "area": None,              # computed from cross section
            "volume": None,            # computed from dimensions
        },
    },
    "IfcBeam": {
        "materials": [
            ("Reinforced Concrete", "M30", 0.60),
            ("Reinforced Concrete", "M40", 0.25),
            ("Structural Steel", "Fe500", 0.15),
        ],
        "count_per_storey": (12, 30),
        "dimensions": {
            "length": (3.0, 9.0),
            "width": (0.23, 0.45),
            "height": (0.30, 0.75),
            "area": None,
            "volume": None,
        },
    },
    "IfcSlab": {
        "materials": [
            ("Reinforced Concrete", "M30", 0.65),
            ("Reinforced Concrete", "M25", 0.25),
            ("Precast Concrete", "M40", 0.10),
        ],
        "count_per_storey": (2, 6),
        "dimensions": {
            "area": (20.0, 200.0),
            "thickness": (0.125, 0.25),
            "volume": None,  # area * thickness
        },
    },
    "IfcWall": {
        "materials": [
            ("Brick", None, 0.35),
            ("Reinforced Concrete", "M25", 0.25),
            ("Concrete Block", None, 0.20),
            ("Masonry", None, 0.15),
            ("Gypsum", None, 0.05),
        ],
        "count_per_storey": (10, 35),
        "dimensions": {
            "length": (1.5, 8.0),
            "height": (2.8, 4.0),
            "thickness": (0.115, 0.30),
            "area": None,      # length * height
            "volume": None,    # area * thickness
        },
    },
    "IfcDoor": {
        "materials": [
            ("Timber", None, 0.40),
            ("Aluminum", None, 0.30),
            ("Steel", None, 0.20),
            ("Glass", None, 0.10),
        ],
        "count_per_storey": (5, 15),
        "dimensions": {
            "width": (0.8, 1.2),
            "height": (2.1, 2.4),
            "area": None,
        },
    },
    "IfcWindow": {
        "materials": [
            ("Glass", None, 0.40),
            ("Aluminum", None, 0.35),
            ("UPVC", None, 0.25),
        ],
        "count_per_storey": (6, 20),
        "dimensions": {
            "width": (0.6, 2.4),
            "height": (0.6, 1.8),
            "area": None,
        },
    },
    "IfcStair": {
        "materials": [
            ("Reinforced Concrete", "M25", 0.70),
            ("Steel", None, 0.20),
            ("Timber", None, 0.10),
        ],
        "count_per_storey": (1, 3),
        "dimensions": {
            "length": (3.0, 6.0),
            "width": (1.0, 1.5),
            "height": (3.0, 4.0),
            "volume": None,
        },
    },
    "IfcRoof": {
        "materials": [
            ("Reinforced Concrete", "M25", 0.50),
            ("Steel", None, 0.30),
            ("Composite", None, 0.20),
        ],
        "count_per_storey": (0, 0),  # Only on terrace
        "dimensions": {
            "area": (50.0, 500.0),
            "thickness": (0.15, 0.30),
            "volume": None,
        },
    },
    "IfcFooting": {
        "materials": [
            ("Reinforced Concrete", "M30", 0.70),
            ("Reinforced Concrete", "M40", 0.30),
        ],
        "count_per_storey": (0, 0),  # Only in foundation
        "dimensions": {
            "length": (1.5, 4.0),
            "width": (1.5, 4.0),
            "height": (0.5, 1.5),
            "volume": None,
        },
    },
    "IfcRailing": {
        "materials": [
            ("Steel", None, 0.50),
            ("Aluminum", None, 0.30),
            ("Glass", None, 0.20),
        ],
        "count_per_storey": (2, 6),
        "dimensions": {
            "length": (2.0, 12.0),
            "height": (0.9, 1.2),
        },
    },
}

# ─── Material Density (kg/m³) for weight calculation ──────────────
MATERIAL_DENSITY = {
    "Reinforced Concrete": 2500,
    "Concrete": 2300,
    "Precast Concrete": 2400,
    "Concrete Block": 2000,
    "Brick": 1800,
    "Masonry": 1900,
    "Structural Steel": 7850,
    "Steel": 7850,
    "Timber": 600,
    "Glass": 2500,
    "Aluminum": 2700,
    "UPVC": 1400,
    "Gypsum": 1100,
    "Composite": 2000,
}


def generate_synthetic_bim_data(
    project_id: str,
    num_storeys: int = None,
    building_name: str = None,
    seed: int = None,
) -> list[dict]:
    """
    Generate realistic synthetic BIM data mimicking a real IFC extraction.

    Args:
        project_id: Project identifier
        num_storeys: Number of storeys (default: random 5-13)
        building_name: Building name (default: random from list)
        seed: Random seed for reproducibility

    Returns:
        List of BIM element dictionaries matching IFC parser output format
    """
    if seed is not None:
        random.seed(seed)
        np.random.seed(seed)

    if num_storeys is None:
        num_storeys = random.randint(5, 13)

    if building_name is None:
        building_name = random.choice(BUILDINGS)

    # Select storeys
    storey_names = list(STOREYS.keys())
    # Always include Foundation and Ground Floor
    selected_storeys = ["Foundation", "Ground Floor"]
    upper_storeys = [s for s in storey_names if s not in selected_storeys and s != "Terrace"]
    num_upper = min(num_storeys - 2, len(upper_storeys))
    selected_storeys.extend(sorted(upper_storeys[:num_upper], key=lambda s: STOREYS[s]))
    selected_storeys.append("Terrace")

    logger.info(
        f"Generating synthetic data | project={project_id} | "
        f"building={building_name} | storeys={len(selected_storeys)}"
    )

    elements = []

    for storey_name in selected_storeys:
        storey_elevation = STOREYS[storey_name]

        for elem_type, config in ELEMENT_CONFIGS.items():
            # Determine count for this storey
            count = _get_element_count(elem_type, storey_name, config)

            for i in range(count):
                element = _generate_element(
                    project_id=project_id,
                    elem_type=elem_type,
                    config=config,
                    building=building_name,
                    storey=storey_name,
                    storey_elevation=storey_elevation,
                    index=i,
                )
                elements.append(element)

    logger.info(f"Synthetic data generated | elements={len(elements)} | project={project_id}")
    return elements


def _get_element_count(elem_type: str, storey_name: str, config: dict) -> int:
    """Determine how many elements of this type go on this storey."""
    min_count, max_count = config["count_per_storey"]

    # Special storey rules
    if elem_type == "IfcFooting" and storey_name == "Foundation":
        return random.randint(6, 20)
    elif elem_type == "IfcFooting":
        return 0

    if elem_type == "IfcRoof" and storey_name == "Terrace":
        return random.randint(1, 3)
    elif elem_type == "IfcRoof":
        return 0

    if storey_name == "Foundation":
        # Only foundation elements and columns at foundation
        if elem_type in ("IfcColumn", "IfcBeam"):
            return random.randint(min_count // 2, max_count // 2)
        elif elem_type not in ("IfcFooting",):
            return 0

    if storey_name == "Terrace":
        if elem_type in ("IfcDoor", "IfcStair"):
            return random.randint(0, 2)
        return random.randint(max(1, min_count // 2), max(2, max_count // 3))

    return random.randint(min_count, max_count)


def _generate_element(
    project_id: str,
    elem_type: str,
    config: dict,
    building: str,
    storey: str,
    storey_elevation: float,
    index: int,
) -> dict:
    """Generate a single realistic BIM element."""
    # Select material based on weighted probabilities
    material_choices = config["materials"]
    materials, grades, weights = zip(*material_choices)
    material_idx = random.choices(range(len(materials)), weights=weights, k=1)[0]
    material = materials[material_idx]
    material_grade = grades[material_idx]

    # Generate dimensions
    dims = config["dimensions"]
    element = {
        "id": str(uuid.uuid4()),
        "project_id": project_id,
        "global_id": f"{elem_type.upper()[:3]}_{uuid.uuid4().hex[:12].upper()}",
        "ifc_type": elem_type,
        "element_name": f"{elem_type.replace('Ifc', '')}_{storey.replace(' ', '')}_{index + 1:03d}",
        "description": f"{material} {elem_type.replace('Ifc', '')} at {storey}",
        "building": building,
        "storey": storey,
        "storey_elevation": storey_elevation,
        "material": material,
        "material_grade": material_grade,
    }

    # Generate realistic dimensions with some noise
    for dim_name, dim_range in dims.items():
        if dim_range is None:
            continue  # Computed field
        if isinstance(dim_range, tuple):
            low, high = dim_range
            value = round(random.uniform(low, high), 4)
            # Add slight Gaussian noise for realism
            value = round(value * np.random.normal(1.0, 0.05), 4)
            value = max(low * 0.8, value)  # Don't go too low
            element[dim_name] = value

    # Compute derived quantities
    _compute_derived_quantities(element, elem_type, material)

    return element


def _compute_derived_quantities(element: dict, elem_type: str, material: str):
    """Compute derived quantities like area, volume, weight."""
    length = element.get("length")
    width = element.get("width")
    height = element.get("height")
    thickness = element.get("thickness")
    area = element.get("area")

    # Compute area if not set
    if area is None:
        if elem_type in ("IfcWall",) and length and height:
            element["area"] = round(length * height, 4)
        elif elem_type in ("IfcDoor", "IfcWindow") and width and height:
            element["area"] = round(width * height, 4)
        elif elem_type in ("IfcColumn",) and length and width:
            element["area"] = round(length * width, 4)  # Cross-sectional area

    # Compute volume if not set
    if element.get("volume") is None:
        computed_area = element.get("area", 0)
        if elem_type in ("IfcSlab", "IfcRoof") and computed_area and thickness:
            element["volume"] = round(computed_area * thickness, 4)
        elif elem_type in ("IfcWall",) and computed_area and thickness:
            element["volume"] = round(computed_area * thickness, 4)
        elif elem_type in ("IfcColumn",) and length and width and height:
            element["volume"] = round(length * width * height, 4)
        elif elem_type in ("IfcBeam",) and length and width and height:
            element["volume"] = round(length * width * height, 4)
        elif elem_type in ("IfcFooting",) and length and width and height:
            element["volume"] = round(length * width * height, 4)
        elif elem_type in ("IfcStair",) and length and width and height:
            element["volume"] = round(length * width * height * 0.35, 4)  # Stair factor

    # Compute perimeter for walls
    if elem_type == "IfcWall" and length and element.get("perimeter") is None:
        element["perimeter"] = round(2 * (length + (thickness or 0.23)), 4)

    # Compute weight from volume and material density
    volume = element.get("volume", 0)
    if volume and volume > 0:
        density = MATERIAL_DENSITY.get(material, 2300)
        element["weight"] = round(volume * density, 2)
