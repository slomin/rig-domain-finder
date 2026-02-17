from __future__ import annotations

import argparse
import json
import os
import sys
from math import ceil
from pathlib import Path

from .env_guard import require_uv_project_env


def _supports_color() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    return sys.stdout.isatty()


def _ansi(text: str, code: str, *, enabled: bool) -> str:
    if not enabled:
        return text
    return f"\033[{code}m{text}\033[0m"


def _status_label(status: str, *, color: bool) -> str:
    normalized = status.lower()
    if normalized == "available":
        return _ansi("AVAILABLE", "1;32", enabled=color)
    if normalized == "taken":
        return _ansi("TAKEN", "1;31", enabled=color)
    if normalized == "unknown":
        return _ansi("UNKNOWN", "1;33", enabled=color)
    return _ansi(normalized.upper(), "1;90", enabled=color)


def _render_user_report(result: dict, theme: str, tlds: list[str]) -> str:
    color = _supports_color()
    ms2_output = result["ms2_output"]
    ts1_output = result["ts1_output"]
    status_counts: dict[str, int] = {"available": 0, "taken": 0, "unknown": 0, "invalid": 0}
    for row in ts1_output["results"]:
        status = str(row.get("status", "unknown")).lower()
        status_counts[status] = status_counts.get(status, 0) + 1

    checked_candidate_count = len(result["ts1_input"]["slds"])
    requested_display_count = max(1, ceil(checked_candidate_count * 0.10))
    ranked_rows = ms2_output.get("ranked", [])[:requested_display_count]

    lines: list[str] = []
    lines.append(_ansi("DomainScout Results", "1;36", enabled=color))
    lines.append(f"Theme: {theme}")
    lines.append(f"TLD preference: {', '.join(tlds)}")
    lines.append(f"Candidates checked: {len(ts1_output['results'])}")
    lines.append(
        "Status counts: "
        + ", ".join(
            [
                f"{_status_label('available', color=color)}={status_counts.get('available', 0)}",
                f"{_status_label('taken', color=color)}={status_counts.get('taken', 0)}",
                f"{_status_label('unknown', color=color)}={status_counts.get('unknown', 0)}",
                f"{_status_label('invalid', color=color)}={status_counts.get('invalid', 0)}",
            ]
        )
    )

    best_domain = ms2_output.get("best_domain")
    if best_domain:
        lines.append(f"Best pick: {_ansi(best_domain, '1;32', enabled=color)}")
    else:
        lines.append(f"Best pick: {_ansi('none', '1;33', enabled=color)}")

    lines.append("")
    lines.append(
        f"{_ansi('Top ranked domains', '1;34', enabled=color)} "
        f"(showing {len(ranked_rows)} of target {requested_display_count})"
    )

    for idx, row in enumerate(ranked_rows, start=1):
        domain = row["domain"]
        status = _status_label(row.get("status", "unknown"), color=color)
        confidence = float(row.get("confidence", 0))
        lines.append(f"{idx:02d}. {domain:<35} {status:<18} confidence={confidence:.2f}")

    rationale = ms2_output.get("rationale")
    if rationale:
        lines.append("")
        lines.append(f"{_ansi('Rationale', '1;35', enabled=color)}: {rationale}")

    next_actions = ms2_output.get("next_actions", [])
    if next_actions:
        lines.append("")
        lines.append(_ansi("Next actions", "1;33", enabled=color))
        for i, action in enumerate(next_actions, start=1):
            lines.append(f"{i}. {action}")

    return "\n".join(lines) + "\n"


def main() -> int:
    try:
        require_uv_project_env()
    except RuntimeError as exc:
        raise SystemExit(f"Environment error: {exc}")

    from .harness import DEFAULT_CANDIDATE_COUNT, HarnessOptions, ModelBridge, UserInput, run_workflow

    class FileBridge(ModelBridge):
        """Simple bridge for host-driven model steps using JSON files."""

        def __init__(self, ms1_path: Path, ms2_path: Path) -> None:
            self.ms1_path = ms1_path
            self.ms2_path = ms2_path

        def generate_slds(self, ms1_request_json: dict) -> dict:
            _ = ms1_request_json
            return json.loads(self.ms1_path.read_text())

        def pick_best(self, ms2_request_json: dict) -> dict:
            _ = ms2_request_json
            return json.loads(self.ms2_path.read_text())

    parser = argparse.ArgumentParser(description="Run DomainScout workflow with host-provided MS outputs")
    parser.add_argument("--theme", required=True)
    parser.add_argument("--tlds", nargs="+", required=True)
    parser.add_argument(
        "--candidate-count",
        "--count",
        type=int,
        default=DEFAULT_CANDIDATE_COUNT,
        help="Candidate count (default: 10%% of max supported, currently %(default)s)",
    )
    parser.add_argument("--ms1", required=True, help="Path to MS1 JSON output")
    parser.add_argument("--ms2", required=True, help="Path to MS2 JSON output")
    parser.add_argument("--out", required=True, help="Path to write workflow result")
    args = parser.parse_args()
    if not (1 <= len(args.tlds) <= 3):
        parser.error("--tlds expects between 1 and 3 values in preference order")

    bridge = FileBridge(ms1_path=Path(args.ms1), ms2_path=Path(args.ms2))
    result = run_workflow(
        user_input=UserInput(
            theme=args.theme,
            tlds=[t.lower() for t in args.tlds],
            candidate_count=args.candidate_count,
        ),
        model_bridge=bridge,
        options=HarnessOptions(),
    )

    Path(args.out).write_text(
        json.dumps(
            {
                "ms1_output": result.ms1_output,
                "ts1_input": result.ts1_input,
                "ts1_output": result.ts1_output,
                "ms2_output": result.ms2_output,
            },
            indent=2,
        )
        + "\n"
    )
    report_payload = {
        "ms1_output": result.ms1_output,
        "ts1_input": result.ts1_input,
        "ts1_output": result.ts1_output,
        "ms2_output": result.ms2_output,
    }
    sys.stdout.write(
        _render_user_report(
            report_payload,
            theme=args.theme,
            tlds=[t.lower() for t in args.tlds],
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
