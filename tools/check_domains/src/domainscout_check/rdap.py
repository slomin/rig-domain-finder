from __future__ import annotations

import json
import time
from pathlib import Path

import httpx


IANA_DNS_BOOTSTRAP_URL = "https://data.iana.org/rdap/dns.json"


def map_rdap_http_status(status_code: int) -> tuple[str, float]:
    if status_code == 200:
        return ("taken", 0.98)
    if status_code == 404:
        return ("available", 0.80)
    if status_code == 400:
        return ("invalid", 1.0)
    return ("unknown", 0.25)


def is_retryable_http_status(status_code: int) -> bool:
    return status_code in {429, 500, 502, 503, 504}


def _parse_bootstrap_tld_to_rdap(data: dict) -> dict[str, str]:
    services = data.get("services", [])
    mapping: dict[str, str] = {}
    for entry in services:
        if not isinstance(entry, list) or len(entry) < 2:
            continue
        tlds, urls = entry[0], entry[1]
        if not tlds or not urls:
            continue
        rdap_url = urls[0].rstrip("/")
        for tld in tlds:
            if isinstance(tld, str):
                mapping[tld.lower()] = rdap_url
    return mapping


async def load_bootstrap_map(
    cache_path: Path,
    ttl_seconds: int,
    client: httpx.AsyncClient | None = None,
    url: str = IANA_DNS_BOOTSTRAP_URL,
) -> dict[str, str]:
    now = time.time()
    if cache_path.exists() and (now - cache_path.stat().st_mtime) < ttl_seconds:
        cached = json.loads(cache_path.read_text())
        return _parse_bootstrap_tld_to_rdap(cached)

    owns_client = client is None
    if client is None:
        client = httpx.AsyncClient(timeout=10.0)

    try:
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = cache_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data))
        tmp.replace(cache_path)
        return _parse_bootstrap_tld_to_rdap(data)
    finally:
        if owns_client:
            await client.aclose()


async def query_rdap_domain(
    client: httpx.AsyncClient,
    rdap_base: str,
    domain: str,
) -> tuple[str, float, int | None, str | None]:
    url = f"{rdap_base.rstrip('/')}/domain/{domain}"
    try:
        response = await client.get(url)
        status, confidence = map_rdap_http_status(response.status_code)
        return status, confidence, response.status_code, None
    except httpx.TimeoutException:
        return "unknown", 0.25, None, "timeout"
    except httpx.HTTPError as exc:
        return "unknown", 0.25, None, str(exc)
