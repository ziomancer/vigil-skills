# Correctness Review — round 1

## Findings

### F-1: VHS-17 (PR #17) is OPEN, not merged — "shipped" premise false on main; ship-spec cuts the VHS-18 worktree from main
**Severity:** P1
PR #17 is OPEN (`mergedAt:null`). On main: `docs/portability-contract.md` untracked, README has no "Cross-harness portability" section, `skills/spec-cycle/SKILL.md` has no `requires:` block. ship-spec Phase 1 cuts the worktree from the default branch (main) — so the VHS-18 worktree won't contain the contract, README anchor, or requires: block unless #17 merges first. The brief's loop note ("gate on VHS-17 being green first") — "green" must mean merged-to-main or stacked, not just PR-opened.
**Fix:** Add an explicit precondition: VHS-18 ship-spec stacks its worktree on the `feat/vhs-17-portability-contract` branch (or #17 merges first); state that Test 2's valid-requires assertion + README anchor depend on it.

### F-2: Test 2 asserts spec-cycle "validates clean with its requires: block" — but on main spec-cycle has no requires: block
**Severity:** P1
The requires: block exists only in unmerged commit. If VHS-18 runs before #17 merges, all four skills hit missing-requires WARN and the valid-block R1 path is untested (test still passes its literal "zero ERRORs" but the happy-path coverage is silently unmet).
**Fix:** Add a dedicated positive fixture `tests/fixtures/good-skill/SKILL.md` with a well-formed requires: block; cover the valid-block R1 path via the fixture, not via spec-cycle's annotation surviving merge order.

### F-3: D5 / Done-when #1 anchor the README pointer to a section not present on main
**Severity:** P2
Same root as F-1: the "Cross-harness portability" section is in the unmerged VHS-17 commit. Tie the README edit to the stacking precondition (append to the section VHS-17's branch introduces).

### F-4: R2 case-2 heuristic ("both e.g. and or-the-equivalent on same line") is narrower than contract §4
**Severity:** P2 — **Pre-ship recommended: yes**
§4 keys case-2 on the "or the equivalent" tag, not on a co-located "e.g." The spec invented the stricter "e.g."-co-marker requirement. Passes all 11 current occurrences but would false-ERROR a contract-valid example using "for instance" or no "e.g." Silent divergence between lint and the contract it cites.
**Fix:** Relax case-2 to key on the "or the equivalent" tag alone (matching §4), example marker optional; or explicitly document the stricter heuristic in spec + lint + guidelines.

### F-5: R2 "line/sentence" is ambiguous; pin to per-line/window
**Severity:** P3
A stdlib line reader doesn't segment sentences. Pin to per physical line (or a defined window). Folds with edge-cases F-3.

### F-6: R1 filesystem/? interaction underspecified (only services may carry ?)
**Severity:** P3
§3 scopes the optional-? strip to services only; `[read?]` must be an out-of-vocabulary ERROR. State explicitly.

### F-7: Done-when #2 names a follow-up ticket the spec doesn't identify
**Severity:** P3
"Filed as a follow-up ticket" is unverifiable without an ID. Soften to "documented in the guidelines doc's promotion path as the tracked backlog item," or cite an actual ticket ID.

## Summary
P0: 0 | P1: 2 | P2: 2 | P3: 3 | P4: 0

STATUS: RED P0=0 P1=2 P2=2 P3=3 P4=0
