from __future__ import annotations

from domainscout_check.dns_probe import map_dns_probe_to_status
from domainscout_check.models import DNSProbeEvidence
from domainscout_check.rdap import map_rdap_http_status


def test_rdap_status_mapping() -> None:
    assert map_rdap_http_status(200) == ("taken", 0.98)
    assert map_rdap_http_status(404) == ("available", 0.80)
    assert map_rdap_http_status(400) == ("invalid", 1.0)
    assert map_rdap_http_status(503) == ("unknown", 0.25)


def test_dns_probe_mapping() -> None:
    assert map_dns_probe_to_status(DNSProbeEvidence(dns_nxdomain=True)) == ("available", 0.60)
    assert map_dns_probe_to_status(DNSProbeEvidence(dns_ns=True)) == ("taken", 0.70)
    assert map_dns_probe_to_status(DNSProbeEvidence(dns_soa=True)) == ("taken", 0.70)
    assert map_dns_probe_to_status(DNSProbeEvidence()) == ("unknown", 0.30)
