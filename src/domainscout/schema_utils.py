from __future__ import annotations

import json
from pathlib import Path

import jsonschema


ROOT = Path(__file__).resolve().parents[2]
SCHEMAS_DIR = ROOT / "schemas"


def load_schema(name: str) -> dict:
    return json.loads((SCHEMAS_DIR / name).read_text())


def validate_payload(payload: dict, schema_name: str) -> None:
    jsonschema.validate(payload, load_schema(schema_name))
