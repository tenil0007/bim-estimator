import random
import uuid
import asyncio
from fastapi import FastAPI, UploadFile, File, Form, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import math

app = FastAPI(title="BIM Mock Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

projects_db = {}

@app.post("/api/v1/upload-ifc")
async def upload_ifc(file: UploadFile = File(...), project_name: str = None):
    project_id = str(uuid.uuid4())
    projects_db[project_id] = {"id": project_id, "name": project_name or file.filename}
    await asyncio.sleep(1) # simulate parsing
    return {
        "project_id": project_id,
        "filename": file.filename,
        "file_size_mb": 15.2,
        "status": "uploaded",
        "message": f"IFC file uploaded successfully. Project ID: {project_id}"
    }

@app.get("/api/v1/projects")
async def list_projects():
    return {
        "projects": [
            {"id": k, "name": v["name"], "ifc_filename": v["name"], "status": "parsed", "uploaded_at": "2026-04-18T10:00:00", "file_size_mb": 15.2}
            for k, v in projects_db.items()
        ],
        "total": len(projects_db)
    }

@app.get("/api/v1/extract-data/{project_id}")
async def extract_data(project_id: str, use_synthetic: bool = False):
    await asyncio.sleep(1)
    elements = []
    for i in range(100):
        elements.append({
            "id": str(uuid.uuid4()),
            "project_id": project_id,
            "ifc_type": random.choice(["IfcWall", "IfcSlab", "IfcColumn", "IfcBeam", "IfcWindow", "IfcDoor"]),
            "material": random.choice(["Concrete", "Steel", "Glass", "Wood"]),
            "storey": f"Level {random.randint(1, 10)}",
            "volume": random.uniform(1.0, 50.0),
            "area": random.uniform(5.0, 100.0)
        })
    return {
        "project_id": project_id,
        "total_elements": 100,
        "element_types": {"IfcWall": 30, "IfcSlab": 20, "IfcColumn": 15, "IfcBeam": 20, "IfcWindow": 10, "IfcDoor": 5},
        "materials": ["Concrete", "Steel", "Glass", "Wood"],
        "storeys": [f"Level {i}" for i in range(1, 11)],
        "elements": elements,
        "status": "parsed"
    }

class PredictRequest(BaseModel):
    project_id: str
    model_type: str = "xgboost"
    element_type_filter: Optional[str] = None
    material_filter: Optional[str] = None

@app.post("/api/v1/predict-cost")
async def predict_cost(req: PredictRequest):
    await asyncio.sleep(1)
    
    # Generate dynamic, pseudo-random values based on the project_id
    seed = sum(ord(c) for c in req.project_id)
    random.seed(seed)
    
    base_cost = random.uniform(1500000.0, 5500000.0)
    
    wall_cost = base_cost * 0.32
    slab_cost = base_cost * 0.24
    col_cost = base_cost * 0.20
    beam_cost = base_cost * 0.16
    window_cost = base_cost * 0.06
    door_cost = base_cost * 0.02
    
    return {
        "project_id": req.project_id,
        "model_type": req.model_type,
        "total_cost": base_cost,
        "currency": "USD",
        "predicted_at": "2026-04-18T10:00:00",
        "cost_breakdown": {
            "IfcWall": wall_cost, "IfcSlab": slab_cost, "IfcColumn": col_cost, 
            "IfcBeam": beam_cost, "IfcWindow": window_cost, "IfcDoor": door_cost
        },
        "metrics": {"test_r2": random.uniform(0.85, 0.98), "mae": random.uniform(800, 1500)},
        "element_level_predictions": []
    }

@app.post("/api/v1/predict-time")
async def predict_time(req: PredictRequest):
    await asyncio.sleep(1)
    
    seed = sum(ord(c) for c in req.project_id) + 1  # different seed for time
    random.seed(seed)
    
    total_hours = random.uniform(1000.0, 5000.0)
    
    return {
        "project_id": req.project_id,
        "model_type": req.model_type,
        "total_duration_hours": total_hours,
        "predicted_at": "2026-04-18T10:00:00",
        "time_breakdown": {
            "by_storey": {f"Level {i}": total_hours/10 for i in range(1, 11)},
            "by_element_type": {"IfcWall": total_hours*0.3, "IfcSlab": total_hours*0.2, "IfcColumn": total_hours*0.2, "IfcBeam": total_hours*0.15, "IfcWindow": total_hours*0.1, "IfcDoor": total_hours*0.05}
        },
        "element_level_predictions": []
    }

@app.get("/api/v1/shap-explanation/{project_id}")
async def get_shap(project_id: str, model: str = "cost", element_index: int = 0):
    await asyncio.sleep(0.5)
    return {
        "project_id": project_id,
        "model": model,
        "element_index": element_index,
        "base_value": 500.0,
        "prediction_value": 750.0,
        "features": ["volume", "area", "ifc_type", "material", "storey_elevation"],
        "shap_values": [120.0, 80.0, 45.0, -15.0, 20.0]
    }

class ScheduleRequest(BaseModel):
    project_id: str
    working_hours_per_day: int = 8
    crew_size_multiplier: float = 1.0
    custom_dependencies: Optional[Any] = None

@app.post("/api/v1/schedule")
async def generate_schedule(req: ScheduleRequest):
    await asyncio.sleep(1)
    tasks = []
    start = "2026-05-01"
    end = "2026-05-10"
    for i in range(10):
        tasks.append({
            "id": f"Task_{i}",
            "name": f"Construct Level {i+1} Walls",
            "start": "2026-05-01",
            "end": "2026-05-15",
            "duration": 15,
            "dependencies": [f"Task_{i-1}"] if i > 0 else [],
            "element_ids": []
        })
    return {
        "project_id": req.project_id,
        "total_duration_days": 150,
        "critical_path_tasks": ["Task_0", "Task_1"],
        "tasks": tasks
    }

@app.post("/api/v1/generate-report")
async def generate_report_endpoint():
    return JSONResponse({"message": "Report generated"}, status_code=200)

@app.get("/health")
async def health():
    return {"status": "ok"}
