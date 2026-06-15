# Edge-Cases Review — round 4 (final)

## Closure of round 3 findings
- edge-cases/F-1 (P3) — CLOSED. Folded into D6 limitation #3 (±1-non-blank-line window may exempt an operative call adjacent to an unrelated tag; deliberate tradeoff). Accurate vs R2's window definition and contract §4.
- line-117 fix (other lenses) — confirmed no impact in this domain.

## Findings

### F-1: D6 heading/lead-in said "two" detection gaps; list enumerates three
**Severity:** P4 (cosmetic)
Stale count after folding limitation #3. [Resolved by author in post-green polish: "two" → "three" at the D6 heading and lead-in.]

## Summary
P0: 0 | P1: 0 | P2: 0 | P3: 0 | P4: 1

Zero impact on the four shipped skills confirmed (all 11 mcp__ self-tagged; fences balanced; zero tilde fences). Lint runs clean.

STATUS: GREEN
