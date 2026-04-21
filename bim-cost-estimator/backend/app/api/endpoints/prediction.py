"""
Prediction Endpoints
---------------------
/predict-cost — Predict construction costs for BIM elements
/predict-time — Predict construction duration for BIM elements
"""

import pandas as pd
import numpy as np
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db import get_db
from app.db.crud import get_project, get_project_elements, update_project_status
from app.core.cost_model import CostPredictor
from app.core.time_model import TimePredictor
from app.core.explainer import SHAPExplainer
from app.models.prediction_models import (
    PredictionRequest,
    CostPredictionResponse,
    TimePredictionResponse,
    ElementPrediction,
    MaterialUnitRate,
    FxMeta,
)
from app.core.material_market_rates import build_material_unit_rates
from app.config import get_settings
from app.utils import get_logger

logger = get_logger("api.prediction")
router = APIRouter()

# Cache for loaded models
_cost_predictor = None
_time_predictor = None


def _get_cost_predictor(model_type: str = "xgboost") -> CostPredictor:
    """Get or create cost predictor (lazy loading)."""
    global _cost_predictor
    if _cost_predictor is None or _cost_predictor.model_type != model_type:
        _cost_predictor = CostPredictor(model_type=model_type)
        try:
            _cost_predictor.load()
            logger.info(f"Cost model loaded from disk | type={model_type}")
        except FileNotFoundError:
            logger.info("No saved cost model found. Will train on demand.")
    return _cost_predictor


def _get_time_predictor(model_type: str = "xgboost") -> TimePredictor:
    """Get or create time predictor (lazy loading)."""
    global _time_predictor
    if _time_predictor is None or _time_predictor.model_type != model_type:
        _time_predictor = TimePredictor(model_type=model_type)
        try:
            _time_predictor.load()
            logger.info(f"Time model loaded from disk | type={model_type}")
        except FileNotFoundError:
            logger.info("No saved time model found. Will train on demand.")
    return _time_predictor


def _elements_to_dataframe(elements) -> pd.DataFrame:
    """Convert ORM elements or dicts to a DataFrame."""
    if not elements:
        return pd.DataFrame()

    records = []
    for elem in elements:
        if hasattr(elem, "__dict__"):
            record = {
                k: v for k, v in elem.__dict__.items()
                if not k.startswith("_")
            }
        else:
            record = dict(elem)
        records.append(record)

    return pd.DataFrame(records)


@router.post("/predict-cost", response_model=CostPredictionResponse)
async def predict_cost(
    request: PredictionRequest,
    db: Session = Depends(get_db),
):
    """
    Predict construction costs for all elements in a project.

    Uses trained ML models (Random Forest or XGBoost) to predict
    element-level costs. If no trained model exists, trains on
    the project's own QTO-estimated costs and predicts.
    """
    project = get_project(db, request.project_id)
    if not project:
        raise HTTPException(status_code=404, detail=f"Project '{request.project_id}' not found")

    # Get elements
    elements = get_project_elements(
        db, request.project_id,
        element_type=request.element_type_filter,
        material=request.material_filter,
    )

    if not elements:
        raise HTTPException(status_code=404, detail="No elements found. Extract data first.")

    df = _elements_to_dataframe(elements)

    logger.info(f"Cost prediction | project={request.project_id} | elements={len(df)}")

    # Get predictor
    predictor = _get_cost_predictor(request.model_type)

    # Train if not already trained
    if not predictor.is_trained:
        logger.info("Training cost model on project data...")
        predictor.train(df)
        predictor.save()

    # Predict
    try:
        predictions = predictor.predict(df)
    except Exception as e:
        logger.warning(f"Prediction failed, retraining | error={e}")
        predictor.train(df)
        predictor.save()
        predictions = predictor.predict(df)

    # Prevent NaN/Inf validation errors during JSON serialization (Network Error)
    predictions = np.nan_to_num(predictions, nan=0.0, posinf=0.0, neginf=0.0)

    # Build response
    element_predictions = []
    cost_by_type = {}
    cost_by_material = {}
    cost_by_storey = {}

    for i, (_, row) in enumerate(df.iterrows()):
        cost = float(predictions[i])
        ifc_type = row.get("ifc_type", "Unknown")
        material = row.get("material", "Unknown")
        storey = row.get("storey", "Unknown")

        element_predictions.append(ElementPrediction(
            element_id=str(row.get("id", i)),
            element_name=row.get("element_name"),
            ifc_type=ifc_type,
            material=material,
            storey=storey,
            predicted_value=round(cost, 2),
            unit="INR",
        ))

        cost_by_type[ifc_type] = cost_by_type.get(ifc_type, 0) + cost
        cost_by_material[material] = cost_by_material.get(material, 0) + cost
        cost_by_storey[storey] = cost_by_storey.get(storey, 0) + cost

    total_cost = float(np.sum(predictions))

    # Round breakdowns
    cost_by_type = {k: round(v, 2) for k, v in cost_by_type.items()}
    cost_by_material = {k: round(v, 2) for k, v in cost_by_material.items()}
    cost_by_storey = {k: round(v, 2) for k, v in cost_by_storey.items()}

    update_project_status(db, request.project_id, "predicted")

    material_rows, fx_meta_raw = await build_material_unit_rates(list(cost_by_material.keys()))
    material_unit_rates = [MaterialUnitRate(**row) for row in material_rows]
    fx_meta = FxMeta(
        usd_inr=fx_meta_raw["usd_inr"],
        reference_usd_inr=fx_meta_raw["reference_usd_inr"],
        fx_source=fx_meta_raw["fx_source"],
        fx_rate_date=fx_meta_raw.get("fx_rate_date"),
        fetched_at_utc=fx_meta_raw["fetched_at_utc"],
    )

    return CostPredictionResponse(
        project_id=request.project_id,
        model_used=predictor.model_type,
        total_cost=round(total_cost, 2),
        cost_breakdown=cost_by_type,
        material_breakdown=cost_by_material,
        storey_breakdown=cost_by_storey,
        predictions=element_predictions,
        metrics=predictor.metrics,
        material_unit_rates=material_unit_rates,
        fx_meta=fx_meta,
    )


@router.post("/predict-time", response_model=TimePredictionResponse)
async def predict_time(
    request: PredictionRequest,
    db: Session = Depends(get_db),
):
    """
    Predict construction duration (labor hours) for all elements.

    Incorporates labor productivity factors, crew sizes, and
    floor-level efficiency degradation.
    """
    project = get_project(db, request.project_id)
    if not project:
        raise HTTPException(status_code=404, detail=f"Project '{request.project_id}' not found")

    elements = get_project_elements(
        db, request.project_id,
        element_type=request.element_type_filter,
        material=request.material_filter,
    )

    if not elements:
        raise HTTPException(status_code=404, detail="No elements found. Extract data first.")

    df = _elements_to_dataframe(elements)

    logger.info(f"Time prediction | project={request.project_id} | elements={len(df)}")

    # Get predictor
    predictor = _get_time_predictor(request.model_type)

    # Train if not already trained
    if not predictor.is_trained:
        logger.info("Training time model on project data...")
        predictor.train(df)
        predictor.save()

    # Predict
    try:
        predictions = predictor.predict(df)
    except Exception as e:
        logger.warning(f"Prediction failed, retraining | error={e}")
        predictor.train(df)
        predictor.save()
        predictions = predictor.predict(df)

    # Prevent NaN/Inf validation errors
    predictions = np.nan_to_num(predictions, nan=0.0, posinf=0.0, neginf=0.0)

    # Build response
    element_predictions = []
    duration_by_type = {}
    duration_by_storey = {}

    for i, (_, row) in enumerate(df.iterrows()):
        hours = float(predictions[i])
        ifc_type = row.get("ifc_type", "Unknown")
        storey = row.get("storey", "Unknown")

        element_predictions.append(ElementPrediction(
            element_id=str(row.get("id", i)),
            element_name=row.get("element_name"),
            ifc_type=ifc_type,
            material=row.get("material"),
            storey=storey,
            predicted_value=round(hours, 2),
            unit="hours",
        ))

        duration_by_type[ifc_type] = duration_by_type.get(ifc_type, 0) + hours
        duration_by_storey[storey] = duration_by_storey.get(storey, 0) + hours

    total_hours = float(np.sum(predictions))

    duration_by_type = {k: round(v, 2) for k, v in duration_by_type.items()}
    duration_by_storey = {k: round(v, 2) for k, v in duration_by_storey.items()}

    return TimePredictionResponse(
        project_id=request.project_id,
        model_used=predictor.model_type,
        total_duration_hours=round(total_hours, 2),
        total_duration_days=round(total_hours / 8.0, 2),
        duration_breakdown=duration_by_type,
        storey_breakdown=duration_by_storey,
        predictions=element_predictions,
        metrics=predictor.metrics,
    )


@router.get("/shap-explanation/{project_id}")
async def get_shap_explanation(
    project_id: str,
    model: str = "cost",
    element_index: int = 0,
    db: Session = Depends(get_db),
):
    """
    Get SHAP explanations for cost or time predictions.

    Returns global feature importance and local element-level
    explanations using SHAP TreeExplainer.
    """
    elements = get_project_elements(db, project_id)
    if not elements:
        raise HTTPException(status_code=404, detail="No elements found")

    df = _elements_to_dataframe(elements)

    if model == "cost":
        predictor = _get_cost_predictor()
    else:
        predictor = _get_time_predictor()

    if not predictor.is_trained:
        raise HTTPException(status_code=400, detail=f"No trained {model} model available")

    # Get transformed features
    X = predictor.feature_engine.transform(df)
    feature_names = predictor.feature_engine.get_feature_names()

    # SHAP explanation
    explainer = SHAPExplainer(predictor.model, feature_names, model_name=model)
    global_exp = explainer.global_explanation(X)
    local_exp = explainer.local_explanation(X, index=min(element_index, len(X) - 1))

    # Generate and save plots
    import os
    reports_dir = os.path.join("reports", "shap")
    os.makedirs(reports_dir, exist_ok=True)
    summary_path = explainer.generate_summary_plot(X, save_path=os.path.join(reports_dir, f"shap_summary_{model}_{project_id}.png"))
    waterfall_path = explainer.generate_waterfall_plot(X, index=min(element_index, len(X) - 1), save_path=os.path.join(reports_dir, f"shap_waterfall_{model}_{project_id}_{element_index}.png"))

    return {
        "project_id": project_id,
        "model": model,
        "global_explanation": global_exp,
        "local_explanation": local_exp,
        "plots": {
            "summary_plot": summary_path,
            "waterfall_plot": waterfall_path,
        }
    }
