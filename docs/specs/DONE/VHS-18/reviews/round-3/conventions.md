# Conventions Review — round 3

## Closure of round 2 findings
- conventions/F-2 (P2) — CLOSED. D5 now does a deterministic grep (append-if-heading-present; create-only-if-none).
- conventions/F-3 (P3) — CLOSED. R1 notes tab-rejection as a v1 lint determinism choice stricter than §3's letter.
- Positives (D1, install-hooks, complement-CodeRabbit, scope fences, public-repo) re-verified, no regression. R1 vocab matches contract §3 exactly; mcp__ keying consistent with the tool-namespacing decision.

## Findings

### F-1: Test-command section (line 116) re-asserts the ship-spec base-branch claim the Precondition fix retracted
**Severity:** P0 (internal contradiction)
spec:15 (corrected) says `/ship-spec` ALWAYS bases on `origin/<default-branch>` (verified `ship-spec/SKILL.md:76`, no override) and the executable path is "merge VHS-17 first." But spec:116 still says "the ship-spec worktree must base on `feat/vhs-17-portability-contract`" — the exact claim F-1 corrected, now in a different location the round-2 fix missed. ship-spec's Phase 0 reads `## Test command` verbatim, so an implementer takes the wrong base and the run fails.
**Fix:** Rewrite line 116's reminder to match the Precondition (merge #17 first; ship-spec bases on origin/default; manual stacked worktree as out-of-band alternative).

## Summary
P0: 1 | P1: 0 | P2: 0 | P3: 0 | P4: 0

STATUS: RED P0=1 P1=0 P2=0
