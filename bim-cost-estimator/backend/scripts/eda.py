import sys
import os
import argparse
from pathlib import Path

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from app.core.synthetic_data import generate_synthetic_bim_data
from app.utils import get_logger

logger = get_logger("eda")

def ensure_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)

def generate_eda_reports(df: pd.DataFrame, output_dir: str = "reports/eda"):
    """Generate exploratory data analysis visualizations."""
    out_path = Path(output_dir)
    ensure_dir(out_path)
    
    logger.info(f"Generating EDA reports from DataFrame with {len(df)} rows")
    
    # Set style
    sns.set_theme(style="whitegrid", palette="muted")
    
    # 1. Distribution of Target Variables
    plt.figure(figsize=(12, 5))
    
    plt.subplot(1, 2, 1)
    sns.histplot(df['qto_estimated_cost'], kde=True, bins=30)
    plt.title("Distribution of Estimated Cost")
    
    plt.subplot(1, 2, 2)
    sns.histplot(df['estimated_labor_hours'], kde=True, bins=30)
    plt.title("Distribution of Estimated Labor Hours")
    
    plt.tight_layout()
    plt.savefig(out_path / "target_distributions.png", dpi=300)
    plt.close()
    
    # 2. Correlation Heatmap (Numeric)
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    if len(numeric_cols) > 1:
        plt.figure(figsize=(12, 10))
        corr = df[numeric_cols].corr()
        mask = np.triu(np.ones_like(corr, dtype=bool))
        sns.heatmap(corr, mask=mask, annot=False, cmap="coolwarm", center=0,
                    square=True, linewidths=.5, cbar_kws={"shrink": .5})
        plt.title("Numeric Features Correlation Matrix")
        plt.tight_layout()
        plt.savefig(out_path / "correlation_heatmap.png", dpi=300)
        plt.close()
        
    # 3. Categorical Boxplots against Target
    if 'material' in df.columns:
        plt.figure(figsize=(12, 6))
        sns.boxplot(x='material', y='qto_estimated_cost', data=df)
        plt.xticks(rotation=45, ha='right')
        plt.title("Estimated Cost by Material")
        plt.tight_layout()
        plt.savefig(out_path / "cost_by_material.png", dpi=300)
        plt.close()

    if 'ifc_type' in df.columns:
        plt.figure(figsize=(12, 6))
        sns.boxplot(x='ifc_type', y='qto_estimated_cost', data=df)
        plt.xticks(rotation=45, ha='right')
        plt.title("Estimated Cost by IFC Element Type")
        plt.tight_layout()
        plt.savefig(out_path / "cost_by_element_type.png", dpi=300)
        plt.close()

    # 4. Pairplot of key features
    key_features = ['volume', 'area', 'qto_estimated_cost', 'estimated_labor_hours']
    available_features = [f for f in key_features if f in df.columns]
    
    if len(available_features) > 1:
        # Sample data if too large to avoid slow plotting
        plot_df = df.sample(n=min(1000, len(df)), random_state=42)
        if 'ifc_type' in df.columns:
            sns.pairplot(plot_df, vars=available_features, hue='ifc_type', corner=True, plot_kws={'alpha':0.5})
        else:
            sns.pairplot(plot_df, vars=available_features, corner=True, plot_kws={'alpha':0.5})
        plt.savefig(out_path / "key_features_pairplot.png", dpi=300)
        plt.close()

    logger.info(f"EDA plots saved successfully to {out_path.absolute()}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate EDA Reports for BIM Data")
    parser.add_argument("--csv", type=str, help="Path to input CSV data. If not provided, synthetic data will be generated.")
    parser.add_argument("--out", type=str, default="reports/eda", help="Output directory for plots")
    args = parser.parse_args()

    if args.csv:
        logger.info(f"Loading data from {args.csv}")
        df = pd.read_csv(args.csv)
    else:
        logger.info("Generating synthetic dataset (2000 records) for EDA...")
        synthetic_data = generate_synthetic_bim_data(project_id="EDA_Demo", num_elements=2000, seed=42)
        df = pd.DataFrame(synthetic_data)
        
        # We need targets for EDA plots
        from app.core.quantity_takeoff import compute_qto
        synthetic_data = compute_qto(synthetic_data)
        df = pd.DataFrame(synthetic_data)

    generate_eda_reports(df, args.out)
