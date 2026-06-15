# Edge-Cases Review — round 1

## Findings

### F-1: Case-3 heading allowlist `^Tool-use (notes|rules)` won't match actual `## Tool-use notes` headings
**Severity:** P1
Real headings are ATX: `## Tool-use notes` (spec-cycle:465, spec-close:375, ship-spec:261). A regex anchored at `^Tool-use` won't match `## Tool-use notes` unless the lint strips leading `#{1,6}\s+` first — which the spec never specifies. Case-3 is dead code as written; Test 2 passes only by accident (the notes-section mcp__ lines also carry case-2 markers).
**Fix:** Normalize the heading (strip `#{1,6}\s+`, trim) before applying the allowlist; add a fixture with a bare mcp__ inventory bullet under `## Tool-use notes` and NO case-2 markers, asserting zero ERRORs.

### F-2: Operative-imperative-under-a-notes-heading (contract §4 case-1 carve-out) not detected
**Severity:** P1
Contract §4 is explicit: an operative imperative under a notes heading is STILL case 1. The spec's case-3 branch is a flat heading exemption with no operativeness test → an operative `mcp__*` call laundered under `## Tool-use notes` is silently OK. The lint over-claims §4 enforcement.
**Fix:** Either add a heuristic (imperative-verb-led / numbered-step line with mcp__ under a notes heading still ERRORs), OR explicitly add this to the documented v1-limitation list (like the bare-name deferral) so the lint doesn't over-claim. Add a fixture.

### F-3: Case-2 markers spanning two physical lines → false-positive ERROR
**Severity:** P2 — **Pre-ship recommended: yes**
A wrapped sentence puts mcp__ + "e.g." on line N and "or the equivalent" on line N+1; a strict per-line check false-ERRORs a correctly-authored example. Define the case-2 window (token line + next non-blank line, or sentence-bounded). Add a split-marker fixture.

### F-4: Frontmatter parser undefined for malformed/absent delimiters, CRLF, BOM, empty file
**Severity:** P1
"Between the first two `---`" is undefined for: no frontmatter, no closing `---`, empty file, `---` not on line 1, CRLF (`'---\r'` != `'---'`), UTF-8 BOM (`'﻿---'`). On Windows (primary platform) a CRLF checkout parses as no-frontmatter, cascading wrong findings; an unterminated block can crash.
**Fix:** Specify a robust reader: strip BOM; `splitlines()` for CRLF/CR/LF; opening `---` as first non-empty line; missing open/close → "no frontmatter" → missing-requires WARN, never raise. Add fixtures: empty, no-frontmatter, unterminated, CRLF, BOM.

### F-5: `requires:` with inline value (`{}` / `[]` / `{shell: true}`) undefined
**Severity:** P2
Block-shaped algorithm has no branch for a value on the `requires:` line. Inline `{shell: true}` (nested mapping per §3) would be silently missed. Define: inline `{…}` → malformed ERROR; `[]`/`{}` → present-but-empty (clean); other inline scalar → malformed.

### F-6: Tabs vs spaces in the requires: block — indentation detection unspecified
**Severity:** P2
"More-indented" is ambiguous with mixed tabs/spaces. Define as longer leading-whitespace prefix; tab in a requires child → malformed (YAML no-tabs). Add a tab fixture.

### F-7: `python tests/test_lint.py` cwd/platform-fragile; Test 2 can pass vacuously on empty skill set
**Severity:** P2
If repo root / skill glob resolves from cwd not `__file__`, running from another cwd ImportErrors or finds zero skills → Test 2 passes vacuously (silent false pass). 
**Fix:** `REPO_ROOT = Path(__file__).resolve().parents[1]`; resolve all paths from it; Test 2 asserts it found exactly 4 skills before the per-skill loop.

### F-8: `lint_paths([])` and "no paths" default need distinct definitions
**Severity:** P3
Define `lint_paths([])` → `[]` (pure aggregation, no implicit glob); default-glob is a CLI/`main()` concern; `main()` notices an empty resolved set so "linted nothing" is never a silent pass.

### F-9: Empty/frontmatter-less SKILL.md in the default glob path → crash/misclassify
**Severity:** P2
Default glob `skills/**/SKILL.md` will feed real empty/malformed files to lint_path. Require lint_path total (no-raise) over any content; emit a deterministic finding. Add an empty-SKILL.md to Test 2's directory-walk.

### F-10: README "Cross-harness portability" anchor absent on main — Done-when #1 unshippable as specified
**Severity:** P2
Same root as correctness F-1/F-3. Tie to the stacking precondition or have VHS-18 create the section.

### F-11: Default-mode ERROR has no machine-detectable signal
**Severity:** P3
Default exits 0 even with ERRORs (by design). Add a summary line on stderr (`lint: N error(s), M warning(s)`) and tell automation to use `--strict`.

### F-12: Multiple mcp__ tokens on one line sharing one case-2 marker pair
**Severity:** P3
spec-close:56 has two mcp__ tokens + one marker pair on one line. State case-2 is line/window-scoped (every occurrence on a line whose window has both markers is exempt). Folds with F-3.

## Summary
P0: 0 | P1: 3 | P2: 6 | P3: 3 | P4: 0

STATUS: RED P0=0 P1=3 P2=6 P3=3 P4=0
