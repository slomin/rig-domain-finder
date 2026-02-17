from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace


def test_run_cli_prints_human_report_and_displays_ten_percent(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    import domainscout.harness as harness_module
    import domainscout.run as run_module
    from domainscout_check.models import CheckDomainsOutput, DomainResult

    ms1_path = tmp_path / "ms1.json"
    ms2_path = tmp_path / "ms2.json"
    out_path = tmp_path / "out.json"

    ms1_payload = {"slds": [f"brand{i}" for i in range(500)]}
    ms2_payload = {"best_domain": "brand0.com", "rationale": "ok", "ranked": []}
    ms1_path.write_text(json.dumps(ms1_payload))
    ms2_path.write_text(json.dumps(ms2_payload))

    async def fake_check_domains(_payload):
        return CheckDomainsOutput(
            checked_at="2026-02-16T14:02:11Z",
            results=[
                DomainResult(domain=f"brand{i}.com", status="available", confidence=0.8, method="rdap")
                for i in range(500)
            ],
            suggested_best="brand0.com",
        )

    monkeypatch.setattr(harness_module, "check_domains", fake_check_domains)
    monkeypatch.setattr(run_module, "require_uv_project_env", lambda: None)
    monkeypatch.setattr(run_module, "_supports_color", lambda: False)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "domainscout-run",
            "--theme",
            "floating chambers",
            "--tlds",
            ".com",
            "--candidate-count",
            "500",
            "--ms1",
            str(ms1_path),
            "--ms2",
            str(ms2_path),
            "--out",
            str(out_path),
        ],
    )

    exit_code = run_module.main()
    assert exit_code == 0

    stdout = capsys.readouterr().out
    assert "DomainScout Results" in stdout
    assert "{" not in stdout
    ranked_lines = [line for line in stdout.splitlines() if line[:2].isdigit() and line[2:4] == ". "]
    assert len(ranked_lines) == 50

    out_payload = json.loads(out_path.read_text())
    assert len(out_payload["ms2_output"]["ranked"]) == 50


def test_run_cli_default_candidate_count_uses_ten_percent_of_max(
    tmp_path: Path, monkeypatch
) -> None:
    import domainscout.harness as harness_module
    import domainscout.run as run_module

    captured: dict[str, int] = {}

    def fake_run_workflow(*, user_input, model_bridge, options):
        _ = model_bridge, options
        captured["candidate_count"] = user_input.candidate_count
        return SimpleNamespace(
            ms1_output={"slds": ["brand0"]},
            ts1_input={"slds": ["brand0"]},
            ts1_output={
                "results": [
                    {
                        "domain": "brand0.com",
                        "status": "available",
                        "confidence": 0.8,
                        "method": "rdap",
                    }
                ]
            },
            ms2_output={
                "best_domain": "brand0.com",
                "rationale": "ok",
                "ranked": [
                    {"domain": "brand0.com", "status": "available", "confidence": 0.8}
                ],
            },
        )

    monkeypatch.setattr(harness_module, "run_workflow", fake_run_workflow)
    monkeypatch.setattr(run_module, "require_uv_project_env", lambda: None)
    monkeypatch.setattr(run_module, "_supports_color", lambda: False)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "domainscout-run",
            "--theme",
            "floating chambers",
            "--tlds",
            ".com",
            "--ms1",
            str(tmp_path / "unused_ms1.json"),
            "--ms2",
            str(tmp_path / "unused_ms2.json"),
            "--out",
            str(tmp_path / "out.json"),
        ],
    )

    exit_code = run_module.main()
    assert exit_code == 0
    assert captured["candidate_count"] == harness_module.DEFAULT_CANDIDATE_COUNT
