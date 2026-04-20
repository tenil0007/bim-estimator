"""
Report Endpoints
-----------------
/generate-report — Generate PDF report for a project
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.db import get_db
from app.db.crud import get_project, get_project_elements, get_project_schedule
from app.core.report_generator import ReportGenerator
from app.models.schedule_models import ReportRequest
from app.utils import get_logger

logger = get_logger("api.reports")
router = APIRouter()


@router.post("/generate-report")
async def generate_report(
    request: ReportRequest,
    db: Session = Depends(get_db),
):
    """
    Generate a comprehensive PDF report for a project.

    Includes:
    - Executive summary with key metrics
    - Cost analysis breakdown
    - Time/duration analysis
    - Project schedule (CPM)
    - SHAP AI explainability insights
    """
    project = get_project(db, request.project_id)
    if not project:
        raise HTTPException(status_code=404, detail=f"Project '{request.project_id}' not found")

    elements = get_project_elements(db, request.project_id)

    logger.info(f"Report generation | project={request.project_id}")

    # Build project data
    element_types = {}
    total_cost = 0
    total_hours = 0
    cost_by_type = {}
    cost_by_material = {}
    duration_by_type = {}

    for elem in elements:
        ifc_type = elem.ifc_type
        material = elem.material or "Unknown"
        cost = elem.predicted_cost or 0
        hours = elem.predicted_duration or 0

        element_types[ifc_type] = element_types.get(ifc_type, 0) + 1
        total_cost += cost
        total_hours += hours
        cost_by_type[ifc_type] = cost_by_type.get(ifc_type, 0) + cost
        cost_by_material[material] = cost_by_material.get(material, 0) + cost
        duration_by_type[ifc_type] = duration_by_type.get(ifc_type, 0) + hours

    project_data = {
        "project_id": request.project_id,
        "name": project.name,
        "ifc_filename": project.ifc_filename,
        "total_elements": len(elements),
        "element_types": element_types,
    }

    cost_data = {
        "total_cost": total_cost,
        "cost_breakdown": cost_by_type,
        "material_breakdown": cost_by_material,
        "metrics": {},
    } if request.include_cost else None

    time_data = {
        "total_duration_hours": total_hours,
        "total_duration_days": total_hours / 8.0,
        "duration_breakdown": duration_by_type,
    } if request.include_time else None

    # Schedule data
    schedule_data = None
    if request.include_schedule:
        activities = get_project_schedule(db, request.project_id)
        if activities:
            schedule_data = {
                "total_duration_days": max(
                    (a.early_finish for a in activities), default=0
                ),
                "critical_path": [
                    a.activity_name for a in activities if a.is_critical
                ],
                "gantt_data": [
                    {
                        "name": a.activity_name,
                        "duration": a.duration,
                        "start_day": a.early_start,
                        "end_day": a.early_finish,
                        "total_float": a.total_float,
                        "is_critical": a.is_critical,
                    }
                    for a in activities
                ],
                "summary": {
                    "total_activities": len(activities),
                    "critical_activities": sum(1 for a in activities if a.is_critical),
                    "avg_float_days": sum(a.total_float or 0 for a in activities) / max(len(activities), 1),
                    "total_labor_hours": sum(a.labor_hours or 0 for a in activities),
                },
            }

    # SHAP data placeholder
    shap_data = None
    if request.include_shap:
        # Generate SHAP data from cached predictions
        try:
            from app.api.endpoints.prediction import _get_cost_predictor
            predictor = _get_cost_predictor()
            if predictor.is_trained:
                shap_data = {
                    "feature_importance": predictor.get_feature_importance(),
                    "feature_direction": {
                        k: "increases" for k in predictor.get_feature_importance()
                    },
                }
        except Exception:
            pass

    # Generate PDF
    try:
        generator = ReportGenerator()
        pdf_path = generator.generate_report(
            project_data=project_data,
            cost_data=cost_data,
            time_data=time_data,
            schedule_data=schedule_data,
            shap_data=shap_data,
            config={
                "report_title": request.report_title,
                "company_name": request.company_name,
                "include_cost": request.include_cost,
                "include_time": request.include_time,
                "include_schedule": request.include_schedule,
                "include_shap": request.include_shap,
            },
        )

        return FileResponse(
            path=pdf_path,
            filename=f"BIM_Report_{request.project_id}.pdf",
            media_type="application/pdf",
        )

    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="ReportLab not installed. Install with: pip install reportlab"
        )
    except Exception as e:
        logger.error(f"Report generation failed | error={e}")
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")
