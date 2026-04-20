"""
ML Training Pipeline Script
-----------------------------
End-to-end script to generate training data, train models,
and compare performance. Run this before starting the API
to have pre-trained models available.

Usage:
    cd backend
    python -m scripts.run_training_pipeline
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pandas as pd
from app.core.synthetic_data import generate_synthetic_bim_data
from app.core.quantity_takeoff import compute_qto
from app.core.cost_model import CostPredictor, compare_models
from app.core.time_model import TimePredictor
from app.config import get_settings


def main():
    """Run the complete ML training pipeline."""
    print("=" * 70)
    print("BIM Cost & Time Estimator — ML Training Pipeline")
    print("=" * 70)

    settings = get_settings()

    # ─── Step 1: Generate Training Data ───
    print("\n📦 Step 1: Generating synthetic BIM data...")
    elements = generate_synthetic_bim_data("training", num_storeys=10, seed=42)
    print(f"   Generated {len(elements)} elements")

    # ─── Step 2: Compute QTO ───
    print("\n📐 Step 2: Computing Quantity Takeoff...")
    elements = compute_qto(elements)

    # Convert to DataFrame
    df = pd.DataFrame(elements)
    print(f"   Dataset shape: {df.shape}")
    print(f"   Element types: {df['ifc_type'].value_counts().to_dict()}")
    print(f"   Materials: {df['material'].nunique()} unique")

    # Save training data
    data_path = settings.extracted_data_path / "training_data.csv"
    df.to_csv(data_path, index=False)
    print(f"   Saved to: {data_path}")

    # ─── Step 3: Train Cost Models ───
    print("\n💰 Step 3: Training Cost Models...")
    print("-" * 40)

    # Random Forest
    print("   Training Random Forest...")
    rf_cost = CostPredictor(model_type="random_forest")
    rf_metrics = rf_cost.train(df)
    rf_cost.save()
    print(f"   RF Cost - R²: {rf_metrics['test_r2']:.4f} | RMSE: {rf_metrics['test_rmse']:.2f}")

    # XGBoost
    print("   Training XGBoost...")
    xgb_cost = CostPredictor(model_type="xgboost")
    xgb_metrics = xgb_cost.train(df)
    xgb_cost.save()
    print(f"   XGB Cost - R²: {xgb_metrics['test_r2']:.4f} | RMSE: {xgb_metrics['test_rmse']:.2f}")

    # ─── Step 4: Train Time Models ───
    print("\n⏱️  Step 4: Training Time Models...")
    print("-" * 40)

    # Random Forest
    print("   Training Random Forest...")
    rf_time = TimePredictor(model_type="random_forest")
    rf_time_metrics = rf_time.train(df)
    rf_time.save()
    print(f"   RF Time - R²: {rf_time_metrics['test_r2']:.4f} | RMSE: {rf_time_metrics['test_rmse']:.2f}")

    # XGBoost
    print("   Training XGBoost...")
    xgb_time = TimePredictor(model_type="xgboost")
    xgb_time_metrics = xgb_time.train(df)
    xgb_time.save()
    print(f"   XGB Time - R²: {xgb_time_metrics['test_r2']:.4f} | RMSE: {xgb_time_metrics['test_rmse']:.2f}")

    # ─── Step 5: Feature Importance ───
    print("\n🔍 Step 5: Feature Importance (Cost Model)...")
    importance = xgb_cost.get_feature_importance()
    for i, (feature, value) in enumerate(list(importance.items())[:10]):
        print(f"   {i+1:2d}. {feature:30s} → {value:.4f}")

    # ─── Summary ───
    print("\n" + "=" * 70)
    print("📊 MODEL COMPARISON SUMMARY")
    print("=" * 70)
    print(f"{'Model':<25} {'Cost R²':<12} {'Cost RMSE':<14} {'Time R²':<12} {'Time RMSE':<14}")
    print("-" * 70)
    print(f"{'Random Forest':<25} {rf_metrics['test_r2']:<12.4f} {rf_metrics['test_rmse']:<14.2f} {rf_time_metrics['test_r2']:<12.4f} {rf_time_metrics['test_rmse']:<14.2f}")
    print(f"{'XGBoost':<25} {xgb_metrics['test_r2']:<12.4f} {xgb_metrics['test_rmse']:<14.2f} {xgb_time_metrics['test_r2']:<12.4f} {xgb_time_metrics['test_rmse']:<14.2f}")
    print("-" * 70)

    best_cost = "XGBoost" if xgb_metrics['test_r2'] > rf_metrics['test_r2'] else "Random Forest"
    best_time = "XGBoost" if xgb_time_metrics['test_r2'] > rf_time_metrics['test_r2'] else "Random Forest"
    print(f"\n🏆 Best Cost Model: {best_cost}")
    print(f"🏆 Best Time Model: {best_time}")
    print(f"\n✅ All models saved to: {settings.model_path}")
    print("=" * 70)


if __name__ == "__main__":
    main()
