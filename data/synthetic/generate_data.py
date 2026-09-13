import random
from datetime import date, timedelta
from pathlib import Path

import pandas as pd


random.seed(42)


LOCATIONS = [
    "Alambagh",
    "Gomti Nagar",
    "Indira Nagar",
    "Hazratganj",
    "Aliganj",
    "Mahanagar",
    "Chinhat",
    "Rajajipuram",
]


CATEGORIES = [
    "respiratory",
    "fever",
    "gastrointestinal",
    "skin",
    "vector_borne",
]


LOCATION_PROFILES = {
    "Alambagh": {
        "category": "respiratory",
        "base": 8,
    },
    "Gomti Nagar": {
        "category": "fever",
        "base": 8,
    },
    "Indira Nagar": {
        "category": "gastrointestinal",
        "base": 8,
    },
    "Hazratganj": {
        "category": "skin",
        "base": 8,
    },
    "Aliganj": {
        "category": "respiratory",
        "base": 8,
    },
    "Mahanagar": {
        "category": "fever",
        "base": 8,
    },
    "Chinhat": {
        "category": "vector_borne",
        "base": 8,
    },
    "Rajajipuram": {
        "category": "gastrointestinal",
        "base": 8,
    },
}


CATEGORY_SYMPTOMS = {
    "respiratory": [
        "cough",
        "cough, sore throat",
        "cough, breathing difficulty",
        "cold, cough",
    ],
    "fever": [
        "fever",
        "fever, fatigue",
        "fever, body ache",
        "high temperature, fatigue",
    ],
    "gastrointestinal": [
        "stomach pain",
        "diarrhea",
        "vomiting",
        "stomach pain, diarrhea",
    ],
    "skin": [
        "skin rash",
        "itching",
        "skin irritation",
        "rash, itching",
    ],
    "vector_borne": [
        "fever, mosquito exposure",
        "fever, suspected dengue",
        "fever, body ache, mosquito exposure",
        "malaria-like fever, mosquito exposure",
    ],
}


SEVERITIES = ["mild", "moderate", "severe"]
GENDERS = ["male", "female", "other"]


def choose_age():
    return random.randint(5, 80)


def choose_severity():
    value = random.random()

    if value < 0.65:
        return "mild"

    if value < 0.92:
        return "moderate"

    return "severe"


def build_report_text(age, gender, location, symptoms, category, severity):
    return (
        f"Patient age {age}, gender {gender}, location {location}. "
        f"Reported symptoms: {symptoms}. "
        f"Health category: {category}. "
        f"Severity: {severity}."
    )


def generate_rows():
    rows = []

    start_date = date(2026, 7, 1)
    total_days = 62

    for day_index in range(total_days):
        current_date = start_date + timedelta(days=day_index)

        for location in LOCATIONS:
            profile = LOCATION_PROFILES[location]

            total_cases = profile["base"]

            # Alambagh respiratory spike during final 12 days.
            if (
                location == "Alambagh"
                and profile["category"] == "respiratory"
                and day_index >= 50
            ):
                total_cases += 8

            # Gomti Nagar fever increase during middle-late period.
            if (
                location == "Gomti Nagar"
                and profile["category"] == "fever"
                and 35 <= day_index <= 55
            ):
                total_cases += 5

            # Indira Nagar gastrointestinal cluster.
            if (
                location == "Indira Nagar"
                and profile["category"] == "gastrointestinal"
                and day_index >= 42
            ):
                total_cases += 6

            # Small random variation.
            total_cases += random.randint(-2, 2)
            total_cases = max(total_cases, 1)

            primary_category = profile["category"]

            for _ in range(total_cases):
                age = choose_age()
                gender = random.choice(GENDERS)
                severity = choose_severity()
                symptoms = random.choice(CATEGORY_SYMPTOMS[primary_category])

                report_text = build_report_text(
                    age=age,
                    gender=gender,
                    location=location,
                    symptoms=symptoms,
                    category=primary_category,
                    severity=severity,
                )

                rows.append(
                    {
                        "report_text": report_text,
                        "patient_age": age,
                        "gender": gender,
                        "location": location,
                        "report_date": current_date.isoformat(),
                        "symptoms": symptoms,
                        "health_category": primary_category,
                        "severity": severity,
                    }
                )

    return rows


def main():
    output_path = (
        Path(__file__).resolve().parent / "medical_reports.csv"
    )

    rows = generate_rows()

    dataframe = pd.DataFrame(rows)

    dataframe.to_csv(
        output_path,
        index=False,
    )

    print("=" * 50)
    print("HealthPulse AI Synthetic Dataset Generated")
    print("=" * 50)
    print(f"Rows: {len(dataframe)}")
    print(f"Locations: {dataframe['location'].nunique()}")
    print(f"Categories: {dataframe['health_category'].nunique()}")
    print(
        f"Date range: "
        f"{dataframe['report_date'].min()} "
        f"to "
        f"{dataframe['report_date'].max()}"
    )
    print(f"Output: {output_path}")
    print("=" * 50)


if __name__ == "__main__":
    main()
