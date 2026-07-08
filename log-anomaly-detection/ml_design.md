# LogSense — ML Design Document

## 1. Purpose

This document defines the data contracts that flow through LogSense's ML pipeline:

```
Raw Log Entry  →  Feature Window (per service, per time bucket)  →  Model Input  →  Anomaly Score
```

Everything downstream — ingestion, feature engineering, model training, the API, and the dashboard — depends on these schemas staying consistent. Changes here should be treated like a breaking API change.

---

## 2. Raw Log Schema

Each ingested log entry (simulated or real) is normalized into the following structure before storage in `data/processed/`.

| Field | Type | Nullable | Description |
|---|---|---|---|
| `timestamp` | ISO 8601 datetime (UTC) | No | When the event occurred |
| `service_name` | string | No | Logical service, e.g. `auth-service`, `payment-service`, `api-gateway` |
| `host_id` | string | No | Simulated instance/pod identifier, e.g. `host-03` |
| `log_level` | enum: `DEBUG`, `INFO`, `WARN`, `ERROR` | No | Severity of the log line |
| `status_code` | int | Yes | HTTP-like status code (200, 404, 500...); null for non-HTTP logs |
| `latency_ms` | float | Yes | Request latency in milliseconds; null if not applicable |
| `message` | string | No | Free-text log message |
| `error_type` | string | Yes | e.g. `TimeoutError`, `DBConnectionError`; set only when `log_level = ERROR` |
| `trace_id` | string | No | Simulated request/trace correlation ID |

### Sample raw log entry (JSON Lines format)

```json
{"timestamp": "2026-07-08T09:14:02.331Z", "service_name": "payment-service", "host_id": "host-03", "log_level": "ERROR", "status_code": 500, "latency_ms": 2340.5, "message": "Downstream payment gateway timeout", "error_type": "TimeoutError", "trace_id": "a1b2c3d4"}
```

### Design notes

- **Why `trace_id`:** not used in v1 features, but reserved for future work (e.g. tracing cascading failures across services). Cheap to include now, expensive to retrofit later.
- **Why nullable `status_code`/`latency_ms`:** not every log line is an HTTP request (e.g. background job logs, health checks). Keeping these nullable avoids polluting aggregates with fake zeros.
- **Storage format:** JSON Lines (`.jsonl`) for raw logs — append-friendly, human-readable, easy to simulate and stream line-by-line.

---

## 3. Feature Window Schema

Raw logs are aggregated into fixed-size time buckets, grouped by `service_name`. **One row = one `(service_name, window_start)` pair.** This is the tabular structure the ML models actually consume.

| Feature | Type | Description |
|---|---|---|
| `window_start` | datetime | Start of the time bucket (UTC) |
| `window_end` | datetime | End of the time bucket |
| `service_name` | string | Which service this row describes |
| `log_count` | int | Total logs in window |
| `error_count` | int | Count of `ERROR` level logs |
| `warn_count` | int | Count of `WARN` level logs |
| `error_rate` | float | `error_count / log_count` |
| `warn_rate` | float | `warn_count / log_count` |
| `avg_latency_ms` | float | Mean latency across logs with non-null latency |
| `p95_latency_ms` | float | 95th percentile latency |
| `p99_latency_ms` | float | 99th percentile latency |
| `status_5xx_rate` | float | Proportion of logs with `status_code` in 500–599 |
| `status_4xx_rate` | float | Proportion of logs with `status_code` in 400–499 |
| `unique_error_types` | int | Distinct `error_type` values seen in window |
| `unique_hosts` | int | Distinct `host_id` values reporting in window |
| `log_volume_delta` | float | % change in `log_count` vs. previous window for same service |

### Sample feature row (JSON)

```json
{
  "window_start": "2026-07-08T09:14:00Z",
  "window_end": "2026-07-08T09:15:00Z",
  "service_name": "payment-service",
  "log_count": 812,
  "error_count": 96,
  "warn_count": 40,
  "error_rate": 0.118,
  "warn_rate": 0.049,
  "avg_latency_ms": 410.2,
  "p95_latency_ms": 1890.0,
  "p99_latency_ms": 2410.5,
  "status_5xx_rate": 0.09,
  "status_4xx_rate": 0.03,
  "unique_error_types": 3,
  "unique_hosts": 4,
  "log_volume_delta": 2.35
}
```

In this example, `error_rate` and `log_volume_delta` are both far above baseline — a candidate anomaly (simulated traffic surge + error spike on `payment-service`).

### Storage format

Feature windows are stored as `data/processed/features.parquet` (columnar, efficient for the volume of numeric data, plays nicely with pandas/scikit-learn).

---

## 4. Design Decisions & Rationale

### 4.1 Window size: 1 minute (default, configurable)

- Fine enough to catch short bursts (error spikes, latency degradation) without waiting too long to detect them.
- Coarse enough that windows aren't dominated by single-log noise.
- Exposed as a config value (`core/config.py`) — e.g. `FEATURE_WINDOW_SECONDS = 60` — so it can be tuned per environment without code changes.

### 4.2 Per-service vs. global aggregation

Features are computed **per service**, not globally across all services. Rationale:

- A spike in `payment-service` errors should not get diluted by a quiet `auth-service` in the same window.
- This also naturally supports service-level dashboards and per-service alerting later.

**Modeling approach (v1):** train a single global Isolation Forest model, with `service_name` included as a categorical feature (one-hot or target-encoded). This keeps the pipeline simple for v1.

**Future extension:** per-service models, if services have meaningfully different "normal" baselines (e.g. `payment-service` naturally has higher latency than `auth-service`). This is a natural v2 improvement to mention in the write-up as a known limitation/next step.

### 4.3 Handling empty windows (zero traffic)

If a service produces zero logs in a given window, LogSense **emits a zero/null-filled row** rather than skipping it:

- Skipping creates time gaps that break rolling/delta calculations (e.g. `log_volume_delta`).
- A zero-traffic window is itself potentially meaningful (e.g. a service going silent could indicate an outage) — the model should be able to learn this pattern rather than have it hidden by missing data.
- Rate-based features (`error_rate`, etc.) are defined as `0` when `log_count = 0` to avoid divide-by-zero.

### 4.4 Feature scaling / normalization

Isolation Forest is not sensitive to feature scaling (it splits on raw values), so no normalization is required for that model. If/when the autoencoder (`ml/autoencoder.py`) is introduced as a second model, features will need standardization (zero mean, unit variance) fit on the training set only, since neural nets are scale-sensitive. This will be handled in a shared preprocessing step so both models can reuse the same feature table.

### 4.5 Ground truth for evaluation

Since logs are simulated, `scripts/simulate_logs.py` will inject **known, labeled anomalies** (e.g. deliberate error-rate spikes, latency degradation events, traffic surges) with their time ranges recorded separately (e.g. `data/samples/injected_anomalies.json`). This label set is *not* used for training (the model stays unsupervised) — it's used only in `ml/evaluate.py` to compute precision/recall/F1 against known anomaly windows, giving an honest way to validate model quality.

---

## 5. Model Input Contract

Whatever model is used (`isolation_forest.py`, later `autoencoder.py`), it consumes a fixed, ordered numeric feature vector derived from the feature window schema above, **excluding** identifier/time columns:

```
[log_count, error_count, warn_count, error_rate, warn_rate,
 avg_latency_ms, p95_latency_ms, p99_latency_ms,
 status_5xx_rate, status_4xx_rate,
 unique_error_types, unique_hosts, log_volume_delta,
 service_name (encoded)]
```

`window_start`, `window_end`, and `service_name` (raw string) are retained alongside predictions for storage/API/dashboard purposes, but are not fed directly into the model as raw values.

Model metadata (`models/isolation_forest/metadata.json`) will record:
- feature list and order (to guard against schema drift between train/serve)
- training data time range
- contamination rate used
- training timestamp / model version

---

## 6. Open Questions / Future Considerations

- Should window size be adaptive (e.g. shorter windows for high-traffic services)? — Deferred; fixed window is simpler for v1.
- Should `message` text be used at all (e.g. via embeddings or keyword extraction)? — Deferred; v1 is purely structured/numeric features. Worth mentioning as a future NLP extension.
- Multi-window context (e.g. rolling 5-minute averages as additional features) — worth considering once basic single-window detection is validated, to catch slower degradations rather than only instantaneous spikes.