import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]
DATABASE_PATH = BASE_DIR / "healthpulse.db"


def get_connection():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    connection = get_connection()

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS medical_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_text TEXT NOT NULL,
            patient_age INTEGER,
            gender TEXT,
            location TEXT NOT NULL,
            report_date TEXT NOT NULL,
            symptoms TEXT,
            health_category TEXT,
            severity TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    connection.commit()
    connection.close()


def clear_reports():
    connection = get_connection()

    connection.execute("DELETE FROM medical_reports")

    connection.commit()
    connection.close()


def get_report_count():
    connection = get_connection()

    row = connection.execute(
        "SELECT COUNT(*) AS count FROM medical_reports"
    ).fetchone()

    connection.close()

    return int(row["count"])
