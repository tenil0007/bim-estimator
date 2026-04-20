"""
IFC Parser Module
-----------------
Extracts structural elements, geometry, materials, and spatial hierarchy
from Industry Foundation Classes (IFC) BIM models using IfcOpenShell.

Supports: IFC2x3, IFC4
Elements: IfcWall, IfcSlab, IfcBeam, IfcColumn, IfcDoor, IfcWindow,
          IfcRoof, IfcStair, IfcRailing, IfcFooting, IfcCurtainWall
"""

import uuid
from pathlib import Path
from typing import Optional
from app.utils import get_logger
from app.models import BIMElementSchema
from pydantic import ValidationError

logger = get_logger("ifc_parser")

# Supported IFC element types for extraction
SUPPORTED_IFC_TYPES = [
    "IfcWall", "IfcWallStandardCase",
    "IfcSlab", "IfcSlabStandardCase",
    "IfcBeam", "IfcBeamStandardCase",
    "IfcColumn", "IfcColumnStandardCase",
    "IfcDoor", "IfcDoorStandardCase",
    "IfcWindow", "IfcWindowStandardCase",
    "IfcRoof",
    "IfcStair", "IfcStairFlight",
    "IfcRailing",
    "IfcFooting",
    "IfcCurtainWall",
    "IfcPlate",
    "IfcMember",
    "IfcPile",
]

# Map standard-case variants to base type
TYPE_NORMALIZATION = {
    "IfcWallStandardCase": "IfcWall",
    "IfcSlabStandardCase": "IfcSlab",
    "IfcBeamStandardCase": "IfcBeam",
    "IfcColumnStandardCase": "IfcColumn",
    "IfcDoorStandardCase": "IfcDoor",
    "IfcWindowStandardCase": "IfcWindow",
}


def parse_ifc_file(file_path: str, project_id: str) -> list[dict]:
    """
    Parse an IFC file and extract structured BIM element data.

    Args:
        file_path: Path to the .ifc file
        project_id: Project identifier for associating elements

    Returns:
        List of element dictionaries with geometry, materials, and spatial info
    """
    try:
        import ifcopenshell
        import ifcopenshell.util.element as element_util
        import ifcopenshell.util.placement as placement_util
    except ImportError:
        logger.warning(
            "IfcOpenShell not installed. Using synthetic data generator as fallback."
        )
        from app.core.synthetic_data import generate_synthetic_bim_data
        return generate_synthetic_bim_data(project_id)

    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"IFC file not found: {file_path}")

    # Preliminary structure validation
    if file_path.stat().st_size == 0:
        raise ValueError(f"IFC file is empty: {file_path}")

    logger.info(f"Parsing IFC file | path={file_path} | project={project_id}")
    
    try:
        ifc_file = ifcopenshell.open(str(file_path))
    except Exception as e:
        logger.error(f"Failed to open IFC file. Invalid structure or corrupted file: {e}")
        raise ValueError(f"Invalid or corrupted IFC file: {e}")
    
    # Basic schema check
    if not ifc_file.schema:
        logger.warning(f"IFC file is missing a schema definition.")
    
    elements = []
    schema = ifc_file.schema

    for ifc_type in SUPPORTED_IFC_TYPES:
        try:
            ifc_elements = ifc_file.by_type(ifc_type)
        except Exception:
            continue

        for ifc_elem in ifc_elements:
            raw_element = _extract_element_data(ifc_file, ifc_elem, project_id, schema)
            if raw_element:
                try:
                    # Pydantic schema validation
                    validated_element = BIMElementSchema(**raw_element)
                    elements.append(validated_element.model_dump())
                except ValidationError as e:
                    logger.debug(f"Pydantic validation failed for element {raw_element.get('id')} | error={e}")

    logger.info(f"IFC parsing complete | elements={len(elements)} | project={project_id}")
    return elements

def _extract_element_data(ifc_file, ifc_elem, project_id: str, schema: str) -> Optional[dict]:
    """Extract all relevant data from a single IFC element."""
    try:
        ifc_type = ifc_elem.is_a()
        normalized_type = TYPE_NORMALIZATION.get(ifc_type, ifc_type)

        # Basic info
        element = {
            "id": str(uuid.uuid4()),
            "project_id": project_id,
            "global_id": getattr(ifc_elem, "GlobalId", None),
            "ifc_type": normalized_type,
            "element_name": getattr(ifc_elem, "Name", None) or f"{normalized_type}_{ifc_elem.id()}",
            "description": getattr(ifc_elem, "Description", None),
        }

        # Spatial hierarchy (Building → Storey)
        _extract_spatial_info(ifc_elem, element)

        # Quantities (Area, Volume, Length, etc.)
        _extract_quantities(ifc_elem, element)

        # Material
        _extract_material(ifc_elem, element)

        return element

    except Exception as e:
        logger.warning(f"Failed to extract element {getattr(ifc_elem, 'id', '?')} | error={e}")
        return None


def _extract_spatial_info(ifc_elem, element: dict):
    """Extract building and storey information from spatial containment."""
    try:
        # Navigate spatial containment: Element → Space → Storey → Building
        for rel in getattr(ifc_elem, "ContainedInStructure", []):
            structure = rel.RelatingStructure
            if structure.is_a("IfcBuildingStorey"):
                element["storey"] = getattr(structure, "Name", "Unknown Storey")
                element["storey_elevation"] = getattr(structure, "Elevation", None)
                # Go up to building
                for parent_rel in getattr(structure, "Decomposes", []):
                    building = parent_rel.RelatingObject
                    if building.is_a("IfcBuilding"):
                        element["building"] = getattr(building, "Name", "Main Building")
            elif structure.is_a("IfcBuilding"):
                element["building"] = getattr(structure, "Name", "Main Building")
    except Exception:
        element["storey"] = "Unknown"
        element["building"] = "Unknown"


def _extract_quantities(ifc_elem, element: dict):
    """
    Extract geometric quantities from IfcElementQuantity property sets.
    Handles both IFC2x3 and IFC4 schemas.
    """
    try:
        for definition in getattr(ifc_elem, "IsDefinedBy", []):
            if not hasattr(definition, "RelatingPropertyDefinition"):
                continue

            prop_def = definition.RelatingPropertyDefinition

            if prop_def.is_a("IfcElementQuantity"):
                for quantity in prop_def.Quantities:
                    q_name = quantity.Name.lower() if quantity.Name else ""

                    if quantity.is_a("IfcQuantityArea"):
                        value = quantity.AreaValue
                        if "net" in q_name or "gross" in q_name or "area" in q_name:
                            element["area"] = round(float(value), 4)

                    elif quantity.is_a("IfcQuantityVolume"):
                        value = quantity.VolumeValue
                        if "net" in q_name or "gross" in q_name or "volume" in q_name:
                            element["volume"] = round(float(value), 4)

                    elif quantity.is_a("IfcQuantityLength"):
                        value = quantity.LengthValue
                        if "length" in q_name or "height" in q_name:
                            if "height" in q_name:
                                element["height"] = round(float(value), 4)
                            else:
                                element["length"] = round(float(value), 4)

                        if "width" in q_name:
                            element["width"] = round(float(value), 4)
                        if "thickness" in q_name or "depth" in q_name:
                            element["thickness"] = round(float(value), 4)
                        if "perimeter" in q_name:
                            element["perimeter"] = round(float(value), 4)

                    elif quantity.is_a("IfcQuantityWeight"):
                        element["weight"] = round(float(quantity.WeightValue), 2)

    except Exception as e:
        logger.debug(f"Quantity extraction partial failure | elem={element.get('element_name')} | {e}")


def _extract_material(ifc_elem, element: dict):
    """Extract material information from IFC material associations."""
    try:
        for rel in getattr(ifc_elem, "HasAssociations", []):
            if rel.is_a("IfcRelAssociatesMaterial"):
                material_select = rel.RelatingMaterial

                if material_select.is_a("IfcMaterial"):
                    element["material"] = material_select.Name
                    element["material_grade"] = getattr(material_select, "Category", None)

                elif material_select.is_a("IfcMaterialLayerSetUsage"):
                    layer_set = material_select.ForLayerSet
                    if layer_set and layer_set.MaterialLayers:
                        # Use the primary (thickest) layer material
                        primary_layer = max(
                            layer_set.MaterialLayers,
                            key=lambda l: getattr(l, "LayerThickness", 0)
                        )
                        if primary_layer.Material:
                            element["material"] = primary_layer.Material.Name
                            element["material_grade"] = getattr(
                                primary_layer.Material, "Category", None
                            )

                elif material_select.is_a("IfcMaterialConstituentSet"):
                    if material_select.MaterialConstituents:
                        constituent = material_select.MaterialConstituents[0]
                        if constituent.Material:
                            element["material"] = constituent.Material.Name

                elif material_select.is_a("IfcMaterialProfileSetUsage"):
                    profile_set = material_select.ForProfileSet
                    if profile_set and profile_set.MaterialProfiles:
                        profile = profile_set.MaterialProfiles[0]
                        if profile.Material:
                            element["material"] = profile.Material.Name

    except Exception as e:
        logger.debug(f"Material extraction failed | elem={element.get('element_name')} | {e}")
        element["material"] = "Unknown"
