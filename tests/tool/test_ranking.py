from __future__ import annotations

from domainscout_check.checker import choose_suggested_best
from domainscout_check.models import DomainResult


def test_choose_suggested_best_prefers_available_by_tld_order() -> None:
    results = [
        DomainResult(domain="alpha.io", status="available", confidence=0.8, method="rdap"),
        DomainResult(domain="alpha.com", status="taken", confidence=0.98, method="rdap"),
        DomainResult(domain="alpha.de", status="available", confidence=0.8, method="rdap"),
    ]
    assert choose_suggested_best(results, [".com", ".de", ".io"], True) == "alpha.de"


def test_choose_suggested_best_can_fallback_to_unknown() -> None:
    results = [
        DomainResult(domain="alpha.com", status="unknown", confidence=0.2, method="rdap", error="timeout"),
        DomainResult(domain="alpha.de", status="taken", confidence=0.98, method="rdap"),
    ]
    assert choose_suggested_best(results, [".com", ".de", ".io"], True) == "alpha.com"


def test_choose_suggested_best_returns_none_without_available_or_unknown() -> None:
    results = [
        DomainResult(domain="alpha.com", status="taken", confidence=0.98, method="rdap"),
        DomainResult(domain="alpha.de", status="invalid", confidence=1.0, method="rdap", error="bad"),
    ]
    assert choose_suggested_best(results, [".com", ".de", ".io"], True) is None
