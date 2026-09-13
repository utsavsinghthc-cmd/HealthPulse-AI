import re


SUPPORTED_CATEGORIES = {
    "respiratory",
    "fever",
    "gastrointestinal",
    "skin",
    "vector_borne",
}


CATEGORY_ALIASES = {
    "respiratory": "respiratory",
    "fever": "fever",
    "gastrointestinal": "gastrointestinal",
    "skin": "skin",
    "vector_borne": "vector_borne",
    "vector-borne": "vector_borne",
    "vector borne": "vector_borne",
}


VECTOR_BORNE_KEYWORDS = (
    "dengue",
    "malaria",
    "mosquito",
    "vector-borne",
    "vector borne",
)


def normalize_category(value):
    if value is None:
        return "unknown"

    text = str(value).strip().lower()
    text = text.replace("-", "_").replace(" ", "_")

    return CATEGORY_ALIASES.get(text, "unknown")


def extract_age(text):
    match = re.search(
        r"\bpatient\s+age\s*[:\-]?\s*(\d{1,3})\b",
        text,
        flags=re.IGNORECASE,
    )

    if match:
        return int(match.group(1))

    match = re.search(
        r"\bage\s*[:\-]?\s*(\d{1,3})\b",
        text,
        flags=re.IGNORECASE,
    )

    if match:
        return int(match.group(1))

    return None


def extract_gender(text):
    lowered = text.lower()

    if re.search(r"\bfemale\b|\bwoman\b|\bgirl\b", lowered):
        return "female"

    if re.search(r"\bmale\b|\bman\b|\bboy\b", lowered):
        return "male"

    return "unknown"


def extract_location(text):
    match = re.search(
        r"\blocation\s*[:\-]?\s*([A-Za-z]+(?:\s+[A-Za-z]+)*)",
        text,
        flags=re.IGNORECASE,
    )

    if match:
        return match.group(1).strip().rstrip("., ")

    return "unknown"


def extract_symptoms(text):
    match = re.search(
        r"\breported\s+symptoms\s*[:\-]?\s*(.*?)(?:\.\s*health\s+category|\.\s*severity|$)",
        text,
        flags=re.IGNORECASE,
    )

    if match:
        return match.group(1).strip().rstrip("., ")

    return ""


def infer_category(text, supplied_category=None):
    explicit = normalize_category(supplied_category)

    if explicit != "unknown":
        return explicit

    lowered = text.lower()

    if any(keyword in lowered for keyword in VECTOR_BORNE_KEYWORDS):
        return "vector_borne"

    if any(
        keyword in lowered
        for keyword in (
            "cough",
            "sore throat",
            "breathing difficulty",
            "shortness of breath",
            "wheezing",
            "respiratory",
        )
    ):
        return "respiratory"

    if any(
        keyword in lowered
        for keyword in (
            "stomach pain",
            "diarrhea",
            "vomiting",
            "nausea",
            "abdominal pain",
            "gastrointestinal",
        )
    ):
        return "gastrointestinal"

    if any(
        keyword in lowered
        for keyword in (
            "skin rash",
            "rash",
            "itching",
            "skin irritation",
        )
    ):
        return "skin"

    if any(
        keyword in lowered
        for keyword in (
            "fever",
            "high temperature",
            "body ache",
            "fatigue",
        )
    ):
        return "fever"

    return "unknown"


def extract_severity(text, supplied_severity=None):
    if supplied_severity:
        severity = str(supplied_severity).strip().lower()

        if severity in {"mild", "moderate", "severe"}:
            return severity

    lowered = text.lower()

    if re.search(r"\bsevere\b|\bcritical\b", lowered):
        return "severe"

    if re.search(r"\bmoderate\b", lowered):
        return "moderate"

    if re.search(r"\bmild\b", lowered):
        return "mild"

    return "unknown"


def parse_medical_report(
    report_text,
    patient_age=None,
    gender=None,
    location=None,
    symptoms=None,
    health_category=None,
    severity=None,
):
    text = str(report_text or "").strip()

    age = extract_age(text)
    if age is None and patient_age is not None:
        try:
            age = int(patient_age)
        except (TypeError, ValueError):
            age = None

    parsed_gender = extract_gender(text)
    if parsed_gender == "unknown" and gender:
        parsed_gender = str(gender).strip().lower()

    parsed_location = extract_location(text)
    if parsed_location == "unknown" and location:
        parsed_location = str(location).strip()

    parsed_symptoms = extract_symptoms(text)
    if not parsed_symptoms and symptoms:
        parsed_symptoms = str(symptoms).strip()

    parsed_category = infer_category(
        text=text,
        supplied_category=health_category,
    )

    parsed_severity = extract_severity(
        text=text,
        supplied_severity=severity,
    )

    return {
        "patient_age": age,
        "gender": parsed_gender,
        "location": parsed_location,
        "symptoms": parsed_symptoms,
        "health_category": parsed_category,
        "severity": parsed_severity,
    }
