from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression


BASE_DIR = Path(__file__).resolve().parents[2]

INPUT_FILE = (
    BASE_DIR
    / "data"
    / "processed"
    / "structured_reports.csv"
)


FORECAST_DAYS = 7
HISTORY_DAYS = 14


def load_data():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Structured reports file not found: {INPUT_FILE}"
        )

    df = pd.read_csv(INPUT_FILE)

    df["report_date"] = pd.to_datetime(
        df["report_date"]
    )

    return df


def build_daily_series(df):
    all_dates = pd.date_range(
        df["report_date"].min(),
        df["report_date"].max(),
        freq="D",
    )

    combinations = df[
        ["location", "health_category"]
    ].drop_duplicates()

    rows = []

    for _, combo in combinations.iterrows():
        location = combo["location"]
        category = combo["health_category"]

        subset = df[
            (df["location"] == location)
            & (
                df["health_category"]
                == category
            )
        ]

        daily = (
            subset
            .groupby("report_date")
            .size()
            .reindex(
                all_dates,
                fill_value=0,
            )
        )

        for date, count in daily.items():
            rows.append(
                {
                    "report_date": date,
                    "location": location,
                    "health_category": category,
                    "case_count": int(count),
                }
            )

    return pd.DataFrame(rows)


def calculate_forecast(
    daily_data,
    history_days=HISTORY_DAYS,
    forecast_days=FORECAST_DAYS,
):
    results = []

    for (location, category), group in daily_data.groupby(
        ["location", "health_category"]
    ):
        group = group.sort_values(
            "report_date"
        ).copy()

        history = group.tail(
            history_days
        ).copy()

        if len(history) < 7:
            continue

        X = np.arange(
            len(history)
        ).reshape(-1, 1)

        y = history[
            "case_count"
        ].values

        model = LinearRegression()

        model.fit(X, y)

        future_X = np.arange(
            len(history),
            len(history) + forecast_days,
        ).reshape(-1, 1)

        predictions = model.predict(
            future_X
        )

        predictions = np.maximum(
            predictions,
            0,
        )

        predictions = np.round(
            predictions,
            2,
        )

        slope = float(
            model.coef_[0]
        )

        current_average = float(
            history[
                "case_count"
            ].tail(3).mean()
        )

        forecast_average = float(
            predictions.mean()
        )

        if slope > 0.15:
            direction = "RISING"
        elif slope < -0.15:
            direction = "DECLINING"
        else:
            direction = "STABLE"

        if current_average > 0:
            expected_change_percent = (
                (
                    forecast_average
                    - current_average
                )
                / current_average
            ) * 100
        else:
            expected_change_percent = (
                100.0
                if forecast_average > 0
                else 0.0
            )

        expected_change_percent = round(
            expected_change_percent,
            2,
        )

        forecast_dates = pd.date_range(
            group["report_date"].max()
            + pd.Timedelta(days=1),
            periods=forecast_days,
            freq="D",
        )

        for date, prediction in zip(
            forecast_dates,
            predictions,
        ):
            results.append(
                {
                    "forecast_date": date,
                    "location": location,
                    "health_category": category,
                    "predicted_cases": float(
                        prediction
                    ),
                    "trend_slope": round(
                        slope,
                        4,
                    ),
                    "direction": direction,
                    "expected_change_percent": (
                        expected_change_percent
                    ),
                }
            )

    return pd.DataFrame(results)


def summarize_forecasts(
    forecasts,
):
    if forecasts.empty:
        return pd.DataFrame()

    summaries = []

    for (
        location,
        category,
    ), group in forecasts.groupby(
        [
            "location",
            "health_category",
        ]
    ):
        first_prediction = group.sort_values(
            "forecast_date"
        ).iloc[0]

        average_prediction = (
            group["predicted_cases"]
            .mean()
        )

        maximum_prediction = (
            group["predicted_cases"]
            .max()
        )

        summaries.append(
            {
                "location": location,
                "health_category": category,
                "forecast_average": round(
                    average_prediction,
                    2,
                ),
                "forecast_peak": round(
                    maximum_prediction,
                    2,
                ),
                "trend_slope": first_prediction[
                    "trend_slope"
                ],
                "direction": first_prediction[
                    "direction"
                ],
                "expected_change_percent": (
                    first_prediction[
                        "expected_change_percent"
                    ]
                ),
            }
        )

    return pd.DataFrame(
        summaries
    ).sort_values(
        "expected_change_percent",
        ascending=False,
    ).reset_index(drop=True)


def build_forecast_report():
    df = load_data()

    daily_data = build_daily_series(
        df
    )

    forecasts = calculate_forecast(
        daily_data
    )

    summaries = summarize_forecasts(
        forecasts
    )

    return {
        "daily_data": daily_data,
        "forecasts": forecasts,
        "summaries": summaries,
        "latest_date": df[
            "report_date"
        ].max(),
    }


def get_top_rising_forecasts(
    limit=10,
):
    report = build_forecast_report()

    return report[
        "summaries"
    ].head(limit)


def get_forecast_for_location(
    location,
):
    report = build_forecast_report()

    return report[
        "forecasts"
    ][
        report["forecasts"]["location"]
        == location
    ].copy()


def main():
    print("=" * 60)
    print("HealthPulse AI - Forecast Engine")
    print("=" * 60)

    report = build_forecast_report()

    print()
    print(
        "Historical Data Until:",
        report["latest_date"].strftime(
            "%Y-%m-%d"
        ),
    )

    print(
        "Forecast Horizon:",
        f"{FORECAST_DAYS} days",
    )

    print()
    print("Top Rising Forecasts")
    print("-" * 60)

    display_columns = [
        "location",
        "health_category",
        "forecast_average",
        "forecast_peak",
        "trend_slope",
        "expected_change_percent",
        "direction",
    ]

    print(
        report["summaries"][
            display_columns
        ].head(10).to_string(
            index=False
        )
    )

    print()
    print("Forecast Direction Summary")
    print("-" * 60)

    print(
        report["summaries"][
            "direction"
        ].value_counts().to_string()
    )

    print()
    print("=" * 60)
    print("FORECAST ENGINE: PASS")
    print("=" * 60)


if __name__ == "__main__":
    main()
