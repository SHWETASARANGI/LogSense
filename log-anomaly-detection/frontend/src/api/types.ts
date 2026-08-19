// Types mirror backend/app/schemas/*.py exactly. Keep these in sync manually -
// if the API contract changes, update here first so TypeScript catches
// every call site that needs to change too.

export type Severity = "low" | "medium" | "high" | "critical";
export type AnomalyStatus = "new" | "acknowledged" | "resolved";

export interface Anomaly {
  id: number;
  window_start: string;
  window_end: string;
  service_name: string;
  anomaly_score: number;
  severity: Severity;
  log_count: number;
  error_rate: number;
  avg_latency_ms: number;
  p95_latency_ms: number;
  log_volume_delta: number;
  model_version: string;
  status: AnomalyStatus;
  created_at: string;
}

export interface DashboardSummary {
  lookback_hours: number;
  total_anomalies: number;
  active_anomalies: number;
  avg_anomaly_score: number;
  avg_error_rate: number;
  total_log_volume: number;
  severity_breakdown: Partial<Record<Severity, number>>;
  model_version: string | null;
  model_trained_at: string | null;
}

export interface ModelStatus {
  version: string;
  model_type: string;
  contamination: number;
  n_estimators: number | null;
  trained_at: string;
  training_data_path: string | null;
  is_active: boolean;
  anomalies_detected: number;
}

export interface RetrainResponse {
  version: string;
  trained_at: string;
  rows_used: number;
  contamination: number;
  n_estimators: number;
}

export interface LogEntry {
  id: number;
  timestamp: string;
  service_name: string;
  host_id: string;
  log_level: "DEBUG" | "INFO" | "WARN" | "ERROR";
  status_code: number | null;
  latency_ms: number | null;
  message: string;
  error_type: string | null;
  trace_id: string;
}

export interface AnomalyFilters {
  service_name?: string;
  severity?: Severity;
  status?: AnomalyStatus;
  limit?: number;
  offset?: number;
}
