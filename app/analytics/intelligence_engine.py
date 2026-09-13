import pandas as pd

from app.analytics.trend_engine import build_trend_report
from app.analytics.anomaly_engine import build_anomaly_report
from app.analytics.cluster_engine import build_cluster_report
from app.analytics.risk_engine import build_risk_report
from app.analytics.forecast_engine import build_forecast_report


def get_dataframe(report, key):
    if not isinstance(report, dict):
        raise ValueError(f"Expected dictionary report, got {type(report)}")

    dataframe = report.get(key)

    if not isinstance(dataframe, pd.DataFrame):
        raise ValueError(
            f"Expected pandas DataFrame for key '{key}', "
            f"got {type(dataframe)}"
        )

    return dataframe.copy()


def prepare_trend_data(trend_report):
    dataframe = get_dataframe(
        trend_report,
        "location_category_growth",
    )

    required_columns = {
        "location",
        "health_category",
        "recent_cases",
        "previous_cases",
        "growth_percent",
    }

    missing = required_columns - set(dataframe.columns)

    if missing:
        raise ValueError(
            f"Trend data missing columns: {sorted(missing)}"
        )

    dataframe = dataframe[
        [
            "location",
            "health_category",
            "recent_cases",
            "previous_cases",
            "growth_percent",
        ]
    ].copy()

    return dataframe.drop_duplicates(
        subset=["location", "health_category"]
    )


def prepare_anomaly_data(anomaly_report):
    # The anomaly engine produces historical rows in "anomalies",
    # but intelligence must use only the latest observation for
    # each location/category pair.
    dataframe = get_dataframe(
        anomaly_report,
        "latest",
    )

    required_columns = {
        "location",
        "health_category",
        "z_score",
        "status",
    }

    missing = required_columns - set(dataframe.columns)

    if missing:
        raise ValueError(
            f"Anomaly data missing columns: {sorted(missing)}"
        )

    dataframe = dataframe[
        [
            "location",
            "health_category",
            "z_score",
            "status",
        ]
    ].copy()

    dataframe = dataframe.rename(
        columns={
            "status": "anomaly_level",
        }
    )

    return dataframe.drop_duplicates(
        subset=["location", "health_category"],
        keep="first",
    )

def prepare_cluster_data(cluster_report):
    dataframe = get_dataframe(
        cluster_report,
        "clusters",
    )

    required_columns = {
        "location",
        "health_category",
        "cluster_score",
        "cluster_level",
    }

    missing = required_columns - set(dataframe.columns)

    if missing:
        raise ValueError(
            f"Cluster data missing columns: {sorted(missing)}"
        )

    dataframe = dataframe[
        [
            "location",
            "health_category",
            "cluster_score",
            "cluster_level",
        ]
    ].copy()

    return dataframe.drop_duplicates(
        subset=["location", "health_category"]
    )


def prepare_risk_data(risk_report):
    dataframe = get_dataframe(
        risk_report,
        "risk_scores",
    )

    required_columns = {
        "location",
        "health_category",
        "risk_score",
        "risk_level",
    }

    missing = required_columns - set(dataframe.columns)

    if missing:
        raise ValueError(
            f"Risk data missing columns: {sorted(missing)}"
        )

    dataframe = dataframe[
        [
            "location",
            "health_category",
            "risk_score",
            "risk_level",
        ]
    ].copy()

    return dataframe.drop_duplicates(
        subset=["location", "health_category"]
    )


def prepare_forecast_data(forecast_report):
    dataframe = get_dataframe(
        forecast_report,
        "summaries",
    )

    required_columns = {
        "location",
        "health_category",
        "direction",
        "expected_change_percent",
    }

    missing = required_columns - set(dataframe.columns)

    if missing:
        raise ValueError(
            f"Forecast data missing columns: {sorted(missing)}"
        )

    dataframe = dataframe[
        [
            "location",
            "health_category",
            "direction",
            "expected_change_percent",
        ]
    ].copy()

    return dataframe.drop_duplicates(
        subset=["location", "health_category"]
    )


def get_signal_priority(risk_level, anomaly_level, cluster_level):
    levels = {
        "CRITICAL": 4,
        "HIGH": 3,
        "WATCH": 2,
        "MODERATE": 2,
        "EMERGING": 2,
        "LOW": 1,
        "NORMAL": 0,
    }

    highest = max(
        levels.get(str(risk_level).upper(), 0),
        levels.get(str(anomaly_level).upper(), 0),
        levels.get(str(cluster_level).upper(), 0),
    )

    if highest >= 4:
        return "CRITICAL"

    if highest >= 3:
        return "HIGH"

    if highest >= 2:
        return "MODERATE"

    return "LOW"


def build_explanation(row):
    location = row["location"]
    category = row["health_category"]

    growth = float(row["growth_percent"])
    cluster_level = str(row["cluster_level"])
    forecast_direction = str(row["forecast_direction"])
    forecast_change = float(row["forecast_change_percent"])
    risk_score = float(row["risk_score"])
    risk_level = str(row["risk_level"])

    if growth > 0:
        growth_text = (
            f"cases increased sharply by {growth:.1f}%"
            if growth >= 50
            else f"cases increased by {growth:.1f}%"
        )
    elif growth < 0:
        growth_text = f"cases decreased by {abs(growth):.1f}%"
    else:
        growth_text = "cases remained stable"

    if forecast_direction == "RISING":
        forecast_text = (
            f"7-day statistical projection indicates a rising trend "
            f"of approximately {forecast_change:.1f}%"
        )
    elif forecast_direction == "DECLINING":
        forecast_text = (
            f"7-day statistical projection indicates a declining trend "
            f"of approximately {abs(forecast_change):.1f}%"
        )
    else:
        forecast_text = (
            f"7-day statistical projection indicates a relatively stable "
            f"trend ({forecast_change:.1f}% expected change)"
        )

    return (
        f"{location} shows a {category} community-health signal: "
        f"{growth_text}; cluster concentration is {cluster_level}; "
        f"{forecast_text}. "
        f"Current combined risk score is {risk_score:.1f} ({risk_level})."
    )


def build_action(row):
    priority = str(row["priority"]).upper()

    if priority == "CRITICAL":
        return (
            "Immediately validate the signal with local health authorities, "
            "prioritize targeted surveillance, and assess urgent preventive "
            "interventions."
        )

    if priority == "HIGH":
        return (
            "Prioritize community surveillance, verify the signal with local "
            "health data, and assess targeted preventive measures."
        )

    if priority == "MODERATE":
        return (
            "Increase monitoring of the affected community-health signal, "
            "validate the trend with local data, and consider preventive "
            "awareness measures."
        )

    return (
        "Continue routine monitoring and reassess the signal if case trends "
        "or anomaly indicators increase."
    )


def build_intelligence_report():
    trend_report = build_trend_report()
    anomaly_report = build_anomaly_report()
    cluster_report = build_cluster_report()
    risk_report = build_risk_report()
    forecast_report = build_forecast_report()

    trend_data = prepare_trend_data(trend_report)
    anomaly_data = prepare_anomaly_data(anomaly_report)
    cluster_data = prepare_cluster_data(cluster_report)
    risk_data = prepare_risk_data(risk_report)
    forecast_data = prepare_forecast_data(forecast_report)

    key_columns = ["location", "health_category"]

    # Start with trend data as the master list of signals.
    intelligence = trend_data.copy()

    # Every source is reduced to one row per location/category
    # before merging. This prevents many-to-many merge duplication.
    intelligence = intelligence.merge(
        anomaly_data,
        on=key_columns,
        how="left",
        validate="one_to_one",
    )

    intelligence = intelligence.merge(
        cluster_data,
        on=key_columns,
        how="left",
        validate="one_to_one",
    )

    intelligence = intelligence.merge(
        risk_data,
        on=key_columns,
        how="left",
        validate="one_to_one",
    )

    intelligence = intelligence.merge(
        forecast_data,
        on=key_columns,
        how="left",
        validate="one_to_one",
    )

    # Fill missing analytical values safely.
    intelligence["z_score"] = pd.to_numeric(
        intelligence["z_score"],
        errors="coerce",
    ).fillna(0)

    intelligence["risk_score"] = pd.to_numeric(
        intelligence["risk_score"],
        errors="coerce",
    ).fillna(0)

    intelligence["risk_level"] = (
        intelligence["risk_level"]
        .fillna("LOW")
        .astype(str)
    )

    intelligence["anomaly_level"] = (
        intelligence["anomaly_level"]
        .fillna("NORMAL")
        .astype(str)
    )

    intelligence["cluster_level"] = (
        intelligence["cluster_level"]
        .fillna("LOW")
        .astype(str)
    )

    intelligence["forecast_direction"] = (
        intelligence["direction"]
        .fillna("STABLE")
        .astype(str)
    )

    intelligence["forecast_change_percent"] = pd.to_numeric(
        intelligence["expected_change_percent"],
        errors="coerce",
    ).fillna(0)

    intelligence["priority"] = intelligence.apply(
        lambda row: get_signal_priority(
            row["risk_level"],
            row["anomaly_level"],
            row["cluster_level"],
        ),
        axis=1,
    )

    intelligence["explanation"] = intelligence.apply(
        build_explanation,
        axis=1,
    )

    intelligence["recommended_action"] = intelligence.apply(
        build_action,
        axis=1,
    )

    # Final safety check:
    # one location/category must represent exactly one signal.
    intelligence = intelligence.drop_duplicates(
        subset=key_columns,
        keep="first",
    )

    priority_order = {
        "CRITICAL": 4,
        "HIGH": 3,
        "MODERATE": 2,
        "LOW": 1,
    }

    intelligence["_priority_order"] = intelligence["priority"].map(
        priority_order
    ).fillna(0)

    intelligence = intelligence.sort_values(
        by=["_priority_order", "risk_score"],
        ascending=[False, False],
    ).drop(
        columns=["_priority_order"]
    )

    output_columns = [
        "location",
        "health_category",
        "priority",
        "risk_score",
        "risk_level",
        "anomaly_level",
        "cluster_level",
        "forecast_direction",
        "forecast_change_percent",
        "recent_cases",
        "previous_cases",
        "growth_percent",
        "explanation",
        "recommended_action",
    ]

    intelligence = intelligence[output_columns].reset_index(drop=True)

    return {
        "intelligence": intelligence,
        "latest_date": trend_report["summary"]["latest_date"],
    }


def save_intelligence_report(report):
    output_path = (
        "data/processed/community_intelligence.csv"
    )

    dataframe = report["intelligence"]

    dataframe.to_csv(
        output_path,
        index=False,
    )

    return output_path


def main():
    print("=" * 70)
    print("HealthPulse AI - Community Intelligence Engine")
    print("=" * 70)
    print()

    report = build_intelligence_report()

    print(f"Latest Date: {report['latest_date']}")
    print()

    print("Priority Signals")
    print("-" * 70)

    display_columns = [
        "location",
        "health_category",
        "priority",
        "risk_score",
        "risk_level",
        "anomaly_level",
        "cluster_level",
        "forecast_direction",
        "forecast_change_percent",
    ]

    print(
        report["intelligence"][display_columns]
        .head(10)
        .to_string(index=False)
    )

    print()
    print("Top Community Intelligence Signal")
    print("-" * 70)

    top_signal = report["intelligence"].iloc[0]

    print(f"Location: {top_signal['location']}")
    print(f"Category: {top_signal['health_category']}")
    print(f"Priority: {top_signal['priority']}")
    print(f"Risk Score: {top_signal['risk_score']:.2f}")
    print(f"Explanation: {top_signal['explanation']}")
    print(
        f"Recommended Action: "
        f"{top_signal['recommended_action']}"
    )

    output_path = save_intelligence_report(report)

    print()
    print(f"Saved: {output_path}")
    print()
    print("=" * 70)
    print("INTELLIGENCE ENGINE: PASS")
    print("=" * 70)


if __name__ == "__main__":
    main()