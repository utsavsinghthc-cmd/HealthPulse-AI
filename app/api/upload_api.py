import io
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, File, HTTPException, UploadFile

from app.ai.report_parser import parse_medical_report
from app.database.database import get_connection, initialize_database


router = APIRouter(
    prefix="/api",
    tags=["Upload"],
)


BASE_DIR = Path(__file__).resolve().parents[2]
PROCESSED_DIR = BASE_DIR / "data" / "processed"
STRUCTURED_FILE = PROCESSED_DIR / "structured_reports.csv"


def find_column(columns, possible_names):
    """
    Find the first matching column from a list of possible aliases.
    """
    normalized = {
        str(column).strip().lower(): column
        for column in columns
    }

    for name in possible_names:
        if name.lower() in normalized:
            return normalized[name.lower()]

    return None


def prepare_uploaded_data(dataframe):
    """
    Validate and convert uploaded CSV into the standard
    HealthPulse database structure.
    """

    if dataframe.empty:
        raise HTTPException(
            status_code=400,
            detail="Uploaded CSV is empty.",
        )

    dataframe.columns = [
        str(column).strip()
        for column in dataframe.columns
    ]

    report_text_column = find_column(
        dataframe.columns,
        [
            "report_text",
            "report",
            "text",
            "medical_report",
            "medical_report_text",
        ],
    )

    date_column = find_column(
        dataframe.columns,
        [
            "report_date",
            "date",
            "report date",
        ],
    )

    location_column = find_column(
        dataframe.columns,
        [
            "location",
            "area",
            "region",
        ],
    )

    if report_text_column is None:
        raise HTTPException(
            status_code=400,
            detail=(
                "CSV must contain a report text column. "
                "Supported names: report_text, report, text, "
                "medical_report, medical_report_text."
            ),
        )

    if date_column is None:
        raise HTTPException(
            status_code=400,
            detail=(
                "CSV must contain a report date column. "
                "Supported names: report_date, date."
            ),
        )

    records = []

    for index, row in dataframe.iterrows():

        report_text = str(
            row.get(report_text_column, "")
        ).strip()

        if not report_text or report_text.lower() == "nan":
            raise HTTPException(
                status_code=400,
                detail=f"Missing report text at CSV row {index + 2}.",
            )

        raw_date = row.get(date_column)

        parsed_date = pd.to_datetime(
            raw_date,
            errors="coerce",
        )

        if pd.isna(parsed_date):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid report date at CSV row {index + 2}.",
            )

        explicit_location = None

        if location_column is not None:
            value = row.get(location_column)

            if pd.notna(value):
                explicit_location = str(value).strip()

        parsed = parse_medical_report(
            report_text=report_text,
            patient_age=row.get("patient_age"),
            gender=row.get("gender"),
            location=explicit_location,
            symptoms=row.get("symptoms"),
            health_category=row.get("health_category"),
            severity=row.get("severity"),
        )

        if not parsed["location"] or parsed["location"] == "unknown":
            raise HTTPException(
                status_code=400,
                detail=f"Location could not be determined at CSV row {index + 2}.",
            )

        if (
            not parsed["health_category"]
            or parsed["health_category"] == "unknown"
        ):
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Health category could not be determined "
                    f"at CSV row {index + 2}."
                ),
            )

        records.append(
            {
                "report_text": report_text,
                "patient_age": parsed["patient_age"],
                "gender": parsed["gender"],
                "location": parsed["location"],
                "report_date": parsed_date.strftime("%Y-%m-%d"),
                "symptoms": parsed["symptoms"],
                "health_category": parsed["health_category"],
                "severity": parsed["severity"],
            }
        )

    return pd.DataFrame(records)


@router.post("/upload")
async def upload_reports(
    file: UploadFile = File(...),
    replace_existing: bool = True,
):
    """
    Upload a medical-report CSV.

    Default behavior:
    replace_existing=true

    This replaces the existing database records instead of
    appending duplicate data.
    """

    initialize_database()

    filename = file.filename or ""

    if not filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="Only CSV files are supported.",
        )

    try:
        contents = await file.read()

        if not contents:
            raise HTTPException(
                status_code=400,
                detail="Uploaded file is empty.",
            )

        dataframe = pd.read_csv(
            io.BytesIO(contents)
        )

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Could not read CSV file: {exc}",
        )

    structured_df = prepare_uploaded_data(dataframe)

    PROCESSED_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    # Save the latest processed/structured dataset.
    structured_df.to_csv(
        STRUCTURED_FILE,
        index=False,
    )

    connection = get_connection()

    try:
        if replace_existing:
            connection.execute(
                "DELETE FROM medical_reports"
            )

        insert_query = """
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
        """

        rows = [
            (
                record["report_text"],
                record["patient_age"],
                record["gender"],
                record["location"],
                record["report_date"],
                record["symptoms"],
                record["health_category"],
                record["severity"],
            )
            for record in structured_df.to_dict(
                orient="records"
            )
        ]

        connection.executemany(
            insert_query,
            rows,
        )

        connection.commit()

    except Exception:
        connection.rollback()
        raise HTTPException(
            status_code=500,
            detail="Database import failed. Existing data was preserved.",
        )

    finally:
        connection.close()

    connection = get_connection()

    total_reports = connection.execute(
        "SELECT COUNT(*) AS count FROM medical_reports"
    ).fetchone()["count"]

    category_rows = connection.execute(
        """
        SELECT
            health_category,
            COUNT(*) AS count
        FROM medical_reports
        GROUP BY health_category
        ORDER BY count DESC
        """
    ).fetchall()

    location_rows = connection.execute(
        """
        SELECT
            location,
            COUNT(*) AS count
        FROM medical_reports
        GROUP BY location
        ORDER BY count DESC
        """
    ).fetchall()

    connection.close()

    return {
        "status": "success",
        "message": (
            "Reports uploaded and existing data replaced."
            if replace_existing
            else "Reports uploaded and appended."
        ),
        "filename": filename,
        "uploaded_rows": int(len(structured_df)),
        "database_total": int(total_reports),
        "replace_existing": replace_existing,
        "categories": {
            row["health_category"]: int(row["count"])
            for row in category_rows
        },
        "locations": {
            row["location"]: int(row["count"])
            for row in location_rows
        },
    }