from __future__ import annotations

from collections import Counter
from math import ceil

from domainscout_check.models import CheckDomainsOutput, DomainResult
from domainscout.harness import (
    DEFAULT_CANDIDATE_COUNT,
    DEFAULT_MS2_RANKED_RATIO,
    HarnessOptions,
    UserInput,
    run_workflow,
)


class FakeBridge:
    def generate_slds(self, ms1_request_json: dict) -> dict:
        assert ms1_request_json["theme"]
        assert ms1_request_json["candidate_count"] == DEFAULT_CANDIDATE_COUNT
        return {"slds": ["pixelforge", "tinyarcade"], "notes": "generated"}

    def pick_best(self, ms2_request_json: dict) -> dict:
        assert ms2_request_json["results"]
        assert ms2_request_json["ranked_target_count"] == max(
            1, ceil(DEFAULT_CANDIDATE_COUNT * DEFAULT_MS2_RANKED_RATIO)
        )
        return {
            "best_domain": ms2_request_json["suggested_best"],
            "rationale": "best by preference",
            "ranked": [
                {
                    "domain": ms2_request_json["suggested_best"],
                    "status": "available",
                    "confidence": 0.8,
                    "tld_preference_rank": 1,
                }
            ],
        }


def test_workflow_happy_path() -> None:
    async def fake_check_domains(_payload):
        return CheckDomainsOutput(
            checked_at="2026-02-16T14:02:11Z",
            results=[
                DomainResult(
                    domain="pixelforge.de",
                    status="available",
                    confidence=0.8,
                    method="rdap",
                )
            ],
            suggested_best="pixelforge.de",
        )

    import domainscout.harness as harness_module

    harness_module.check_domains = fake_check_domains

    result = run_workflow(
        user_input=UserInput(theme="minimalist indie game portfolio", tlds=[".com", ".de", ".io"]),
        model_bridge=FakeBridge(),
        options=HarnessOptions(),
    )

    assert result.ms2_output["best_domain"]
    assert result.ts1_output["results"]


def test_workflow_candidate_count_trims_ms1_output() -> None:
    class OverflowBridge:
        def generate_slds(self, ms1_request_json: dict) -> dict:
            assert ms1_request_json["candidate_count"] == 5
            return {"slds": [f"brand{i}" for i in range(7)]}

        def pick_best(self, _ms2_request_json: dict) -> dict:
            return {"best_domain": None, "rationale": "ok", "ranked": []}

    async def fake_check_domains(payload):
        assert payload.slds == [f"brand{i}" for i in range(5)]
        return CheckDomainsOutput(
            checked_at="2026-02-16T14:02:11Z",
            results=[
                DomainResult(
                    domain="brand0.com",
                    status="available",
                    confidence=0.8,
                    method="rdap",
                )
            ],
            suggested_best="brand0.com",
        )

    import domainscout.harness as harness_module

    harness_module.check_domains = fake_check_domains

    result = run_workflow(
        user_input=UserInput(
            theme="agentic ai coding",
            tlds=[".com", ".de", ".io"],
            candidate_count=5,
        ),
        model_bridge=OverflowBridge(),
        options=HarnessOptions(),
    )

    assert result.ms1_output["slds"] == [f"brand{i}" for i in range(5)]
    assert result.ts1_input["slds"] == [f"brand{i}" for i in range(5)]


def test_workflow_enforces_ranked_target_with_autofill() -> None:
    class SparseRankBridge:
        def generate_slds(self, ms1_request_json: dict) -> dict:
            assert ms1_request_json["candidate_count"] == 50
            return {"slds": [f"brand{i}" for i in range(50)]}

        def pick_best(self, ms2_request_json: dict) -> dict:
            assert ms2_request_json["ranked_target_count"] == 5
            return {
                "best_domain": "brand0.com",
                "rationale": "initial sparse ranking",
                "ranked": [
                    {
                        "domain": "brand0.com",
                        "status": "available",
                        "confidence": 0.8,
                    }
                ],
            }

    async def fake_check_domains(_payload):
        return CheckDomainsOutput(
            checked_at="2026-02-16T14:02:11Z",
            results=[
                DomainResult(domain="brand0.com", status="available", confidence=0.8, method="rdap"),
                DomainResult(domain="brand1.com", status="available", confidence=0.8, method="rdap"),
                DomainResult(domain="brand2.com", status="available", confidence=0.8, method="rdap"),
                DomainResult(domain="brand3.de", status="available", confidence=0.8, method="rdap"),
                DomainResult(domain="brand4.io", status="unknown", confidence=0.3, method="dns"),
                DomainResult(domain="brand5.com", status="taken", confidence=0.98, method="rdap"),
            ],
            suggested_best="brand0.com",
        )

    import domainscout.harness as harness_module

    harness_module.check_domains = fake_check_domains

    result = run_workflow(
        user_input=UserInput(
            theme="agentic ai coding",
            tlds=[".com", ".de", ".io"],
            candidate_count=50,
        ),
        model_bridge=SparseRankBridge(),
        options=HarnessOptions(),
    )

    assert len(result.ms2_output["ranked"]) == 5
    assert result.ms2_output["ranked"][0]["domain"] == "brand0.com"
    assert any(item.get("summary") == "autofilled_from_ts1_fallback" for item in result.ms2_output["ranked"][1:])


def test_workflow_trims_ranked_to_target() -> None:
    class VerboseRankBridge:
        def generate_slds(self, _ms1_request_json: dict) -> dict:
            return {"slds": [f"brand{i}" for i in range(50)]}

        def pick_best(self, ms2_request_json: dict) -> dict:
            assert ms2_request_json["ranked_target_count"] == 5
            return {
                "best_domain": "brand0.com",
                "rationale": "too many entries",
                "ranked": [
                    {"domain": "brand0.com", "status": "available", "confidence": 0.8},
                    {"domain": "brand1.com", "status": "available", "confidence": 0.8},
                    {"domain": "brand2.com", "status": "available", "confidence": 0.8},
                    {"domain": "brand3.com", "status": "available", "confidence": 0.8},
                    {"domain": "brand4.com", "status": "available", "confidence": 0.8},
                    {"domain": "brand5.com", "status": "available", "confidence": 0.8},
                    {"domain": "brand6.com", "status": "available", "confidence": 0.8},
                ],
            }

    async def fake_check_domains(_payload):
        return CheckDomainsOutput(
            checked_at="2026-02-16T14:02:11Z",
            results=[
                DomainResult(domain=f"brand{i}.com", status="available", confidence=0.8, method="rdap")
                for i in range(7)
            ],
            suggested_best="brand0.com",
        )

    import domainscout.harness as harness_module

    harness_module.check_domains = fake_check_domains

    result = run_workflow(
        user_input=UserInput(
            theme="agentic ai coding",
            tlds=[".com", ".de", ".io"],
            candidate_count=50,
        ),
        model_bridge=VerboseRankBridge(),
        options=HarnessOptions(),
    )

    assert len(result.ms2_output["ranked"]) == 5
    assert [row["domain"] for row in result.ms2_output["ranked"]] == [
        "brand0.com",
        "brand1.com",
        "brand2.com",
        "brand3.com",
        "brand4.com",
    ]


def test_workflow_pads_ms1_underflow_to_candidate_count() -> None:
    class UnderflowBridge:
        def generate_slds(self, ms1_request_json: dict) -> dict:
            assert ms1_request_json["candidate_count"] == 10
            return {"slds": ["brand0", "brand1", "brand2"], "notes": "underflow"}

        def pick_best(self, _ms2_request_json: dict) -> dict:
            return {"best_domain": None, "rationale": "ok", "ranked": []}

    async def fake_check_domains(payload):
        assert len(payload.slds) == 10
        assert payload.slds[:3] == ["brand0", "brand1", "brand2"]
        return CheckDomainsOutput(
            checked_at="2026-02-16T14:02:11Z",
            results=[
                DomainResult(domain=f"{sld}.com", status="taken", confidence=0.98, method="rdap")
                for sld in payload.slds
            ],
            suggested_best=None,
        )

    import domainscout.harness as harness_module

    harness_module.check_domains = fake_check_domains

    result = run_workflow(
        user_input=UserInput(
            theme="agentic ai coding",
            tlds=[".com", ".de", ".io"],
            candidate_count=10,
        ),
        model_bridge=UnderflowBridge(),
        options=HarnessOptions(),
    )

    assert len(result.ms1_output["slds"]) == 10
    assert "padded_to_candidate_count=10" in result.ms1_output["notes"]
    assert len(result.ts1_input["slds"]) == 10


def test_workflow_returns_50_ranked_for_candidate_count_500() -> None:
    class SparseRankBridge:
        def generate_slds(self, _ms1_request_json: dict) -> dict:
            return {"slds": [f"brand{i}" for i in range(500)]}

        def pick_best(self, ms2_request_json: dict) -> dict:
            assert ms2_request_json["ranked_target_count"] == 50
            return {
                "best_domain": "brand0.com",
                "rationale": "sparse",
                "ranked": [{"domain": "brand0.com", "status": "available", "confidence": 0.8}],
            }

    async def fake_check_domains(_payload):
        return CheckDomainsOutput(
            checked_at="2026-02-16T14:02:11Z",
            results=[
                DomainResult(domain=f"brand{i}.com", status="available", confidence=0.8, method="rdap")
                for i in range(500)
            ],
            suggested_best="brand0.com",
        )

    import domainscout.harness as harness_module

    harness_module.check_domains = fake_check_domains

    result = run_workflow(
        user_input=UserInput(
            theme="agentic ai coding",
            tlds=[".com", ".de", ".io"],
            candidate_count=500,
        ),
        model_bridge=SparseRankBridge(),
        options=HarnessOptions(),
    )

    assert len(result.ms2_output["ranked"]) == 50


def test_workflow_balances_ranked_output_across_requested_tlds() -> None:
    class SkewedBridge:
        def generate_slds(self, _ms1_request_json: dict) -> dict:
            return {"slds": [f"brand{i}" for i in range(60)]}

        def pick_best(self, ms2_request_json: dict) -> dict:
            assert ms2_request_json["ranked_target_count"] == 6
            return {
                "best_domain": "brand0.com",
                "rationale": "skewed model output",
                "ranked": [
                    {"domain": "brand0.com", "status": "available", "confidence": 0.8},
                    {"domain": "brand1.com", "status": "available", "confidence": 0.8},
                    {"domain": "brand2.com", "status": "available", "confidence": 0.8},
                    {"domain": "brand3.com", "status": "available", "confidence": 0.8},
                    {"domain": "brand4.com", "status": "available", "confidence": 0.8},
                    {"domain": "brand5.com", "status": "available", "confidence": 0.8},
                ],
            }

    async def fake_check_domains(_payload):
        return CheckDomainsOutput(
            checked_at="2026-02-16T14:02:11Z",
            results=[
                DomainResult(domain="brand0.com", status="available", confidence=0.8, method="rdap"),
                DomainResult(domain="brand1.com", status="available", confidence=0.8, method="rdap"),
                DomainResult(domain="brand2.com", status="available", confidence=0.8, method="rdap"),
                DomainResult(domain="brand3.com", status="available", confidence=0.8, method="rdap"),
                DomainResult(domain="brand4.ai", status="available", confidence=0.8, method="rdap"),
                DomainResult(domain="brand5.ai", status="available", confidence=0.8, method="rdap"),
                DomainResult(domain="brand6.ai", status="available", confidence=0.8, method="rdap"),
                DomainResult(domain="brand7.ai", status="available", confidence=0.8, method="rdap"),
                DomainResult(domain="brand8.io", status="available", confidence=0.8, method="rdap"),
                DomainResult(domain="brand9.io", status="available", confidence=0.8, method="rdap"),
                DomainResult(domain="brand10.io", status="available", confidence=0.8, method="rdap"),
                DomainResult(domain="brand11.io", status="available", confidence=0.8, method="rdap"),
            ],
            suggested_best="brand0.com",
        )

    import domainscout.harness as harness_module

    harness_module.check_domains = fake_check_domains

    result = run_workflow(
        user_input=UserInput(
            theme="agentic ai coding",
            tlds=[".com", ".ai", ".io"],
            candidate_count=60,
        ),
        model_bridge=SkewedBridge(),
        options=HarnessOptions(),
    )

    ranked = result.ms2_output["ranked"]
    assert len(ranked) == 6
    tld_counts = Counter(domain["domain"].rsplit(".", 1)[1] for domain in ranked)
    assert tld_counts["com"] == 2
    assert tld_counts["ai"] == 2
    assert tld_counts["io"] == 2
