from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest


ROOT = Path(__file__).resolve().parents[2]
SCHEMAS = ROOT / "schemas"


def _load(name: str) -> dict:
    return json.loads((SCHEMAS / name).read_text())


def test_ms1_schema_accepts_valid_payload() -> None:
    schema = _load("ms1_generate_slds.schema.json")
    payload = {"slds": ["pixelforge", "tiny-arcade"], "notes": "ok"}
    jsonschema.validate(payload, schema)


def test_ms1_schema_accepts_500_plus_payload() -> None:
    schema = _load("ms1_generate_slds.schema.json")
    payload = {"slds": [f"brand{i}" for i in range(550)]}
    jsonschema.validate(payload, schema)


def test_ms1_schema_rejects_more_than_5000_slds() -> None:
    schema = _load("ms1_generate_slds.schema.json")
    payload = {"slds": [f"brand{i}" for i in range(5001)]}
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(payload, schema)


def test_ms1_schema_rejects_bad_slds() -> None:
    schema = _load("ms1_generate_slds.schema.json")
    payload = {"slds": ["Bad.Name"]}
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(payload, schema)


def test_ts1_input_schema_rejects_empty_tld_list() -> None:
    schema = _load("ts1_check_domains_in.schema.json")
    payload = {"tlds": [], "slds": ["pixelforge"]}
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(payload, schema)


def test_ts1_input_schema_rejects_more_than_three_tlds() -> None:
    schema = _load("ts1_check_domains_in.schema.json")
    payload = {"tlds": [".com", ".net", ".io", ".ai"], "slds": ["pixelforge"]}
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(payload, schema)


def test_ts1_input_schema_accepts_single_tld() -> None:
    schema = _load("ts1_check_domains_in.schema.json")
    payload = {"tlds": [".com"], "slds": ["pixelforge"]}
    jsonschema.validate(payload, schema)


def test_ts1_input_schema_accepts_large_sld_lists_with_batching_option() -> None:
    schema = _load("ts1_check_domains_in.schema.json")
    payload = {
        "tlds": [".com", ".net", ".io"],
        "slds": [f"brand{i}" for i in range(250)],
        "options": {"batch_size": 100},
    }
    jsonschema.validate(payload, schema)


def test_ts1_input_schema_accepts_deterministic_mode_options() -> None:
    schema = _load("ts1_check_domains_in.schema.json")
    payload = {
        "tlds": [".com", ".ai", ".io"],
        "slds": ["agentforge", "codepilot"],
        "options": {"deterministic_mode": True, "deterministic_seed": 99},
    }
    jsonschema.validate(payload, schema)


def test_ts1_output_schema_accepts_minimal_result() -> None:
    schema = _load("ts1_check_domains_out.schema.json")
    payload = {
        "checked_at": "2026-02-16T14:02:11Z",
        "results": [
            {
                "domain": "pixelforge.com",
                "status": "taken",
                "confidence": 0.98,
                "method": "rdap",
            }
        ],
        "suggested_best": "pixelforge.de",
    }
    jsonschema.validate(payload, schema)


def test_ms2_schema_allows_null_best_domain() -> None:
    schema = _load("ms2_pick_best.schema.json")
    payload = {
        "best_domain": None,
        "rationale": "none confirmed",
        "ranked": [],
        "next_actions": ["Try more SLDs"],
    }
    jsonschema.validate(payload, schema)
