from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .models import CheckDomainsInput, CheckDomainsOutput


def append_run_log(cache_dir: Path, payload: CheckDomainsInput, output: CheckDomainsOutput) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    log_path = cache_dir / "results.jsonl"

    summary = {
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "tool_version": "0.1.0",
        "options": payload.options.model_dump(),
        "counts": {
            "available": sum(1 for r in output.results if r.status == "available"),
            "taken": sum(1 for r in output.results if r.status == "taken"),
            "unknown": sum(1 for r in output.results if r.status == "unknown"),
            "invalid": sum(1 for r in output.results if r.status == "invalid"),
        },
        "suggested_best": output.suggested_best,
    }
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(summary) + "\n")
