# Correctness Review — round 2

## Closure of round 1 findings
All 7 round-1 P1s and both P2s CLOSED, verified against current spec + files + the VHS-17 branch:
- correctness F-1/F-2 (PR open / requires path) — Precondition + good-skill fixture.
- correctness F-4 (case-2 keying) — now keys on "or the equivalent" tag, matches contract §4.
- correctness F-5/F-6/F-7 — window pinned; filesystem no-`?`; Done-when #2 softened.
- edge-cases F-1 (heading normalize), F-2 (operative-under-notes v1 limitation), F-4 (robust frontmatter reader), F-3/F-5/F-6/F-7/F-8/F-9/F-10/F-11/F-12 — all CLOSED.
- conventions F-1/F-2 — D5 history corrected; Precondition.

R1↔§3 and R2↔§4 re-verified exact. All 11 shipped `mcp__*` occurrences carry the tag on the token's own line → all four skills pass clean. Precondition internally consistent (the VHS-17 branch genuinely carries contract + README section + spec-cycle requires:).

## Findings

### F-1: Case-2 window is forward-only (token line + next non-blank); a tag on the previous line false-ERRORs
**Severity:** P3
Forward-only window doesn't cover a tag wrapping onto the line before the token, or a 2-ahead wrap. Zero current impact (all shipped occurrences have token+tag on one line). Make the window symmetric (prev + token + next non-blank) or document the forward-only scope.

### F-2: CLI default glob `skills/**/SKILL.md` vs Test 3 `skills/*/SKILL.md` differ
**Severity:** P4
Same 4 files today (flat layout), but `**` vs `*` diverge if a nested SKILL.md is ever added. Use the same glob in both.

## Summary
P0: 0 | P1: 0 | P2: 0 | P3: 1 | P4: 1

STATUS: GREEN
