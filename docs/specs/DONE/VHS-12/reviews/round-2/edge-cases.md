# Edge-Cases Review — round 2

## Closure of round 1 findings

| Lens | ID | Title | Status | Evidence |
|---|---|---|---|---|
| correctness | F-1 (P0) | Never-needs-wiki vs log.md append | CLOSED | § Decision 8 (spec.md:69–75); Phase 1 rows 7–8; Phase 4 Wiki line; no mid-execute decisions (spec.md:74) |
| correctness | F-2 (P1) | Dual DONE-shape vs verbatim carry | CLOSED | Decision 6 ticketless rename (spec.md:49–50); carried text matches without dual-shape parsing |
| correctness | F-3 (P2) | CLAUDE.md:23 outside anchor | CLOSED | spec.md:20, :149; CLAUDE.md:23 text verified |
| correctness | F-4 (P3) | Grep expectation | CLOSED | spec.md:165 "zero matches" |
| correctness | F-5 (P4) | git grep naming | CLOSED | spec.md:118 |
| correctness | F-6 (P4) | "2a" citation | CLOSED | spec.md:92 |
| edge-cases | F-1 (P0) | Partial-close wiki contradiction | CLOSED | Same as correctness F-1; test plan (spec.md:160) |
| edge-cases | F-2 (P1) | Prefix collision (guard, 2a/2b) | CLOSED | Deviations 1–2 (spec.md:64–65); NEW variant at strategy (a) → F-4 below |
| edge-cases | F-3 (P2) | Unresolvable-UUID fallthrough | CLOSED | Phase 1 row 4 (spec.md:108) |
| edge-cases | F-4 (P2) | Failure-modes/Tool-use not carried | CLOSED | Decision 7 disposition block (spec.md:55–59) |
| edge-cases | F-5 (P2) | DONE rules vs full-name artifacts | CLOSED (by redesign) | Ticketless artifacts exclusively; unparseable shape never created |
| edge-cases | F-6 (P3) | Namespace drift nulls strategy (b) | CLOSED | Deviation 4 folded; Deferred wording imprecise → F-2 below |
| edge-cases | F-7 (P3) | Interrupted Phase 5 | CLOSED (as written) | Recovery bullet exists (spec.md:59); not implementable from carried text → F-1 below |
| edge-cases | F-8 (P4) | Silent report overwrite | CLOSED | Decision 4 notice (spec.md:44) |
| edge-cases | F-9 (P4) | Em-dash fragility | CLOSED | Bullet (spec.md:59) |
| conventions | F-1–F-10 | (round-1 set) | CLOSED | Per closure manifest; spot-verified |

## Findings

### F-1: The documented interrupted-execute recovery cannot be produced from the carried Phase 4 text
**Severity:** P2
**Pre-ship recommended:** yes
**Where:** spec.md:59 (recovery bullet) vs spec.md:53 (carry rule) vs spec.md:145 (Phase 5) vs spec.md:159 (test plan)
**Edge case:** Phase 5 dies after some artifacts moved to `DONE/`; re-run processes sources that no longer exist in `TODO/`.
**What happens:** The bullet promises "already-moved archive steps make re-execution idempotent" — but carried spec-retire Phase 4 step 3 has no skip-if-source-missing logic. Missing source → `git ls-files --error-unmatch` exits nonzero → classified *untracked* → `mv` fails on nonexistent source. A literal implementer under the carry rule ships a recovery path that errors mid-Phase-5. The spec asserts behavior its own carry rule prohibits implementing.
**Suggested fix:** Sanctioned deviation 5: "Phase 4's per-artifact loop skips artifacts whose source path no longer exists, printing `already archived: <name>`." Update test-plan "four" → "five".

### F-2: The spec's own install instruction propagates a stale repo states.json over the live one
**Severity:** P2
**Pre-ship recommended:** yes
**Where:** spec.md:25, :167, :179, :193
**Edge case:** Repo↔installed drift in `skills/ship-spec/states.json` when the PR-prescribed sync runs. Live data: repo copy `:53` maps VHS → `"vhs"`; installed copy maps VHS → `"skills"` (where the VHS-12 record lives, confidence 1.00) and carries a CLT entry absent from the repo copy.
**What happens:** `install --prune` mirrors repo → installed wholesale: overwrites live `"skills"` with stale `"vhs"`, silently drops CLT. Next VHS backfill: strategy (b) returns zero (warned, post-deviation-4). CLT closes hard-degrade to forced partial. Done-when 5's "status clean" is satisfied *because* the live fix was destroyed. This also bounds the round-1 orchestrator correction: wrong about runtime (skill reads installed copy), but the repo file at HEAD still says `vhs` and the spec's instruction is the mechanism that would make the round-1 failure real.
**Suggested fix:** (a) push states.json repo-ward in this PR, or (b) PR instruction: "run `python sync.py status` first; reconcile states.json drift before `install --prune`." Reword the Deferred bullet to name both copies' values.

### F-3: Rows 1 and 2 both match for `--report-only` + states.json fallback
**Severity:** P3
**Where:** spec.md:101, :105–106, :87, :94
**Edge case:** `--report-only` on a machine with missing/invalid states.json → `force_partial_close = true` → rows 1 and 2 both match; the runs differ materially (report vs archive mutations). Mutual exclusion covers only the two flags.
**Suggested fix:** State top-down evaluation; row 1 ignores `force_partial_close`.

### F-4: Prefix collision survives in merge-commit strategy (a); `-i` slightly widens it
**Severity:** P3
**Where:** spec.md:118, :67; carried `spec-reconcile/SKILL.md:28`
**Edge case:** Closing VHS-1 with VHS-11/VHS-12 in history (backfill makes this concrete). `git log --grep="VHS-1"` substring-matches both; `-i` adds lowercase `close(vhs-11):` commits.
**What happens:** Mixed commit list; worst case the wrong PR is reconciled and drift/evidence derive from another ticket's diff. Moderated by `--oneline` visibility — hence P3. The spec fixed the identical root at three sites and left the fourth.
**Suggested fix:** Extend the deviation to strategy (a): `-E --grep="<TICKET-ID>([^0-9]|$)"` or filter oneline output to exact-ID word matches.

### F-5: Partial-then-full re-run suppresses the full-close log entry
**Severity:** P4
**Where:** spec.md:61, :64, :38/:109, :59
**Edge case:** Partial-close today, full-close later via DONE path. The partial run's entry matches the guard; the full run's wiki-harvest event never lands in log.md. Inherited semantics, but the merged skill makes partial→full a first-class flow.
**Suggested fix:** Failure-mode sentence ("by design"), or distinguish `close(partial) |` vs `close |`.

### F-6: Fresh wiki without log.md — guard greps a nonexistent file
**Severity:** P4
**Where:** spec.md:71, :145; carried `spec-retire/SKILL.md:220`
**Edge case:** Configured wiki dir that never had `log.md` (the Decision 8 population). `grep -F` exits 2 (no such file) vs 1 (no match); carried text doesn't say which means "not present."
**Suggested fix:** "if `log.md` does not exist, treat as not-present and create it on append."

## Summary
P0: 0 | P1: 0 | P2: 2 | P3: 2 | P4: 2

STATUS: GREEN
