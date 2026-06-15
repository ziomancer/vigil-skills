# Edge-Cases Review — round 2

## Closure of round 1 findings
All 12 round-1 findings CLOSED, verified against current spec + the four shipped skills + contract:
- F-1 heading normalize (verified vs real `## Tool-use notes` headings), F-2 operative-under-notes v1 limitation, F-4 robust frontmatter reader, F-3 case-2 window, F-5 inline requires, F-6 tabs, F-7 REPO_ROOT/__file__ + assert-4, F-9 lint_path no-raise, F-10 README precondition, F-8 lint_paths([]), F-11 stderr summary, F-12 window-scoped.

## Findings

### F-1: Fenced-code-block tracking underspecified for indented fences — shipped skills use them heavily
**Severity:** P2 — **Pre-ship recommended: yes**
134 fence markers across the 4 skills, many indented inside lists (e.g. spec-cycle:62 `      ```bash`, :191 8-space, :196 10-space). A naive `line.startswith("```")` misses indented fences; one missed open-fence inverts the in-code boolean for the rest of the file, making the case-3 fenced exemption unreliable. Zero current impact (no `mcp__*` sits inside a fence today), but latent.
**Fix:** Specify the matcher: strip leading whitespace; fence line = stripped content starts with ≥3 backticks; info string is part of the open; v1 toggles symmetric (no close-must-match). Add an indented-fence fixture with an `mcp__*` inside.

### F-2: `~~~` (tilde) fences silently unsupported
**Severity:** P3
CommonMark allows `~~~`; spec hardcodes backticks. No shipped skill uses `~~~`. Support `~~~` (cheap, same toggle) or add to D6 documented limitations.

### F-3: Case-2 window forward-only / one-line
**Severity:** P3
Can't see a tag on the line above the token or a 2-ahead wrap. Make symmetric or document. (Same root as correctness F-1.)

### F-4: CLI `**` vs Test `*` glob mismatch
**Severity:** P3
Same set today; diverge on nested SKILL.md. Reconcile to `skills/*/SKILL.md` in both.

### F-5: "Assert exactly 4 skills" is an intentional tripwire that breaks on skill #5
**Severity:** P3
Correct now (fixes vacuous-pass) but a 5th skill fails the test by design. Give the assertion a message naming the cause + note it's a deliberate inventory tripwire.

### F-6: "More-indented child" undefined for blank/comment-only lines inside the block
**Severity:** P3
A blank line (prefix length 0) terminates the contiguous run; a comment-only child becomes empty after strip. Specify: blank + comment-only lines inside the block are skipped (not terminators, not violations). Add a comment-in-block fixture.

## Summary
P0: 0 | P1: 0 | P2: 1 | P3: 5 | P4: 0

STATUS: GREEN
