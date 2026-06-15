# Correctness Review — round 3

## Closure of round 2 findings
All round-2 findings CLOSED except the line-116 leftover (PARTIAL, same root as conventions F-1). Verified: symmetric case-2 window (spec:79), CLI/test glob reconciled to `skills/*/SKILL.md`, fence matcher (backticks+tildes, leading-WS-stripped), blank/comment-line skip, tab-note, D5 deterministic grep. R1↔§3 and R2↔§4 re-verified exact; all 11 shipped mcp__ occurrences self-tag → four skills pass clean.

## Findings

### F-1: Test-command note (line 116) contradicts the rewritten Precondition on ship-spec's worktree base
**Severity:** P1
Line 116 still says "the ship-spec worktree must base on `feat/vhs-17-portability-contract`" — the claim round-3 corrected at spec:13/15 (ship-spec hardcodes `origin/<default-branch>`, verified ship-spec/SKILL.md:76). Same root as conventions F-1; the Precondition prose was fixed but this back-reference wasn't. An implementer reading the Test-command section takes the false instruction and the run fails.
**Fix:** Replace line 116's reminder with the corrected wording (merge VHS-17 first; manual stacked worktree out-of-band).

### F-2: Symmetric case-2 window is a slightly-lenient encoding, not a correctness hole today
**Severity:** P3
±1-non-blank-line window could exempt an operative call adjacent to an unrelated tag. Zero impact on shipped skills (all self-tag). Optional: document as a v1 limitation in D6.

## Summary
P0: 0 | P1: 1 | P2: 0 | P3: 1 | P4: 0

STATUS: RED P0=0 P1=1 P2=0 P3=1 P4=0
