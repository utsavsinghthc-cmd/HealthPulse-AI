from pathlib import Path
from app.api.location_api import router as location_router

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.database.database import initialize_database, get_report_count

from app.analytics.trend_engine import build_trend_report
from app.analytics.risk_engine import build_risk_report
from app.analytics.anomaly_engine import build_anomaly_report
from app.analytics.cluster_engine import build_cluster_report
from app.analytics.forecast_engine import build_forecast_report
from app.analytics.intelligence_engine import build_intelligence_report

from app.api.trends_api import router as trends_router
from app.api.anomaly_api import router as anomaly_router
from app.api.cluster_api import router as cluster_router
from app.api.risk_api import router as risk_router
from app.api.forecast_api import router as forecast_router
from app.api.intelligence_api import router as intelligence_router
from app.api.upload_api import router as upload_router


# =========================================
# PATHS
# =========================================

BASE_DIR = Path(__file__).resolve().parents[1]

FRONTEND_DIR = BASE_DIR / "frontend"


# =========================================
# FASTAPI APP
# =========================================

app = FastAPI(
    title="HealthPulse AI",
    description=(
        "AI-Powered Community Health Intelligence "
        "& Early-Warning Platform"
    ),
    version="1.0.0",
)


# =========================================
# CORS
# =========================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================
# FRONTEND STATIC FILES
# =========================================

app.mount(
    "/static",
    StaticFiles(directory=FRONTEND_DIR),
    name="static",
)


# =========================================
# API ROUTERS
# =========================================

app.include_router(trends_router)
app.include_router(anomaly_router)
app.include_router(cluster_router)
app.include_router(risk_router)
app.include_router(forecast_router)
app.include_router(intelligence_router)
app.include_router(upload_router)
app.include_router(location_router)

# =========================================
# STARTUP
# =========================================

@app.on_event("startup")
def startup_event():
    initialize_database()


# =========================================
# FRONTEND
# =========================================

@app.get("/", include_in_schema=False)
def serve_dashboard():
    return FileResponse(
        FRONTEND_DIR / "index.html"
    )


# =========================================
# HEALTH
# =========================================

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "service": "HealthPulse AI",
        "version": "1.0.0",
    }


# =========================================
# OVERVIEW
# =========================================

@app.get("/api/overview")
def get_overview():

    trend_report = build_trend_report()

    risk_report = build_risk_report()

    anomaly_report = build_anomaly_report()

    cluster_report = build_cluster_report()

    forecast_report = build_forecast_report()

    intelligence_report = (
        build_intelligence_report()
    )


    summary = trend_report["summary"]

    risk_scores = risk_report["risk_scores"]

    alerts = anomaly_report["alerts"]

    clusters = cluster_report["clusters"]

    forecasts = forecast_report["summaries"]

    intelligence = (
        intelligence_report["intelligence"]
    )


    return {

        "status": "success",

        "latest_date":
            str(summary["latest_date"]),

        "total_reports":
            int(get_report_count()),

        "locations":
            int(summary["locations"]),

        "categories":
            int(summary["categories"]),

        "risk": {

            "critical":
                int(
                    (
                        risk_scores["risk_level"]
                        == "CRITICAL"
                    ).sum()
                ),

            "high":
                int(
                    (
                        risk_scores["risk_level"]
                        == "HIGH"
                    ).sum()
                ),

            "moderate":
                int(
                    (
                        risk_scores["risk_level"]
                        == "MODERATE"
                    ).sum()
                ),

            "low":
                int(
                    (
                        risk_scores["risk_level"]
                        == "LOW"
                    ).sum()
                ),
        },

        "active_anomalies":
            int(len(alerts)),

        "high_risk_clusters":
            int(
                (
                    clusters["cluster_level"]
                    == "HIGH"
                ).sum()
            ),

        "rising_forecasts":
            int(
                (
                    forecasts["direction"]
                    == "RISING"
                ).sum()
            ),

        "priority_signals":
            int(
                intelligence["priority"]
                .isin(
                    ["CRITICAL", "HIGH"]
                )
                .sum()
            ),

        "top_signal": (

            intelligence.iloc[0].to_dict()

            if not intelligence.empty

            else None
        ),
    }