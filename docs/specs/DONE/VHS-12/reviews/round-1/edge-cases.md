# Edge-Cases Review — round 1

## Closure of round 0 findings
N/A — round 1.

## Findings

### F-1: Partial-close both "never needs the wiki" and appends to wiki log.md
**Severity:** P0
**Where:** spec.md:70 (Phase 0 step 3) vs spec.md:96 (Phase 3), spec.md:106 (Phase 4 template), spec.md:114 (Phase 5 verbatim carry of spec-retire Phase 4 step 4)
**Edge case:** Wiki directory missing or unresolvable while mode is partial-close — including the compounding case where states.json is missing, which *forces* partial-close.
**What happens:** Line 70 states "`--report-only` and partial-close never need the wiki," so preflight only warns. But partial-close's plan is "archive list + log entry only" (line 96), the Phase 4 template includes the log.md block, and Phase 5 carries spec-retire Phase 4 verbatim — whose step 4 appends to `<wiki_root>/log.md`. With no wiki, Phase 5 executes the archive moves and then hits a nonexistent path *after* the TODO→DONE mutations have already been applied. Half-closed state, no documented recovery. No-wiki repos are an expected configuration per the public-repo generalization principle. Secondary effect: in full-close + wiki-missing, the halt is deferred to Phase 3 — after the user has answered Phase 2 prompts and the report has been written — and is a dead end with no partial offer.
**Suggested fix:** Define wiki-missing behavior per mode explicitly: (a) partial-close with no wiki drops the log.md entry from the plan with a printed notice; (b) full-close with no wiki surfaces the partial-or-abort prompt at mode resolution (Phase 1). Add wiki-missing × mode rows to the test-plan matrix.

### F-2: Ticket-ID prefix collision makes the log.md idempotency guard silently skip entries (VHS-1 vs VHS-11 is live data)
**Severity:** P1
**Where:** spec.md:128, spec.md:131; carried text at `skills/spec-retire/SKILL.md:220` (Phase 4 step 4), `:48–49` (2a), `:101–103` (2b Stage 2)
**Edge case:** A ticket ID that is a string prefix of another already-closed ticket: `close | VHS — VHS-1` is a fixed-string substring of `close | VHS — VHS-11: <title>`.
**What happens:** Close VHS-11, then close VHS-1: the idempotency grep matches VHS-11's line and **silently skips writing VHS-1's log entry** — silent data loss in the wiki's audit trail. Not hypothetical: `docs/specs/TODO/` currently holds both VHS-1 and VHS-11 artifacts, and the brief's stated follow-up is backfilling all unretired specs. The same root poisons the carried 2a duplicate detection and 2b coverage greps (`grep -rl "VHS-1"` matches every file containing "VHS-11"): the partial-coverage branch silently narrows derivation scope, starving VHS-1's wiki harvest.
**Suggested fix:** Include the trailing colon in the fixed-string pattern — `grep -F "close | <PROJECT> — <TICKET-ID>:"` — and use word-boundary matching (`grep -rlw "<TICKET-ID>"`) for the 2a/2b greps. Record as a sanctioned deviation from Decision 7's "verbatim."

### F-3: Mode-resolution table has a silent fallthrough — state UUID unresolvable to a group
**Severity:** P2
**Pre-ship recommended:** yes
**Where:** spec.md:82–85 (Phase 1), spec.md:129 (seven-row checklist)
**Edge case:** Both Plane calls succeed, but the ticket's `state` UUID is absent from the `list_states` response — stale `project_id` in states.json, or a null/empty `state` field. states.json's own `_note` warns its UUIDs go stale.
**What happens:** Group is undefined; none of the three Phase 1 branches applies. Worst case the LLM treats the ticket as completed and proceeds to full-close, ending in a state.md "What's Shipped" entry for unshipped work.
**Suggested fix:** Eighth row: state UUID not found in state map (or null state) → same partial-or-abort prompt as Plane-unreachable, naming the unmatched UUID and suggesting a states.json refresh.

### F-4: Decision 7's carry inventory omits both skills' "Failure modes" and "Tool-use notes" sections
**Severity:** P2
**Where:** spec.md:52 (Decision 7); source sections at `skills/spec-reconcile/SKILL.md:104–118` and `skills/spec-retire/SKILL.md:249–267`
**What happens:** Degradation guidance that lives *only* in those sections is lost: "Plane ticket not in MCP memory → warn and proceed," cross-repo commit discipline, the read-only-vs-mutating tool boundary. The test checklist even *presupposes* a failure-modes section exists (requires the completed_at-quirk bullet) but nothing instructs creating it.
**Suggested fix:** Extend Decision 7's inventory to include both skills' Failure modes and Tool-use notes sections, merged and de-duplicated, plus the new bullets this spec introduces.

### F-5: Carried DONE-path filename rules don't cover the full-name shape the skill itself produces
**Severity:** P2
**Pre-ship recommended:** yes
**Where:** spec.md:49 (Decision 6) vs spec.md:89 (Phase 2 carry); `skills/spec-reconcile/SKILL.md:37,53`
**Edge case:** Invoking `/spec-close docs/specs/DONE/VHS-12/VHS-12.spec.md --report-only` — re-auditing a spec the new skill itself archived under Decision 6's full-name rule.
**What happens:** Carried Phase 1 step 3 looks for `brief.md` (won't exist — silently drops the brief's acceptance criteria from reconciliation); carried Phase 3 report-path rule matches neither branch, so the report filename is undefined.
**Suggested fix:** Extend Decision 6 to companion resolution: on DONE paths, resolve brief/report names by trying `<TICKET-ID>.<role>.md` first, then `<role>.md`. Note as sanctioned edit to carried text.

### F-6: states.json namespace drift silently nulls the memory-lookup merge-commit strategy
**Severity:** P3
**Where:** spec.md:71, spec.md:89 (carry of `skills/spec-reconcile/SKILL.md:29`)
**Edge case:** states.json's `namespace` doesn't match where the `plane_work_item` records live.
**What happens:** Strategy (b) of the merge-commit hunt returns empty. Masked when strategy (a) git log works; when (a) fails the user lands at the manual prompt with no hint that the configured namespace was the reason. Graceful but undebuggable as written.
**Suggested fix:** When strategy (b)'s tag search returns zero results, warn naming the namespace and tags searched. Optionally add `-i` to strategy (a)'s git log grep since the skill's own commit convention produces lowercase subjects.
**[Orchestrator note, round 1: the reviewer's live-drift claim is incorrect — states.json maps VHS → `skills`, which is where the VHS-12 record was found. The observability fix is still worth folding; the drift claim is not.]**

### F-7: Interrupted Phase 5 leaves cross-repo half-state with no documented resume path
**Severity:** P3
**Where:** spec.md:112–114 (Phase 5), spec.md:68 (Phase 0 halt-if-missing)
**Edge case:** Phase 5 dies mid-sequence after the spec file moved to DONE but before log.md/wiki writes complete.
**What happens:** Re-running with the original TODO path halts at "Confirm the spec exists; halt if not." The recovery path — re-invoke with the DONE path — is never stated.
**Suggested fix:** Failure-mode bullet: "Interrupted execute — re-run `/spec-close` with the DONE path; duplicate detection and the log guard make re-execution idempotent; archive steps skip already-moved files."

### F-8: Reconciliation-report overwrite happens with no notice line
**Severity:** P4
**Where:** spec.md:43 (Decision 4)
**Suggested fix:** One printed line when an existing report is replaced: `overwriting existing reconciliation report (was: RECONCILED: <old> DRIFT: <old-n>)`.

### F-9: Idempotency guard's em dash is encoding-fragile
**Severity:** P4
**Where:** spec.md:128, :131; carried pattern at `skills/spec-retire/SKILL.md:220`
**Edge case:** `log.md` edited by a tool that normalizes `—` (U+2014); codepage mangling on Windows.
**What happens:** The `grep -F` guard stops matching prior entries → duplicate log entries on re-run.
**Suggested fix:** Mention in failure modes that the guard depends on the literal em dash, or anchor on `close | <PROJECT>` plus the ticket-colon token.

## Summary
P0: 1 | P1: 1 | P2: 3 | P3: 2 | P4: 2

STATUS: RED P0=1 P1=1 P2=3 P3=2 P4=2
