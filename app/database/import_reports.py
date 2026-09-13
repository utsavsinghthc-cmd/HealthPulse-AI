from pathlib import Path

import pandas as pd

from app.database.database import get_connection, initialize_database


BASE_DIR = Path(__file__).resolve().parents[2]

INPUT_FILE = (
    BASE_DIR
    / "data"
    / "processed"
    / "structured_reports.csv"
)


def import_reports():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Structured reports file not found: {INPUT_FILE}"
        )

    dataframe = pd.read_csv(INPUT_FILE)

    initialize_database()

    connection = get_connection()

    try:
        connection.execute("DELETE FROM medical_reports")

        records = [
            (
                row["report_text"],
                int(row["patient_age"]),
                row["gender"],
                row["location"],
                row["report_date"],
                row["symptoms"],
                row["health_category"],
                row["severity"],
            )
            for _, row in dataframe.iterrows()
        ]

        connection.executemany(
            """
            INSERT INTO medical_reports (
                report_text,
                patient_age,
                gender,
                location,
                report_date,
                symptoms,
                health_category,
                severity
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            records,
        )

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()

    return len(records)


def verify_database():
    connection = get_connection()

    total = connection.execute(
        "SELECT COUNT(*) FROM medical_reports"
    ).fetchone()[0]

    categories = connection.execute(
        """
        SELECT health_category, COUNT(*) AS count
        FROM medical_reports
        GROUP BY health_category
        ORDER BY count DESC
        """
    ).fetchall()

    locations = connection.execute(
        """
        SELECT location, COUNT(*) AS count
        FROM medical_reports
        GROUP BY location
        ORDER BY count DESC
        """
    ).fetchall()

    connection.close()

    return total, categories, locations


def main():
    print("=" * 60)
    print("HealthPulse AI - Database Import")
    print("=" * 60)

    imported = import_reports()

    total, categories, locations = verify_database()

    print(f"CSV records imported: {imported}")
    print(f"Database records:      {total}")
    print()

    print("Health categories:")
    for category, count in categories:
        print(f"  {category}: {count}")

    print()

    print("Locations:")
    for location, count in locations:
        print(f"  {location}: {count}")

    print()
    print("=" * 60)

    if imported == total == 4247:
        print("DATABASE IMPORT: PASS")
    else:
        print("DATABASE IMPORT: FAILED")

    print("=" * 60)


if __name__ == "__main__":
    main()
