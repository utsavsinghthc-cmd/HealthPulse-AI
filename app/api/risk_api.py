from fastapi import APIRouter

from app.analytics.risk_engine import build_risk_report


router = APIRouter(
    prefix="/api",
    tags=["Risks"],
)


@router.get("/risks")
def get_risks():
    report = build_risk_report()

    risk_scores = report["risk_scores"]
    high_risk = report["high_risk"]

    return {
        "status": "success",
        "latest_date": str(report["latest_date"]),
        "total_signals": int(len(risk_scores)),
        "high_risk_signals": int(len(high_risk)),
        "risk_distribution": {
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
        "risk_scores": risk_scores.to_dict(
            orient="records"
        ),
        "high_risk": high_risk.to_dict(
            orient="records"
        ),
    }