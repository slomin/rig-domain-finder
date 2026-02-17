from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from .env_guard import require_uv_project_env


def _read_payload(input_path: str | None) -> dict:
    if input_path:
        return json.loads(Path(input_path).read_text())
    return json.loads(sys.stdin.read())


def _write_output(payload: dict, output_path: str | None) -> None:
    rendered = json.dumps(payload, indent=2)
    if output_path:
        Path(output_path).write_text(rendered + "\n")
    else:
        sys.stdout.write(rendered + "\n")


def main() -> int:
    try:
        require_uv_project_env()
    except RuntimeError as exc:
        sys.stderr.write(f"Environment error: {exc}\n")
        return 2

    from pydantic import ValidationError

    from .checker import check_domains
    from .models import CheckDomainsInput

    parser = argparse.ArgumentParser(description="DomainScout domain checker")
    parser.add_argument("--input", help="Path to JSON input payload")
    parser.add_argument("--output", help="Path to JSON output payload")
    args = parser.parse_args()

    try:
        raw = _read_payload(args.input)
        payload = CheckDomainsInput.model_validate(raw)
    except (json.JSONDecodeError, OSError, ValidationError) as exc:
        sys.stderr.write(f"Input validation error: {exc}\n")
        return 2

    try:
        output = asyncio.run(check_domains(payload))
        _write_output(output.model_dump(mode="json"), args.output)
    except Exception as exc:  # pragma: no cover - defensive fallback for CLI consumers
        error_payload = {"error": str(exc)}
        _write_output(error_payload, args.output)
        return 3

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
