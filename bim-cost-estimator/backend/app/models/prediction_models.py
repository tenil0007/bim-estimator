"""
Pydantic Models - Predictions
-----------------------------
Request/Response schemas for cost and time prediction endpoints.
"""

from pydantic import BaseModel, Field
from typing import Optional


class MaterialUnitRate(BaseModel):
    """Reference ₹/unit for a BIM material (live USD/INR + indicative schedule)."""
    material_name: str
    matched_category: str
    unit: str = Field(description="e.g. per m³, per kg")
    rate_inr: float
    base_rate_inr: float = Field(description="Pre-FX indicative base in INR")
    fx_weight: float = Field(description="How much the rate tracks USD/INR vs local baseline")
    usd_inr_spot: float = Field(description="INR per 1 USD at fetch time")
    pricing_note: str
    as_of_utc: str


class FxMeta(BaseModel):
    """Metadata for the live FX snapshot used to adjust reference rates."""
    usd_inr: float
    reference_usd_inr: float
    fx_source: str
    fx_rate_date: Optional[str] = None
    fetched_at_utc: str


class MaterialRatesResponse(BaseModel):
    """Standalone material reference rates (same schema as embedded in cost response)."""
    material_unit_rates: list[MaterialUnitRate]
    fx_meta: FxMeta


class PredictionRequest(BaseModel):
    """Request body for cost/time prediction."""
    project_id: str
    model_type: str = Field(
        default="xgboost",
        description="ML model to use: 'xgboost' or 'random_forest'"
    )
    element_type_filter: Optional[str] = Field(
        default=None,
        description="Filter predictions by element type (e.g., 'IfcWall')"
    )
    material_filter: Optional[str] = Field(
        default=None,
        description="Filter predictions by material (e.g., 'Concrete')"
    )


class ElementPrediction(BaseModel):
    """Cost/time prediction for a single element."""
    element_id: str
    element_name: Optional[str] = None
    ifc_type: str
    material: Optional[str] = None
    storey: Optional[str] = None
    predicted_value: float
    unit: str
    confidence: Optional[float] = None


class CostPredictionResponse(BaseModel):
    """Response from cost prediction endpoint."""
    project_id: str
    model_used: str
    total_cost: float
    currency: str = "INR"
    cost_breakdown: dict[str, float]  # by element type
    material_breakdown: dict[str, float]  # by material
    storey_breakdown: dict[str, float]  # by floor
    predictions: list[ElementPrediction]
    metrics: dict[str, float]  # R², RMSE, etc.
    material_unit_rates: list[MaterialUnitRate] = Field(
        default_factory=list,
        description="Indicative ₹/unit reference rates (live USD/INR snapshot)",
    )
    fx_meta: Optional[FxMeta] = Field(
        default=None,
        description="FX snapshot used for material reference rates",
    )


class TimePredictionResponse(BaseModel):
    """Response from time prediction endpoint."""
    project_id: str
    model_used: str
    total_duration_hours: float
    total_duration_days: float
    duration_breakdown: dict[str, float]  # by element type (hours)
    storey_breakdown: dict[str, float]  # by floor (hours)
    predictions: list[ElementPrediction]
    metrics: dict[str, float]
