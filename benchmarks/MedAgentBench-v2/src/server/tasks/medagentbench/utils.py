import json
import re
import requests


def parse_agent_result(raw):
    """Normalize agent result to a Python object regardless of whether it
    arrived as a JSON string (from the HTTP API) or was already deserialized."""
    if isinstance(raw, str):
        return json.loads(raw)
    return raw


def extract_numeric(raw):
    """Extract the first numeric value from any result representation.

    Handles JSON strings, Python lists of numbers, Python lists of prose
    strings (e.g. ["85 mg/dL"]), and bare strings.
    Returns float, or None if no number can be found.
    """
    try:
        parsed = parse_agent_result(raw)
    except Exception:
        parsed = raw

    if isinstance(parsed, (int, float)):
        return float(parsed)
    if isinstance(parsed, list) and len(parsed) >= 1:
        val = parsed[0]
        if isinstance(val, (int, float)):
            return float(val)
        if isinstance(val, str):
            m = re.search(r"-?\d+(?:\.\d+)?", val)
            if m:
                return float(m.group())
    if isinstance(parsed, str):
        m = re.search(r"-?\d+(?:\.\d+)?", parsed)
        if m:
            return float(m.group())
    return None


def match_agent_result(ref_sol, raw, tol=0.0, accept_empty=False):
    """Compare agent result against reference with lenient type handling.

    Steps:
    1. Normalize raw (JSON string or Python object → Python object).
    2. Try exact equality.
    3. If ref_sol is [single_number], try extracting a number from raw
       and compare with the given tolerance (default 0 = exact).
    4. If ref_sol is [number, timestamp_str] and parsed is a 2-element list,
       check numeric value and date prefix element-by-element.
    5. Optionally accept [] as a valid answer (write tasks where the
       agent signals completion without restating the measured value).
    """
    try:
        parsed = parse_agent_result(raw)
    except Exception:
        parsed = None

    if parsed is not None and ref_sol == parsed:
        return True

    if accept_empty and parsed == []:
        return True

    if (isinstance(ref_sol, list) and len(ref_sol) == 1
            and isinstance(ref_sol[0], (int, float))):
        extracted = extract_numeric(raw)
        if extracted is not None:
            return abs(extracted - float(ref_sol[0])) <= tol

    if (isinstance(ref_sol, list) and len(ref_sol) == 2
            and isinstance(ref_sol[0], (int, float))
            and isinstance(ref_sol[1], str)
            and isinstance(parsed, list) and len(parsed) == 2):
        extracted = extract_numeric(parsed[0])
        date_prefix = str(ref_sol[1])[:10]
        if (extracted is not None
                and abs(extracted - float(ref_sol[0])) <= tol
                and isinstance(parsed[1], str)
                and parsed[1].startswith(date_prefix)):
            return True

    return False


def verify_fhir_server(fhir_api_base):
    """
    Verify connection to FHIR server. Returns True if everything is good
    """
    res = send_get_request(f'{fhir_api_base}metadata')
    if res.get('status_code', 0) != 200:
        return False
    return True

def send_get_request(url, params=None, headers=None):
    """
    Sends a GET HTTP request to the given URL.

    Args:
        url (str): The URL to send the GET request to.
        params (dict, optional): Query parameters to include in the request. Defaults to None.
        headers (dict, optional): HTTP headers to include in the request. Defaults to None.

    Returns:
        dict: A dictionary containing the response's status code and data.

    Raises:
        requests.exceptions.RequestException: If an error occurs during the request.
    """
    try:
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()  # Raises an HTTPError if the response code is 4xx or 5xx
        # Always return text so callers can json.loads() uniformly.
        # HAPI FHIR returns 'application/fhir+json' (not 'application/json'),
        # so response.text is always the right type here.
        return {
            "status_code": response.status_code,
            "data": response.text,
        }
    except Exception as e:
        return {"error": str(e)}