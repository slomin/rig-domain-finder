# RIG v0.1: DomainScout — Engineering Guide (Proposal)

> **Status / intent**: This document is a **proposal + preliminary research guide** to help an engineer implement the first RIG (“v0.1”). It is **not** the only valid approach. The engineer may choose different libraries/techniques, **but must adhere to the user story and the structured I/O constraints**.

---

## 1) User story (what to build)

As a RIG user, I want to:

- Provide an **overall theme / generic idea** for my website.
- Provide **one to three TLDs** in **preference order** (most desirable → least), e.g. `.com, .de, .io`.
- Have the **RIG check domain availability** for candidate names derived from the theme and the preferred TLDs.
- Have the RIG return the **best available domain** (or the best “maybe available” choice if certainty isn’t possible).

Notes:
- The check can be **simple**.
- **Occasional false positives** (reporting “available” when it’s actually not) are acceptable if rare.
- Use **Python + uv** for the domain-check tool step.

---

## 2) Terminology (aligning mental models)

- **Model**: “the brains” (like ChatGPT). It generates/chooses decisions.
- **Harness**: software that runs model calls + tool calls.
- **Agent**: **model + harness** (brains + hands).
- **RIG**: the **machine/environment** the agent uses to do work (tools, definitions, state). The agent can potentially modify the RIG if allowed.

Implementation note:
- In the repo, treat `main` and `for_agents` as **branches** and keep naming consistent in docs and tooling.

---

## 3) Design goals for v0.1

1. **Minimal** end-to-end flow that works.
2. **Strict structured I/O** whenever the model provides inputs for a tool step (JSON only; no prose).
3. **Auditable**: tool step behavior deterministic, logged, easy to test.
4. **Acceptable accuracy**: “good enough” availability checks via RDAP + DNS fallback.
5. **Fast**: concurrency for checking many domains.

Non-goals (v0.1):
- No registrar purchase/checkout.
- No UI polish.
- No perfect domain truth; false positives are acceptable if rare.

---

## 4) High-level architecture

### 4.1 Steps (MS/TS)

**MS1 — Candidate generation (Model Step)**
- Input: user theme + preferred TLDs
- Output: JSON list of candidate SLDs (second-level domains), e.g. `"pixelforge"`, `"tinyarcade"`

**TS1 — Domain availability check (Tool Step, Python)**
- Input: JSON (candidate SLDs × 1..3 TLDs)
- Output: JSON results with per-domain status and evidence

**MS2 — Select best (Model Step)**
- Input: tool results + TLD preference order
- Output: JSON containing chosen best domain + ranked list

### 4.2 Model/tool boundary (critical)

- Anything that becomes **tool input** must come from the model as **structured output**, validated against a schema.
- Tool output must also be structured JSON.
- Harness is responsible for:
  - requesting structured output from the model
  - validating JSON against schema
  - calling tools with the validated JSON
  - feeding tool results back into the model

---

## 5) Suggested repository layout

```
rig-domainscout/
  rig.md
  rig.yaml
  schemas/
    ms1_generate_slds.schema.json
    ts1_check_domains_in.schema.json
    ts1_check_domains_out.schema.json
    ms2_pick_best.schema.json
  tools/
    check_domains/
      pyproject.toml
      src/domainscout_check/
        __init__.py
        cli.py            # optional interface; harness integration is TBD
        bootstrap.py
        rdap.py
        dns_probe.py
        models.py
      .rig_cache/         # bootstrap + caching (gitignored)
  .gitignore
```

**Interface note**: the harness-to-tool invocation mechanism is **TBD** for v0.1. A pragmatic option is a JSON stdin/stdout CLI entrypoint, but the engineer may implement a different interface as long as it accepts/returns the same JSON structures.

---

## 6) Data contracts (schemas)

### 6.1 MS1 output schema — `ms1_generate_slds.schema.json`

Purpose: ensure the model produces tool-ready candidate SLDs.

**Fields**
- `slds`: array of candidate SLD strings
- `notes`: optional short string

**Constraints**
- Lowercase a–z, 0–9, hyphen
- Length 2–63
- Must not start/end with hyphen
- No dots

Example:
```json
{
  "slds": ["pixelforge", "tinyarcade", "playstacked"],
  "notes": "Short, brandable; avoided trademarks"
}
```

### 6.2 TS1 input schema — `ts1_check_domains_in.schema.json`

**Fields**
- `tlds`: 1 to 3 strings, each beginning with dot
- `slds`: list from MS1
- `options`:
  - `timeout_ms` (default 2500)
  - `max_concurrency` (default 20)
  - `prefer_rdap` (default true)
  - `enable_dns_fallback` (default true)
  - `treat_unknown_as_available` (default false)
  - `bootstrap_cache_path` (default `.rig_cache/rdap_dns.json`)
  - `bootstrap_ttl_seconds` (default 604800)
  - `rdap_fallback_base` (optional; e.g. `https://rdap.org`)

Example:
```json
{
  "tlds": [".com", ".de", ".io"],
  "slds": ["pixelforge", "tinyarcade"],
  "options": {
    "timeout_ms": 2500,
    "max_concurrency": 20,
    "prefer_rdap": true,
    "enable_dns_fallback": true,
    "treat_unknown_as_available": false
  }
}
```

### 6.3 TS1 output schema — `ts1_check_domains_out.schema.json`

**Fields**
- `checked_at`: ISO 8601 UTC timestamp
- `results`: array of per-domain objects
- `suggested_best`: optional string (deterministic tool suggestion)

**Per-domain object**
- `domain`: string
- `status`: `available | taken | unknown | invalid`
- `confidence`: 0–1
- `method`: `rdap | dns | rdap+dns`
- Evidence fields (optional):
  - `rdap_server`, `rdap_http`
  - `dns_nxdomain`, `dns_ns`, `dns_soa`
  - `error`

Example:
```json
{
  "checked_at": "2026-02-16T14:02:11Z",
  "results": [
    {"domain":"pixelforge.com","status":"taken","confidence":0.98,"method":"rdap","rdap_http":200},
    {"domain":"pixelforge.de","status":"available","confidence":0.80,"method":"rdap","rdap_http":404},
    {"domain":"tinyarcade.io","status":"unknown","confidence":0.30,"method":"rdap","rdap_http":503}
  ],
  "suggested_best": "pixelforge.de"
}
```

### 6.4 MS2 output schema — `ms2_pick_best.schema.json`

**Fields**
- `best_domain`: string or null
- `rationale`: short string
- `ranked`: array of domains with summary fields
- `next_actions`: optional array of suggestions if no good option

---

## 7) Domain availability strategy (v0.1)

### 7.1 Primary check: RDAP

- Use RDAP HTTP queries against the authoritative RDAP server for each TLD.
- Obtain RDAP endpoints from IANA “RDAP bootstrap” (`dns.json`) and cache.

Interpretation:
- HTTP 200 → **taken**
- HTTP 404 → **available** (good enough for v0.1; may still be false positive rarely)
- HTTP 400 → **invalid**
- 401/403/429/5xx/timeouts → **unknown**

Practical note:
- Some servers throttle; implement retries with jitter for 429/5xx (small and capped).

### 7.2 Fallback: DNS probe

Used only if RDAP is `unknown` (or if TLD not in bootstrap).

- Query `NS` and `SOA` records for the domain.
- If NXDOMAIN: likely **available** (still can be false positive)
- If records exist: likely **taken**
- Else: **unknown**

### 7.3 Confidence model (simple)

- `taken` via RDAP 200 → 0.98
- `available` via RDAP 404 → 0.80
- `taken` via DNS records → 0.70
- `available` via DNS NXDOMAIN → 0.60
- `unknown` → 0.20–0.35 depending on error type

This keeps scoring mechanical and easy to reason about.

---

## 8) Selection logic (MS2)

### 8.1 Hard requirements

- Respect TLD preference order.
- Prefer `available` over everything.
- If no `available`, optionally allow `unknown` as “maybe” (depending on policy).

### 8.2 Suggested ranking key

Sort by:
1. TLD preference index
2. Status rank: `available` > `unknown` > `taken` > `invalid`
3. Confidence descending
4. Domain length ascending (shorter is better)

### 8.3 What MS2 should say

- If `best_domain` is truly `available`, say so.
- If it’s `unknown`, label it clearly (“could not confirm availability; try again / alternate”).

---

## 9) Python tool step implementation details

### 9.1 Use `uv`

- Create a tool project in `tools/check_domains`
- Dependencies (suggested):
  - `httpx` (async HTTP)
  - `dnspython` (DNS queries)
  - `pydantic` (models + validation)
  - optionally `tenacity` (retries) or implement simple retry yourself

### 9.2 Concurrency

- Use `asyncio` + `httpx.AsyncClient`
- Cap concurrency with a semaphore
- Keep timeouts small; this is a bulk “check” tool, not a crawler

### 9.3 Bootstrap caching

- Cache file: `.rig_cache/rdap_dns.json`
- TTL: 7 days
- If cache missing/expired:
  - download bootstrap
  - write atomically (write temp then rename)

### 9.4 Input normalization

- Lowercase SLDs
- Validate `tlds` start with `.` and are ASCII
- For IDNs: optionally punycode using `idna` (can be v0.2; for v0.1 you may reject non-ASCII)

### 9.5 Logging

- Append a JSONL record per run to `.rig_cache/results.jsonl`
- Include tool version, options, and summary counts

### 9.6 Deterministic `suggested_best` (tool-side)

- Tool can return a deterministic suggestion to help MS2.
- Example: pick first `available` by TLD order; otherwise first `unknown` if policy allows.

---

## 10) Harness integration requirements

The harness must:

1. Request **structured JSON** for MS1.
2. Validate MS1 output against `ms1_generate_slds.schema.json`.
3. Call TS1 with validated JSON.
4. Validate TS1 output against `ts1_check_domains_out.schema.json`.
5. Feed TS1 output to MS2 and request **structured JSON**.
6. Validate MS2 output against `ms2_pick_best.schema.json`.

If validation fails at any step:
- The harness should re-ask the model with the validation error and require corrected JSON.

---

## 11) Error handling & edge cases

- **Rate limiting (429)**: retry 1–2 times with small exponential backoff + jitter.
- **RDAP bootstrap missing TLD**: mark as `unknown` and use fallback RDAP base or DNS.
- **Timeouts**: return `unknown`, include `error` field.
- **Invalid domain label**: mark `invalid` early, no network calls.
- **Reserved names**: (optional) reject obviously invalid SLDs.

---

## 12) Testing plan

### 12.1 Unit tests

- Domain validation
- RDAP response mapping (200/404/400/5xx)
- DNS mapping (NXDOMAIN vs records)
- Ranking key logic

### 12.2 Integration tests

- Live “smoke” test with a few known-taken domains and a few randomly generated ones.
- Ensure tests can run in CI with network either mocked or allowed behind a flag.

### 12.3 Contract tests

- Validate example JSON payloads against schemas.

---

## 13) Acceptance criteria (v0.1)

1. Given `{theme, [tld1,tld2,tld3]}`, the system produces candidate SLDs and checks `SLD×TLD` availability.
2. The tool step returns structured JSON with `status` + evidence fields.
3. The final output includes a `best_domain` that:
   - respects TLD preference order
   - prefers `available` results
   - falls back to `unknown` only if configured
4. All model→tool interactions use **validated JSON**.
5. Basic logging and caching exist.

---

## 14) Future enhancements (v0.2+)

- IDN support (punycode)
- WHOIS fallback (careful: variable formats)
- Registrar API checks (more accurate, more complexity)
- Better candidate generation (brand checks, trigram scoring)
- Automatic retries / re-check scheduling

---

## 15) Quick “happy path” example

### User input
- Theme: “minimalist portfolio for indie game developer”
- TLDs: `[".com", ".de", ".io"]`

### Output (conceptual)
- Best: `pixelforge.de`
- Ranked list: all checked domains with status + confidence
- Next actions: suggestions if no `available` found (e.g., add prefix/suffix)
