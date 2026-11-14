"""Central access to the toxage-sim data schema.

The schema files in this folder are the single source for field names, types
and allowed values. This module loads them and checks records against them.
It needs only the Python standard library.
"""
import csv
import json
from pathlib import Path

SCHEMA_DIR = Path(__file__).resolve().parent
TABLES = ("scenario", "baseline", "observation", "event", "alert", "outcome", "risk_score")

_TYPES = {
    "string": lambda v: isinstance(v, str),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
    "null": lambda v: v is None,
}


_CACHE = {}


def load(table):
    """Return the JSON Schema of one table, see TABLES."""
    if table not in TABLES:
        raise ValueError(f"unknown table: {table}")
    if table not in _CACHE:
        with open(SCHEMA_DIR / f"{table}.schema.json", encoding="utf-8") as f:
            _CACHE[table] = json.load(f)
    return _CACHE[table]


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


def _to_cell(value):
    """A value as text of a CSV cell: empty for None, true/false for booleans."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return value


def _from_cell(text, spec):
    """The text of a CSV cell as a value of the type the schema gives the field."""
    types = spec.get("type", [])
    types = [types] if isinstance(types, str) else types
    if text == "" and "null" in types:
        return None
    if "boolean" in types:
        if text not in ("true", "false"):
            raise ValueError(f"{text!r} is not true or false")
        return text == "true"
    if "integer" in types:
        return int(text)
    if "number" in types:
        return float(text)
    return text


def write_csv(path, table, records):
    """Write records of a table as CSV, with the field names as header."""
    names = fields(table)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(names)
        for record in records:
            writer.writerow([_to_cell(record[name]) for name in names])


def read_csv(path, table):
    """Read a CSV file of a table and return typed, validated records."""
    props = load(table)["properties"]
    with open(path, newline="", encoding="utf-8") as f:
        records = [
            {name: _from_cell(text, props[name]) for name, text in row.items()}
            for row in csv.DictReader(f)
        ]
    validate(table, records)
    return records
