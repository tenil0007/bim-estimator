"""
Pydantic Models - Scheduling
-----------------------------
Request/Response schemas for scheduling endpoints.
"""

from pydantic import BaseModel, Field
from typing import Optional


class DependencyRule(BaseModel):
    """A dependency between two activities."""
    predecessor: str
    successor: str
    lag_days: float = 0.0  # Finish-to-Start lag


class ScheduleRequest(BaseModel):
    """Request body for schedule generation."""
    project_id: str
    custom_dependencies: Optional[list[DependencyRule]] = None
    working_hours_per_day: float = Field(default=8.0, ge=1.0, le=24.0)
    crew_size_multiplier: float = Field(
        default=1.0, ge=0.5, le=3.0,
        description="Multiply default crew size (for scenario analysis)"
    )


class GanttItem(BaseModel):
    """A single item for Gantt chart rendering."""
    id: str
    name: str
    element_type: Optional[str] = None
    start_day: float
    end_day: float
    duration: float
    is_critical: bool
    slack: float
    predecessors: list[str] = []
    progress: float = 0.0  # 0-100%


class ScheduleResponse(BaseModel):
    """Response from schedule generation endpoint."""
    project_id: str
    total_duration_days: float
    critical_path: list[str]  # Activity names on critical path
    critical_path_duration: float
    gantt_data: list[GanttItem]
    summary: dict[str, float]  # stats like avg_slack, num_critical, etc.


class ReportRequest(BaseModel):
    """Request body for PDF report generation."""
    project_id: str
    include_cost: bool = True
    include_time: bool = True
    include_schedule: bool = True
    include_shap: bool = True
    report_title: Optional[str] = "BIM Cost & Time Estimation Report"
    company_name: Optional[str] = "Larsen & Toubro Limited"
