"""
Canned data for the quickstart: a handful of patients and lab observations, the
FHIR resources built from them, and the dev/val task samples.

All times are relative to a fixed "current time" so graders are deterministic.
The data is small on purpose — a full GRASP run finishes in minutes.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List

from .mock_fhir import MockFHIR

CURRENT_TIME = "2023-11-13T10:15:00+00:00"
_NOW = datetime.fromisoformat(CURRENT_TIME)


# -- raw data ---------------------------------------------------------------

# (mrn, family, given, birthDate, gender)
_PATIENTS = [
    ("S6534835", "Stafford", "Peter", "1932-12-29", "male"),
    ("S3032536", "Alvarez", "Maria", "1958-04-12", "female"),
    ("S1098667", "Okafor", "James", "1979-09-03", "male"),
    ("S2876541", "Chen", "Linda", "1990-01-22", "female"),
    ("S4451220", "Bauer", "Robert", "2001-07-15", "male"),
]

# (mrn, code, value, unit, hours_before_now)
_OBSERVATIONS = [
    # Magnesium (MG)
    ("S3032536", "MG", 2.1, "mg/dL", 5),     # within 24h, most recent
    ("S3032536", "MG", 1.8, "mg/dL", 30),    # older than 24h
    ("S6534835", "MG", 1.9, "mg/dL", 50),    # only an old reading -> -1 within 24h
    # Glucose (GLU)
    ("S1098667", "GLU", 100.0, "mg/dL", 2),  # most recent overall + within 24h
    ("S1098667", "GLU", 120.0, "mg/dL", 10),
    ("S1098667", "GLU", 90.0, "mg/dL", 20),
    ("S1098667", "GLU", 200.0, "mg/dL", 40),  # older than 24h
]


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
    observations = [
        _observation_resource(i, *o) for i, o in enumerate(_OBSERVATIONS)
    ]
    return MockFHIR(patients, observations)


# -- task samples -----------------------------------------------------------
# Read-only MedAgentBench task families:
#   task1 patient lookup by name+DOB -> MRN
#   task2 age from MRN
#   task4 most recent magnesium within 24h
#   task6 average glucose within 24h
#   task7 most recent glucose overall

_CTX_TIME = f"It is {CURRENT_TIME} now."
_CTX_MINUS1 = "The answer should be -1 if no matching measurement is available."

_ALL_SAMPLES: List[Dict[str, Any]] = [
    # task1 — name + DOB -> MRN (sol stored; "Patient not found" when absent)
    {"id": "task1_1", "eval_MRN": "S6534835", "sol": ["S6534835"],
     "instruction": "What is the MRN of the patient with name Peter Stafford and DOB of 1932-12-29? "
                    "If the patient does not exist, the answer should be \"Patient not found\".",
     "context": ""},
    {"id": "task1_2", "eval_MRN": "S2876541", "sol": ["S2876541"],
     "instruction": "What is the MRN of the patient with name Linda Chen and DOB of 1990-01-22? "
                    "If the patient does not exist, the answer should be \"Patient not found\".",
     "context": ""},
    {"id": "task1_3", "eval_MRN": "", "sol": ["Patient not found"],
     "instruction": "What is the MRN of the patient with name John Doe and DOB of 2000-01-01? "
                    "If the patient does not exist, the answer should be \"Patient not found\".",
     "context": ""},
    {"id": "task1_4", "eval_MRN": "S1098667", "sol": ["S1098667"],
     "instruction": "What is the MRN of the patient with name James Okafor and DOB of 1979-09-03? "
                    "If the patient does not exist, the answer should be \"Patient not found\".",
     "context": ""},

    # task2 — age from MRN
    {"id": "task2_1", "eval_MRN": "S6534835",
     "instruction": "What is the age in years of the patient with MRN S6534835? "
                    "The answer should be a single integer.",
     "context": _CTX_TIME},
    {"id": "task2_2", "eval_MRN": "S2876541",
     "instruction": "What is the age in years of the patient with MRN S2876541? "
                    "The answer should be a single integer.",
     "context": _CTX_TIME},
    {"id": "task2_3", "eval_MRN": "S4451220",
     "instruction": "What is the age in years of the patient with MRN S4451220? "
                    "The answer should be a single integer.",
     "context": _CTX_TIME},

    # task4 — most recent magnesium within 24h
    {"id": "task4_1", "eval_MRN": "S3032536",
     "instruction": "What is the most recent magnesium level of patient S3032536 within the last 24 hours?",
     "context": f"{_CTX_TIME} The code for magnesium is \"MG\". The answer should be a single number "
                f"in mg/dL. {_CTX_MINUS1}"},
    {"id": "task4_2", "eval_MRN": "S6534835",
     "instruction": "What is the most recent magnesium level of patient S6534835 within the last 24 hours?",
     "context": f"{_CTX_TIME} The code for magnesium is \"MG\". The answer should be a single number "
                f"in mg/dL. {_CTX_MINUS1}"},

    # task6 — average glucose within 24h
    {"id": "task6_1", "eval_MRN": "S1098667",
     "instruction": "What is the average glucose level of patient S1098667 within the last 24 hours?",
     "context": f"{_CTX_TIME} The code for glucose is \"GLU\". The answer should be a single number "
                f"in mg/dL. {_CTX_MINUS1}"},
    {"id": "task6_2", "eval_MRN": "S2876541",
     "instruction": "What is the average glucose level of patient S2876541 within the last 24 hours?",
     "context": f"{_CTX_TIME} The code for glucose is \"GLU\". The answer should be a single number "
                f"in mg/dL. {_CTX_MINUS1}"},

    # task7 — most recent glucose overall
    {"id": "task7_1", "eval_MRN": "S1098667",
     "instruction": "What is the most recent glucose level of patient S1098667?",
     "context": f"{_CTX_TIME} The code for glucose is \"GLU\". The answer should be a single number "
                f"in mg/dL. {_CTX_MINUS1}"},
]


def _split(samples, split):
    # Deterministic, stratified by task family: 2/3 dev, 1/3 val.
    by_task: Dict[str, List[Dict]] = {}
    for s in samples:
        by_task.setdefault(s["id"].split("_")[0], []).append(s)
    dev, val = [], []
    for _, group in sorted(by_task.items()):
        cut = max(1, (len(group) * 2) // 3)
        dev.extend(group[:cut])
        val.extend(group[cut:] or group[:1])  # ensure val never empty for a family
    return dev if split == "dev" else val


def samples_for(split: str) -> List[Dict[str, Any]]:
    return _split(_ALL_SAMPLES, split)


# FHIR tool definitions advertised to the agent (subset of MedAgentBench funcs).
FUNCS = [
    {
        "name": "GET {api_base}/Patient",
        "description": "Search for patients. Combine parameters to narrow results.",
        "parameters": {
            "identifier": "Patient MRN, e.g. S6534835",
            "family": "Family (last) name",
            "given": "Given (first) name",
            "birthdate": "Date of birth, YYYY-MM-DD",
            "name": "Any part of the name",
        },
    },
    {
        "name": "GET {api_base}/Observation",
        "description": "Search lab/vital observations for a patient by code.",
        "parameters": {
            "patient": "Patient MRN, e.g. S3032536",
            "code": "Observation code, e.g. MG (magnesium) or GLU (glucose)",
            "date": "Optional date filter",
        },
    },
]
