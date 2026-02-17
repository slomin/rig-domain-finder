# DomainScout RIG

DomainScout is a RIG v0.1 for agent-driven domain ideation and availability checking.

## Setup
This RIG is uv-only by design.

Required flow:

`uv sync`

Run commands with uv:

`uv run domainscout-check ...`
`uv run domainscout-run ...`

Runtime guard behavior:
- Running outside `uv run` is blocked.
- Running in a virtualenv other than project `.venv` is blocked.

## Mandatory startup behavior
When this RIG is invoked, the agent must start with user input collection before any domain generation or lookup.

Required first action:
1. Ask the user for `theme` (one sentence).
2. Ask the user for `1` to `3` TLDs in strict preference order.
3. Optionally ask for candidate count (default is `10%` of max supported, currently `500`, if not provided).
4. Collect these inputs in plain language; do not require the user to reply in JSON.

Do not generate candidate SLDs, run TS1, or present domain suggestions until the required user inputs are collected.

## Workflow
1. MS1 generates SLD candidates as structured JSON.
2. TS1 checks availability through RDAP with DNS fallback.
3. MS2 selects best domain from structured tool output.

## MS2 naming guidance (brand/marketing)
- Use `references/domain_naming_guide.md` to evaluate naming quality after TS1.
- Keep hard ordering for decision quality:
  1. Availability/status confidence from TS1.
  2. Brand/marketing scoring from the naming guide.
- Treat the guide as a ranking framework, not a schema change.
- Always keep MS2 tool handoff and output schema-valid JSON.

## Candidate count handling
- Requested `candidate_count` is passed to MS1.
- Supported range is `1..5000`; out-of-range values are clamped automatically.
- If omitted, `candidate_count` defaults to `ceil(5000 * 0.10) = 500`.
- If MS1 returns more than requested, the harness trims before TS1.
- If MS1 returns fewer than requested, the harness deterministically pads valid SLDs to match `candidate_count` before TS1.
- MS2 ranked output target is `ceil(candidate_count * 0.10)`.
- If MS2 returns fewer ranked items than target, the harness auto-fills from TS1 results.
- If MS2 returns more than target, the harness trims to target.
- Final user-facing ranked list length is enforced to `min(ceil(candidate_count * 0.10), len(ts1.results))`.

## User-facing output
- IMPORTANT: Display approximately 10% of checked candidates in the ranked section: `ceil(len(ts1_input.slds) * 0.10)`, bounded by available ranked results.
- Ranked output should be balanced across requested TLDs when possible (roughly equal representation for each requested TLD).
- Agent/tool handoff remains strict JSON and schema-validated.
- User-facing `domainscout-run` output must be plain text, not raw JSON.
- Terminal output should use ANSI color styling when supported.

## TS1 robustness rules
- TS1 must handle large candidate lists in one request.
- Internal batching is mandatory in tool code (not model-side splitting).
- Default internal `batch_size` is `200` SLDs per batch.
- `slds` input supports up to `5000` candidates per request; the tool splits automatically.

## Deterministic mode (generic data)
- For reproducible testing, TS1 supports `options.deterministic_mode=true`.
- In deterministic mode, TS1 bypasses RDAP/DNS network calls and returns stable synthetic statuses derived from `domain` + `deterministic_seed`.
- Default `deterministic_seed` is `17`; change it explicitly to generate a different but still deterministic synthetic dataset.

## First prompt template
Use this prompt at startup:

`Tell me: (1) your theme in one sentence, (2) one to three TLDs in order (example: .com, .de, .io), and (3) optional candidate count (default: 10% of max, currently 500). Plain text is fine.`

## Branch model
- `main`: upstream maintainer branch
- `for_agent`: customizable agent branch

## Resources

### references/
- `references/domain_naming_guide.md`: Brand naming evaluation framework (recall, clarity, pronunciation, distinctiveness, channel consistency, weighted scorecard).
