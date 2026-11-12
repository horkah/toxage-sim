"""Central access to the toxage-sim data schema.

The schema files in this folder are the single source for field names, types
and allowed values. This module loads them and checks records against them.
It needs only the Python standard library.
"""
import json
from pathlib import Path

SCHEMA_DIR = Path(__file__).resolve().parent
TABLES = ("baseline", "outcome")

_TYPES = {
    "string": lambda v: isinstance(v, str),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
    "null": lambda v: v is None,
}


def load(table):
    """Return the JSON Schema of one table ("baseline" or "outcome")."""
    if table not in TABLES:
        raise ValueError(f"unknown table: {table}")
    with open(SCHEMA_DIR / f"{table}.schema.json", encoding="utf-8") as f:
        return json.load(f)


def fields(table):
    """Return the field names of a table in schema order."""
    return list(load(table)["properties"])


def allowed_values(table, field):
    """Return the allowed values of an enumerated field."""
    return list(load(table)["properties"][field]["enum"])


def errors(table, record, schema=None):
    """Return a list of problems of one record. An empty list means valid."""
    schema = schema or load(table)
    props = schema["properties"]
    found = []
    for name in schema["required"]:
        if name not in record:
            found.append(f"{name}: missing")
    for name, value in record.items():
        if name not in props:
            found.append(f"{name}: not in schema")
            continue
        spec = props[name]
        types = spec.get("type", [])
        types = [types] if isinstance(types, str) else types
        if types and not any(_TYPES[t](value) for t in types):
            found.append(f"{name}: {value!r} is not of type {'/'.join(types)}")
            continue
        if value is None:
            continue
        if "enum" in spec and value not in spec["enum"]:
            found.append(f"{name}: {value!r} is not an allowed value")
        if "minimum" in spec and value < spec["minimum"]:
            found.append(f"{name}: {value!r} is below {spec['minimum']}")
        if "maximum" in spec and value > spec["maximum"]:
            found.append(f"{name}: {value!r} is above {spec['maximum']}")
    return found


def validate(table, records):
    """Raise ValueError at the first invalid record."""
    schema = load(table)
    for i, record in enumerate(records):
        found = errors(table, record, schema)
        if found:
            raise ValueError(f"{table} record {i}: " + "; ".join(found))
