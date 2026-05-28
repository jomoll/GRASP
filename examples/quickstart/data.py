"""
Canned data for the quickstart, focused on **one** MedAgentBench task family:

    task4 — most recent magnesium (FHIR code "MG") within the last 24 hours.

This is intentionally a single-skill exercise — one mechanism, one failure
mode, one learnable skill to discover. The released MedAgentBench skill libraries
include exactly this kind of skill (``observation_value_extraction``):

    CORRECT: FINISH([2.1])             # bare valueQuantity.value as a number
    WRONG:   FINISH(["2.1 mg/dL"])     # units in the value
    WRONG:   FINISH([null])            # missing recency / 24h-window logic
    WRONG:   FINISH(["No data"])       # not the prescribed -1 sentinel

All observation timestamps are relative to a fixed "current time" so the grader
is deterministic. Half the patients have a magnesium reading within 24 h (real
numeric answer), half do not (answer ``-1`` — either no MG observations at all,
or only readings older than 24 h).
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List

from .mock_fhir import MockFHIR

CURRENT_TIME = "2023-11-13T10:15:00+00:00"
_NOW = datetime.fromisoformat(CURRENT_TIME)


# -- patients ---------------------------------------------------------------
# 30 patients: 15 with a magnesium reading within 24h (real answer), 15 without
# (answer -1 — either old-only or no MG observations at all).
# (mrn, family, given, birthDate, gender)
_PATIENTS = [
    # --- 15 patients with a within-24h MG reading (real-value answer) ---
    ("S3032536", "Alvarez",  "Maria",   "1958-04-12", "female"),
    ("S1098667", "Okafor",   "James",   "1979-09-03", "male"),
    ("S2876541", "Chen",     "Linda",   "1990-01-22", "female"),
    ("S4451220", "Bauer",    "Robert",  "2001-07-15", "male"),
    ("S5523451", "Garcia",   "Sofia",   "1985-11-30", "female"),
    ("S8801776", "Mueller",  "Hannah",  "1995-06-04", "female"),
    ("S1122334", "Roberts",  "James",   "1962-04-18", "male"),
    ("S2233445", "Khan",     "Amira",   "1974-11-02", "female"),
    ("S3344556", "Schmidt",  "Klaus",   "1955-07-19", "male"),
    ("S4455667", "Lopez",    "Carmen",  "1988-12-05", "female"),
    ("S5566778", "Park",     "Ji-hoon", "1969-02-27", "male"),
    ("S6677889", "Rossi",    "Giulia",  "1981-09-08", "female"),
    ("S7788990", "Anderson", "Mark",    "1948-06-23", "male"),
    ("S8899001", "Singh",    "Priya",   "1992-03-10", "female"),
    ("S9900112", "Hoffmann", "Lukas",   "1976-10-14", "male"),

    # --- 15 patients with no within-24h MG reading (answer = -1) ---
    ("S6534835", "Stafford", "Peter",   "1932-12-29", "male"),
    ("S7712334", "Nguyen",   "Thi",     "1965-08-09", "female"),
    ("S9908762", "Sato",     "Haruki",  "1972-02-18", "male"),
    ("S2299114", "Patel",    "Arjun",   "1947-03-21", "male"),
    ("S6630228", "Kowalski", "Eva",     "1958-09-14", "female"),
    ("S3344199", "Tanaka",   "Yui",     "1978-05-08", "female"),
    ("S1234567", "Lewis",    "Sarah",   "1959-05-11", "female"),
    ("S2345678", "Martin",   "Pierre",  "1944-08-29", "male"),
    ("S3456789", "Yamamoto", "Hiroshi", "1953-01-17", "male"),
    ("S4567890", "Costa",    "Lucia",   "1971-04-22", "female"),
    ("S5678901", "OBrien",   "Sean",    "1937-12-08", "male"),
    ("S6789012", "Davis",    "Emma",    "1996-07-30", "female"),
    ("S7890123", "Wang",     "Wei",     "1962-11-15", "male"),
    ("S8901234", "Brown",    "Olivia",  "1985-02-04", "female"),
    ("S9012345", "Petrov",   "Alexei",  "1949-09-26", "male"),
]

# -- magnesium observations -------------------------------------------------
# (mrn, code, value, unit, hours_before_now)
# A 24-hour cutoff splits "within window" from "outside window".
_OBSERVATIONS = [
    # --- within-24h readings (real-value answers) ---
    ("S3032536", "MG", 2.1, "mg/dL",  5),    # most recent within 24h
    ("S3032536", "MG", 1.8, "mg/dL", 30),    # distractor (outside)
    ("S1098667", "MG", 2.4, "mg/dL", 10),    # most recent within 24h
    ("S1098667", "MG", 1.9, "mg/dL", 22),    # within 24h, older
    ("S1098667", "MG", 1.6, "mg/dL", 50),    # outside
    ("S2876541", "MG", 2.0, "mg/dL",  1),    # within 24h (single)
    ("S4451220", "MG", 2.3, "mg/dL", 12),    # within 24h
    ("S4451220", "MG", 2.5, "mg/dL", 36),    # outside
    ("S5523451", "MG", 2.2, "mg/dL", 18),    # within 24h
    ("S8801776", "MG", 2.6, "mg/dL",  6),    # within 24h, most recent
    ("S8801776", "MG", 2.5, "mg/dL", 15),    # within 24h, older
    ("S1122334", "MG", 1.9, "mg/dL",  8),    # within 24h
    ("S2233445", "MG", 2.7, "mg/dL",  3),    # within 24h
    ("S3344556", "MG", 1.8, "mg/dL", 14),    # within 24h
    ("S3344556", "MG", 2.0, "mg/dL", 40),    # outside
    ("S4455667", "MG", 2.5, "mg/dL", 19),    # within 24h
    ("S5566778", "MG", 2.4, "mg/dL",  2),    # most recent within 24h
    ("S5566778", "MG", 2.2, "mg/dL", 20),    # within 24h, older
    ("S6677889", "MG", 2.1, "mg/dL",  7),    # within 24h
    ("S7788990", "MG", 2.8, "mg/dL", 11),    # within 24h
    ("S7788990", "MG", 1.9, "mg/dL", 35),    # outside
    ("S8899001", "MG", 1.7, "mg/dL", 21),    # within 24h
    ("S9900112", "MG", 2.6, "mg/dL",  4),    # most recent within 24h
    ("S9900112", "MG", 2.3, "mg/dL", 13),    # within 24h, older
    ("S9900112", "MG", 1.5, "mg/dL", 48),    # outside

    # --- old-only readings (answer -1) ---
    ("S6534835", "MG", 1.9, "mg/dL", 50),
    ("S7712334", "MG", 1.5, "mg/dL", 30),
    ("S9908762", "MG", 1.7, "mg/dL", 28),
    ("S9908762", "MG", 1.4, "mg/dL", 60),
    ("S1234567", "MG", 2.0, "mg/dL", 26),
    ("S3456789", "MG", 1.8, "mg/dL", 32),
    ("S3456789", "MG", 1.6, "mg/dL", 50),
    ("S5678901", "MG", 2.2, "mg/dL", 48),
    ("S7890123", "MG", 1.9, "mg/dL", 40),
    ("S7890123", "MG", 1.5, "mg/dL", 72),
    ("S9012345", "MG", 1.7, "mg/dL", 28),
    # No-MG patients: S2299114, S6630228, S3344199, S2345678, S4567890,
    # S6789012, S8901234  (answer -1 via empty Observation result).
]


# -- expected answers per patient (used by tests and by the sample builder) -
_EXPECTED = {
    # 15 real-value answers (most recent within 24h)
    "S3032536": 2.1, "S1098667": 2.4, "S2876541": 2.0,
    "S4451220": 2.3, "S5523451": 2.2, "S8801776": 2.6,
    "S1122334": 1.9, "S2233445": 2.7, "S3344556": 1.8,
    "S4455667": 2.5, "S5566778": 2.4, "S6677889": 2.1,
    "S7788990": 2.8, "S8899001": 1.7, "S9900112": 2.6,
    # 15 patients without a within-24h reading
    "S6534835": -1, "S7712334": -1, "S9908762": -1,
    "S2299114": -1, "S6630228": -1, "S3344199": -1,
    "S1234567": -1, "S2345678": -1, "S3456789": -1,
    "S4567890": -1, "S5678901": -1, "S6789012": -1,
    "S7890123": -1, "S8901234": -1, "S9012345": -1,
}


# -- FHIR resource construction --------------------------------------------

def _patient_resource(mrn, family, given, birth_date, gender) -> Dict[str, Any]:
    return {
        "resourceType": "Patient",
        "id": mrn,
        "identifier": [{"use": "usual", "value": mrn}],
        "name": [{"use": "official", "family": family, "given": [given]}],
        "birthDate": birth_date,
        "gender": gender,
    }


def _observation_resource(idx, mrn, code, value, unit, hours_before) -> Dict[str, Any]:
    eff = (_NOW - timedelta(hours=hours_before)).isoformat()
    return {
        "resourceType": "Observation",
        "id": f"obs-{idx}",
        "status": "final",
        "code": {"text": code, "coding": [{"code": code, "display": code}]},
        "subject": {"reference": f"Patient/{mrn}"},
        "effectiveDateTime": eff,
        "valueQuantity": {"value": value, "unit": unit},
    }


def build_mock() -> MockFHIR:
    patients = [_patient_resource(*p) for p in _PATIENTS]
    observations = [_observation_resource(i, *o) for i, o in enumerate(_OBSERVATIONS)]
    return MockFHIR(patients, observations)


# -- task samples -----------------------------------------------------------
# One task4 sample per patient. Order is interleaved (real-value, -1, real-value, …)
# so a 2/3 dev : 1/3 val slice keeps both kinds in both splits.

_CONTEXT = (
    f"It is {CURRENT_TIME} now. The code for magnesium is \"MG\". "
    "The answer should be a single number in mg/dL. "
    "The answer should be -1 if no measurement within the last 24 hours is available."
)


def _samples_all() -> List[Dict[str, Any]]:
    # interleave real-value patients with -1 patients
    real = [m for m, v in _EXPECTED.items() if v != -1]
    none = [m for m, v in _EXPECTED.items() if v == -1]
    ordered = []
    for i in range(max(len(real), len(none))):
        if i < len(real):
            ordered.append(real[i])
        if i < len(none):
            ordered.append(none[i])
    return [
        {
            "id": f"task4_{i+1}",
            "eval_MRN": mrn,
            "instruction": f"What is the most recent magnesium level of patient "
                           f"{mrn} within the last 24 hours?",
            "context": _CONTEXT,
        }
        for i, mrn in enumerate(ordered)
    ]


_ALL_SAMPLES = _samples_all()


def samples_for(split: str) -> List[Dict[str, Any]]:
    """Deterministic 2/3 dev : 1/3 val slice over the single task family."""
    cut = (len(_ALL_SAMPLES) * 2) // 3
    return _ALL_SAMPLES[:cut] if split == "dev" else _ALL_SAMPLES[cut:]


# FHIR tool advertised to the agent — Observation search only (the agent never
# needs Patient lookup for this task: the MRN is given in the instruction).
FUNCS = [
    {
        "name": "GET {api_base}/Observation",
        "description": "Search lab/vital observations for a patient by code.",
        "parameters": {
            "patient": "Patient MRN, e.g. S3032536",
            "code":    "Observation code, e.g. MG (magnesium)",
            "date":    "Optional date filter",
        },
    },
]
