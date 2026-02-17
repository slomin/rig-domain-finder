from __future__ import annotations

import asyncio

import pytest

from domainscout_check.checker import check_domains
from domainscout_check.models import CheckDomainsInput, DomainResult


@pytest.mark.asyncio
async def test_check_domains_batches_large_inputs_internally(monkeypatch) -> None:
    async def fake_bootstrap(*_args, **_kwargs):
        return {"com": "https://rdap.example", "net": "https://rdap.example", "io": "https://rdap.example"}

    async def fake_check_one_domain(domain, tld, rdap_base_map, payload, client, semaphore):
        _ = (tld, rdap_base_map, payload, client, semaphore)
        return DomainResult(domain=domain, status="taken", confidence=0.98, method="rdap")

    async def tracking_gather(*tasks):
        batch_sizes.append(len(tasks))
        return await real_gather(*tasks)

    def fake_append_log(*_args, **_kwargs):
        return None

    real_gather = asyncio.gather
    batch_sizes: list[int] = []

    monkeypatch.setattr("domainscout_check.checker.load_bootstrap_map", fake_bootstrap)
    monkeypatch.setattr("domainscout_check.checker._check_one_domain", fake_check_one_domain)
    monkeypatch.setattr("domainscout_check.checker.append_run_log", fake_append_log)
    monkeypatch.setattr("domainscout_check.checker.asyncio.gather", tracking_gather)

    payload = CheckDomainsInput.model_validate(
        {
            "tlds": [".com", ".net", ".io"],
            "slds": [f"brand{i}" for i in range(95)],
            "options": {"batch_size": 40},
        }
    )

    output = await check_domains(payload)

    assert len(output.results) == 285
    assert batch_sizes == [120, 120, 45]
