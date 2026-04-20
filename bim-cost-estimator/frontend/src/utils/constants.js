/**
 * App Constants
 */

export const ELEMENT_TYPES = [
  'IfcWall', 'IfcSlab', 'IfcBeam', 'IfcColumn',
  'IfcDoor', 'IfcWindow', 'IfcRoof', 'IfcStair',
  'IfcRailing', 'IfcFooting', 'IfcCurtainWall',
];

export const MATERIALS = [
  'Reinforced Concrete', 'Structural Steel', 'Brick',
  'Timber', 'Glass', 'Aluminum', 'Masonry',
  'Precast Concrete', 'Steel', 'Gypsum', 'UPVC',
  'Concrete Block', 'Composite',
];

export const MODEL_TYPES = [
  { value: 'xgboost', label: 'XGBoost (Recommended)' },
  { value: 'random_forest', label: 'Random Forest' },
];

export const CHART_COLORS = {
  primary: ['#3b82f6', '#60a5fa', '#93c5fd', '#bfdbfe'],
  accent: ['#06d6a0', '#34d399', '#6ee7b7', '#a7f3d0'],
  warm: ['#f59e0b', '#fbbf24', '#fcd34d', '#fde68a'],
  danger: ['#ef4444', '#f87171', '#fca5a5', '#fecaca'],
  palette: [
    '#3b82f6', '#06d6a0', '#f59e0b', '#ef4444',
    '#8b5cf6', '#ec4899', '#14b8a6', '#f97316',
    '#6366f1', '#84cc16', '#0ea5e9', '#d946ef',
  ],
};

export const formatCurrency = (value) => {
  if (value >= 10000000) return `₹${(value / 10000000).toFixed(2)} Cr`;
  if (value >= 100000) return `₹${(value / 100000).toFixed(2)} L`;
  if (value >= 1000) return `₹${(value / 1000).toFixed(1)}K`;
  return `₹${value.toFixed(0)}`;
};

/** Full INR for tables (reference unit rates). */
export const formatInrFull = (value) =>
  new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: value >= 100 ? 0 : 2,
  }).format(value);

export const formatNumber = (value, decimals = 0) =>
  new Intl.NumberFormat('en-IN', { maximumFractionDigits: decimals }).format(value);

export const formatDuration = (hours) => {
  if (hours >= 24) return `${(hours / 8).toFixed(1)} days`;
  return `${hours.toFixed(1)} hrs`;
};
