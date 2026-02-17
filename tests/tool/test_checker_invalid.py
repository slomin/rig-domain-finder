from __future__ import annotations

import pytest

from domainscout_check.checker import check_domains
from domainscout_check.models import CheckDomainsInput


@pytest.mark.asyncio
async def test_invalid_sld_yields_invalid_results_without_network(monkeypatch) -> None:
    async def _should_not_run(*_args, **_kwargs):
        raise AssertionError("bootstrap fetch should not run when all SLDs are invalid")

    monkeypatch.setattr("domainscout_check.checker.load_bootstrap_map", _should_not_run)

    payload = CheckDomainsInput.model_validate(
        {
            "tlds": [".com", ".de", ".io"],
            "slds": ["bad.name"],
            "options": {"enable_dns_fallback": False}
        }
    )

    output = await check_domains(payload)
    assert len(output.results) == 3
    assert all(result.status == "invalid" for result in output.results)
