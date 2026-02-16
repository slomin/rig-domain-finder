# RIG

## Definition (one sentence)
A **RIG** is an **app for agents**: a versioned bundle of **tools + state + instructions** that an agent installs and operates to get real work done.

## The metaphor
- **Agent** = humanoid robot (**harness** = body, **model** = brain)
- **OS/environment** = construction site
- **RIG** = heavy machinery (excavator, crane, forklift)

A humanoid can move dirt with its hands; an **excavator** moves mountains. A RIG is that excavator: purpose-built machinery an agent can operate.

## How a RIG is different from a normal app
Normal apps are built for humans. A **RIG is built for agents**:
- **Structured I/O first** (typically JSON in/out); human UI is optional.
- **Operational knowledge ships with the rig** (the built-in manual: `rig.md`).
- **Repeatability + auditability** are expected.

## What a RIG contains
- **Interface (TBD):** how the harness calls the rig.
- **Tools:** scripts, libraries, binaries, workflows.
- **Tool contracts:** a tool list plus **schemas** (usually JSON) for tool inputs/outputs.
- **State:** caches, indexes, DBs, artifacts, logs.
- **Instructions:** `rig.md`.
- **Versioning + updates:** maintainer releases; agent can customize.

## The two step types
RIG workflows alternate between **Model steps (MS)** and **Tool steps (TS)**.

### Model step (MS)
A **Model step** means “use the model like ChatGPT.” You ask it to think and produce output.

Use an MS to:
- **Generate inputs** (ideas, candidates, drafts).
- **Decide** (what to do next, priorities, plans).
- **Evaluate** (score/rank/filter, explain tradeoffs).

**Critical rule:** if an MS is preparing input for a Tool step, it must output **structured data** (usually **JSON**) that matches the rig’s tool schema. Tools should not be driven by free-form prose.

Example (Domain Finder):
- MS returns `{"candidates":["foo.com","bar.com"]}`
- TS checks availability
- MS ranks the results

### Tool step (TS)
A **Tool step** means “run normal software (software 1.0).” Code/binaries interact with the environment to produce facts/artifacts: files, API results, DNS checks, commits, etc.

### Typical loop
MS generates candidates → TS looks things up / measures reality → MS ranks/filters → TS applies the chosen action.

## Security (v0.1)
This is intentionally **simple for v0.1** and will need to be more robust later.
- **Permissions:** the rig declares what it wants; the environment grants a subset.
- **Audit:** log tool invocations and key model outputs/decisions.

## Self-modification (core feature)
A RIG is attached to a **git repo** with two **branches**:
- **`main` branch:** maintainer upstream (updates come from here).
- **`for_agent` branch:** agent/user working branch (can change anything: code, tools, `rig.md`, schemas, config).

**Simple attachment model (v0.1):** each installed rig is a git checkout in a known directory (e.g., `~/.rig/rigs/<name>`). The harness runs the rig from the active branch.

**How it works:**
- Default: run from the `main` branch.
- Customize: switch to the `for_agent` branch, edit, and commit.
- Update: rebase/merge `main` into `for_agent` to pick up upstream changes.
- Upstream (optional): promote changes via PR/review when you want them in `main`.

---

## Short version you can reuse
A **RIG** is an **app for an AI agent**. It gives the agent **pre-built, hardened tools** plus a manual (`rig.md`). The agent uses **Model steps** to generate/decide/rank (in **structured JSON**), and **Tool steps** to run software that touches the real world. The rig can be customized safely on a separate **`for_agent` branch** while upstream updates keep coming on **`main`.**