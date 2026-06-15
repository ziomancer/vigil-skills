# VHS-18 — Cross-harness: harness-agnostic authoring guidelines + lint

**Status:** Backlog · **Priority:** Medium · **Assignee:** Unassigned
**Created:** 2026-06-14 · **Plane:** VHS-18 (child of VHS-16)
**Origin:** The portability contract (VHS-17) is only as good as its enforcement. Devin's framing: the hard part is no longer model capability, it's saying what you mean unambiguously. This item turns the contract into day-to-day authoring discipline plus an automated guard, so skills stay portable **by construction** rather than by after-the-fact audit.

> **Loop note.** This is genuinely loopable — it produces a guidelines doc *and* a lint with a test suite, so `/ship-spec`'s test gate has real assertions to run (lint fires on a known-bad fixture, passes on the four shipped skills). **Sequencing: VHS-18 depends on VHS-17.** Do not loop VHS-18 until VHS-17 has merged, because the lint enforces the rules VHS-17 defines. If both are looped in one session, gate VHS-18's spec-cycle on VHS-17 being green first.

## Goal

Author harness-agnostic skill-writing guidelines, and a lint rule set that flags violations, wired into the repo's check path so portability regressions are caught before merge.

## Scope

Two deliverables:

1. **Guidelines doc** — what to write and what to avoid when authoring a portable skill: lead with intent, declare capabilities, never name a specific harness's tools or call syntax in the body, never assume one harness's affordances.
2. **Lint rule set** that flags, at minimum:
   - harness-specific tool names / call syntax in skill bodies (e.g. literal `mcp__*` tool identifiers, Claude-Code-only slash-command call conventions),
   - missing or malformed capability declarations (the VHS-17 schema),
   - intent that only resolves under one harness's affordances.

## Critical correction — there is no "existing CI path" to wire into (verified 2026-06-14)

The Plane ticket says "wire the lint into the existing sync/CI path." **That path does not exist today**, and the spec must not assume it:

- There is **no `.github/workflows/`** in the repo and `CLAUDE.md` states plainly: *"Not an application — no build step, no test suite, no dependencies beyond Python 3.8+ stdlib."*
- `sync.py` has **no test or lint hook** — it is a pure file-mirror utility (`grep -n "test\|lint\|hook" sync.py` → no matches, 2026-06-14).
- The **only** automated review surface is **CodeRabbit**, which already carries `path_instructions` for `skills/**` and `agents/**` (`.coderabbit.yaml`).

So the spec must **decide where the lint actually hooks in**, rather than reference a path that isn't there. Constraints that bound that decision:

- **Stdlib Python only.** To honor the repo's "no dependencies beyond Python 3.8+ stdlib" rule, the lint should be a stdlib Python script (the wiki's `wiki-lint.mjs` is a Node precedent for *shape*, not for language — do not import its toolchain here).
- **Plausible hook points** for the spec to choose among (and justify): a standalone `lint.py` (or a subcommand on `sync.py`) runnable locally; an optional pre-commit hook installed by a script (mirroring the wiki's `install-hooks` precedent); and/or a new minimal CI workflow. The brief deliberately does not pre-pick — that is spec-cycle's call — but the spec **must** name the chosen hook and explain why.

## Decisions carried forward

- **Depends on VHS-17.** The lint enforces the contract's rules and the capability-declaration schema; it cannot be specified before they are.
- **Advisory-then-blocking.** Ship the lint as **warn-only first**; promote to a hard gate only once all currently-shipped skills pass clean. This mirrors the repo's existing severity discipline and avoids blocking unrelated work on day one.
- **Stdlib Python, no new dependencies.** Matches `CLAUDE.md` and the `.coderabbit.yaml` `sync.py` path-instruction ("no pip dependencies allowed").
- **Don't fork CodeRabbit's job — complement it.** CodeRabbit reviews skill prose qualitatively; this lint is the *mechanical* portability check. Where they overlap, the lint is the deterministic gate.
- **The lint must run clean against the 4 shipped skills**, or every residual violation must be ticketed — no silent backlog.

## Done when

- The guidelines doc is merged and **linked from `CLAUDE.md`** (next to the VHS-17 contract reference).
- The lint rule set runs against **all current skills** (`skills/{spec-cycle,ship-spec,spec-close,review-pr}`) and the violation backlog is **zero or fully ticketed**.
- The spec has named a concrete, stdlib-only hook point (local script and/or pre-commit and/or CI) and the lint is invokable there; it ships in warn-only mode with a documented path to promotion.
- A known-bad fixture (a skill body containing a literal harness-specific tool name and a missing capability declaration) makes the lint fire, and the four shipped skills make it pass — both demonstrated in the test output.

## Out of scope

- The conversion engine and per-harness output (VHS-19 / VHS-20).
- Defining the portability rules themselves (that is VHS-17; VHS-18 only enforces them).
- The behavioral conformance suite (VHS-21) — runtime parity testing is distinct from static authoring lint.
- Rewriting existing skills beyond the minimal edits needed to clear lint violations they already contain.
- Any change to the Plane/wiki evidence-triple model.

## References

- Plane: VHS-18 (child of VHS-16, priority Medium, created 2026-06-14); depends on VHS-17.
- `CLAUDE.md` — "no build step, no test suite, no dependencies beyond Python 3.8+ stdlib"; the lint-language and hook-point constraints derive from this.
- `.coderabbit.yaml` — existing `path_instructions` for `skills/**` / `agents/**` and the `sync.py` "no pip dependencies" rule (read 2026-06-14).
- `sync.py` — no test/lint/hook present today (verified 2026-06-14); candidate host for a lint subcommand.
- Absence of `.github/workflows/` confirmed 2026-06-14 — the "existing CI path" the ticket references does not exist.
- Precedent (shape only, not toolchain): wiki `wiki-lint.mjs` + `scripts/install-hooks.{sh,ps1}`.
- Lint target inventory: `skills/{spec-cycle,ship-spec,spec-close,review-pr}/SKILL.md` (the four skills the lint must pass clean, read 2026-06-14).
