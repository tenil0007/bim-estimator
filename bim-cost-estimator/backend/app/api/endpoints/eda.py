"""
EDA Analysis Endpoint
----------------------
Generates Exploratory Data Analysis results for a project's BIM data.
"""

import pandas as pd
import numpy as np
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db import get_db
from app.db.crud import get_project, get_project_elements
from app.utils import get_logger

logger = get_logger("api.eda")
router = APIRouter()


def _elements_to_dataframe(elements) -> pd.DataFrame:
    """Convert ORM elements to a DataFrame."""
    if not elements:
        return pd.DataFrame()
    records = []
    for elem in elements:
        if hasattr(elem, "__dict__"):
            record = {k: v for k, v in elem.__dict__.items() if not k.startswith("_")}
        else:
            record = dict(elem)
        records.append(record)
    return pd.DataFrame(records)


@router.get("/eda-analysis/{project_id}", tags=["Data Science"])
async def eda_analysis(project_id: str, db: Session = Depends(get_db)):
    """
    Run Exploratory Data Analysis on extracted BIM data.

    Returns statistical summaries, distributions, correlations,
    and outlier analysis for the project's elements.
    """
    project = get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")

    elements = get_project_elements(db, project_id)
    if not elements:
        raise HTTPException(status_code=404, detail="No extracted elements. Run /extract-data first.")

    df = _elements_to_dataframe(elements)
    logger.info(f"EDA analysis | project={project_id} | rows={len(df)}")

    # --- 1. Basic Statistics ---
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    stats = {}
    for col in numeric_cols:
        series = df[col].dropna()
        if len(series) == 0:
            continue
        stats[col] = {
            "count": int(series.count()),
            "mean": round(float(series.mean()), 4),
            "std": round(float(series.std()), 4),
            "min": round(float(series.min()), 4),
            "25%": round(float(series.quantile(0.25)), 4),
            "50%": round(float(series.quantile(0.50)), 4),
            "75%": round(float(series.quantile(0.75)), 4),
            "max": round(float(series.max()), 4),
        }

    # --- 2. Distribution by IFC Type ---
    type_dist = df["ifc_type"].value_counts().to_dict() if "ifc_type" in df.columns else {}

    # --- 3. Material Distribution ---
    material_dist = df["material"].value_counts().to_dict() if "material" in df.columns else {}

    # --- 4. Storey Distribution ---
    storey_dist = df["storey"].value_counts().to_dict() if "storey" in df.columns else {}

    # --- 5. Correlation Matrix (numeric only) ---
    key_cols = [c for c in ["area", "volume", "length", "height", "width", "thickness"] if c in numeric_cols]
    correlation = {}
    if len(key_cols) > 1:
        corr_df = df[key_cols].corr()
        correlation = {
            col: {row: round(float(corr_df.loc[row, col]), 4) for row in corr_df.index}
            for col in corr_df.columns
        }

    # --- 6. Outlier Detection (IQR method) ---
    outliers = {}
    for col in key_cols:
        series = df[col].dropna()
        if len(series) < 4:
            continue
        q1, q3 = series.quantile(0.25), series.quantile(0.75)
        iqr = q3 - q1
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        n_outliers = int(((series < lower) | (series > upper)).sum())
        outliers[col] = {
            "total": int(len(series)),
            "outlier_count": n_outliers,
            "outlier_pct": round(n_outliers / len(series) * 100, 2),
            "lower_bound": round(float(lower), 4),
            "upper_bound": round(float(upper), 4),
        }

    # --- 7. Missing Value Summary ---
    missing = {
        col: {"count": int(df[col].isna().sum()), "pct": round(float(df[col].isna().mean() * 100), 2)}
        for col in df.columns
        if df[col].isna().sum() > 0
    }

    # --- 8. Volume by element type (chart data) ---
    volume_by_type = {}
    if "volume" in df.columns and "ifc_type" in df.columns:
        volume_by_type = df.groupby("ifc_type")["volume"].sum().round(2).to_dict()

    return {
        "project_id": project_id,
        "total_elements": len(df),
        "numeric_columns": numeric_cols,
        "statistics": stats,
        "distributions": {
            "by_ifc_type": type_dist,
            "by_material": material_dist,
            "by_storey": storey_dist,
        },
        "correlation_matrix": correlation,
        "outlier_analysis": outliers,
        "missing_values": missing,
        "chart_data": {
            "volume_by_type": {
                "labels": list(volume_by_type.keys()),
                "values": list(volume_by_type.values()),
                "chart_type": "bar",
                "title": "Total Volume by Element Type",
            },
            "element_type_distribution": {
                "labels": list(type_dist.keys()),
                "values": list(type_dist.values()),
                "chart_type": "pie",
                "title": "Element Type Distribution",
            },
        },
    }
