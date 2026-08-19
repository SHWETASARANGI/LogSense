"""
main.py
 
LogSense FastAPI application entrypoint. Wires together the DB, the model
registry, and all API routers. The frontend talks ONLY to this API - never
directly to the ML model or the database.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import anomalies, dashboard, logs, model as model_routes
from app.db.database import SessionLocal, init_db
from app.services import model_registry

app = FastAPI(
    title="LogSense API",
    description="MLOps-oriented log monitoring and anomaly detection platform.",
    version="0.1.0",
)

# Allow the local Vite/React dev servers to call this API during development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(anomalies.router)
app.include_router(dashboard.router)
app.include_router(logs.router)
app.include_router(model_routes.router)


@app.on_event("startup")
def on_startup():
    init_db()

    # Best-effort: if a model has already been trained (models/isolation_forest/
    # exists), make sure the DB's model_metadata table reflects it. If no model
    # has been trained yet, this is expected to fail silently - GET /model/status
    # will report 404 until POST /model/retrain or ml/train.py is run.
    db = SessionLocal()
    try:
        model_registry.sync_model_metadata(db)
    except FileNotFoundError:
        print("[main] No trained model found yet. Run ml/train.py or POST /model/retrain.")
    finally:
        db.close()


@app.get("/health", tags=["health"])
def health_check():
    return {"status": "ok"}