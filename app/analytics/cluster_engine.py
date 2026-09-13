from pathlib import Path

import pandas as pd
import numpy as np


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


def calculate_location_category_density(
    df,
    recent_days=14,
):
    latest_date = df["report_date"].max()

    start_date = (
        latest_date
        - pd.Timedelta(days=recent_days - 1)
    )

    recent = df[
        df["report_date"].between(
            start_date,
            latest_date,
        )
    ].copy()

    density = (
        recent
        .groupby(
            [
                "location",
                "health_category",
            ]
        )
        .size()
        .reset_index(
            name="recent_cases"
        )
    )

    total_by_category = (
        recent
        .groupby("health_category")
        .size()
        .reset_index(
            name="category_total"
        )
    )

    density = density.merge(
        total_by_category,
        on="health_category",
        how="left",
    )

    density["category_share_percent"] = (
        density["recent_cases"]
        / density["category_total"]
        * 100
    ).round(2)

    return density.sort_values(
        "recent_cases",
        ascending=False,
    ).reset_index(drop=True)


def calculate_location_activity(
    df,
    recent_days=14,
):
    latest_date = df["report_date"].max()

    start_date = (
        latest_date
        - pd.Timedelta(days=recent_days - 1)
    )

    recent = df[
        df["report_date"].between(
            start_date,
            latest_date,
        )
    ]

    activity = (
        recent
        .groupby("location")
        .size()
        .reset_index(
            name="total_cases"
        )
    )

    average = activity[
        "total_cases"
    ].mean()

    std = activity[
        "total_cases"
    ].std()

    if std and std > 0:
        activity["activity_z_score"] = (
            (
                activity["total_cases"]
                - average
            )
            / std
        ).round(2)
    else:
        activity["activity_z_score"] = 0.0

    return activity.sort_values(
        "total_cases",
        ascending=False,
    ).reset_index(drop=True)


def calculate_cluster_scores(
    df,
    recent_days=14,
):
    density = calculate_location_category_density(
        df,
        recent_days,
    )

    activity = calculate_location_activity(
        df,
        recent_days,
    )

    result = density.merge(
        activity[
            [
                "location",
                "total_cases",
                "activity_z_score",
            ]
        ],
        on="location",
        how="left",
    )

    # Normalize case density
    max_cases = result[
        "recent_cases"
    ].max()

    if max_cases > 0:
        result["density_score"] = (
            result["recent_cases"]
            / max_cases
            * 100
        )
    else:
        result["density_score"] = 0

    # Category concentration
    result["concentration_score"] = (
        result["category_share_percent"]
        .clip(upper=100)
    )

    # Activity contribution
    result["activity_score"] = (
        result["activity_z_score"]
        .clip(lower=0)
        * 10
    ).clip(upper=100)

    # Final cluster score
    result["cluster_score"] = (
        result["density_score"] * 0.45
        + result["concentration_score"] * 0.35
        + result["activity_score"] * 0.20
    ).round(2)

    def classify(score):
        if score >= 70:
            return "HIGH"

        if score >= 45:
            return "MODERATE"

        return "LOW"

    result["cluster_level"] = (
        result["cluster_score"]
        .apply(classify)
    )

    return result.sort_values(
        "cluster_score",
        ascending=False,
    ).reset_index(drop=True)


def get_top_clusters(
    df,
    limit=10,
):
    clusters = calculate_cluster_scores(
        df
    )

    return clusters.head(limit)


def get_high_risk_clusters(df):
    clusters = calculate_cluster_scores(
        df
    )

    return clusters[
        clusters["cluster_level"]
        == "HIGH"
    ].copy()


def build_cluster_report():
    df = load_data()

    clusters = calculate_cluster_scores(
        df
    )

    return {
        "clusters": clusters,
        "top_clusters": clusters.head(10),
        "high_risk_clusters": clusters[
            clusters["cluster_level"]
            == "HIGH"
        ],
        "latest_date": df[
            "report_date"
        ].max(),
    }


def main():
    print("=" * 60)
    print("HealthPulse AI - Cluster Detection Engine")
    print("=" * 60)

    report = build_cluster_report()

    print()
    print(
        "Latest Date:",
        report["latest_date"].strftime(
            "%Y-%m-%d"
        ),
    )

    print()
    print("Top Community Health Clusters")
    print("-" * 60)

    display_columns = [
        "location",
        "health_category",
        "recent_cases",
        "category_share_percent",
        "total_cases",
        "cluster_score",
        "cluster_level",
    ]

    print(
        report["top_clusters"][
            display_columns
        ].to_string(
            index=False
        )
    )

    print()
    print("High-Risk Clusters")
    print("-" * 60)

    if report["high_risk_clusters"].empty:
        print("No high-risk clusters detected.")
    else:
        print(
            report["high_risk_clusters"][
                display_columns
            ].to_string(
                index=False
            )
        )

    print()
    print("=" * 60)
    print("CLUSTER ENGINE: PASS")
    print("=" * 60)


if __name__ == "__main__":
    main()
