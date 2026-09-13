from pathlib import Path

import pandas as pd
import numpy as np

from app.analytics.trend_engine import (
    load_data as load_trend_data,
    calculate_growth,
)

from app.analytics.anomaly_engine import (
    build_daily_series,
    calculate_anomalies,
)

from app.analytics.cluster_engine import (
    calculate_cluster_scores,
)


BASE_DIR = Path(__file__).resolve().parents[2]


def load_data():
    return load_trend_data()


def calculate_trend_score(growth_percent):
    """
    Convert percentage growth into a 0-100 trend score.
    """

    if growth_percent <= 0:
        return 0.0

    if growth_percent >= 100:
        return 100.0

    return round(
        growth_percent,
        2,
    )


def calculate_anomaly_score(z_score):
    """
    Convert statistical anomaly into a 0-100 score.
    """

    if z_score <= 0:
        return 0.0

    score = (
        z_score / 3
    ) * 100

    return round(
        min(score, 100),
        2,
    )


def calculate_risk_level(score):
    if score >= 80:
        return "CRITICAL"

    if score >= 60:
        return "HIGH"

    if score >= 30:
        return "MODERATE"

    return "LOW"


def build_risk_scores():
    df = load_data()

    # --------------------------------------------------
    # 1. TREND SIGNAL
    # --------------------------------------------------

    trend = calculate_growth(
        df,
        [
            "location",
            "health_category",
        ],
    )

    trend["trend_score"] = (
        trend["growth_percent"]
        .apply(calculate_trend_score)
    )

    # --------------------------------------------------
    # 2. ANOMALY SIGNAL
    # --------------------------------------------------

    daily_data = build_daily_series(df)

    anomalies = calculate_anomalies(
        daily_data
    )

    latest_date = anomalies[
        "report_date"
    ].max()

    latest_anomalies = anomalies[
        anomalies["report_date"]
        == latest_date
    ].copy()

    latest_anomalies[
        "anomaly_score"
    ] = latest_anomalies[
        "z_score"
    ].apply(
        calculate_anomaly_score
    )

    # --------------------------------------------------
    # 3. CLUSTER SIGNAL
    # --------------------------------------------------

    clusters = calculate_cluster_scores(
        df
    )

    cluster_columns = [
        "location",
        "health_category",
        "cluster_score",
        "cluster_level",
    ]

    clusters = clusters[
        cluster_columns
    ]

    # --------------------------------------------------
    # 4. MERGE ALL SIGNALS
    # --------------------------------------------------

    result = trend[
        [
            "location",
            "health_category",
            "recent_cases",
            "previous_cases",
            "growth_percent",
            "trend_score",
        ]
    ].merge(
        latest_anomalies[
            [
                "location",
                "health_category",
                "case_count",
                "z_score",
                "anomaly_score",
            ]
        ],
        on=[
            "location",
            "health_category",
        ],
        how="left",
    )

    result = result.merge(
        clusters,
        on=[
            "location",
            "health_category",
        ],
        how="left",
    )

    # --------------------------------------------------
    # 5. CLEAN SIGNALS
    # --------------------------------------------------

    result["anomaly_score"] = (
        result["anomaly_score"]
        .fillna(0)
    )

    result["cluster_score"] = (
        result["cluster_score"]
        .fillna(0)
    )

    result["z_score"] = (
        result["z_score"]
        .fillna(0)
    )

    result["case_count"] = (
        result["case_count"]
        .fillna(0)
        .astype(int)
    )

    # --------------------------------------------------
    # 6. FINAL COMMUNITY RISK SCORE
    # --------------------------------------------------

    result["risk_score"] = (
        result["trend_score"] * 0.40
        + result["anomaly_score"] * 0.30
        + result["cluster_score"] * 0.30
    ).round(2)

    result["risk_level"] = (
        result["risk_score"]
        .apply(calculate_risk_level)
    )

    # --------------------------------------------------
    # 7. RANKING
    # --------------------------------------------------

    result = result.sort_values(
        "risk_score",
        ascending=False,
    ).reset_index(
        drop=True
    )

    result["risk_rank"] = (
        result.index + 1
    )

    return result


def get_top_risks(
    limit=10,
):
    result = build_risk_scores()

    return result.head(limit)


def get_high_risk_areas():
    result = build_risk_scores()

    return result[
        result["risk_level"].isin(
            [
                "CRITICAL",
                "HIGH",
            ]
        )
    ].copy()


def build_risk_report():
    result = build_risk_scores()

    return {
        "risk_scores": result,
        "top_risks": result.head(10),
        "high_risk": result[
            result["risk_level"].isin(
                [
                    "CRITICAL",
                    "HIGH",
                ]
            )
        ],
        "latest_date": load_data()[
            "report_date"
        ].max(),
    }


def main():
    print("=" * 60)
    print("HealthPulse AI - Community Risk Engine")
    print("=" * 60)

    report = build_risk_report()

    print()
    print(
        "Latest Date:",
        report["latest_date"].strftime(
            "%Y-%m-%d"
        ),
    )

    print()
    print("Top Community Risk Signals")
    print("-" * 60)

    display_columns = [
        "risk_rank",
        "location",
        "health_category",
        "recent_cases",
        "growth_percent",
        "z_score",
        "cluster_score",
        "risk_score",
        "risk_level",
    ]

    print(
        report["top_risks"][
            display_columns
        ].to_string(
            index=False
        )
    )

    print()
    print("High / Critical Risk Areas")
    print("-" * 60)

    if report["high_risk"].empty:
        print(
            "No high or critical community "
            "risk signals detected."
        )
    else:
        print(
            report["high_risk"][
                display_columns
            ].to_string(
                index=False
            )
        )

    print()
    print("=" * 60)
    print("RISK ENGINE: PASS")
    print("=" * 60)


if __name__ == "__main__":
    main()
