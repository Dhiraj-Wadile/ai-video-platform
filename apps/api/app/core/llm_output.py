"""Defensive parsing of LLM output.

Every agent and service treats model output as untrusted text: models wrap JSON in
markdown fences, return "30s" where the schema says int, or return a bare list where a
mapping was expected. Without a single normalisation point each call site grows its own
incomplete `.replace("```json\n", "")` and a stray `data.get(...)` turns a survivable
model quirk into an HTTP 500.
"""
import json
import re
from typing import Any, Optional

_FENCE = re.compile(r"^\s*```[a-zA-Z0-9_-]*\s*|\s*```\s*$")
_NUMBER = re.compile(r"-?\d+(?:\.\d+)?")


def strip_fences(content: str) -> str:
    """Remove a surrounding markdown code fence.

    Handles ```json\\n, ```json, and ```\\n, which the string-replace approach missed.
    """
    if not isinstance(content, str):
        return ""
    return _FENCE.sub("", content.strip()).strip()


def parse_json(content: str) -> Any:
    """Parse LLM text as JSON. Returns None when it is not valid JSON."""
    try:
        return json.loads(strip_fences(content))
    except (json.JSONDecodeError, TypeError, ValueError):
        return None


def parse_json_object(content: str) -> dict:
    """Parse LLM text and require a JSON object.

    A list or scalar is a legitimate model response, so it is wrapped under "data"
    rather than discarded. Callers always get a mapping they can call `.get` on.
    """
    parsed = parse_json(content)
    if isinstance(parsed, dict):
        return parsed
    if parsed is None:
        return {}
    return {"data": parsed}


def as_dict(value: Any) -> dict:
    """Coerce arbitrary structured data into a mapping.

    Model output that already is a mapping is returned unchanged, so this is safe to
    place in front of any `x.get(...)`.
    """
    if isinstance(value, dict):
        return value
    return {}


def coerce_int(value: Any, default: Optional[int] = None) -> Optional[int]:
    """Coerce 30, "30", "30s", 30.9 or None into an int."""
    if value is None or isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        return int(value)
    match = _NUMBER.search(str(value))
    return int(float(match.group())) if match else default


def coerce_float(value: Any, default: Optional[float] = None) -> Optional[float]:
    """Coerce 3, "3", "3.5", "3-4s" or None into a float.

    "3-4s" resolves to the first number (3.0), which is the lower bound of the range the
    model described - a defensible scene duration.
    """
    if value is None or isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        return float(value)
    match = _NUMBER.search(str(value))
    return float(match.group()) if match else default
