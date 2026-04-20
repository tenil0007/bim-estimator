"""
Database Table Models
---------------------
SQLAlchemy ORM models representing the database schema.
Maps to the ER diagram in the architecture document.
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, Boolean, DateTime, ForeignKey, Integer, Text
from sqlalchemy.orm import relationship
from app.db import Base


def generate_uuid():
    return str(uuid.uuid4())[:8]


class Project(Base):
    """Represents a BIM project uploaded by the user."""
    __tablename__ = "projects"

    id = Column(String(8), primary_key=True, default=generate_uuid)
    name = Column(String(256), nullable=False)
    ifc_filename = Column(String(512), nullable=False)
    file_path = Column(String(1024), nullable=True)
    file_size_mb = Column(Float, nullable=True)
    status = Column(String(32), default="uploaded")  # uploaded, parsed, predicted, scheduled
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    elements = relationship("BIMElement", back_populates="project", cascade="all, delete-orphan")
    schedule_activities = relationship("ScheduleActivity", back_populates="project", cascade="all, delete-orphan")


class BIMElement(Base):
    """Represents an individual BIM element extracted from IFC."""
    __tablename__ = "bim_elements"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(8), ForeignKey("projects.id"), nullable=False)
    global_id = Column(String(64), nullable=True)  # IFC GlobalId

    # Element classification
    ifc_type = Column(String(64), nullable=False)  # IfcWall, IfcSlab, etc.
    element_name = Column(String(256), nullable=True)
    description = Column(Text, nullable=True)

    # Spatial hierarchy
    building = Column(String(256), nullable=True)
    storey = Column(String(256), nullable=True)
    storey_elevation = Column(Float, nullable=True)

    # Geometry / Quantities
    area = Column(Float, nullable=True)        # m²
    volume = Column(Float, nullable=True)       # m³
    length = Column(Float, nullable=True)       # m
    width = Column(Float, nullable=True)        # m
    height = Column(Float, nullable=True)       # m
    thickness = Column(Float, nullable=True)    # m
    perimeter = Column(Float, nullable=True)    # m
    weight = Column(Float, nullable=True)       # kg

    # Material
    material = Column(String(256), nullable=True)
    material_grade = Column(String(128), nullable=True)

    # Predictions
    predicted_cost = Column(Float, nullable=True)
    predicted_duration = Column(Float, nullable=True)  # hours
    cost_model_used = Column(String(32), nullable=True)
    time_model_used = Column(String(32), nullable=True)
    prediction_confidence = Column(Float, nullable=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    project = relationship("Project", back_populates="elements")


class ScheduleActivity(Base):
    """Represents a scheduled construction activity from CPM analysis."""
    __tablename__ = "schedule_activities"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(8), ForeignKey("projects.id"), nullable=False)

    # Activity details
    activity_name = Column(String(256), nullable=False)
    element_type = Column(String(64), nullable=True)
    description = Column(Text, nullable=True)

    # Scheduling
    duration = Column(Float, nullable=False)        # days
    early_start = Column(Float, nullable=True)      # day number
    early_finish = Column(Float, nullable=True)
    late_start = Column(Float, nullable=True)
    late_finish = Column(Float, nullable=True)
    total_float = Column(Float, nullable=True)       # slack in days
    free_float = Column(Float, nullable=True)
    is_critical = Column(Boolean, default=False)

    # Dependencies
    predecessors = Column(Text, nullable=True)  # JSON list of predecessor activity IDs
    successors = Column(Text, nullable=True)    # JSON list of successor activity IDs

    # Resources
    labor_hours = Column(Float, nullable=True)
    crew_size = Column(Integer, nullable=True)
    equipment = Column(String(256), nullable=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    project = relationship("Project", back_populates="schedule_activities")
