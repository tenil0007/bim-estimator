"""
Scheduling Endpoints
---------------------
/schedule — Generate CPM schedule from BIM elements
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db import get_db
from app.db.crud import get_project, get_project_elements, bulk_create_activities, update_project_status
from app.core.scheduler import CPMScheduler
from app.models.schedule_models import ScheduleRequest, ScheduleResponse, GanttItem
from app.utils import get_logger

logger = get_logger("api.scheduling")
router = APIRouter()


@router.post("/schedule", response_model=ScheduleResponse)
async def generate_schedule(
    request: ScheduleRequest,
    db: Session = Depends(get_db),
):
    """
    Generate a CPM schedule from BIM elements with predicted durations.

    Builds a Directed Acyclic Graph (DAG) of construction activities,
    applies L&T construction sequencing rules, and computes:
    - Early/Late Start & Finish times
    - Float/Slack for each activity
    - Critical Path
    - Gantt chart data
    """
    project = get_project(db, request.project_id)
    if not project:
        raise HTTPException(status_code=404, detail=f"Project '{request.project_id}' not found")

    elements = get_project_elements(db, request.project_id)
    if not elements:
        raise HTTPException(status_code=404, detail="No elements found. Extract data first.")

    logger.info(f"Schedule generation | project={request.project_id} | elements={len(elements)}")

    # Convert elements to dicts
    element_dicts = []
    for elem in elements:
        element_dicts.append({
            k: v for k, v in elem.__dict__.items()
            if not k.startswith("_")
        })

    # Build custom dependencies
    custom_deps = None
    if request.custom_dependencies:
        custom_deps = [
            {
                "predecessor": d.predecessor,
                "successor": d.successor,
                "lag_days": d.lag_days,
            }
            for d in request.custom_dependencies
        ]

    # Generate schedule
    scheduler = CPMScheduler()
    try:
        result = scheduler.build_schedule(
            elements=element_dicts,
            working_hours_per_day=request.working_hours_per_day,
            crew_multiplier=request.crew_size_multiplier,
            custom_dependencies=custom_deps,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    result["project_id"] = request.project_id

    # Store activities in database
    activities_to_store = []
    for gantt_item in result["gantt_data"]:
        activities_to_store.append({
            "project_id": request.project_id,
            "activity_name": gantt_item["name"],
            "element_type": gantt_item.get("element_type"),
            "duration": gantt_item["duration"],
            "early_start": gantt_item["early_start"],
            "early_finish": gantt_item["early_finish"],
            "late_start": gantt_item["late_start"],
            "late_finish": gantt_item["late_finish"],
            "total_float": gantt_item["total_float"],
            "is_critical": gantt_item["is_critical"],
            "predecessors": str(gantt_item.get("predecessors", [])),
            "labor_hours": gantt_item.get("labor_hours", 0),
            "crew_size": gantt_item.get("crew_size", 4),
        })

    bulk_create_activities(db, activities_to_store)
    update_project_status(db, request.project_id, "scheduled")

    # Convert to response model
    gantt_items = [
        GanttItem(
            id=g["id"],
            name=g["name"],
            element_type=g.get("element_type"),
            start_day=g["start_day"],
            end_day=g["end_day"],
            duration=g["duration"],
            is_critical=g["is_critical"],
            slack=g["total_float"],
            predecessors=g.get("predecessors", []),
        )
        for g in result["gantt_data"]
    ]

    return ScheduleResponse(
        project_id=request.project_id,
        total_duration_days=result["total_duration_days"],
        critical_path=result["critical_path"],
        critical_path_duration=result["critical_path_duration"],
        gantt_data=gantt_items,
        summary=result["summary"],
    )
