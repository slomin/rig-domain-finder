from __future__ import annotations

import asyncio
import hashlib
import random
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

import httpx

from .dns_probe import map_dns_probe_to_status, probe_domain_dns
from .logging import append_run_log
from .models import CheckDomainsInput, CheckDomainsOutput, DomainResult
from .rdap import is_retryable_http_status, load_bootstrap_map, query_rdap_domain


SLD_RE = re.compile(r"^(?!-)[a-z0-9-]{2,63}(?<!-)$")
TLD_RE = re.compile(r"^\.[a-z0-9-]{2,63}$")


def _extract_tld(domain: str) -> str:
    parts = domain.rsplit(".", maxsplit=1)
    if len(parts) != 2:
        return ""
    return f".{parts[1].lower()}"


def choose_suggested_best(results: list[DomainResult], tlds: list[str], allow_unknown: bool) -> str | None:
    tld_order = {t.lower(): idx for idx, t in enumerate(tlds)}

    def sort_key(result: DomainResult) -> tuple[int, float, int, str]:
        tld_idx = tld_order.get(_extract_tld(result.domain), len(tlds) + 1)
        return (tld_idx, -result.confidence, len(result.domain), result.domain)

    available = sorted((r for r in results if r.status == "available"), key=sort_key)
    if available:
        return available[0].domain

    if allow_unknown:
        unknown = sorted((r for r in results if r.status == "unknown"), key=sort_key)
        if unknown:
            return unknown[0].domain

    return None


async def _rdap_with_retry(
    client: httpx.AsyncClient,
    rdap_base: str,
    domain: str,
    retries: int = 2,
) -> tuple[str, float, int | None, str | None]:
    for attempt in range(retries + 1):
        status, confidence, http_code, error = await query_rdap_domain(client, rdap_base, domain)
        retryable = (http_code is not None and is_retryable_http_status(http_code)) or (error is not None)
        if retryable and attempt < retries:
            await asyncio.sleep((0.05 * (2**attempt)) + random.uniform(0.0, 0.03))
            continue
        return status, confidence, http_code, error

    return "unknown", 0.25, None, "unreachable"


def _validate_tlds(tlds: list[str]) -> None:
    for tld in tlds:
        if not TLD_RE.match(tld):
            raise ValueError(f"Invalid TLD: {tld}")


def _chunk_slds(slds: list[str], batch_size: int) -> Iterator[list[str]]:
    for idx in range(0, len(slds), batch_size):
        yield slds[idx : idx + batch_size]


def _deterministic_result_for_domain(domain: str, seed: int) -> DomainResult:
    digest = hashlib.sha256(f"{seed}:{domain}".encode("utf-8")).digest()
    bucket = digest[0]
    if bucket < 150:
        status = "taken"
        confidence = 0.98
        rdap_http = 200
        error = None
    elif bucket < 235:
        status = "available"
        confidence = 0.80
        rdap_http = 404
        error = None
    else:
        status = "unknown"
        confidence = 0.25
        rdap_http = 503
        error = "deterministic_unknown"

    return DomainResult(
        domain=domain,
        status=status,
        confidence=confidence,
        method="rdap",
        rdap_server="deterministic://offline",
        rdap_http=rdap_http,
        error=error,
    )


async def _check_one_domain(
    domain: str,
    tld: str,
    rdap_base_map: dict[str, str],
    payload: CheckDomainsInput,
    client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
) -> DomainResult:
    async with semaphore:
        options = payload.options
        rdap_base = rdap_base_map.get(tld.lstrip("."))
        if not rdap_base and options.rdap_fallback_base:
            rdap_base = options.rdap_fallback_base.rstrip("/")

        rdap_status = "unknown"
        rdap_confidence = 0.25
        rdap_http: int | None = None
        rdap_error: str | None = None
        used_rdap = False

        if options.prefer_rdap and rdap_base:
            used_rdap = True
            rdap_status, rdap_confidence, rdap_http, rdap_error = await _rdap_with_retry(client, rdap_base, domain)
            if rdap_status in {"taken", "available", "invalid"}:
                return DomainResult(
                    domain=domain,
                    status=rdap_status,
                    confidence=rdap_confidence,
                    method="rdap",
                    rdap_server=rdap_base,
                    rdap_http=rdap_http,
                    error=rdap_error,
                )

        if options.enable_dns_fallback:
            dns_evidence = await probe_domain_dns(domain, options.timeout_ms)
            dns_status, dns_confidence = map_dns_probe_to_status(dns_evidence)
            return DomainResult(
                domain=domain,
                status=dns_status,
                confidence=dns_confidence,
                method="rdap+dns" if used_rdap else "dns",
                rdap_server=rdap_base,
                rdap_http=rdap_http,
                dns_nxdomain=dns_evidence.dns_nxdomain,
                dns_ns=dns_evidence.dns_ns,
                dns_soa=dns_evidence.dns_soa,
                error=rdap_error,
            )

        return DomainResult(
            domain=domain,
            status=rdap_status,
            confidence=rdap_confidence,
            method="rdap" if used_rdap else "dns",
            rdap_server=rdap_base,
            rdap_http=rdap_http,
            error=rdap_error,
        )


async def check_domains(payload: CheckDomainsInput) -> CheckDomainsOutput:
    normalized_tlds = [t.lower() for t in payload.tlds]
    normalized_slds = [s.lower() for s in payload.slds]
    _validate_tlds(normalized_tlds)

    timeout_seconds = payload.options.timeout_ms / 1000
    timeout = httpx.Timeout(timeout_seconds, connect=timeout_seconds, read=timeout_seconds, write=timeout_seconds, pool=timeout_seconds)
    limits = httpx.Limits(
        max_connections=payload.options.max_concurrency,
        max_keepalive_connections=payload.options.max_concurrency,
    )
    semaphore = asyncio.Semaphore(payload.options.max_concurrency)

    cache_path = Path(payload.options.bootstrap_cache_path)

    immediate_results: list[DomainResult] = []
    valid_slds: list[str] = []
    for sld in normalized_slds:
        if not SLD_RE.match(sld):
            for tld in normalized_tlds:
                immediate_results.append(
                    DomainResult(
                        domain=f"{sld}{tld}",
                        status="invalid",
                        confidence=1.0,
                        method="rdap",
                        error="invalid_sld",
                    )
                )
            continue
        valid_slds.append(sld)

    results = list(immediate_results)
    if valid_slds and payload.options.deterministic_mode:
        for sld in valid_slds:
            for tld in normalized_tlds:
                domain = f"{sld}{tld}"
                results.append(_deterministic_result_for_domain(domain, payload.options.deterministic_seed))

        results_sorted = sorted(results, key=lambda r: (_extract_tld(r.domain), r.domain))
        suggested_best = choose_suggested_best(
            results=results_sorted,
            tlds=normalized_tlds,
            allow_unknown=payload.options.treat_unknown_as_available,
        )
        return CheckDomainsOutput(
            checked_at="1970-01-01T00:00:00Z",
            results=results_sorted,
            suggested_best=suggested_best,
        )

    if valid_slds:
        async with httpx.AsyncClient(timeout=timeout, limits=limits) as client:
            rdap_base_map = await load_bootstrap_map(
                cache_path=cache_path,
                ttl_seconds=payload.options.bootstrap_ttl_seconds,
                client=client,
            )

            for sld_batch in _chunk_slds(valid_slds, payload.options.batch_size):
                tasks: list[asyncio.Task[DomainResult]] = []
                for sld in sld_batch:
                    for tld in normalized_tlds:
                        domain = f"{sld}{tld}"
                        tasks.append(
                            asyncio.create_task(
                                _check_one_domain(
                                    domain=domain,
                                    tld=tld,
                                    rdap_base_map=rdap_base_map,
                                    payload=payload,
                                    client=client,
                                    semaphore=semaphore,
                                )
                            )
                        )
                results.extend(await asyncio.gather(*tasks))

    results_sorted = sorted(results, key=lambda r: (_extract_tld(r.domain), r.domain))
    suggested_best = choose_suggested_best(
        results=results_sorted,
        tlds=normalized_tlds,
        allow_unknown=payload.options.treat_unknown_as_available,
    )

    output = CheckDomainsOutput(
        checked_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        results=results_sorted,
        suggested_best=suggested_best,
    )

    append_run_log(cache_path.parent, payload, output)
    return output
