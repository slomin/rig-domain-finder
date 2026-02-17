from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from math import ceil
from typing import Protocol

from domainscout_check.checker import check_domains
from domainscout_check.models import CheckDomainsInput

from .schema_utils import validate_payload

MIN_CANDIDATE_COUNT = 1
MAX_CANDIDATE_COUNT = 5000
DEFAULT_CANDIDATE_COUNT_RATIO = 0.10
DEFAULT_CANDIDATE_COUNT = max(
    MIN_CANDIDATE_COUNT, ceil(MAX_CANDIDATE_COUNT * DEFAULT_CANDIDATE_COUNT_RATIO)
)
DEFAULT_MS2_RANKED_RATIO = DEFAULT_CANDIDATE_COUNT_RATIO
SLD_RE = re.compile(r"^(?!-)[a-z0-9-]{2,63}(?<!-)$")


@dataclass(frozen=True)
class UserInput:
    theme: str
    tlds: list[str]
    candidate_count: int = DEFAULT_CANDIDATE_COUNT


@dataclass(frozen=True)
class HarnessOptions:
    timeout_ms: int = 2500
    max_concurrency: int = 20
    batch_size: int = 200
    prefer_rdap: bool = True
    enable_dns_fallback: bool = True
    treat_unknown_as_available: bool = True
    bootstrap_cache_path: str = ".rig_cache/rdap_dns.json"
    bootstrap_ttl_seconds: int = 604800
    rdap_fallback_base: str | None = None
    deterministic_mode: bool = False
    deterministic_seed: int = 17


@dataclass(frozen=True)
class WorkflowResult:
    ms1_output: dict
    ts1_input: dict
    ts1_output: dict
    ms2_output: dict


class ModelBridge(Protocol):
    def generate_slds(self, ms1_request_json: dict) -> dict: ...

    def pick_best(self, ms2_request_json: dict) -> dict: ...


def _normalize_candidate_count(candidate_count: int) -> int:
    if candidate_count < MIN_CANDIDATE_COUNT:
        return MIN_CANDIDATE_COUNT
    if candidate_count > MAX_CANDIDATE_COUNT:
        return MAX_CANDIDATE_COUNT
    return candidate_count


def _extract_tld(domain: str) -> str:
    parts = domain.rsplit(".", maxsplit=1)
    if len(parts) != 2:
        return ""
    return f".{parts[1].lower()}"


def _append_note(ms1_output: dict, note_suffix: str) -> dict:
    normalized = dict(ms1_output)
    note_prefix = normalized.get("notes", "").strip()
    normalized["notes"] = f"{note_prefix} {note_suffix}".strip()[:2000]
    return normalized


def _theme_seed(theme: str) -> str:
    parts = re.findall(r"[a-z0-9]+", theme.lower())
    seed = "".join(parts)
    if not seed:
        return "brand"
    return seed


def _pad_slds_to_candidate_count(slds: list[str], theme: str, candidate_count: int) -> list[str]:
    if len(slds) >= candidate_count:
        return slds

    seed = _theme_seed(theme)
    padded = list(slds)
    seen = set(slds)
    idx = 1
    while len(padded) < candidate_count:
        suffix = str(idx)
        max_seed_len = max(1, 63 - len(suffix))
        candidate = f"{seed[:max_seed_len]}{suffix}"
        idx += 1
        if candidate in seen:
            continue
        if not SLD_RE.match(candidate):
            continue
        padded.append(candidate)
        seen.add(candidate)
    return padded


def _build_ms2_fallback_ranked(results: list[dict], tlds: list[str]) -> list[dict]:
    tld_order = {tld.lower(): idx for idx, tld in enumerate(tlds)}
    status_order = {"available": 0, "unknown": 1, "taken": 2, "invalid": 3}

    def sort_key(row: dict) -> tuple[int, int, float, int, str]:
        domain = row["domain"]
        tld = _extract_tld(domain)
        return (
            status_order.get(row["status"], 99),
            tld_order.get(tld, len(tlds) + 1),
            -float(row["confidence"]),
            len(domain),
            domain,
        )

    ranked: list[dict] = []
    for row in sorted(results, key=sort_key):
        tld = _extract_tld(row["domain"])
        ranked.append(
            {
                "domain": row["domain"],
                "status": row["status"],
                "confidence": row["confidence"],
                "tld_preference_rank": tld_order.get(tld, len(tlds)),
                "summary": "autofilled_from_ts1_fallback",
            }
        )
    return ranked


def _rebalance_ranked_for_tld_coverage(ranked: list[dict], tlds: list[str], max_count: int) -> list[dict]:
    if max_count <= 0:
        return []
    if not ranked:
        return []
    if not tlds:
        return ranked[:max_count]

    requested_tlds: list[str] = []
    seen_tlds: set[str] = set()
    for tld in tlds:
        normalized = tld.lower()
        if normalized in seen_tlds:
            continue
        requested_tlds.append(normalized)
        seen_tlds.add(normalized)

    buckets: dict[str, list[dict]] = {tld: [] for tld in requested_tlds}
    for row in ranked:
        bucket_tld = _extract_tld(row["domain"])
        if bucket_tld in buckets:
            buckets[bucket_tld].append(row)

    selected: list[dict] = []
    seen_domains: set[str] = set()
    progress = True
    while len(selected) < max_count and progress:
        progress = False
        for tld in requested_tlds:
            bucket = buckets[tld]
            if not bucket:
                continue
            row = bucket.pop(0)
            domain = row["domain"]
            if domain in seen_domains:
                continue
            selected.append(row)
            seen_domains.add(domain)
            progress = True
            if len(selected) >= max_count:
                break

    if len(selected) < max_count:
        for row in ranked:
            domain = row["domain"]
            if domain in seen_domains:
                continue
            selected.append(row)
            seen_domains.add(domain)
            if len(selected) >= max_count:
                break

    return selected[:max_count]


def _normalize_ranked_output(ms2_output: dict, ts1_results: list[dict], tlds: list[str], target_count: int) -> dict:
    if target_count <= 0:
        return ms2_output

    max_count = min(target_count, len(ts1_results))
    ranked = ms2_output.get("ranked", [])
    deduped_ranked: list[dict] = []
    seen_domains: set[str] = set()
    for row in ranked:
        domain = row["domain"]
        if domain in seen_domains:
            continue
        seen_domains.add(domain)
        deduped_ranked.append(row)

    for row in _build_ms2_fallback_ranked(ts1_results, tlds):
        domain = row["domain"]
        if domain in seen_domains:
            continue
        deduped_ranked.append(row)
        seen_domains.add(domain)

    normalized = dict(ms2_output)
    normalized["ranked"] = _rebalance_ranked_for_tld_coverage(deduped_ranked, tlds, max_count)
    return normalized


def run_workflow(user_input: UserInput, model_bridge: ModelBridge, options: HarnessOptions) -> WorkflowResult:
    candidate_count = _normalize_candidate_count(user_input.candidate_count)
    ranked_target_count = max(1, ceil(candidate_count * DEFAULT_MS2_RANKED_RATIO))
    ms1_request = {
        "theme": user_input.theme,
        "tlds": user_input.tlds,
        "candidate_count": candidate_count,
        "instructions": (
            "Return only structured JSON payload matching ms1_generate_slds schema. "
            "Generate up to candidate_count unique SLDs."
        ),
    }

    ms1_output = model_bridge.generate_slds(ms1_request)
    validate_payload(ms1_output, "ms1_generate_slds.schema.json")
    slds = ms1_output["slds"][:candidate_count]
    if len(slds) < len(ms1_output["slds"]):
        ms1_output = dict(ms1_output)
        ms1_output["slds"] = slds
        ms1_output = _append_note(ms1_output, f"trimmed_to_candidate_count={candidate_count}")
    if len(slds) < candidate_count:
        slds = _pad_slds_to_candidate_count(slds, user_input.theme, candidate_count)
        ms1_output = dict(ms1_output)
        ms1_output["slds"] = slds
        ms1_output = _append_note(ms1_output, f"padded_to_candidate_count={candidate_count}")

    ts1_input = {
        "tlds": user_input.tlds,
        "slds": slds,
        "options": {
            "timeout_ms": options.timeout_ms,
            "max_concurrency": options.max_concurrency,
            "batch_size": options.batch_size,
            "prefer_rdap": options.prefer_rdap,
            "enable_dns_fallback": options.enable_dns_fallback,
            "treat_unknown_as_available": options.treat_unknown_as_available,
            "bootstrap_cache_path": options.bootstrap_cache_path,
            "bootstrap_ttl_seconds": options.bootstrap_ttl_seconds,
            "rdap_fallback_base": options.rdap_fallback_base,
            "deterministic_mode": options.deterministic_mode,
            "deterministic_seed": options.deterministic_seed,
        },
    }
    validate_payload(ts1_input, "ts1_check_domains_in.schema.json")

    ts1_output_model = asyncio.run(check_domains(CheckDomainsInput.model_validate(ts1_input)))
    ts1_output = ts1_output_model.model_dump(mode="json")
    validate_payload(ts1_output, "ts1_check_domains_out.schema.json")

    ms2_request = {
        "theme": user_input.theme,
        "tld_preference": user_input.tlds,
        "results": ts1_output["results"],
        "suggested_best": ts1_output.get("suggested_best"),
        "policy": {
            "allow_unknown_fallback": options.treat_unknown_as_available,
        },
        "ranked_target_count": ranked_target_count,
        "instructions": (
            "Return only structured JSON payload matching ms2_pick_best schema. "
            "Include approximately ranked_target_count items in ranked."
        ),
    }
    ms2_output = model_bridge.pick_best(ms2_request)
    validate_payload(ms2_output, "ms2_pick_best.schema.json")
    ms2_output = _normalize_ranked_output(
        ms2_output=ms2_output,
        ts1_results=ts1_output["results"],
        tlds=user_input.tlds,
        target_count=ranked_target_count,
    )
    validate_payload(ms2_output, "ms2_pick_best.schema.json")

    return WorkflowResult(
        ms1_output=ms1_output,
        ts1_input=ts1_input,
        ts1_output=ts1_output,
        ms2_output=ms2_output,
    )
