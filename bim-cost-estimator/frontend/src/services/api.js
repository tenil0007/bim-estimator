/**
 * API Service Layer
 * Centralized API client for all backend communication.
 */
import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api/v1';

const api = axios.create({
  baseURL: API_BASE,
  timeout: 120000, // 2 min timeout for large IFC files
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for logging
api.interceptors.request.use(
  (config) => {
    console.log(`[API] ${config.method?.toUpperCase()} ${config.url}`);
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const message = error.response?.data?.detail || error.message || 'An error occurred';
    console.error(`[API Error] ${message}`);
    return Promise.reject({ message, status: error.response?.status });
  }
);

// ─── IFC / BIM Data ───────────────────────────────────────────────

export const uploadIFC = async (file, projectName = null) => {
  const formData = new FormData();
  formData.append('file', file);
  const params = projectName ? `?project_name=${encodeURIComponent(projectName)}` : '';
  const response = await api.post(`/upload-ifc${params}`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (progressEvent) => {
      const pct = Math.round((progressEvent.loaded * 100) / progressEvent.total);
      console.log(`Upload: ${pct}%`);
    },
  });
  return response.data;
};

export const extractData = async (projectId, useSynthetic = false) => {
  const response = await api.get(`/extract-data/${projectId}?use_synthetic=${useSynthetic}`);
  return response.data;
};

export const listProjects = async () => {
  const response = await api.get('/projects');
  return response.data;
};

// ─── Predictions ──────────────────────────────────────────────────

export const getMaterialRates = async (materialNames) => {
  const list = Array.isArray(materialNames) ? materialNames : [materialNames];
  const materials = list.filter(Boolean).join(',') || 'Unknown';
  const response = await api.get('/material-rates', { params: { materials } });
  return response.data;
};

export const predictCost = async (projectId, modelType = 'xgboost', filters = {}) => {
  const response = await api.post('/predict-cost', {
    project_id: projectId,
    model_type: modelType,
    element_type_filter: filters.elementType || null,
    material_filter: filters.material || null,
  });
  return response.data;
};

export const predictTime = async (projectId, modelType = 'xgboost', filters = {}) => {
  const response = await api.post('/predict-time', {
    project_id: projectId,
    model_type: modelType,
    element_type_filter: filters.elementType || null,
    material_filter: filters.material || null,
  });
  return response.data;
};

export const getShapExplanation = async (projectId, model = 'cost', elementIndex = 0) => {
  const response = await api.get(
    `/shap-explanation/${projectId}?model=${model}&element_index=${elementIndex}`
  );
  return response.data;
};

// ─── Scheduling ───────────────────────────────────────────────────

export const generateSchedule = async (projectId, options = {}) => {
  const response = await api.post('/schedule', {
    project_id: projectId,
    working_hours_per_day: options.workingHours || 8,
    crew_size_multiplier: options.crewMultiplier || 1.0,
    custom_dependencies: options.dependencies || null,
  });
  return response.data;
};

// ─── Reports ──────────────────────────────────────────────────────

export const generateReport = async (projectId, options = {}) => {
  const response = await api.post('/generate-report', {
    project_id: projectId,
    include_cost: options.includeCost ?? true,
    include_time: options.includeTime ?? true,
    include_schedule: options.includeSchedule ?? true,
    include_shap: options.includeShap ?? true,
    report_title: options.title || 'BIM Cost & Time Estimation Report',
    company_name: options.company || 'Larsen & Toubro Limited',
  }, {
    responseType: 'blob',
  });

  // Trigger download
  const url = window.URL.createObjectURL(new Blob([response.data]));
  const link = document.createElement('a');
  link.href = url;
  link.setAttribute('download', `BIM_Report_${projectId}.pdf`);
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);

  return true;
};

// ─── EDA Analysis ─────────────────────────────────────────────────

export const getEdaAnalysis = async (projectId) => {
  const response = await api.get(`/eda-analysis/${projectId}`);
  return response.data;
};

// ─── Data Export ──────────────────────────────────────────────────

export const exportData = async (projectId, format = 'csv') => {
  const response = await api.get(`/export-data/${projectId}?format=${format}`, {
    responseType: 'blob',
  });
  const url = window.URL.createObjectURL(new Blob([response.data]));
  const link = document.createElement('a');
  link.href = url;
  link.setAttribute('download', `project_${projectId}.${format}`);
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
  return true;
};

export default api;
