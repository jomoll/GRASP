"""
A tiny in-process mock FHIR server for the quickstart.

It implements just enough of the FHIR search API for MedAgentBench's read-only
lookup tasks — ``Patient`` search (by identifier / name / birthdate) and
``Observation`` search (by patient + code) — with no Docker and no sockets.

``get(url)`` matches the contract of MedAgentBench's ``send_get_request``: it
returns ``{"status_code": 200, "data": <json string>}`` on success (the data is
a JSON *string*, because real FHIR servers return ``application/fhir+json`` and
the benchmark reads ``response.text``), or ``{"error": ...}`` on failure.
"""

import json
from typing import Any, Dict, List
from urllib.parse import parse_qs, urlsplit


def _bundle(resources: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "resourceType": "Bundle",
        "type": "searchset",
        "total": len(resources),
        "entry": [{"resource": r} for r in resources],
    }


class MockFHIR:
    def __init__(self, patients: List[Dict[str, Any]], observations: List[Dict[str, Any]]):
        self.patients = patients
        self.observations = observations

    # -- query entry point -------------------------------------------------

    def get(self, url: str) -> Dict[str, Any]:
        try:
            parts = urlsplit(url)
            path = parts.path.rstrip("/")
            resource = path.split("/")[-1] if path else ""
            # Some callers put the resource in the query-less remainder; also
            # handle base URLs without a real scheme by scanning the raw string.
            if resource not in ("Patient", "Observation"):
                for r in ("Patient", "Observation"):
                    if f"/{r}" in url or url.lstrip().startswith(r) or f" {r}" in url:
                        resource = r
                        break
            params = {k.lower(): v for k, v in parse_qs(parts.query).items()}

            if resource == "Patient":
                matches = self._search_patients(params)
            elif resource == "Observation":
                matches = self._search_observations(params)
            else:
                return {"error": f"unsupported resource: {resource or url!r}"}

            return {"status_code": 200, "data": json.dumps(_bundle(matches))}
        except Exception as e:  # pragma: no cover - defensive
            return {"error": str(e)}

    # -- search implementations -------------------------------------------

    def _search_patients(self, params: Dict[str, List[str]]) -> List[Dict[str, Any]]:
        def first(key):
            v = params.get(key)
            return v[0] if v else None

        identifier = first("identifier")
        family = first("family")
        given = first("given")
        birthdate = first("birthdate")
        name = first("name")

        out = []
        for p in self.patients:
            mrn = p["identifier"][0]["value"]
            if identifier is not None and identifier != mrn:
                continue
            fam = p["name"][0]["family"]
            giv = p["name"][0]["given"][0]
            if family is not None and family.lower() != fam.lower():
                continue
            if given is not None and given.lower() != giv.lower():
                continue
            if birthdate is not None and birthdate != p["birthDate"]:
                continue
            if name is not None:
                full = f"{giv} {fam}".lower()
                if name.lower() not in full:
                    continue
            out.append(p)
        return out

    def _search_observations(self, params: Dict[str, List[str]]) -> List[Dict[str, Any]]:
        def first(key):
            v = params.get(key)
            return v[0] if v else None

        patient = first("patient")
        code = first("code")

        out = []
        for o in self.observations:
            ref = o["subject"]["reference"]  # "Patient/<MRN>"
            mrn = ref.split("/", 1)[-1]
            if patient is not None and patient != mrn:
                continue
            if code is not None:
                obs_code = o["code"].get("text") or o["code"]["coding"][0]["code"]
                if code != obs_code:
                    continue
            out.append(o)
        return out
