from fastapi import APIRouter

from app.analytics.forecast_engine import build_forecast_report


router = APIRouter(
    prefix="/api",
    tags=["Forecasts"],
)


@router.get("/forecasts")
def get_forecasts():
    report = build_forecast_report()

    summaries = report["summaries"]

    return {
        "status": "success",
        "latest_date": str(report["latest_date"]),
        "forecast_horizon_days": 7,
        "total_forecasts": int(len(summaries)),
        "direction_distribution": {
            "rising": int(
                (summaries["direction"] == "RISING").sum()
            ),
            "stable": int(
                (summaries["direction"] == "STABLE").sum()
            ),
            "declining": int(
                (summaries["direction"] == "DECLINING").sum()
            ),
        },
        "forecasts": summaries.to_dict(
            orient="records"
        ),
    }