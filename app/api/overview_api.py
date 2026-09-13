from fastapi import APIRouter

from app.database.database import get_connection, get_report_count
from app.analytics.trend_engine import build_trend_report
from app.analytics.risk_engine import build_risk_report
from app.analytics.anomaly_engine import build_anomaly_report
from app.analytics.cluster_engine import build_cluster_report
from app.analytics.forecast_engine import build_forecast_report
from app.analytics.intelligence_engine import build_intelligence_report


router = APIRouter(
    prefix="/api",
    tags=["Overview"],
)


@router.get("/overview")
def get_overview():
    trend_report = build_trend_report()
    risk_report = build_risk_report()
    anomaly_report = build_anomaly_report()
    cluster_report = build_cluster_report()
    forecast_report = build_forecast_report()
    intelligence_report = build_intelligence_report()

    summary = trend_report["summary"]
    risk_scores = risk_report["risk_scores"]
    high_risk = risk_report["high_risk"]
    alerts = anomaly_report["alerts"]
    clusters = cluster_report["clusters"]
    forecasts = forecast_report["summaries"]
    intelligence = intelligence_report["intelligence"]

    return {
        "status": "success",
        "latest_date": str(summary["latest_date"]),
        "total_reports": int(get_report_count()),
        "locations": int(summary["locations"]),
        "categories": int(summary["categories"]),

        "risk": {
            "critical": int(
                (risk_scores["risk_level"] == "CRITICAL").sum()
            ),
            "high": int(
                (risk_scores["risk_level"] == "HIGH").sum()
            ),
            "moderate": int(
                (risk_scores["risk_level"] == "MODERATE").sum()
            ),
            "low": int(
                (risk_scores["risk_level"] == "LOW").sum()
            ),
        },

        "active_anomalies": int(len(alerts)),

        "high_risk_clusters": int(
            (clusters["cluster_level"] == "HIGH").sum()
        ),

        "rising_forecasts": int(
            (forecasts["direction"] == "RISING").sum()
        ),

        "priority_signals": int(
            intelligence["priority"].isin(
                ["CRITICAL", "HIGH"]
            ).sum()
        ),

        "top_signal": (
            intelligence.iloc[0].to_dict()
            if not intelligence.empty
            else None
        ),
    }
