# Edge-Cases Review — round 3

## Closure of round 2 findings
All round-2 findings CLOSED, verified against current spec + shipped skills:
- F-1 indented-fence matcher (leading-WS-stripped, ≥3 backticks/tildes) + indented-fence fixture; F-2 tilde fences supported; F-3 symmetric case-2 window + split-marker fixture; F-4 CLI/test glob reconciled; F-5 assert-4 tripwire message; F-6 blank/comment-line skip + comment-in-requires fixture.
- conventions F-1/F-2/F-3 and correctness F-1/F-2 also verified closed (window symmetric; glob reconciled). [Note: line-116 leftover flagged by the other two lenses is outside this lens's scope.]

## Findings

### F-1: Symmetric case-2 window + flat case-3 fence exemption widen the v1 false-negative surface (documentation completeness)
**Severity:** P3
The ±1-non-blank-line window can exempt an operative call adjacent to an unrelated tagged sentence — a third precision tradeoff alongside D6's two documented gaps. Zero impact on shipped skills (all mcp__ self-tag; all fences balanced; zero tilde fences). Add one clause to D6's limitation list so the lint doesn't over-claim §4. No code change.

## Summary
P0: 0 | P1: 0 | P2: 0 | P3: 1 | P4: 0

STATUS: GREEN
