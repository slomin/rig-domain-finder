# Repository Guidelines

## Run, Debug, and Test First
1. Install dependencies: `uv sync`
2. Run all tests: `uv run pytest`
3. Run focused tests while iterating:
   - Tool logic: `uv run pytest tests/tool -q`
   - Contracts/schemas: `uv run pytest tests/contracts -q`
   - Harness + CLI behavior: `uv run pytest tests/harness tests/run -q`
4. Run TS1 tool directly (JSON in/out):
   - `uv run domainscout-check --input in.json --output out.json`
5. Run end-to-end harness with host model outputs:
   - `uv run domainscout-run --theme "privacy-first analytics" --tlds .com .io --ms1 ms1.json --ms2 ms2.json --out result.json`

Debug checklist:
- If you see environment errors, rerun with `uv run ...` (runtime guard blocks non-`uv` execution).
- For reproducible tool behavior, set `options.deterministic_mode=true` in TS1 input payloads.
- Check schema failures in `tests/contracts/` before changing tool logic.

## RIG Context (Required)
- This repository is a **RIG** (app for agents), not a generic script bundle.
- RIG definition and operation rules are in `rig.md`; read it before workflow changes.
- Step wiring is in `rig.yaml`; JSON contracts are in `schemas/`.
- Agents operating this repo must use the `rig-operator` skill and follow strict MS/TS separation with schema-validated JSON handoffs.

## Project Structure & Module Organization
- `src/domainscout/`: harness and user-facing runner (`harness.py`, `run.py`, schema helpers, env guard).
- `tools/check_domains/src/domainscout_check/`: TS1 domain-check tool implementation (RDAP, DNS probing, CLI, models).
- `schemas/`: JSON schemas for step contracts (`ms1_*`, `ts1_*`, `ms2_*`).
- `tests/`: `contracts/`, `tool/`, `harness/`, and `run/` suites.

## Coding Style & Naming Conventions
- Python 3.11+, 4-space indentation, explicit type hints, and `from __future__ import annotations`.
- Use `snake_case` for functions/modules, `PascalCase` for classes, and descriptive names for schema fields.
- Keep CLI behavior deterministic and JSON-focused at model/tool boundaries.

## Testing Guidelines
- Frameworks: `pytest` + `pytest-asyncio`.
- Name tests `test_*.py`.
- Mark async tests with `@pytest.mark.asyncio`.
- Prefer targeted runs first (for example `uv run pytest tests/tool/test_batching.py -q`) before full suite.
- Preserve contract coverage: schema shape, CLI output format, and deterministic-mode behavior.

## Commit & Pull Request Guidelines
- Current history is minimal (`Initial commit`), so no strict convention is established yet.
- Use concise, imperative commit subjects (for example: `Add deterministic TS1 batching test`).
- PRs should include: purpose, key behavior changes, test evidence (`uv run pytest ...`), and linked issue/context when available.

## Security & Configuration Tips
- This repo is `uv`-only by design; runtime guards block execution outside project `uv run`.
