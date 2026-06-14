# Correctness Review — round 2

## Closure of round 1 findings

| Lens | ID | Title | Status | Evidence |
|---|---|---|---|---|
| correctness | F-1 (P0) | Partial-close "never needs the wiki" vs log.md append | CLOSED | § Decision 8 (spec.md:69–75); Phase 1 rows 7–8 (spec.md:111–112); Phase 4 `Wiki:` plan line (spec.md:135); no mid-execute decision (spec.md:74) |
| correctness | F-2 (P1) | Dual DONE-shape acceptance vs carried shape logic | CLOSED | § Decision 6 flipped to ticketless rename-on-archive (spec.md:49–50); carried DONE branches now match what the skill produces; verified vs `skills/spec-reconcile/SKILL.md:11,37,53` |
| correctness | F-3 (P2) | CLAUDE.md anchor excluded line 23 | CLOSED | Scope `:23–31` + intro rewrite (spec.md:20); cross-ref edits (spec.md:149); test-plan row (spec.md:166) |
| correctness | F-4 (P3) | Grep expectation contradicted its command | CLOSED | "zero matches" with docs/specs exclusion explained (spec.md:165); re-verified at HEAD |
| correctness | F-5 (P4) | `git grep` vs `git log --grep` | CLOSED | spec.md:118 |
| correctness | F-6 (P4) | Ambiguous "2a" citation | CLOSED | spec.md:92 cites "spec-retire Phase 0 step 2a" |
| edge-cases | F-1 (P0) | Same root as correctness F-1 | CLOSED | Same evidence; test plan rows 7–8 (spec.md:160) |
| edge-cases | F-2 (P1) | Prefix collision in log guard and 2a/2b greps | CLOSED | Decision 7 deviations 1–2 (spec.md:64–65); colon verified against entry format |
| edge-cases | F-3 (P2) | State-UUID-unresolvable fallthrough | CLOSED | Phase 1 row 4 (spec.md:108); test plan (spec.md:160) |
| edge-cases | F-4 (P2) | Tool-use/Failure modes omitted from carry | CLOSED | Decision 7 disposition block (spec.md:55–59); source ranges verified accurate |
| edge-cases | F-5 (P2) | DONE re-audit misses full-named companions | CLOSED | Direction change: ticketless rename means the shape is never produced |
| edge-cases | F-6 (P3) | Namespace drift nulls strategy (b) | CLOSED (fix folded) | Deviation 4 (spec.md:67). Deferred rebuttal itself wrong for repo copy — new F-1 |
| edge-cases | F-7 (P3) | Interrupted Phase 5, no resume path | CLOSED | New failure-mode bullet (spec.md:59) |
| edge-cases | F-8 (P4) | Silent report overwrite | CLOSED | Decision 4 notice (spec.md:44) |
| edge-cases | F-9 (P4) | Em-dash fragility | CLOSED | New bullet (spec.md:59) |
| conventions | F-1 (P2) | CLAUDE.md:23 intro | CLOSED | Same as correctness F-3 |
| conventions | F-2 (P2) | Decision 6 hedged vs fleet corpus | CLOSED | Corpus stated as fact, conformed to (spec.md:50) |
| conventions | F-3 (P2) | Naive carry reintroduces superseded halts | CLOSED | *Deleted* disposition list (spec.md:58); test plan asserts absence |
| conventions | F-4 (P2) | "auto-detected" wording | CLOSED | Goal (spec.md:8); Done-when 1 (spec.md:175); Decision 2 (spec.md:38) |
| conventions | F-5 (P3) | Rebrand set partial | CLOSED | Enumerated (spec.md:61); residual gap → new F-2 |
| conventions | F-6 (P3) | Additions inventory | CLOSED | Deferred note (spec.md:192) |
| conventions | F-7 (P3) | states.json path/OS parenthetical | CLOSED | spec.md:94 |
| conventions | F-8 (P3) | completed_at not generic | CLOSED | Decision 3 (spec.md:41) |
| conventions | F-9 (P4) | force_partial_retire name | CLOSED | Rebrand set + spec.md:94 |
| conventions | F-10 (P4) | Grep expectation muddled | CLOSED | Same as correctness F-4 |

## Grounding verification summary (round 2)

- Decision 7 line citations re-verified at HEAD; every disposition maps to a real source bullet.
- Decision 6 round-trip consistent: ticketless writes ↔ carried read sites.
- CLAUDE.md anchors accurate; "zero matches" expectation holds.
- ship-spec/spec-cycle frontmatter verified; description-only edits suffice.
- Trailing-colon and `-w` semantics verified (hyphen is a non-word char).
- Last commit touching targets: 4088ee8 (VHS-11) — spec-cycle body only; no staleness risk.
- Plane ticket VHS-12 retrieved (namespace `skills`); no extra acceptance criteria.

## Findings

### F-1: Deferred-section rebuttal "states.json maps VHS → `skills`" contradicts the committed repo copy
**Severity:** P2
**Pre-ship recommended:** yes
**Where:** spec.md:193 (§ Deferred)
**Why this is wrong:** Only the *installed* copy (`~\.claude\skills\ship-spec\states.json:53`) maps VHS → `"skills"`. The *committed* copy — `skills/ship-spec/states.json:53` — maps VHS → `"vhs"` (and lags the installed copy: different `_note`, missing CLT entry). The round-1 reviewer's drift assertion was correct for the repo's source of truth. Operationally: the spec's own PR instruction (`python sync.py install --prune`) overwrites installed with repo — reverting VHS → `vhs` and re-creating the silent strategy-(b) failure (mitigated only after the fact by the deviation-4 warning).
**Suggested fix:** Reword the Deferred note to state both values; add an operational pre-ship step: reconcile states.json drift (push the installed copy's newer values) before telling installers to run `install --prune`.

### F-2: Rebrand set declared "exhaustive" but omits mode-name strings embedded in carried text
**Severity:** P2
**Pre-ship recommended:** yes
**Where:** spec.md:61 (Decision 7 rebrand set) vs spec.md:53 (carry rule) and spec.md:159 (test plan)
**Why this is wrong:** Carried text contains `full-retire`/`partial-retire`/"retirement log entry" in running prose (`spec-retire/SKILL.md:66,68,90,94,168,207,209`) that none of the six rebrand items covers. An implementer following the spec literally ships a skill whose Phase 1 table says `full-close`/`partial-close` while carried 2b/2c/execute text still says `full-retire`/`partial-retire` — and the checklist passes.
**Suggested fix:** Add mode-name strings (`full-retire` → `full-close`, `partial-retire` → `partial-close`, "retirement log entry" → "close log entry") to the rebrand set.

### F-3: "(archive only)" labels contradict Decision 5's definition of partial-close
**Severity:** P3
**Where:** spec.md:84 (invocation comment), spec.md:108 (row-4 prompt label)
**Why this is wrong:** Decision 5 defines partial-close as archive **plus the close log entry**; "archive only" is the Decision 8 row-8 degraded shape. The labels use the degraded name for the normal mode.
**Suggested fix:** "Partial-close (archive + close log entry)" or plain "Partial-close".

### F-4: Deviation 4's `-i` rationale cites the wrong lowercase producer
**Severity:** P4
**Where:** spec.md:67
**Why this is wrong:** At first-close time no `close(…)` commit exists yet. The live lowercase producer is ship-spec's `<type>(<ticket-lower>):` convention — e.g., 491f13a `feat(vhs-7): …` has no uppercase ticket ID anywhere, so case-sensitive `--grep` misses it today. The deviation is correct; the justification cites the re-run path.
**Suggested fix:** Cite ship-spec's commit convention as primary rationale.

### F-5: Phase 1 rows 1 and 2 overlap for `--report-only` + states.json failure
**Severity:** P4
**Where:** spec.md:101 vs rows 1–2 (spec.md:105–106)
**Why this is wrong:** `--report-only` + `force_partial_close` satisfies both predicates; intended winner (row 1) is implicit top-down precedence, which "exactly one row" disclaims.
**Suggested fix:** State top-down evaluation or "row 1 takes precedence over force_partial_close."

## Summary
P0: 0 | P1: 0 | P2: 2 | P3: 1 | P4: 2

STATUS: GREEN
