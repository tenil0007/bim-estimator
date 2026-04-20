"""
Pydantic Models - IFC Data
--------------------------
Request/Response schemas for IFC-related endpoints.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class IFCUploadResponse(BaseModel):
    """Response after uploading an IFC file."""
    project_id: str
    filename: str
    file_size_mb: float
    status: str = "uploaded"
    message: str = "IFC file uploaded successfully"


class BIMElementSchema(BaseModel):
    """Schema for a single BIM element."""
    id: str
    project_id: str
    global_id: Optional[str] = None
    ifc_type: str
    element_name: Optional[str] = None
    building: Optional[str] = None
    storey: Optional[str] = None
    storey_elevation: Optional[float] = None
    area: Optional[float] = None
    volume: Optional[float] = None
    length: Optional[float] = None
    width: Optional[float] = None
    height: Optional[float] = None
    thickness: Optional[float] = None
    material: Optional[str] = None
    material_grade: Optional[str] = None

    class Config:
        from_attributes = True


class ExtractDataResponse(BaseModel):
    """Response after extracting BIM data from IFC."""
    project_id: str
    total_elements: int
    element_types: dict[str, int]
    materials: list[str]
    storeys: list[str]
    elements: list[BIMElementSchema]
    status: str = "parsed"


class ProjectSchema(BaseModel):
    """Schema for project metadata."""
    id: str
    name: str
    ifc_filename: str
    file_size_mb: Optional[float] = None
    status: str
    uploaded_at: datetime
    element_count: int = 0

    class Config:
        from_attributes = True
