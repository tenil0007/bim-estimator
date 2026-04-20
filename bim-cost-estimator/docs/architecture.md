# System Architecture Documentation

## AI-Driven BIM Cost & Time Estimator — L&T Construction

---

## 1. Architectural Overview

The system follows a **layered architecture** pattern with clear separation of concerns:

```
┌─────────────────────────────────────────────────┐
│           Presentation Layer (React)             │
│  Dashboard │ Charts │ Gantt │ SHAP │ Reports     │
├─────────────────────────────────────────────────┤
│             API Layer (FastAPI)                   │
│  REST Endpoints │ Validation │ Error Handling     │
├─────────────────────────────────────────────────┤
│           Business Logic Layer                    │
│  IFC Parser │ Feature Engine │ ML │ Scheduler     │
├─────────────────────────────────────────────────┤
│             Data Access Layer                     │
│  SQLAlchemy ORM │ CRUD Operations                 │
├─────────────────────────────────────────────────┤
│             Data Storage Layer                    │
│  SQLite/PostgreSQL │ File System │ Model Store    │
└─────────────────────────────────────────────────┘
```

## 2. Component Architecture

### 2.1 IFC Parser (`core/__init__.py`)
- **Input**: `.ifc` file path
- **Process**: Iterates through IfcOpenShell entity types
- **Output**: Structured list of element dictionaries
- **Fallback**: Synthetic data generator when IfcOpenShell unavailable
- **Supported Types**: IfcWall, IfcSlab, IfcBeam, IfcColumn, IfcDoor, IfcWindow, IfcRoof, IfcStair, IfcRailing, IfcFooting, IfcCurtainWall

### 2.2 Quantity Takeoff (`core/quantity_takeoff.py`)
- Computes primary quantities (area, volume, length) per element type
- Maps to Indian construction rate database
- Calculates QTO-estimated costs and labor hours
- Material-specific rate adjustments (Steel 1.8x, Precast 1.3x)

### 2.3 Feature Engineering (`core/feature_engine.py`)
- **Imputation**: Median for numeric, mode for categorical
- **Encoding**: LabelEncoder for categoricals (ifc_type, material, storey)
- **Scaling**: StandardScaler for all numeric features
- **Derived Features**:
  - `volume_to_area_ratio` — element thickness indicator
  - `element_complexity_score` — multi-factor (type + volume + material)
  - `floor_level_factor` — productivity degradation with height
  - `material_density_factor` — normalized material weight
  - `cost_per_unit_volume` — unit cost indicator
  - `surface_to_volume_ratio` — geometric complexity
  - `aspect_ratio` — length/height ratio
  - `is_structural` — binary structural classification
  - `storey_index` — ordinal floor encoding

### 2.4 ML Models (`core/cost_model.py`, `core/time_model.py`)
- **Random Forest**: 300 trees, max_depth=15, sqrt features
- **XGBoost**: 300 rounds, lr=0.05, max_depth=8, L1+L2 regularization
- **Training**: 80/20 split, 5-fold cross-validation
- **Tuning**: Optuna Bayesian optimization (50 trials)
- **Serialization**: joblib for model + feature engine artifacts

### 2.5 Scheduling Engine (`core/scheduler.py`)
- **Graph**: NetworkX DiGraph (activities as nodes, dependencies as edges)
- **Algorithm**: CPM forward + backward pass
- **Sequencing**: L&T standard construction rules (10 phases)
- **Output**: Gantt data, critical path, float/slack values

### 2.6 SHAP Explainer (`core/explainer.py`)
- **Method**: TreeExplainer for tree-based models (exact SHAP)
- **Global**: Mean |SHAP| rankings, direction analysis
- **Local**: Per-element waterfall breakdown
- **Visualization**: Beeswarm and waterfall plots (matplotlib)

### 2.7 Report Generator (`core/report_generator.py`)
- **Library**: ReportLab (PDF)
- **Branding**: L&T colors (navy blue, dark theme)
- **Sections**: Cover, Executive Summary, Cost, Time, Schedule, SHAP, Disclaimer
- **Tables**: Styled with alternating rows, header formatting

## 3. Data Flow

```
User uploads .ifc
        │
        ▼
  IfcOpenShell parse → Extract elements (type, geometry, material, storey)
        │
        ▼
  Quantity Takeoff → Map to rate database → Compute primary quantities
        │
        ▼
  Feature Engineering → Impute → Encode → Scale → Derive features
        │
        ▼
  ML Prediction → Cost per element + Time per element
        │
        ▼
  CPM Scheduling → Group into activities → Build DAG → Forward/Backward pass
        │
        ▼
  SHAP Explanation → Global importance + Local waterfall
        │
        ▼
  Dashboard → Charts, Gantt, Tables, Filters
        │
        ▼
  PDF Report → Download
```

## 4. Database Schema

- **Projects**: id, name, ifc_filename, status, timestamps
- **BIM Elements**: id, project_id, ifc_type, geometry, material, predictions
- **Schedule Activities**: id, project_id, name, duration, ES/EF/LS/LF, slack, is_critical

## 5. Security Considerations (Production)

- Input validation via Pydantic schemas
- File upload size limits (500MB)
- File type validation (.ifc, .ifczip only)
- CORS origin whitelist
- SQL injection prevention (SQLAlchemy ORM)
- Rate limiting (to be added with slowapi)
- JWT authentication (to be added for production)

## 6. Scalability Path

1. **Current**: SQLite + single process (development)
2. **Stage 1**: PostgreSQL + Gunicorn workers (production)
3. **Stage 2**: Celery + Redis for async ML tasks
4. **Stage 3**: Kubernetes + horizontal pod autoscaling
5. **Stage 4**: Model serving with MLflow/BentoML
