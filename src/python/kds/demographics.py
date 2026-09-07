"""Demographic table of the 12 participants.

Recorded at acquisition and used by the pipeline for sex-specific COM
computation, normalisation, and reporting. See Caracteristicas muestra.csv
in the source archive for the full questionnaire fields.
"""

from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class Subject:
    id: str
    sex: str            # 'M' or 'F'
    age_years: int
    height_cm: float
    mass_kg: float
    bmi: float
    practice_years: int
    grade: str          # e.g. '1 Dan', '3 Dan', 'Branca'
    style: str          # 'Shotokan' | 'Goju-Ryu' | 'Wado-Ryu'
    modality: str | None  # 'Kata' | 'Kumite' | None
    level: str | None     # 'International' | 'National' | 'Regional' | None
    weekly_days: float
    weekly_hours: float
    upper_dominant: str   # 'Right' | 'Left'
    lower_dominant: str   # 'Right' | 'Left'
    dominant_guard: str   # 'Left' | 'Right'


SUBJECTS: dict[str, Subject] = {
    "ID003": Subject("ID003", "M", 22, 158.5, 69.2, 27.7, 17, "3 Dan", "Goju-Ryu", "Kata", "International", 1, 1, "Right", "Right", "Left"),
    "ID004": Subject("ID004", "M", 23, 170.5, 104.4, 36.1, 13, "1 Dan", "Shotokan", "Kumite", "Regional", 1, 1, "Right", "Left", "Left"),
    "ID005": Subject("ID005", "M", 21, 167.5, 70.9, 25.4, 13, "1 Dan", "Shotokan", "Kumite", "International", 1, 1, "Right", "Left", "Left"),
    "ID006": Subject("ID006", "F", 22, 158.0, 56.6, 22.7, 10, "1 Dan", "Goju-Ryu", "Kumite", "International", 2, 1, "Right", "Right", "Left"),
    "ID007": Subject("ID007", "F", 20, 165.0, 72.5, 26.6, 15, "1 Dan", "Goju-Ryu", "Kata", "International", 3, 4, "Right", "Right", "Left"),
    "ID008": Subject("ID008", "F", 19, 155.0, 52.9, 22.0, 15, "1 Dan", "Goju-Ryu", "Kata", "International", 6, 12, "Right", "Right", "Left"),
    "ID009": Subject("ID009", "F", 20, 155.0, 72.2, 30.1, 12, "1 Dan", "Shotokan", "Kata", "National", 3, 4, "Right", "Right", "Left"),
    "ID010": Subject("ID010", "F", 20, 161.5, 70.7, 27.3, 15, "1 Dan", "Shotokan", "Kumite", "International", 5, 8, "Right", "Right", "Left"),
    "ID011": Subject("ID011", "M", 21, 184.5, 84.8, 25.0, 16, "1 Dan", "Shotokan", "Kumite", "International", 6, 10, "Left", "Left", "Left"),
    "ID012": Subject("ID012", "F", 32, 161.0, 90.6, 35.0, 25, "3 Dan", "Shotokan", "Kata", "National", 4, 5, "Right", "Right", "Left"),
    "ID013": Subject("ID013", "F", 45, 160.0, 61.7, 24.1, 1, "Branca", "Shotokan", None, None, 2, 2, "Right", "Right", "Left"),
    "ID014": Subject("ID014", "F", 20, 163.5, 59.8, 22.5, 13, "1 Dan", "Goju-Ryu", "Kata", "International", 5, 7, "Right", "Right", "Left"),
}


def get(subject_id: str) -> Subject:
    return SUBJECTS[subject_id]
