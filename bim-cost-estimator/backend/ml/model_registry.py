"""
Model Version Registry
-----------------------
Simple JSON-based model versioning and tracking system.
Tracks model type, metrics, training date, and artifact paths.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from app.utils import get_logger

logger = get_logger("model_registry")

REGISTRY_FILE = Path(__file__).parent / "registry.json"


def _load_registry() -> dict:
    """Load the registry from disk."""
    if REGISTRY_FILE.exists():
        with open(REGISTRY_FILE, "r") as f:
            return json.load(f)
    return {"models": [], "best_cost_model": None, "best_time_model": None}


def _save_registry(registry: dict):
    """Save the registry to disk."""
    REGISTRY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(REGISTRY_FILE, "w") as f:
        json.dump(registry, f, indent=2, default=str)


def register_model(
    model_name: str,
    model_type: str,
    task: str,
    metrics: dict,
    artifact_path: str,
    feature_count: int = 0,
    training_samples: int = 0,
    notes: str = "",
) -> dict:
    """
    Register a trained model in the version registry.

    Args:
        model_name: Human-readable name (e.g. "cost_xgboost_v3")
        model_type: Algorithm type (xgboost, random_forest, lightgbm, gradient_boosting)
        task: "cost" or "time"
        metrics: Dict of evaluation metrics (r2, rmse, mae, etc.)
        artifact_path: Where the .joblib artifact was saved
        feature_count: Number of features used
        training_samples: Number of samples used for training
        notes: Optional description or notes

    Returns:
        The entry dict that was stored
    """
    registry = _load_registry()

    version = len([m for m in registry["models"] if m["task"] == task]) + 1

    entry = {
        "id": f"{task}_{model_type}_v{version}",
        "model_name": model_name,
        "model_type": model_type,
        "task": task,
        "version": version,
        "metrics": metrics,
        "artifact_path": artifact_path,
        "feature_count": feature_count,
        "training_samples": training_samples,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "notes": notes,
    }

    registry["models"].append(entry)

    # Auto-select best model for each task based on test_r2
    best_key = f"best_{task}_model"
    current_best = registry.get(best_key)
    if current_best is None:
        registry[best_key] = entry["id"]
    else:
        best_entry = next((m for m in registry["models"] if m["id"] == current_best), None)
        if best_entry and metrics.get("test_r2", 0) > best_entry.get("metrics", {}).get("test_r2", 0):
            registry[best_key] = entry["id"]
            logger.info(f"New best {task} model: {entry['id']} (R²={metrics.get('test_r2')})")

    _save_registry(registry)
    logger.info(f"Model registered | id={entry['id']} | R²={metrics.get('test_r2')}")
    return entry


def get_best_model(task: str) -> dict | None:
    """Get the best registered model for a task (cost or time)."""
    registry = _load_registry()
    best_id = registry.get(f"best_{task}_model")
    if best_id:
        return next((m for m in registry["models"] if m["id"] == best_id), None)
    return None


def list_models(task: str = None) -> list[dict]:
    """List all registered models, optionally filtered by task."""
    registry = _load_registry()
    models = registry["models"]
    if task:
        models = [m for m in models if m["task"] == task]
    return models


def get_registry_summary() -> dict:
    """Get a summary of the model registry."""
    registry = _load_registry()
    return {
        "total_models": len(registry["models"]),
        "best_cost_model": registry.get("best_cost_model"),
        "best_time_model": registry.get("best_time_model"),
        "cost_models": len([m for m in registry["models"] if m["task"] == "cost"]),
        "time_models": len([m for m in registry["models"] if m["task"] == "time"]),
    }
