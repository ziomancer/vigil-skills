# Conventions Review — round 2

## Closure of round 1 findings
All six round-1 conventions findings CLOSED (verified against current spec + wiki):
- conventions/F-1 (README prose not bullet) — CLOSED: "add a sentence matching paragraph style," idempotent on substring.
- conventions/F-2 (smoke-target (c) addition) — CLOSED: D6 states OpenCode is a spec-level refinement of the brief's open e.g.
- conventions/F-3 (stale fleet-serves-OpenClaw) — CLOSED: rationale re-grounded on "richest implemented adapter"; no fleet-serving claim. Cross-checked vs decisions/2026-06-12-openclaw-fork-update-archive-and-reset.md.
- conventions/F-4 (agnostic-to-§3 → drop key) — CLOSED: D4 preserves the requires: block verbatim (§2-portable, portability-contract.md:35).
- conventions/F-5 (repo name unpinned) — CLOSED: D1 pins `vigil-converter`; D7 sequences pointer URL after repo exists.
- conventions/F-6 (judgment-laden residue grep) — CLOSED: path-scoped structural assertion.
- correctness/F-4 (docs untracked) — PARTIAL (carried as F-1 below).

## Findings

### F-1: Two cited source docs still untracked — in-repo citation convention unmet until ship-spec commits them
**Severity:** P2 · **Pre-ship recommended:** yes
**Where:** spec § Prerequisite; cited at D1/D3/Design/Out-of-scope note
**Convention:** AGENTS.md:71 — anything that must ship in a PR belongs in a tracked file. Spec rationale (MIT, reject-list, Tier-3) resolves only to untracked `docs/compound-engineering-evaluation.md` + `docs/cross-harness-spike-synthesis.md` (`git status` → `??`). Spec correctly states the prerequisite but can't enforce it; binding is on ship-spec's commit set.
**Fix:** Make it a hard ship-spec checklist item (`git ls-files --error-unmatch ...`) and reflect the two docs in Test-plan #6's diff expectation. [Test-plan #6 updated in 2g.]

### F-2: Test-plan #6 "diff shows only README + spec artifacts" tension with the prerequisite docs riding the same PR
**Severity:** P3
**Where:** Test-plan #6 vs § Prerequisite
**Fix:** Reconcile #6 to include the two prereq docs, or commit them in a preceding PR. [Addressed in 2g.]

### F-3: ship-spec `Test command: N/A` reuse — positive verification
**Severity:** P3
Reuses VHS-7's documented N/A propagation (verified vs skills/ship-spec/SKILL.md:20 at round 1). Correct convention; confirm the installed ship-spec still honors N/A at ship time.

### F-4: `vigil-converter` wiki onboarding (projects/ page + fork-and-own decision) is /spec-close's job
**Severity:** P3
Observation for the drift-check: each owned repo gets a `projects/<slug>/` wiki entry; `vigil-converter` will need one at close. Not a spec defect. [Recorded in Deferred.]

## What the spec gets right
stdlib-only/no-build-step honored (Bun isolated to fork; sync.py/skills/agents/lint.py/tests untouched, AGENTS.md:7); CLAUDE.md-gitignored convention followed (README pointer); no stale OpenClaw-serving claim (vs 2026-06-12 park decision); requires: preservation aligns with portability-contract.md:35; no premature abstraction/duplication/back-compat shims.

## Summary
P0: 0 | P1: 0 | P2: 1 | P3: 3 | P4: 0

STATUS: GREEN
