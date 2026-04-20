"""
File Handler Utility
--------------------
Handles file upload, validation, and storage for IFC files
and generated reports.
"""

import os
import uuid
import shutil
from pathlib import Path
from fastapi import UploadFile, HTTPException
from app.config import get_settings
from app.utils import get_logger

logger = get_logger("file_handler")

ALLOWED_EXTENSIONS = {".ifc", ".ifczip"}
MAX_SIZE_BYTES = get_settings().max_upload_size_mb * 1024 * 1024


async def save_upload_file(upload_file: UploadFile, project_id: str = None) -> dict:
    """
    Save an uploaded IFC file to the upload directory.

    Args:
        upload_file: FastAPI UploadFile object
        project_id: Optional project identifier

    Returns:
        dict with file metadata (path, size, project_id)
    """
    # Validate extension
    file_ext = Path(upload_file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type '{file_ext}'. Allowed: {ALLOWED_EXTENSIONS}"
        )

    # Generate project ID if not provided
    if not project_id:
        project_id = str(uuid.uuid4())[:8]

    # Create project directory
    settings = get_settings()
    project_dir = settings.upload_path / project_id
    project_dir.mkdir(parents=True, exist_ok=True)

    # Save file
    file_path = project_dir / upload_file.filename
    try:
        contents = await upload_file.read()

        # Validate size
        if len(contents) > MAX_SIZE_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Max size: {settings.max_upload_size_mb}MB"
            )

        with open(file_path, "wb") as f:
            f.write(contents)

        file_size = len(contents)
        logger.info(
            f"File saved | project={project_id} | file={upload_file.filename} | size={file_size}"
        )

        return {
            "project_id": project_id,
            "filename": upload_file.filename,
            "file_path": str(file_path),
            "file_size_bytes": file_size,
            "file_size_mb": round(file_size / (1024 * 1024), 2),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File upload failed | error={e}")
        raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")


def get_project_ifc_path(project_id: str) -> Path:
    """Get the IFC file path for a given project."""
    settings = get_settings()
    project_dir = settings.upload_path / project_id

    if not project_dir.exists():
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")

    ifc_files = list(project_dir.glob("*.ifc")) + list(project_dir.glob("*.ifczip"))
    if not ifc_files:
        raise HTTPException(
            status_code=404,
            detail=f"No IFC file found for project '{project_id}'"
        )

    return ifc_files[0]


def cleanup_project(project_id: str):
    """Remove all files for a given project."""
    settings = get_settings()
    project_dir = settings.upload_path / project_id
    if project_dir.exists():
        shutil.rmtree(project_dir)
        logger.info(f"Project cleaned up | project={project_id}")
