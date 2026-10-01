"""Portable BuckPi case files."""

from __future__ import annotations

from dataclasses import dataclass
import json


CASE_FORMAT = "buckpi-case"
CASE_VERSION = 1


@dataclass(frozen=True)
class CaseVariable:
    name: str
    unit: str
    isolate: bool = False


@dataclass(frozen=True)
class SavedCase:
    variables: tuple[CaseVariable, ...]
    repeating_variables: tuple[str, ...] = ()


def encode_case(variables, repeating_variables=()) -> bytes:
    """Encode variables and the selected representation as portable JSON."""
    saved = SavedCase(
        tuple(CaseVariable(str(name), str(unit), bool(isolate)) for name, unit, isolate in variables),
        tuple(str(name) for name in repeating_variables),
    )
    _validate_case(saved)
    payload = {
        "format": CASE_FORMAT,
        "version": CASE_VERSION,
        "variables": [
            {"name": item.name, "unit": item.unit, "isolate": item.isolate}
            for item in saved.variables
        ],
        "repeating_variables": list(saved.repeating_variables),
    }
    return (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def decode_case(content) -> SavedCase:
    """Decode and structurally validate a BuckPi JSON case file."""
    try:
        if isinstance(content, bytes):
            content = content.decode("utf-8")
        payload = json.loads(content)
    except (TypeError, UnicodeDecodeError, json.JSONDecodeError):
        raise ValueError("Not a valid BuckPi case file") from None

    if not isinstance(payload, dict) or payload.get("format") != CASE_FORMAT:
        raise ValueError("Not a valid BuckPi case file")
    if payload.get("version") != CASE_VERSION:
        raise ValueError("Unsupported BuckPi case-file version")
    raw_variables = payload.get("variables")
    if not isinstance(raw_variables, list):
        raise ValueError("A BuckPi case must contain a variable list")

    variables = []
    for item in raw_variables:
        if not isinstance(item, dict):
            raise ValueError("Each saved variable must be an object")
        name, unit, isolate = item.get("name"), item.get("unit"), item.get("isolate", False)
        if not isinstance(name, str) or not isinstance(unit, str) or not isinstance(isolate, bool):
            raise ValueError("Each saved variable needs text name/unit fields and a Boolean isolate field")
        variables.append(CaseVariable(name, unit, isolate))

    repeating = payload.get("repeating_variables", [])
    if not isinstance(repeating, list) or any(not isinstance(name, str) for name in repeating):
        raise ValueError("Saved repeating variables must be a list of names")
    saved = SavedCase(tuple(variables), tuple(repeating))
    _validate_case(saved)
    return saved


def _validate_case(saved: SavedCase) -> None:
    if len(saved.variables) < 2:
        raise ValueError("A BuckPi case must contain at least two variables")
    names = [item.name.strip() for item in saved.variables]
    if any(not name or not item.unit.strip() for name, item in zip(names, saved.variables)):
        raise ValueError("Every saved variable needs a name and unit expression")
    if len(set(names)) != len(names):
        raise ValueError("Saved variable names must be unique")
    if len(set(saved.repeating_variables)) != len(saved.repeating_variables):
        raise ValueError("Saved repeating-variable names must be unique")
    if any(name not in names for name in saved.repeating_variables):
        raise ValueError("A saved repeating variable is not present in the variable list")
