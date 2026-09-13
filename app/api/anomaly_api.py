from fastapi import APIRouter

from app.analytics.anomaly_engine import build_anomaly_report


router = APIRouter(
    prefix="/api",
    tags=["Anomalies"],
)


@router.get("/anomalies")
def get_anomalies():
    report = build_anomaly_report()

    latest = report["latest"]
    alerts = report["alerts"]

    return {
        "status": "success",
        "latest_date": str(report["latest_date"]),
        "active_anomalies": int(len(alerts)),
        "latest_signals": latest.to_dict(
            orient="records"
        ),
        "alerts": alerts.to_dict(
            orient="records"
        ),
    }