"""
Time Prediction Model
----------------------
Predicts construction duration (labor hours) per BIM element.
Incorporates labor productivity factors, crew sizes, and
floor-level productivity degradation.

Uses the same ML framework as the cost model with time-specific
feature adjustments.
"""

import numpy as np
import pandas as pd
import joblib
from pathlib import Path
from typing import Optional
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.model_selection import cross_val_score, train_test_split, GridSearchCV
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from app.utils import get_logger
from app.config import get_settings
from app.core.feature_engine import BIMFeatureEngine, TIME_TARGET

logger = get_logger("time_model")

try:
    from xgboost import XGBRegressor
    HAS_XGBOOST = True
except ImportError:
    HAS_XGBOOST = False

try:
    import optuna
    HAS_OPTUNA = True
except ImportError:
    HAS_OPTUNA = False

# ─── Labor Productivity Constants (Indian Construction Standards) ──

CREW_SIZES = {
    "IfcFooting": 8,
    "IfcColumn": 6,
    "IfcBeam": 6,
    "IfcSlab": 10,
    "IfcWall": 4,
    "IfcDoor": 2,
    "IfcWindow": 2,
    "IfcStair": 6,
    "IfcRoof": 8,
    "IfcRailing": 3,
    "IfcCurtainWall": 4,
}

# Productivity degradation per floor (L&T empirical data)
FLOOR_PRODUCTIVITY_FACTOR = {
    0: 1.00,   # Ground floor baseline
    1: 1.00,
    2: 1.05,
    3: 1.08,
    4: 1.12,
    5: 1.15,
    6: 1.18,
    7: 1.22,
    8: 1.25,
    9: 1.30,
    10: 1.35,
}


class TimePredictor:
    """
    Construction time/duration prediction using ensemble ML models.

    Predicts labor hours per element, incorporating:
    - Element type and geometry
    - Material workability
    - Floor level productivity factors
    - Crew size optimization
    """

    def __init__(self, model_type: str = "xgboost"):
        supported = ["xgboost", "random_forest", "gradient_boosting"]
        self.model_type = model_type if model_type in supported else "random_forest"
        if self.model_type == "xgboost" and not HAS_XGBOOST:
            self.model_type = "gradient_boosting"
        self.model = None
        self.feature_engine = BIMFeatureEngine()
        self.metrics: dict = {}
        self.is_trained = False

    def train(self, df: pd.DataFrame, tune_hyperparams: bool = False) -> dict:
        """
        Train the time prediction model.

        Args:
            df: Raw BIM element DataFrame with time labels
            tune_hyperparams: Whether to run Optuna tuning

        Returns:
            Dictionary of evaluation metrics
        """
        logger.info(f"Training time model | type={self.model_type} | rows={len(df)}")

        # Enrich with time-specific features
        df = self._add_time_features(df)

        # Feature engineering
        X, y = self.feature_engine.fit_transform(df, target=TIME_TARGET)

        # Filter out zero-duration elements
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
        y_pred_test = self.model.predict(X_test)

        self.metrics = {
            "train_r2": round(r2_score(y_train, self.model.predict(X_train)), 4),
            "test_r2": round(r2_score(y_test, y_pred_test), 4),
            "test_rmse": round(np.sqrt(mean_squared_error(y_test, y_pred_test)), 2),
            "test_mae": round(mean_absolute_error(y_test, y_pred_test), 2),
        }

        # Cross-validation
        cv_scores = cross_val_score(self.model, X, y, cv=5, scoring="r2")
        self.metrics["cv_r2_mean"] = round(cv_scores.mean(), 4)
        self.metrics["cv_r2_std"] = round(cv_scores.std(), 4)

        self.is_trained = True
        logger.info(f"Time model trained | R²={self.metrics['test_r2']} | RMSE={self.metrics['test_rmse']}")

        return self.metrics

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        """Predict labor hours for new BIM elements."""
        if not self.is_trained:
            raise RuntimeError("Model not trained. Call train() first or load a saved model.")

        df = self._add_time_features(df)
        X = self.feature_engine.transform(df)
        predictions = self.model.predict(X)

        # Ensure non-negative and apply floor factor
        predictions = np.maximum(predictions, 0)
        return predictions

    def predict_with_details(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Predict with detailed breakdown: labor hours, crew-days, calendar days.

        Returns:
            DataFrame with prediction columns added
        """
        df = df.copy()
        df = self._add_time_features(df)
        predictions = self.predict(df)

        df["predicted_labor_hours"] = predictions
        df["crew_size"] = df["ifc_type"].map(CREW_SIZES).fillna(4)
        df["crew_days"] = (df["predicted_labor_hours"] / 8.0).round(2)  # 8-hour work day
        df["calendar_days"] = (df["crew_days"] / df["crew_size"]).round(2)

        return df

    def _add_time_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add time-specific features to the dataset."""
        df = df.copy()

        # Crew size by element type
        df["crew_size"] = df["ifc_type"].map(CREW_SIZES).fillna(4)

        # Floor productivity factor
        storey_map = {name: idx for idx, name in enumerate(sorted(
            df["storey"].unique(),
            key=lambda s: df[df["storey"] == s]["storey_elevation"].mean()
            if "storey_elevation" in df.columns else 0
        ))}
        df["floor_index"] = df["storey"].map(storey_map).fillna(0).astype(int)
        df["productivity_factor"] = df["floor_index"].map(
            lambda x: FLOOR_PRODUCTIVITY_FACTOR.get(min(x, 10), 1.35)
        )

        return df

    def _build_default_model(self):
        """Build model with default hyperparameters."""
        if self.model_type == "xgboost" and HAS_XGBOOST:
            return XGBRegressor(
                n_estimators=100,
                max_depth=5,
                learning_rate=0.05,
                subsample=0.8,
                colsample_bytree=0.8,
                reg_alpha=0.1,
                reg_lambda=1.0,
                random_state=42,
                n_jobs=1,
                verbosity=0,
            )
        elif self.model_type == "gradient_boosting":
            return GradientBoostingRegressor(
                n_estimators=100,
                max_depth=5,
                learning_rate=0.05,
                subsample=0.8,
                random_state=42,
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
                "max_depth": [4, 7],
                "learning_rate": [0.05, 0.1],
            }
        elif self.model_type == "gradient_boosting":
            model = GradientBoostingRegressor(random_state=42)
            param_grid = {
                "n_estimators": [100, 300],
                "max_depth": [4, 7],
                "learning_rate": [0.05, 0.1],
            }
        else:
            model = RandomForestRegressor(random_state=42)
            param_grid = {
                "n_estimators": [100, 300],
                "max_depth": [8, 15],
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

        model_name = f"time_{self.model_type}_model.joblib"
        joblib.dump(self.model, path / model_name)
        joblib.dump(self.metrics, path / "time_metrics.joblib")
        self.feature_engine.save(str(path))
        logger.info(f"Time model saved | path={path / model_name}")

    def load(self, directory: str = None):
        """Load a previously trained model."""
        if directory is None:
            directory = str(get_settings().model_path)
        path = Path(directory)

        model_name = f"time_{self.model_type}_model.joblib"
        if not (path / model_name).exists():
            alt_type = "random_forest" if self.model_type == "xgboost" else "xgboost"
            alt_name = f"time_{alt_type}_model.joblib"
            if (path / alt_name).exists():
                model_name = alt_name
                self.model_type = alt_type
            else:
                raise FileNotFoundError(f"No time model found in {path}")

        self.model = joblib.load(path / model_name)
        self.feature_engine.load(str(path))

        metrics_file = path / "time_metrics.joblib"
        if metrics_file.exists():
            self.metrics = joblib.load(metrics_file)

        self.is_trained = True
        logger.info(f"Time model loaded | type={self.model_type}")
