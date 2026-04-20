"""
API Router Configuration
-------------------------
Main router that aggregates all endpoint modules.
"""

from fastapi import APIRouter
from app.api.endpoints.prediction import router as prediction_router
from app.api.endpoints.scheduling import router as scheduling_router
from app.api.endpoints.reports import router as reports_router
from app.api.endpoints.material_rates import router as material_rates_router
from app.api.endpoints.eda import router as eda_router

api_router = APIRouter(prefix="/api/v1")

# IFC endpoints are registered directly below
# Prediction, Scheduling, Reports are imported from their modules
api_router.include_router(prediction_router, tags=["Predictions"])
api_router.include_router(scheduling_router, tags=["Scheduling"])
api_router.include_router(reports_router, tags=["Reports"])
api_router.include_router(material_rates_router, tags=["Materials"])
api_router.include_router(eda_router, tags=["Data Science"])

# ─── IFC endpoints defined inline for clean imports ────────────────
import pandas as pd
import io
from fastapi import UploadFile, File, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.db import get_db
from app.db.crud import (
    create_project, update_project_status, get_project,
    bulk_create_elements, get_project_elements, list_projects as db_list_projects
)
from app.utils.file_handler import save_upload_file
from app.core import parse_ifc_file
from app.core.quantity_takeoff import compute_qto
from app.core.synthetic_data import generate_synthetic_bim_data
from app.db.tables import BIMElement
from app.models import IFCUploadResponse, ExtractDataResponse, BIMElementSchema
from app.utils import get_logger

logger = get_logger("api.ifc")


@api_router.post("/upload-ifc", response_model=IFCUploadResponse, tags=["IFC / BIM Data"])
async def upload_ifc(
    file: UploadFile = File(..., description="IFC BIM file (.ifc or .ifczip)"),
    project_name: str = Query(default=None, description="Optional project name"),
    db: Session = Depends(get_db),
):
    """Upload an IFC file for a new project."""
    logger.info(f"IFC upload initiated | file={file.filename}")
    file_info = await save_upload_file(file)
    name = project_name or file.filename.replace(".ifc", "").replace(".ifczip", "")
    project = create_project(
        db=db, name=name, ifc_filename=file.filename,
        file_path=file_info["file_path"], file_size_mb=file_info["file_size_mb"],
    )
    return IFCUploadResponse(
        project_id=project.id, filename=file.filename,
        file_size_mb=file_info["file_size_mb"], status="uploaded",
        message=f"IFC file uploaded successfully. Project ID: {project.id}",
    )


def _parse_and_store(project, use_synthetic: bool, db: Session, project_id: str):
    if use_synthetic:
        elements = generate_synthetic_bim_data(project_id, seed=42)
    else:
        try:
            elements = parse_ifc_file(project.file_path, project_id)
        except Exception:
            elements = generate_synthetic_bim_data(project_id, seed=42)

    elements = compute_qto(elements)
    # Clear existing elements if reprasing
    db.query(BIMElement).filter(BIMElement.project_id == project_id).delete()
    bulk_create_elements(db, elements)
    update_project_status(db, project_id, "parsed")
    return elements


@api_router.get("/extract-data/{project_id}", response_model=ExtractDataResponse, tags=["IFC / BIM Data"])
async def extract_data(
    project_id: str,
    use_synthetic: bool = Query(default=False, description="Use synthetic data for demo"),
    db: Session = Depends(get_db),
):
    """Extract BIM data from an uploaded IFC file."""
    project = get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")

    if project.status == "parsed" and not use_synthetic:
        db_elements = get_project_elements(db, project_id)
        if db_elements:
            # Reconstruct list of dicts from SQLAlchemy models
            elements = [
                {
                    "id": elem.id, "project_id": elem.project_id, "global_id": elem.global_id,
                    "ifc_type": elem.ifc_type, "element_name": elem.element_name,
                    "building": elem.building, "storey": elem.storey,
                    "storey_elevation": elem.storey_elevation, "area": elem.area,
                    "volume": elem.volume, "length": elem.length, "width": elem.width,
                    "height": elem.height, "thickness": elem.thickness,
                    "material": elem.material, "material_grade": elem.material_grade,
                }
                for elem in db_elements
            ]
            logger.info(f"Loaded {len(elements)} elements from cache for project {project_id}")
        else:
            elements = _parse_and_store(project, use_synthetic, db, project_id)
    else:
        elements = _parse_and_store(project, use_synthetic, db, project_id)

    element_types = {}
    materials_set = set()
    storeys_set = set()
    for elem in elements:
        ifc_type = elem.get("ifc_type", "Unknown")
        element_types[ifc_type] = element_types.get(ifc_type, 0) + 1
        materials_set.add(elem.get("material", "Unknown"))
        storeys_set.add(elem.get("storey", "Unknown"))

    element_schemas = [
        BIMElementSchema(
            id=e["id"], project_id=e["project_id"], global_id=e.get("global_id"),
            ifc_type=e["ifc_type"], element_name=e.get("element_name"),
            building=e.get("building"), storey=e.get("storey"),
            storey_elevation=e.get("storey_elevation"), area=e.get("area"),
            volume=e.get("volume"), length=e.get("length"), width=e.get("width"),
            height=e.get("height"), thickness=e.get("thickness"),
            material=e.get("material"), material_grade=e.get("material_grade"),
        )
        for e in elements
    ]

    return ExtractDataResponse(
        project_id=project_id, total_elements=len(elements),
        element_types=element_types, materials=sorted(materials_set),
        storeys=sorted(storeys_set), elements=element_schemas, status="parsed",
    )


@api_router.get("/projects", tags=["IFC / BIM Data"])
async def list_all_projects(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    """List all projects."""
    projects = db_list_projects(db, skip=skip, limit=limit)
    return {
        "projects": [{
            "id": p.id, "name": p.name, "ifc_filename": p.ifc_filename,
            "status": p.status, "uploaded_at": p.uploaded_at.isoformat() if p.uploaded_at else None,
            "file_size_mb": p.file_size_mb,
        } for p in projects],
        "total": len(projects),
    }

@api_router.get("/export-data/{project_id}", tags=["IFC / BIM Data"])
async def export_data(
    project_id: str,
    format: str = Query("csv", description="Export format: csv or parquet"),
    db: Session = Depends(get_db)
):
    """Export extracted BIM data to CSV or Parquet format."""
    project = get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")

    db_elements = get_project_elements(db, project_id)
    if not db_elements:
        raise HTTPException(status_code=404, detail="No extracted elements found for this project")

    # Reconstruct list of dicts from SQLAlchemy models
    data = [
        {
            "id": elem.id, "ifc_type": elem.ifc_type, "element_name": elem.element_name,
            "building": elem.building, "storey": elem.storey,
            "storey_elevation": elem.storey_elevation, "area": elem.area,
            "volume": elem.volume, "length": elem.length, "width": elem.width,
            "height": elem.height, "thickness": elem.thickness,
            "material": elem.material, "material_grade": elem.material_grade,
        }
        for elem in db_elements
    ]
    df = pd.DataFrame(data)
    
    if format.lower() == "parquet":
        buffer = io.BytesIO()
        df.to_parquet(buffer, index=False)
        buffer.seek(0)
        return StreamingResponse(
            buffer,
            media_type="application/octet-stream",
            headers={"Content-Disposition": f"attachment; filename=project_{project_id}.parquet"}
        )
    else:  # default to csv
        buffer = io.StringIO()
        df.to_csv(buffer, index=False)
        buffer.seek(0)
        return StreamingResponse(
            iter([buffer.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=project_{project_id}.csv"}
        )
