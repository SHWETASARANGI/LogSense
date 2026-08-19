// client.ts
//
// Thin, typed wrapper around the LogSense backend API (backend/app/main.py).
// This is the ONLY place that knows the base URL / fetch mechanics - every
// hook and component calls through here, never fetch() directly.

import type {
  Anomaly,
  AnomalyFilters,
  AnomalyStatus,
  DashboardSummary,
  LogEntry,
  ModelStatus,
  RetrainResponse,
} from "./types";

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(res.status, body.detail ?? `Request failed: ${res.status}`);
  }
  return res.json() as Promise<T>;
}

function buildQuery(params: Record<string, string | number | undefined>): string {
  const entries = Object.entries(params).filter(([, v]) => v !== undefined);
  if (entries.length === 0) return "";
  const usp = new URLSearchParams(entries as [string, string][]);
  return `?${usp.toString()}`;
}

export const api = {
  getDashboard: (lookbackHours = 24) =>
    request<DashboardSummary>(`/dashboard/${buildQuery({ lookback_hours: lookbackHours })}`),

  listAnomalies: (filters: AnomalyFilters = {}) =>
    request<Anomaly[]>(`/anomalies/${buildQuery(filters as Record<string, string | number | undefined>)}`),

  getAnomaly: (id: number) => request<Anomaly>(`/anomalies/${id}`),

  updateAnomalyStatus: (id: number, status: AnomalyStatus) =>
    request<Anomaly>(`/anomalies/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    }),

  getModelStatus: () => request<ModelStatus>("/model/status"),

  retrainModel: (params: { contamination?: number; n_estimators?: number } = {}) =>
    request<RetrainResponse>("/model/retrain", {
      method: "POST",
      body: JSON.stringify(params),
    }),

  listLogs: (
    filters: {
      service_name?: string;
      log_level?: string;
      limit?: number;
      offset?: number;
    } = {}
  ) => request<LogEntry[]>(`/logs/${buildQuery(filters)}`),
};

export { ApiError };
