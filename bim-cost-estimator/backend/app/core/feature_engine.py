"""
Feature Engineering Pipeline
------------------------------
Production-grade feature engineering for BIM cost and time prediction.
Handles missing values, encodes categoricals, normalizes numerics,
and creates derived features that capture construction complexity.

Pipeline is serializable with joblib for production inference.
"""

import numpy as np
import pandas as pd
from typing import Optional
from sklearn.preprocessing import StandardScaler, LabelEncoder, OneHotEncoder
from sklearn.impute import SimpleImputer
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
import joblib
from pathlib import Path
from app.utils import get_logger
from app.config import get_settings

logger = get_logger("feature_engine")

# ─── Feature Definitions ─────────────────────────────────────────

NUMERIC_FEATURES = [
    "area", "volume", "length", "width", "height",
    "thickness", "perimeter", "weight",
    "storey_elevation", "primary_quantity",
    "unit_rate", "labor_productivity",
]

CATEGORICAL_FEATURES = [
    "ifc_type", "material", "storey",
]

# Target columns
COST_TARGET = "qto_estimated_cost"
TIME_TARGET = "estimated_labor_hours"

# Derived features to create
DERIVED_FEATURES = [
    "volume_to_area_ratio",
    "element_complexity_score",
    "floor_level_factor",
    "material_density_factor",
    "cost_per_unit_volume",
    "surface_to_volume_ratio",
    "aspect_ratio",
    "is_structural",
    "storey_index",
    "labor_intensity",
    "material_cost_factor",
]


class BIMFeatureEngine:
    """
    End-to-end feature engineering pipeline for BIM element data.

    Usage:
        engine = BIMFeatureEngine()
        X_train, y_train = engine.fit_transform(train_df, target="qto_estimated_cost")
        X_test = engine.transform(test_df)
        engine.save("path/to/save")
    """

    def __init__(self):
        self.numeric_imputer = SimpleImputer(strategy="median")
        self.scaler = StandardScaler()
        self.label_encoders: dict[str, LabelEncoder] = {}
        self.feature_names: list[str] = []
        self.is_fitted = False
        self._storey_order = {}

    def fit_transform(self, df: pd.DataFrame, target: str = COST_TARGET) -> tuple[np.ndarray, np.ndarray]:
        """
        Fit the pipeline on training data and transform it.

        Args:
            df: Raw BIM element DataFrame
            target: Target column name

        Returns:
            (X_transformed, y_target) tuple
        """
        logger.info(f"Fitting feature engine | rows={len(df)} | target={target}")

        # Step 1: Clean and validate
        df = self._clean_data(df)

        # Step 2: Create derived features
        df = self._create_derived_features(df)

        # Step 3: Encode categoricals
        df = self._fit_encode_categoricals(df)

        # Step 4: Select features
        feature_cols = self._get_feature_columns(df)
        X = df[feature_cols].copy()

        # Step 5: Impute missing numerics
        X_imputed = pd.DataFrame(
            self.numeric_imputer.fit_transform(X),
            columns=feature_cols,
            index=X.index,
        )

        # Step 6: Scale features
        X_scaled = self.scaler.fit_transform(X_imputed)

        # Extract target
        y = df[target].values if target in df.columns else np.zeros(len(df))

        self.feature_names = feature_cols
        self.is_fitted = True

        logger.info(f"Feature engine fitted | features={len(feature_cols)} | samples={len(X_scaled)}")
        return X_scaled, y

    def transform(self, df: pd.DataFrame) -> np.ndarray:
        """Transform new data using the fitted pipeline."""
        if not self.is_fitted:
            raise RuntimeError("Feature engine not fitted. Call fit_transform() first.")

        df = self._clean_data(df)
        df = self._create_derived_features(df)
        df = self._encode_categoricals(df)

        feature_cols = self.feature_names
        X = df[feature_cols].copy()

        # Handle any new columns that may be missing
        for col in feature_cols:
            if col not in X.columns:
                X[col] = 0

        X = X[feature_cols]
        X_imputed = pd.DataFrame(
            self.numeric_imputer.transform(X),
            columns=feature_cols,
        )
        X_scaled = self.scaler.transform(X_imputed)

        return X_scaled

    def get_feature_names(self) -> list[str]:
        """Return the list of feature names after transformation."""
        return self.feature_names

    def _clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean raw data: handle nulls, remove irrelevant columns."""
        df = df.copy()

        # Fill missing materials
        df["material"] = df["material"].fillna("Unknown")
        df["storey"] = df["storey"].fillna("Unknown")
        df["ifc_type"] = df["ifc_type"].fillna("Unknown")

        # Remove elements with all zero quantities
        qty_cols = ["area", "volume", "length"]
        available_qty = [c for c in qty_cols if c in df.columns]
        if available_qty:
            df[available_qty] = df[available_qty].fillna(0)
            mask = df[available_qty].sum(axis=1) > 0
            dropped = (~mask).sum()
            if dropped > 0:
                logger.info(f"Dropped {dropped} elements with zero quantities")
            df = df[mask].reset_index(drop=True)

        return df

    def _create_derived_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create construction-domain derived features."""
        df = df.copy()

        # Volume-to-Area ratio (indicates element thickness/depth)
        area = df.get("area", pd.Series(0, index=df.index)).replace(0, np.nan)
        volume = df.get("volume", pd.Series(0, index=df.index))
        df["volume_to_area_ratio"] = (volume / area).fillna(0)

        # Surface-to-Volume ratio (complexity indicator)
        df["surface_to_volume_ratio"] = (area / volume.replace(0, np.nan)).fillna(0)

        # Aspect ratio (length/height or width/height)
        height = df.get("height", pd.Series(1, index=df.index)).replace(0, 1)
        length = df.get("length", pd.Series(1, index=df.index))
        df["aspect_ratio"] = (length / height).fillna(1)

        # Element complexity score (multi-factor)
        df["element_complexity_score"] = self._compute_complexity(df)

        # Floor level factor (productivity decreases with height)
        elevation = df.get("storey_elevation", pd.Series(0, index=df.index)).fillna(0)
        df["floor_level_factor"] = 1.0 + (elevation.clip(lower=0) / 100.0)

        # Material density factor
        density_map = {
            "Reinforced Concrete": 2500, "Concrete": 2300, "Steel": 7850,
            "Structural Steel": 7850, "Brick": 1800, "Timber": 600,
            "Glass": 2500, "Aluminum": 2700, "Masonry": 1900,
            "Precast Concrete": 2400, "Gypsum": 1100, "UPVC": 1400,
            "Concrete Block": 2000, "Composite": 2000,
        }
        df["material_density_factor"] = df["material"].map(density_map).fillna(2000) / 2500

        # Cost per unit volume
        cost = df.get("qto_estimated_cost", pd.Series(0, index=df.index))
        df["cost_per_unit_volume"] = (cost / volume.replace(0, np.nan)).fillna(0)

        # Is structural (binary feature)
        structural_types = {"IfcColumn", "IfcBeam", "IfcSlab", "IfcFooting", "IfcStair"}
        df["is_structural"] = df["ifc_type"].isin(structural_types).astype(int)

        # Storey index (ordinal encoding by elevation)
        unique_storeys = df.sort_values("storey_elevation")["storey"].unique()
        storey_map = {s: i for i, s in enumerate(unique_storeys)}
        # Material cost factor (derived from density and complexity)
        df["material_cost_factor"] = df["material_density_factor"] * df["element_complexity_score"]
        
        # Labor intensity (derived from complexity and volume/area ratio)
        df["labor_intensity"] = df["element_complexity_score"] * (1 + df["volume_to_area_ratio"]) * df["floor_level_factor"]

        return df

    def _compute_complexity(self, df: pd.DataFrame) -> pd.Series:
        """
        Multi-factor element complexity score (0-1 scale).
        Considers geometry, material type, and floor level.
        """
        scores = pd.Series(0.0, index=df.index)

        # Type complexity
        type_complexity = {
            "IfcStair": 0.9, "IfcCurtainWall": 0.85, "IfcRoof": 0.8,
            "IfcColumn": 0.6, "IfcBeam": 0.6, "IfcFooting": 0.55,
            "IfcSlab": 0.5, "IfcWall": 0.4, "IfcWindow": 0.35,
            "IfcDoor": 0.3, "IfcRailing": 0.25,
        }
        scores += df["ifc_type"].map(type_complexity).fillna(0.5) * 0.4

        # Volume complexity (larger = more complex)
        vol = df.get("volume", pd.Series(0, index=df.index)).fillna(0)
        if vol.max() > 0:
            scores += (vol / vol.max()).clip(0, 1) * 0.3

        # Material complexity
        mat_complexity = {
            "Structural Steel": 0.9, "Precast Concrete": 0.8, "Composite": 0.75,
            "Reinforced Concrete": 0.6, "Glass": 0.5, "Aluminum": 0.5,
            "Timber": 0.4, "Brick": 0.3, "Masonry": 0.3, "Gypsum": 0.2,
        }
        scores += df["material"].map(mat_complexity).fillna(0.4) * 0.3

        return scores.round(4)

    def _fit_encode_categoricals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Fit and transform categorical features using LabelEncoder."""
        df = df.copy()
        for col in CATEGORICAL_FEATURES:
            if col in df.columns:
                le = LabelEncoder()
                df[f"{col}_encoded"] = le.fit_transform(df[col].astype(str))
                self.label_encoders[col] = le
        return df

    def _encode_categoricals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transform categorical features using pre-fitted encoders."""
        df = df.copy()
        for col, le in self.label_encoders.items():
            if col in df.columns:
                # Handle unseen categories
                known = set(le.classes_)
                df[col] = df[col].astype(str).apply(
                    lambda x: x if x in known else le.classes_[0]
                )
                df[f"{col}_encoded"] = le.transform(df[col].astype(str))
        return df

    def _get_feature_columns(self, df: pd.DataFrame) -> list[str]:
        """Get final feature column list after all transformations."""
        feature_cols = []

        # Numeric features
        for col in NUMERIC_FEATURES:
            if col in df.columns:
                feature_cols.append(col)

        # Derived features
        for col in DERIVED_FEATURES:
            if col in df.columns:
                feature_cols.append(col)

        # Encoded categoricals
        for col in CATEGORICAL_FEATURES:
            encoded_col = f"{col}_encoded"
            if encoded_col in df.columns:
                feature_cols.append(encoded_col)

        return feature_cols

    def save(self, directory: str):
        """Save fitted pipeline artifacts."""
        path = Path(directory)
        path.mkdir(parents=True, exist_ok=True)

        joblib.dump(self.numeric_imputer, path / "feature_imputer.joblib")
        joblib.dump(self.scaler, path / "feature_scaler.joblib")
        joblib.dump(self.label_encoders, path / "label_encoders.joblib")
        joblib.dump(self.feature_names, path / "feature_names.joblib")

        logger.info(f"Feature engine saved to {path}")

    def load(self, directory: str):
        """Load previously fitted pipeline artifacts."""
        path = Path(directory)

        self.numeric_imputer = joblib.load(path / "feature_imputer.joblib")
        self.scaler = joblib.load(path / "feature_scaler.joblib")
        self.label_encoders = joblib.load(path / "label_encoders.joblib")
        self.feature_names = joblib.load(path / "feature_names.joblib")
        self.is_fitted = True

        logger.info(f"Feature engine loaded from {path}")
