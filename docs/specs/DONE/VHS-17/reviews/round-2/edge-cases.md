# Edge-Cases Review — round 2

## Closure of round 1 findings
Round-1 P1s: 4 of 5 fully CLOSED; edge-cases/F-4 PARTIAL (resurfaces as F-1 below). Other closures verified: comment-strip (§3), availability (§3), §5 dim 1, Hermes reconciliation (D4/§3), tokenization (§3), uniqueness (§3), load-check (Test plan).

## Findings

### F-1: §4 construct 3 requires a "harness-neutral role," but shipped "Tool-use notes" name bare Claude tool names with no role — lint would fire on the shipped skills (re: round-1 F-4, PARTIAL → P1)
**Severity:** P1
**Where:** spec §4 construct 3 (line 101); Test-plan checklist (line 143)
The shipped skills' "Tool-use notes" sections contain bullets naming only Claude Code tool names, no neutral role, no "or the equivalent": spec-cycle:467 ("Read, Edit, Write for spec authorship"), :469 ("Agent calls (parallel) for the three reviewers"); ship-spec:263/264 ("Read, Edit, Write…"; "Bash for git, gh…"); spec-close:377/381 ("Read, Grep…"; "Write for the reconciliation report… Edit for state.md"). These satisfy neither case 2 (no "or the equivalent") nor case 3 as worded (no neutral role) nor case 1 (not operative imperatives). VHS-18 built to §4 fires on all four skills, contradicting checklist line 143 and VHS-18's acceptance criterion.
**Fix:** Broaden case 3 to allow bare tool names in **non-operative** meta/reference sections ("Tool-use notes") — make the allow-condition the section's non-operative role, not the presence of a neutral role. Add the spec-cycle:467/469, ship-spec:263/264, spec-close:377/381 lines as worked proof.

### F-2: §4's "verbatim" quote is not verbatim — anti-staleness guarantee already stale
**Severity:** P2 — **Pre-ship recommended: yes**
spec line 100 quotes "(e.g. `mcp__plane__list_projects` in Claude Code, or the equivalent in your host)" but SKILL.md:228 reads "(e.g.**,** `mcp__plane__list_projects` in Claude Code, or the equivalent in your host**'s Plane integration**)". Dropped a comma and the trailing qualifier.
**Fix:** Use the exact line-228 text, or reword "quotes verbatim" → "paraphrases."

### F-3: Tokenization leaves two decidability gaps (colon-in-element; `[ ]` → empty element)
**Severity:** P2 — **Pre-ship recommended: yes**
(i) The "split on first `:`" rule doesn't state colons inside a flow element are not separators (and make the element a violation). (ii) After bracket-strip, `[ ]` yields a one-element `" "` that trims to empty; spec says empty means none but a naive reader could emit `[""]`. State: discard empty elements; zero elements means none.
**Fix:** Add the two clarifying sentences to §3 tokenization.

### F-4: Optional-service probe at pre-flight unspecified
**Severity:** P3
The MUST clause scopes only required capabilities; whether optional services are probed at pre-flight is undefined, so two harnesses diverge on early-warning timing.
**Fix:** "Optional services MAY be probed early for an advisory warning but never block; parity is judged on point-of-use behavior, not early-advisory presence."

### F-5: Manual load-check has no objective pass artifact
**Severity:** P3
"Confirm it loads" is eyeball-judged; in a ship-spec worktree the gate is non-reproducible.
**Fix:** Specify a concrete artifact: after `sync.py install`, grep the installed SKILL.md for the `requires:` block AND a fresh `/spec-cycle` reaches Phase 0 without a frontmatter parse error; capture the grep for the PR audit trail.

## Summary
P0: 0 | P1: 1 | P2: 2 | P3: 2 | P4: 0

STATUS: RED P0=0 P1=1 P2=2 P3=2 P4=0
