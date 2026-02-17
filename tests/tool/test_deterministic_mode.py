from __future__ import annotations

import pytest

from domainscout_check.checker import check_domains
from domainscout_check.models import CheckDomainsInput


@pytest.mark.asyncio
async def test_deterministic_mode_is_stable_and_skips_network(monkeypatch) -> None:
    async def _should_not_run(*_args, **_kwargs):
        raise AssertionError("network path should not run in deterministic mode")

    monkeypatch.setattr("domainscout_check.checker.load_bootstrap_map", _should_not_run)
    monkeypatch.setattr("domainscout_check.checker._rdap_with_retry", _should_not_run)
    monkeypatch.setattr("domainscout_check.checker.probe_domain_dns", _should_not_run)

    payload = CheckDomainsInput.model_validate(
        {
            "tlds": [".com", ".ai", ".io"],
            "slds": ["agentforge", "codepilot", "devmesh"],
            "options": {
                "deterministic_mode": True,
                "deterministic_seed": 17,
                "treat_unknown_as_available": True,
            },
        }
    )

    output_a = await check_domains(payload)
    output_b = await check_domains(payload)

    assert output_a.checked_at == "1970-01-01T00:00:00Z"
    assert output_b.checked_at == "1970-01-01T00:00:00Z"
    assert output_a.model_dump(mode="json") == output_b.model_dump(mode="json")
    assert len(output_a.results) == 9
    assert all(result.method == "rdap" for result in output_a.results)


@pytest.mark.asyncio
async def test_deterministic_mode_changes_with_seed() -> None:
    payload_seed_1 = CheckDomainsInput.model_validate(
        {
            "tlds": [".com", ".ai", ".io"],
            "slds": ["agentforge", "codepilot"],
            "options": {"deterministic_mode": True, "deterministic_seed": 1},
        }
    )
    payload_seed_2 = CheckDomainsInput.model_validate(
        {
            "tlds": [".com", ".ai", ".io"],
            "slds": ["agentforge", "codepilot"],
            "options": {"deterministic_mode": True, "deterministic_seed": 2},
        }
    )

    output_1 = await check_domains(payload_seed_1)
    output_2 = await check_domains(payload_seed_2)

    statuses_1 = [(item.domain, item.status, item.rdap_http) for item in output_1.results]
    statuses_2 = [(item.domain, item.status, item.rdap_http) for item in output_2.results]
    assert statuses_1 != statuses_2
