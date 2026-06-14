# Conventions Review — round 2

## Closure of round 1 findings

| Lens | ID | Title | Status | Evidence |
|---|---|---|---|---|
| correctness | F-1 (P0) | Wiki/partial-close contradiction | CLOSED | § Decision 8 (spec.md:69–75); Phase 1 rows 7–8; nothing mid-execute |
| correctness | F-2 (P1) | Dual DONE-shape vs carried logic | CLOSED | Decision 6 ticketless rename; fleet corpus verified (every petasos `DONE/<ID>/` ticketless, `find` for full-named → none); carried branches work unchanged |
| correctness | F-3 (P2) | CLAUDE.md:23 anchor | CLOSED | spec.md:20, :149 |
| correctness | F-4 (P3) | Grep expectation | CLOSED | spec.md:165; re-verified at HEAD |
| correctness | F-5 (P4) | git log --grep naming | CLOSED | spec.md:118 |
| correctness | F-6 (P4) | "2a" citation | CLOSED | spec.md:92 |
| edge-cases | F-1 (P0) | Wiki contradiction | CLOSED | As correctness F-1; test plan (spec.md:160) |
| edge-cases | F-2 (P1) | Prefix collision | CLOSED | Deviations 1–2 (spec.md:64–65); colon guaranteed by source format (`spec-retire/SKILL.md:222`) |
| edge-cases | F-3 (P2) | Unresolvable UUID | CLOSED | Row 4 (spec.md:108); eight-row check (spec.md:160) |
| edge-cases | F-4 (P2) | Tool-use/Failure carry | CLOSED | spec.md:55–59; source anchors exact |
| edge-cases | F-5 (P2) | Full-name DONE shape | CLOSED | Mooted by Decision 6 rework |
| edge-cases | F-6 (P3) | Namespace drift | CLOSED | Deviation 4 folded; Deferred rebuttal wrong about committed file → NEW F-1 |
| edge-cases | F-7 (P3) | Interrupted Phase 5 | CLOSED | Recovery bullet (spec.md:59) |
| edge-cases | F-8 (P4) | Report overwrite notice | CLOSED | spec.md:44 |
| edge-cases | F-9 (P4) | Em-dash guard | CLOSED | spec.md:59 |
| conventions | F-1 (P2) | CLAUDE.md:23 intro | CLOSED | spec.md:20, :149 |
| conventions | F-2 (P2) | Decision 6 hedge vs corpus | CLOSED | Corpus stated as fact, conformed to (count nit → NEW F-3) |
| conventions | F-3 (P2) | Inventory omits Tool-use/Failure + contradicting bullets | CLOSED | Dispositions incl. explicit deletion of superseded halts (`spec-retire/SKILL.md:260,263`) |
| conventions | F-4 (P2) | "auto-detected" stale | CLOSED | spec.md:8, :175 |
| conventions | F-5 (P3) | Rebrand set partial | CLOSED | spec.md:61 verified against source anchors (:231, :174, :30, :220–222, :245–246, :20–24) |
| conventions | F-6 (P3) | Additions inventory | CLOSED | spec.md:192; round-2 delta → NEW F-2 |
| conventions | F-7 (P3) | states.json path | CLOSED | spec.md:94 |
| conventions | F-8 (P3) | completed_at generic | CLOSED | spec.md:41 |
| conventions | F-9 (P4) | Flag name | CLOSED | spec.md:61, :94 |
| conventions | F-10 (P4) | Grep expectation | CLOSED | spec.md:165 |

## Findings

### F-1: § Deferred's factual rebuttal is false against the committed states.json — and the spec's install instruction would propagate the stale value
**Severity:** P2
**Pre-ship recommended:** yes
**Where:** spec.md:193 · interacts with spec.md:25, :167, :179
**Convention violated:** CLAUDE.md § Plan & Spec Reviews ("verify load-bearing claims against the actual codebase"); § What this repo is (repo = source-of-truth mirror).
**Evidence:** Committed `skills/ship-spec/states.json:53` reads `"namespace": "vhs"`; only the installed copy reads `"skills"` — drift confirmed by diff (also: `_note` differs, CLT entry missing from repo). The VHS-12 record lives in `skills` (confidence 1.00), so the installed copy is live-correct and the committed copy stale: the round-1 drift claim was correct about the artifact this PR ships. The spec twice instructs `python sync.py install --prune`, which would regress VHS → `vhs` and drop CLT; Done-when 5's "status clean" would be satisfied precisely because the live fix was clobbered.
**Suggested fix:** Correct the Deferred text (both copies' values). Resolve the divergence explicitly: one-line repo fix in Scope, or a mandatory pre-install reconciliation step in the PR description.

### F-2: Decision 8 is a new spec-level addition — surfaced for the drift-check inventory
**Severity:** P3
**Where:** spec.md:69–75, :111–112
**Convention violated:** None — category-(c) addition with explicit rationale.
**Evidence:** Neither brief nor ticket addresses wiki availability; prior posture was an unconditional halt (`spec-retire/SKILL.md:263`). Rationale stated (no-wiki repos are expected public-repo configurations). Decision 6's round-2 rework now *conforms to* the fleet corpus — a reduction in drift relative to round 1.
**Suggested fix:** None required — informational for the human drift-check.

### F-3: Petasos corpus count is 42 archived tickets, not 43
**Severity:** P4
**Where:** spec.md:8 (Goal), spec.md:50 (Decision 6)
**Evidence:** `ls -d DONE/*/ | wc -l` → 42 ticket directories; the 43rd entry is `wiki-archivist-handoff.md`, a stray file. (The "43" originated in my own round-1 review — correcting the record.) The load-bearing claim — all ticketless, zero full-named — re-verified true.
**Suggested fix:** "42" or "40+".

## Summary
P0: 0 | P1: 0 | P2: 1 | P3: 1 | P4: 1

Clean checks: `retire |` appears nowhere in wiki SCHEMA.md / wiki-lint.mjs / wiki CLAUDE.md/AGENTS.md (only historical log entries, correctly untouched); `docs/spec-workflow-reference.md` leave-alone verified; CLAUDE.md anchors exact; Decision 7 source anchors and rebrand set exact; Decisions 1/6 align with the no-backwards-compat stance; no premature abstractions; frontmatter conventions met.

STATUS: GREEN
