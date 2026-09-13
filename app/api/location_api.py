from fastapi import APIRouter, HTTPException

import pandas as pd

from app.database.database import get_connection
from app.analytics.intelligence_engine import build_intelligence_report
from app.analytics.forecast_engine import build_forecast_report


router = APIRouter(
    prefix="/api",
    tags=["Location Intelligence"],
)


@router.get("/location-intelligence/{location}")
def get_location_intelligence(location: str):

    connection = get_connection()

    rows = connection.execute(
        """
        SELECT
            report_date,
            location,
            health_category,
            COUNT(*) AS case_count
        FROM medical_reports
        WHERE location = ?
        GROUP BY
            report_date,
            location,
            health_category
        ORDER BY
            report_date ASC
        """,
        (location,),
    ).fetchall()

    connection.close()

    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"No data found for location: {location}",
        )


    daily_data = pd.DataFrame(
        [dict(row) for row in rows]
    )


    daily_data["report_date"] = pd.to_datetime(
        daily_data["report_date"]
    )


    # -----------------------------------------------------
    # LOCATION SUMMARY
    # -----------------------------------------------------

    total_cases = int(
        daily_data["case_count"].sum()
    )


    latest_date = daily_data["report_date"].max()


    previous_date = latest_date - pd.Timedelta(days=13)


    recent_start = latest_date - pd.Timedelta(days=13)

    previous_start = latest_date - pd.Timedelta(days=27)

    previous_end = latest_date - pd.Timedelta(days=14)


    recent_cases = int(
        daily_data[
            daily_data["report_date"] >= recent_start
        ]["case_count"].sum()
    )


    previous_cases = int(
        daily_data[
            (
                daily_data["report_date"] >= previous_start
            )
            &
            (
                daily_data["report_date"] <= previous_end
            )
        ]["case_count"].sum()
    )


    if previous_cases > 0:

        growth_percent = (
            (
                recent_cases -
                previous_cases
            )
            /
            previous_cases
        ) * 100

    else:

        growth_percent = 0


    # -----------------------------------------------------
    # CATEGORY DISTRIBUTION
    # -----------------------------------------------------

    category_totals = (
        daily_data
        .groupby("health_category")["case_count"]
        .sum()
        .sort_values(ascending=False)
    )


    categories = [
        {
            "health_category": str(index),
            "case_count": int(value),
        }
        for index, value
        in category_totals.items()
    ]


    # -----------------------------------------------------
    # INTELLIGENCE
    # -----------------------------------------------------

    intelligence_report = (
        build_intelligence_report()
    )

    intelligence = (
        intelligence_report["intelligence"]
    )


    location_intelligence = intelligence[
        intelligence["location"] == location
    ].copy()


    signals = (
        location_intelligence
        .to_dict(orient="records")
    )


    # -----------------------------------------------------
    # FORECAST
    # -----------------------------------------------------

    forecast_report = (
        build_forecast_report()
    )

    forecasts = (
        forecast_report["summaries"]
    )


    location_forecasts = forecasts[
        forecasts["location"] == location
    ].copy()


    forecast_records = (
        location_forecasts
        .to_dict(orient="records")
    )


    # -----------------------------------------------------
    # DAILY LOCATION TREND
    # -----------------------------------------------------

    daily_location = (
        daily_data
        .groupby("report_date")["case_count"]
        .sum()
        .reset_index()
        .sort_values("report_date")
    )


    daily_records = []

    for _, row in daily_location.iterrows():

        daily_records.append(
            {
                "date": row["report_date"].strftime(
                    "%Y-%m-%d"
                ),
                "case_count": int(
                    row["case_count"]
                ),
            }
        )


    # -----------------------------------------------------
    # CATEGORY DAILY TREND
    # -----------------------------------------------------

    category_daily = []

    for category, group in (
        daily_data
        .groupby("health_category")
    ):

        group = (
            group
            .sort_values("report_date")
        )


        category_daily.append(
            {
                "health_category": str(
                    category
                ),

                "daily": [
                    {
                        "date": row[
                            "report_date"
                        ].strftime(
                            "%Y-%m-%d"
                        ),

                        "case_count": int(
                            row["case_count"]
                        ),
                    }

                    for _, row
                    in group.iterrows()
                ],
            }
        )


    return {

        "status": "success",

        "location": location,

        "latest_date": latest_date.strftime(
            "%Y-%m-%d"
        ),

        "summary": {

            "total_cases": total_cases,

            "recent_cases": recent_cases,

            "previous_cases": previous_cases,

            "growth_percent": round(
                growth_percent,
                2
            ),

            "categories": len(
                categories
            ),
        },

        "categories": categories,

        "daily": daily_records,

        "category_daily": category_daily,

        "signals": signals,

        "forecasts": forecast_records,
    }