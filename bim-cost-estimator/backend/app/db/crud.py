"""
CRUD Operations
---------------
Database operations for Projects, BIM Elements, and Schedule Activities.
"""

from typing import Optional
from sqlalchemy.orm import Session
from app.db.tables import Project, BIMElement, ScheduleActivity
from app.utils import get_logger

logger = get_logger("crud")


# ─── Project Operations ──────────────────────────────────────────

def create_project(db: Session, name: str, ifc_filename: str,
                   file_path: str = None, file_size_mb: float = None) -> Project:
    """Create a new project record."""
    project = Project(
        name=name,
        ifc_filename=ifc_filename,
        file_path=file_path,
        file_size_mb=file_size_mb,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    logger.info(f"Project created | id={project.id} | name={name}")
    return project


def get_project(db: Session, project_id: str) -> Optional[Project]:
    """Get a project by ID."""
    return db.query(Project).filter(Project.id == project_id).first()


def update_project_status(db: Session, project_id: str, status: str) -> Optional[Project]:
    """Update project status."""
    project = get_project(db, project_id)
    if project:
        project.status = status
        db.commit()
        db.refresh(project)
    return project


def list_projects(db: Session, skip: int = 0, limit: int = 100) -> list[Project]:
    """List all projects with pagination."""
    return db.query(Project).offset(skip).limit(limit).all()


def delete_project(db: Session, project_id: str) -> bool:
    """Delete a project and all associated data."""
    project = get_project(db, project_id)
    if project:
        db.delete(project)
        db.commit()
        logger.info(f"Project deleted | id={project_id}")
        return True
    return False


# ─── BIM Element Operations ──────────────────────────────────────

def bulk_create_elements(db: Session, elements: list[dict]) -> int:
    """Bulk insert BIM elements. Filters out keys not in the table schema."""
    valid_columns = {c.key for c in BIMElement.__table__.columns}
    db_elements = [
        BIMElement(**{k: v for k, v in elem.items() if k in valid_columns})
        for elem in elements
    ]
    db.add_all(db_elements)
    db.commit()
    logger.info(f"Bulk inserted {len(db_elements)} BIM elements")
    return len(db_elements)


def get_project_elements(db: Session, project_id: str,
                         element_type: str = None,
                         material: str = None) -> list[BIMElement]:
    """Get elements for a project with optional filtering."""
    query = db.query(BIMElement).filter(BIMElement.project_id == project_id)

    if element_type:
        query = query.filter(BIMElement.ifc_type == element_type)
    if material:
        query = query.filter(BIMElement.material == material)

    return query.all()


def update_element_predictions(db: Session, element_id: str,
                                predicted_cost: float = None,
                                predicted_duration: float = None,
                                cost_model: str = None,
                                time_model: str = None) -> Optional[BIMElement]:
    """Update prediction values for an element."""
    element = db.query(BIMElement).filter(BIMElement.id == element_id).first()
    if element:
        if predicted_cost is not None:
            element.predicted_cost = predicted_cost
            element.cost_model_used = cost_model
        if predicted_duration is not None:
            element.predicted_duration = predicted_duration
            element.time_model_used = time_model
        db.commit()
        db.refresh(element)
    return element


# ─── Schedule Operations ─────────────────────────────────────────

def bulk_create_activities(db: Session, activities: list[dict]) -> int:
    """Bulk insert schedule activities."""
    db_activities = [ScheduleActivity(**act) for act in activities]
    db.add_all(db_activities)
    db.commit()
    logger.info(f"Bulk inserted {len(db_activities)} schedule activities")
    return len(db_activities)


def get_project_schedule(db: Session, project_id: str) -> list[ScheduleActivity]:
    """Get all schedule activities for a project."""
    return (
        db.query(ScheduleActivity)
        .filter(ScheduleActivity.project_id == project_id)
        .order_by(ScheduleActivity.early_start)
        .all()
    )


def get_critical_path(db: Session, project_id: str) -> list[ScheduleActivity]:
    """Get critical path activities for a project."""
    return (
        db.query(ScheduleActivity)
        .filter(
            ScheduleActivity.project_id == project_id,
            ScheduleActivity.is_critical == True
        )
        .order_by(ScheduleActivity.early_start)
        .all()
    )
