from pathlib import Path

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

    dataframe = pd.read_csv(INPUT_FILE)

    dataframe["report_date"] = pd.to_datetime(
        dataframe["report_date"]
    )

    return dataframe


def calculate_category_trends(dataframe):
    daily = (
        dataframe
        .groupby(
            ["report_date", "health_category"]
        )
        .size()
        .reset_index(name="case_count")
        .sort_values("report_date")
    )

    return daily


def calculate_location_trends(dataframe):
    daily = (
        dataframe
        .groupby(
            [
                "report_date",
                "location",
                "health_category",
            ]
        )
        .size()
        .reset_index(name="case_count")
        .sort_values("report_date")
    )

    return daily


def calculate_growth(
    dataframe,
    group_columns,
    recent_days=14,
):
    latest_date = dataframe["report_date"].max()

    recent_start = (
        latest_date
        - pd.Timedelta(days=recent_days - 1)
    )

    previous_end = recent_start - pd.Timedelta(days=1)

    previous_start = (
        previous_end
        - pd.Timedelta(days=recent_days - 1)
    )

    recent = dataframe[
        dataframe["report_date"].between(
            recent_start,
            latest_date,
        )
    ]

    previous = dataframe[
        dataframe["report_date"].between(
            previous_start,
            previous_end,
        )
    ]

    recent_counts = (
        recent
        .groupby(group_columns)
        .size()
        .reset_index(name="recent_cases")
    )

    previous_counts = (
        previous
        .groupby(group_columns)
        .size()
        .reset_index(name="previous_cases")
    )

    result = recent_counts.merge(
        previous_counts,
        on=group_columns,
        how="outer",
    )

    result["recent_cases"] = (
        result["recent_cases"]
        .fillna(0)
        .astype(int)
    )

    result["previous_cases"] = (
        result["previous_cases"]
        .fillna(0)
        .astype(int)
    )

    def growth_percentage(row):
        previous = row["previous_cases"]
        recent = row["recent_cases"]

        if previous == 0:
            if recent > 0:
                return 100.0
            return 0.0

        return round(
            ((recent - previous) / previous) * 100,
            2,
        )

    result["growth_percent"] = result.apply(
        growth_percentage,
        axis=1,
    )

    return result.sort_values(
        "growth_percent",
        ascending=False,
    ).reset_index(drop=True)


def calculate_overall_summary(dataframe):
    latest_date = dataframe["report_date"].max()

    total_cases = len(dataframe)

    locations = dataframe["location"].nunique()

    categories = dataframe["health_category"].nunique()

    return {
        "total_cases": int(total_cases),
        "locations": int(locations),
        "categories": int(categories),
        "latest_date": latest_date.strftime("%Y-%m-%d"),
    }


def get_top_emerging_signals(
    dataframe,
    limit=10,
):
    growth = calculate_growth(
        dataframe,
        [
            "location",
            "health_category",
        ],
    )

    return growth.head(limit)


def build_trend_report():
    dataframe = load_data()

    category_daily = calculate_category_trends(
        dataframe
    )

    location_daily = calculate_location_trends(
        dataframe
    )

    category_growth = calculate_growth(
        dataframe,
        ["health_category"],
    )

    location_growth = calculate_growth(
        dataframe,
        ["location"],
    )

    location_category_growth = calculate_growth(
        dataframe,
        [
            "location",
            "health_category",
        ],
    )

    summary = calculate_overall_summary(
        dataframe
    )

    emerging_signals = get_top_emerging_signals(
        dataframe
    )

    return {
        "summary": summary,
        "category_daily": category_daily,
        "location_daily": location_daily,
        "category_growth": category_growth,
        "location_growth": location_growth,
        "location_category_growth": location_category_growth,
        "emerging_signals": emerging_signals,
    }


def main():
    print("=" * 60)
    print("HealthPulse AI - Trend Engine")
    print("=" * 60)

    report = build_trend_report()

    print()
    print("Overall Summary")
    print("-" * 60)

    for key, value in report["summary"].items():
        print(f"{key}: {value}")

    print()
    print("Category Growth - Last 14 Days")
    print("-" * 60)

    print(
        report["category_growth"].to_string(
            index=False
        )
    )

    print()
    print("Location Growth - Last 14 Days")
    print("-" * 60)

    print(
        report["location_growth"].to_string(
            index=False
        )
    )

    print()
    print("Top Emerging Location + Category Signals")
    print("-" * 60)

    print(
        report["emerging_signals"].to_string(
            index=False
        )
    )

    print()
    print("=" * 60)
    print("TREND ENGINE: PASS")
    print("=" * 60)


if __name__ == "__main__":
    main()
