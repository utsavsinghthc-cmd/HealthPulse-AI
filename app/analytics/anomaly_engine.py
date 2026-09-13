from pathlib import Path

import numpy as np
import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[2]

INPUT_FILE = (
    BASE_DIR
    / "data"
    / "processed"
    / "structured_reports.csv"
)


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


def calculate_anomalies(
    daily_data,
    baseline_days=14,
):
    results = []

    for (location, category), group in daily_data.groupby(
        ["location", "health_category"]
    ):
        group = group.sort_values(
            "report_date"
        ).copy()

        # Previous-period rolling baseline
        group["baseline_mean"] = (
            group["case_count"]
            .rolling(
                window=baseline_days,
                min_periods=7,
            )
            .mean()
            .shift(1)
        )

        group["baseline_std"] = (
            group["case_count"]
            .rolling(
                window=baseline_days,
                min_periods=7,
            )
            .std()
            .shift(1)
        )

        group["baseline_mean"] = (
            group["baseline_mean"]
            .fillna(
                group["case_count"]
                .expanding()
                .mean()
            )
        )

        group["baseline_std"] = (
            group["baseline_std"]
            .fillna(
                group["case_count"]
                .expanding()
                .std()
            )
            .fillna(0)
        )

        # Z-score
        group["z_score"] = np.where(
            group["baseline_std"] > 0,
            (
                group["case_count"]
                - group["baseline_mean"]
            )
            / group["baseline_std"],
            0,
        )

        # 14-day growth
        group["recent_14_day_avg"] = (
            group["case_count"]
            .rolling(
                window=14,
                min_periods=7,
            )
            .mean()
        )

        group["previous_14_day_avg"] = (
            group["case_count"]
            .shift(14)
            .rolling(
                window=14,
                min_periods=7,
            )
            .mean()
        )

        group["trend_growth_percent"] = np.where(
            group["previous_14_day_avg"] > 0,
            (
                (
                    group["recent_14_day_avg"]
                    - group["previous_14_day_avg"]
                )
                / group["previous_14_day_avg"]
            )
            * 100,
            0,
        )

        group["trend_growth_percent"] = (
            group["trend_growth_percent"]
            .replace(
                [np.inf, -np.inf],
                0,
            )
            .fillna(0)
            .round(2)
        )

        # Daily deviation
        group["deviation_percent"] = np.where(
            group["baseline_mean"] > 0,
            (
                (
                    group["case_count"]
                    - group["baseline_mean"]
                )
                / group["baseline_mean"]
            )
            * 100,
            0,
        )

        group["deviation_percent"] = (
            group["deviation_percent"]
            .replace(
                [np.inf, -np.inf],
                0,
            )
            .fillna(0)
            .round(2)
        )

        # Hybrid classification
        def classify(row):
            z = row["z_score"]
            growth = row["trend_growth_percent"]

            if z >= 3 and growth >= 25:
                return "CRITICAL"

            if z >= 2.5 or growth >= 50:
                return "ALERT"

            if z >= 2 or growth >= 25:
                return "WATCH"

            if growth >= 15:
                return "EMERGING"

            return "NORMAL"

        group["status"] = group.apply(
            classify,
            axis=1,
        )

        results.append(group)

    if not results:
        return pd.DataFrame()

    result = pd.concat(
        results,
        ignore_index=True,
    )

    result["z_score"] = (
        result["z_score"]
        .replace(
            [np.inf, -np.inf],
            0,
        )
        .fillna(0)
        .round(2)
    )

    return result


def build_anomaly_report():
    df = load_data()

    daily_data = build_daily_series(df)

    anomalies = calculate_anomalies(
        daily_data
    )

    latest_date = anomalies[
        "report_date"
    ].max()

    latest = anomalies[
        anomalies["report_date"]
        == latest_date
    ].copy()

    severity_order = {
        "CRITICAL": 0,
        "ALERT": 1,
        "WATCH": 2,
        "EMERGING": 3,
        "NORMAL": 4,
    }

    latest["severity_order"] = (
        latest["status"]
        .map(severity_order)
    )

    latest = latest.sort_values(
        [
            "severity_order",
            "trend_growth_percent",
            "z_score",
        ],
        ascending=[
            True,
            False,
            False,
        ],
    )

    alerts = latest[
        latest["status"].isin(
            [
                "CRITICAL",
                "ALERT",
                "WATCH",
                "EMERGING",
            ]
        )
    ].copy()

    return {
        "daily_data": daily_data,
        "anomalies": anomalies,
        "latest": latest,
        "alerts": alerts,
        "latest_date": latest_date,
    }


def main():
    print("=" * 60)
    print("HealthPulse AI - Hybrid Anomaly Engine")
    print("=" * 60)

    report = build_anomaly_report()

    print()
    print(
        "Latest Date:",
        report["latest_date"].strftime(
            "%Y-%m-%d"
        ),
    )

    display_columns = [
        "location",
        "health_category",
        "case_count",
        "baseline_mean",
        "z_score",
        "trend_growth_percent",
        "deviation_percent",
        "status",
    ]

    print()
    print("Top Latest Signals")
    print("-" * 60)

    print(
        report["latest"][
            display_columns
        ].head(15).to_string(
            index=False
        )
    )

    print()
    print("Active Health Signals")
    print("-" * 60)

    if report["alerts"].empty:
        print("No active health signals.")
    else:
        print(
            report["alerts"][
                display_columns
            ].to_string(
                index=False
            )
        )

    print()
    print("=" * 60)
    print("HYBRID ANOMALY ENGINE: PASS")
    print("=" * 60)


if __name__ == "__main__":
    main()
