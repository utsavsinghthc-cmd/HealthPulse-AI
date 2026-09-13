from fastapi import APIRouter

from app.analytics.intelligence_engine import build_intelligence_report


router = APIRouter(
    prefix="/api",
    tags=["Intelligence"],
)


@router.get("/intelligence")
def get_intelligence():
    report = build_intelligence_report()

    intelligence = report["intelligence"]

    priority_counts = {
        "critical": int(
            (intelligence["priority"] == "CRITICAL").sum()
        ),
        "high": int(
            (intelligence["priority"] == "HIGH").sum()
        ),
        "moderate": int(
            (intelligence["priority"] == "MODERATE").sum()
        ),
        "low": int(
            (intelligence["priority"] == "LOW").sum()
        ),
    }

    top_signal = (
        intelligence.iloc[0].to_dict()
        if not intelligence.empty
        else None
    )

    return {
        "status": "success",
        "latest_date": str(report["latest_date"]),
        "total_signals": int(len(intelligence)),
        "priority_distribution": priority_counts,
        "top_signal": top_signal,
        "signals": intelligence.to_dict(
            orient="records"
        ),
    }