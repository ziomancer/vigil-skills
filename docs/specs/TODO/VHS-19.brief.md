# VHS-19 — Cross-harness: fork CE converter & establish vigil converter baseline

**Status:** Backlog · **Priority:** High · **Assignee:** Devin
**Created:** 2026-06-14 · **Plane:** VHS-19 (child of VHS-16)
**Origin:** VHS-16's "Hermes-first" cross-harness epic needs an owned conversion engine before any per-harness adapter (VHS-20) can be built. The engine is the fork of EveryInc/compound-engineering-plugin's Bun/TypeScript converter, retargeted at our `SKILL.md` tree and stripped of CE-specific content.

> **Blocker — now cleared (verified).** The ticket text says "Blocked by the portability contract (VHS-17)." VHS-17 is **merged and closed** (commit `39006cc`, PR #17, closed 2026-06-14 via `/spec-close`), so this item is **unblocked**. The converter targets the contract in `docs/portability-contract.md` — specifically §1 (canonical source = `SKILL.md`) and §2 (portable frontmatter subset). It does **not** target §3–§5; those are the adapter's and conformance suite's concern (VHS-20 / VHS-21).

> **Loop note.** The deliverable is a *forked engine with a passing smoke test*, not a complete Hermes adapter. The "at least one target end-to-end" smoke test exists to prove the inherited engine still runs after the CE strip — it is **not** a validation of that target's output (per the contract, inherited CE targets are "unvalidated → v2"). Do not let the loop expand this into building the Hermes adapter (VHS-20) or writing conformance tests (VHS-21). If the strip turns out to entangle a CE-specific skill with the engine, narrow scope and file the entanglement rather than rewriting the converter.

## Goal

Stand up our owned, security-vetted fork of CE's converter as the engine that emits per-harness skill packages from canonical `SKILL.md` sources — building from `~/.claude/skills/` with no CE residue, proven by a smoke-test conversion that runs in CI.

## Context (verified)

The upstream is **EveryInc/compound-engineering-plugin** — a Bun/TypeScript CLI that re-targets Claude Code skills/plugins to a roster of harnesses: Cursor, OpenCode, Codex, Gemini CLI, GitHub Copilot, Windsurf, Qwen Code, Factory Droid, Pi, and Kiro CLI (verified against upstream `src/targets/`, 2026-06-14; an earlier draft listed "OpenClaw" here — that is the fleet's own harness, not a CE target, corrected during VHS-19 spec-cycle round 1). **Hermes is not in that roster** — which is exactly why VHS-16 chose *fork-and-own* over *vendor-as-dependency*: a vendored dependency we cannot extend would never gain a Hermes adapter (that gap is the headline new work in VHS-20). The MIT license (per the component README, recorded in `docs/compound-engineering-evaluation.md`) permits the fork. Third-party forks already exist in the wild (e.g. `64labs/compound-engineering-plugin-fork`), confirming the pattern is mechanically clean.

**Toolchain tension to resolve up front.** vigil-skills is "no dependencies beyond Python 3.8+ stdlib" (`AGENTS.md`). The converter is Bun/TypeScript. The fork therefore must **not** live inside the vigil-skills tree — it gets its own repo home so the stdlib-only contract here is preserved and the Bun toolchain/CI stays isolated. Settling that repo home, its CI, and its update cadence relative to upstream is part of this ticket's scope, not a follow-up.

## Scope

1. **Fork & repo home.** Fork the MIT repo into our org under a new repo home (not inside vigil-skills). Record the fork point (upstream commit SHA) so the diff baseline is unambiguous.
2. **Strip to the engine.** Remove CE-specific skills, agents, personas, marketplace metadata, and branding, leaving the conversion engine and its target adapters. The strip must be a documented, reproducible diff against upstream — not an opaque rewrite — so future CE engine improvements can be cherry-picked.
3. **Retarget input.** Point the converter's input at our canonical source: the `~/.claude/skills/` tree (the same `SKILL.md` files `sync.py` installs), per portability-contract §1.
4. **Two end-to-end paths as the smoke test.** Produce (a) a **source ingestion / parse check** of a canonical `SKILL.md` (Claude Code is the converter's *input*, not a `--to` target, so there is no "passthrough" conversion — this path proves the engine reads our source; corrected during VHS-19 spec-cycle) and (b) **at least one inherited CE target** end-to-end (e.g. OpenCode or Codex) to prove the engine still converts after the strip. This proves the *engine runs*; it does not certify the target's behavior (that is VHS-21).
5. **Supply-chain vetting.** Audit the inherited dependency tree, pin versions (lockfile committed), and document the supply-chain surface in the fork's README. Confirm — and assert in the README — that the converter **never executes skill content during conversion** (parse/transform only, no eval of skill bodies).
6. **CI + cadence.** Wire the smoke-test conversion into CI on the fork. Document the update cadence against upstream (how/when CE changes are reviewed and cherry-picked through the recorded diff).

## Decisions carried forward

- **Fork and own — not vendor-as-dependency.** A vendored converter could not be extended for Hermes; ownership is the precondition for VHS-20. MIT permits it.
- **Security-first (pairs with the Petasos posture).** Forking third-party code is a supply-chain surface: the inherited dependency tree is audited, versions are pinned, and the surface is documented. **The converter must never execute skill content during conversion** — conversion is parse-and-transform only.
- **Keep a documented diff against upstream.** The strip and any local changes are expressed as a reviewable delta from a recorded fork point so CE engine improvements remain cherry-pickable.
- **Canonical source stays `SKILL.md`** (portability-contract §1); the converter consumes `~/.claude/skills/`, never a per-harness source fork.
- **The fork lives outside vigil-skills** so this repo's stdlib-only, build-step-free contract is preserved; the Bun toolchain and its CI are isolated to the fork.
- **Inherited CE targets are unvalidated.** The smoke test demonstrates the *engine* works end-to-end; OpenCode/Codex output is not certified here (deferred to v2 / the conformance suite).

## Done when

- The fork builds and converts the vigil skill set from `~/.claude/skills/` with **no CE residue** (no CE-specific skills, agents, or branding remain).
- The **dependency audit and version pinning are recorded**, and a supply-chain note (including the "never executes skill content" assertion) lives in the fork's README.
- A **smoke-test conversion runs in CI** — source ingestion plus at least one inherited target, end-to-end, green.
- The fork point (upstream SHA), the strip diff, the repo home, and the upstream update cadence are documented in the fork's README.

## Out of scope

- **The Hermes adapter itself** — the v1 target harness — is VHS-20. This ticket only stands up the engine and proves it runs.
- **Conformance / behavioral-parity testing** (portability-contract §5) is VHS-21. The smoke test is an engine liveness check, not a parity assertion.
- **Validating the inherited OpenCode/Codex targets** (v2) and adding Gemini/Cursor/Copilot/others.
- **Any `sync.py` or vigil-skills repo change** to carry adapters or multi-harness output — distribution is VHS-22; vigil-skills stays stdlib-only.
- **Porting CE's skills, agents, or knowledge-capture mechanisms** (the `ce-compound` lifts) — those are tracked separately off the evaluation brief.

## References

- Plane: VHS-19 (child of VHS-16 epic; blocked-by VHS-17, now merged). Sibling items: VHS-18 (authoring lint, merged `7ec40ca` PR #18), VHS-20 (Hermes adapter), VHS-21 (conformance suite), VHS-22 (distribution).
- `docs/portability-contract.md` (VHS-17, merged `39006cc` PR #17) — §1 canonical source, §2 portable frontmatter subset: the contract this converter targets.
- `docs/compound-engineering-evaluation.md` (merged 2026-06-14) — the adapt-don't-adopt analysis; MIT license; "do not install the plugin, we may read and re-implement freely."
- `docs/cross-harness-spike-synthesis.md` — VHS-16/17/18 spike; cross-ticket dependency-from-`main` finding (relevant to CI base for a stacked fork).
- `AGENTS.md` "What this repo is" — the stdlib-only, no-build-step contract that forces the converter into its own repo home.
- Upstream: [EveryInc/compound-engineering-plugin](https://github.com/EveryInc/compound-engineering-plugin) (MIT; Bun/TypeScript converter). Target roster verified 2026-06-14 — Hermes absent. Prior-art fork: `64labs/compound-engineering-plugin-fork`.
- Wiki: `tools/hermes-agent/` (architecture, skills-system) — informs why Hermes needs a hand-built adapter (VHS-20), out of scope here.
