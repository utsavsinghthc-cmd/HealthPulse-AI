from pathlib import Path

import pandas as pd

from app.ai.report_parser import parse_medical_report


BASE_DIR = Path(__file__).resolve().parents[2]

INPUT_FILE = (
    BASE_DIR
    / "data"
    / "synthetic"
    / "medical_reports.csv"
)

OUTPUT_FILE = (
    BASE_DIR
    / "data"
    / "processed"
    / "structured_reports.csv"
)


REQUIRED_COLUMNS = [
    "report_text",
    "patient_age",
    "gender",
    "location",
    "report_date",
    "symptoms",
    "health_category",
    "severity",
]


def process_reports():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Input dataset not found: {INPUT_FILE}"
        )

    dataframe = pd.read_csv(INPUT_FILE)

    missing_columns = [
        column
        for column in REQUIRED_COLUMNS
        if column not in dataframe.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {missing_columns}"
        )

    structured_rows = []

    for _, row in dataframe.iterrows():
        parsed = parse_medical_report(
            report_text=row["report_text"],
            patient_age=row["patient_age"],
            gender=row["gender"],
            location=row["location"],
            symptoms=row["symptoms"],
            health_category=row["health_category"],
            severity=row["severity"],
        )

        structured_rows.append(
            {
                "report_text": row["report_text"],
                "patient_age": parsed["patient_age"],
                "gender": parsed["gender"],
                "location": parsed["location"],
                "report_date": row["report_date"],
                "symptoms": parsed["symptoms"],
                "health_category": parsed["health_category"],
                "severity": parsed["severity"],
            }
        )

    structured_dataframe = pd.DataFrame(structured_rows)

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    structured_dataframe.to_csv(
        OUTPUT_FILE,
        index=False,
    )

    return structured_dataframe


def main():
    print("=" * 60)
    print("HealthPulse AI - Report Processing")
    print("=" * 60)

    dataframe = process_reports()

    print(f"Input rows:  {len(dataframe)}")
    print(f"Output rows: {len(dataframe)}")
    print()
    print("Health categories:")
    print(dataframe["health_category"].value_counts())
    print()
    print("Missing values:")
    print(dataframe.isna().sum())
    print()
    print(f"Output file: {OUTPUT_FILE}")
    print("=" * 60)


if __name__ == "__main__":
    main()
