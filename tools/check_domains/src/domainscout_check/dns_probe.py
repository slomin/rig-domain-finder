from __future__ import annotations

import asyncio

import dns.exception
import dns.resolver

from .models import DNSProbeEvidence


def map_dns_probe_to_status(evidence: DNSProbeEvidence) -> tuple[str, float]:
    if evidence.dns_nxdomain:
        return "available", 0.60
    if evidence.dns_ns or evidence.dns_soa:
        return "taken", 0.70
    return "unknown", 0.30


def _probe_domain_dns_sync(domain: str, timeout_s: float) -> DNSProbeEvidence:
    resolver = dns.resolver.Resolver(configure=True)
    resolver.lifetime = timeout_s
    resolver.timeout = timeout_s

    try:
        ns_records = resolver.resolve(domain, "NS")
        if ns_records:
            return DNSProbeEvidence(dns_ns=True)
    except dns.resolver.NXDOMAIN:
        return DNSProbeEvidence(dns_nxdomain=True)
    except (dns.resolver.NoAnswer, dns.resolver.NoNameservers, dns.exception.Timeout):
        pass

    try:
        soa_records = resolver.resolve(domain, "SOA")
        if soa_records:
            return DNSProbeEvidence(dns_soa=True)
    except dns.resolver.NXDOMAIN:
        return DNSProbeEvidence(dns_nxdomain=True)
    except (dns.resolver.NoAnswer, dns.resolver.NoNameservers, dns.exception.Timeout):
        pass

    return DNSProbeEvidence()


async def probe_domain_dns(domain: str, timeout_ms: int) -> DNSProbeEvidence:
    timeout_s = timeout_ms / 1000
    return await asyncio.to_thread(_probe_domain_dns_sync, domain, timeout_s)
