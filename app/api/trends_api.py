from fastapi import APIRouter

from app.analytics.trend_engine import build_trend_report


router = APIRouter(
    prefix="/api",
    tags=["Trends"],
)


@router.get("/trends")
def get_trends():
    report = build_trend_report()

    summary = report["summary"]

    return {
        "status": "success",
        "latest_date": str(summary["latest_date"]),
        "summary": {
            "total_cases": int(summary["total_cases"]),
            "locations": int(summary["locations"]),
            "categories": int(summary["categories"]),
        },
        "category_growth": report["category_growth"].to_dict(
            orient="records"
        ),
        "location_growth": report["location_growth"].to_dict(
            orient="records"
        ),
        "emerging_signals": report["emerging_signals"].to_dict(
            orient="records"
        ),
    }