"""
Cost Prediction Model
----------------------
Machine learning models for construction cost estimation.
Supports Random Forest and XGBoost with cross-validation,
hyperparameter tuning, and model comparison.

Uses the feature engineering pipeline for consistent preprocessing.
"""

import numpy as np
import pandas as pd
import joblib
from pathlib import Path
from typing import Optional
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import cross_val_score, train_test_split, GridSearchCV
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from app.utils import get_logger
from app.config import get_settings
from app.core.feature_engine import BIMFeatureEngine, COST_TARGET

import lightgbm as lgb

logger = get_logger("cost_model")

try:
    from xgboost import XGBRegressor
    HAS_XGBOOST = True
except ImportError:
    HAS_XGBOOST = False
    logger.warning("XGBoost not available. Using Random Forest only.")

try:
    import optuna
    HAS_OPTUNA = True
except ImportError:
    HAS_OPTUNA = False


class CostPredictor:
    """
    Construction cost prediction using ensemble ML models.

    Supports:
        - Random Forest Regressor
        - XGBoost Regressor
        - Hyperparameter tuning via Optuna
        - Cross-validation
        - Model comparison
    """

    def __init__(self, model_type: str = "xgboost"):
        supported = ["xgboost", "random_forest", "lightgbm"]
        self.model_type = model_type if model_type in supported else "random_forest"
        if self.model_type == "xgboost" and not HAS_XGBOOST:
            self.model_type = "random_forest"
        self.model = None
        self.feature_engine = BIMFeatureEngine()
        self.metrics: dict = {}
        self.is_trained = False

    def train(self, df: pd.DataFrame, tune_hyperparams: bool = False) -> dict:
        """
        Train the cost prediction model.

        Args:
            df: Raw BIM element DataFrame with cost labels
            tune_hyperparams: Whether to run Optuna hyperparameter tuning

        Returns:
            Dictionary of evaluation metrics
        """
        logger.info(f"Training cost model | type={self.model_type} | rows={len(df)}")

        # Feature engineering
        X, y = self.feature_engine.fit_transform(df, target=COST_TARGET)

        # Filter out zero-cost elements for training
        mask = y > 0
        X, y = X[mask], y[mask]

        # Train/test split
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )

        # Build model
        if tune_hyperparams:
            self.model = self._tune_hyperparameters(X_train, y_train)
        else:
            self.model = self._build_default_model()

        # Train
        self.model.fit(X_train, y_train)

        # Evaluate
        y_pred_train = self.model.predict(X_train)
        y_pred_test = self.model.predict(X_test)

        self.metrics = {
            "train_r2": round(r2_score(y_train, y_pred_train), 4),
            "test_r2": round(r2_score(y_test, y_pred_test), 4),
            "test_rmse": round(np.sqrt(mean_squared_error(y_test, y_pred_test)), 2),
            "test_mae": round(mean_absolute_error(y_test, y_pred_test), 2),
            "test_mape": round(
                np.mean(np.abs((y_test - y_pred_test) / np.maximum(y_test, 1))) * 100, 2
            ),
        }

        # Cross-validation
        cv_scores = cross_val_score(self.model, X, y, cv=5, scoring="r2")
        self.metrics["cv_r2_mean"] = round(cv_scores.mean(), 4)
        self.metrics["cv_r2_std"] = round(cv_scores.std(), 4)

        self.is_trained = True
        logger.info(f"Cost model trained | R²={self.metrics['test_r2']} | RMSE={self.metrics['test_rmse']}")

        return self.metrics

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        """Predict costs for new BIM elements."""
        if not self.is_trained:
            raise RuntimeError("Model not trained. Call train() first or load a saved model.")

        X = self.feature_engine.transform(df)
        predictions = self.model.predict(X)

        # Ensure non-negative predictions
        predictions = np.maximum(predictions, 0)
        return predictions

    def _build_default_model(self):
        """Build model with sensible default hyperparameters."""
        if self.model_type == "xgboost" and HAS_XGBOOST:
            return XGBRegressor(
                n_estimators=100,
                max_depth=6,
                learning_rate=0.05,
                subsample=0.8,
                colsample_bytree=0.8,
                reg_alpha=0.1,
                reg_lambda=1.0,
                min_child_weight=5,
                random_state=42,
                n_jobs=1,
                verbosity=0,
            )
        elif self.model_type == "lightgbm":
            return lgb.LGBMRegressor(
                n_estimators=100,
                max_depth=6,
                learning_rate=0.05,
                subsample=0.8,
                random_state=42,
                n_jobs=1,
                verbose=-1
            )
        else:
            return RandomForestRegressor(
                n_estimators=100,
                max_depth=10,
                min_samples_split=5,
                min_samples_leaf=2,
                max_features="sqrt",
                random_state=42,
                n_jobs=1,
            )

    def _tune_hyperparameters(self, X_train, y_train):
        """Tune hyperparameters using GridSearchCV."""
        logger.info("Starting hyperparameter tuning with GridSearchCV...")

        if self.model_type == "xgboost" and HAS_XGBOOST:
            model = XGBRegressor(random_state=42, verbosity=0)
            param_grid = {
                "n_estimators": [100, 300],
                "max_depth": [4, 8],
                "learning_rate": [0.05, 0.1],
            }
        elif self.model_type == "lightgbm":
            model = lgb.LGBMRegressor(random_state=42, verbose=-1)
            param_grid = {
                "n_estimators": [100, 300],
                "max_depth": [4, 8],
                "learning_rate": [0.05, 0.1],
            }
        else:
            model = RandomForestRegressor(random_state=42)
            param_grid = {
                "n_estimators": [100, 300],
                "max_depth": [10, 20],
                "min_samples_split": [2, 5],
            }

        grid_search = GridSearchCV(
            estimator=model,
            param_grid=param_grid,
            cv=3,
            scoring="r2",
            n_jobs=-1,
            verbose=1,
        )
        grid_search.fit(X_train, y_train)

        logger.info(f"Best params | R²={grid_search.best_score_:.4f} | params={grid_search.best_params_}")

        return grid_search.best_estimator_

    def get_feature_importance(self) -> dict[str, float]:
        """Get feature importance from the trained model."""
        if not self.is_trained:
            return {}

        importances = self.model.feature_importances_
        feature_names = self.feature_engine.get_feature_names()

        importance_dict = dict(zip(feature_names, importances))
        return dict(sorted(importance_dict.items(), key=lambda x: x[1], reverse=True))

    def save(self, directory: str = None):
        """Save trained model and feature engine."""
        if directory is None:
            directory = str(get_settings().model_path)

        path = Path(directory)
        path.mkdir(parents=True, exist_ok=True)

        model_name = f"cost_{self.model_type}_model.joblib"
        joblib.dump(self.model, path / model_name)
        joblib.dump(self.metrics, path / "cost_metrics.joblib")
        self.feature_engine.save(str(path))

        logger.info(f"Cost model saved | path={path / model_name}")

    def load(self, directory: str = None):
        """Load a previously trained model."""
        if directory is None:
            directory = str(get_settings().model_path)

        path = Path(directory)
        model_name = f"cost_{self.model_type}_model.joblib"

        if not (path / model_name).exists():
            # Try the other model type
            alt_type = "random_forest" if self.model_type == "xgboost" else "xgboost"
            alt_name = f"cost_{alt_type}_model.joblib"
            if (path / alt_name).exists():
                model_name = alt_name
                self.model_type = alt_type
            else:
                raise FileNotFoundError(f"No cost model found in {path}")

        self.model = joblib.load(path / model_name)
        self.feature_engine.load(str(path))

        metrics_file = path / "cost_metrics.joblib"
        if metrics_file.exists():
            self.metrics = joblib.load(metrics_file)

        self.is_trained = True
        logger.info(f"Cost model loaded | type={self.model_type}")


def compare_models(df: pd.DataFrame) -> dict:
    """
    Train and compare both Random Forest and XGBoost for cost prediction.

    Returns:
        Comparison dictionary with metrics for each model
    """
    results = {}

    for model_type in ["random_forest", "xgboost", "lightgbm"]:
        try:
            predictor = CostPredictor(model_type=model_type)
            metrics = predictor.train(df)
            results[model_type] = {
                "metrics": metrics,
                "feature_importance": predictor.get_feature_importance(),
            }
            predictor.save()
        except Exception as e:
            logger.error(f"Failed to train {model_type} | error={e}")
            results[model_type] = {"error": str(e)}

    # Determine best model
    best_model = max(
        [k for k, v in results.items() if "metrics" in v],
        key=lambda k: results[k]["metrics"].get("test_r2", 0),
        default="random_forest"
    )
    results["best_model"] = best_model

    logger.info(f"Model comparison complete | best={best_model}")
    return results
