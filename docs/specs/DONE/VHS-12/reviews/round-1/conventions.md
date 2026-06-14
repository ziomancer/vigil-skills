# Conventions Review — round 1

## Closure of round 0 findings
N/A — round 1.

## Findings

### F-1: CLAUDE.md edit anchor `:25–31` misses the "Four skills" intro sentence at line 23
**Severity:** P2
**Pre-ship recommended:** yes
**Where:** spec.md:20, spec.md:118 (§ Cross-reference edits)
**Convention violated:** Done-when 4 / test-plan item "CLAUDE.md lifecycle reads as three steps" — the spec's own anchor excludes a required edit.
**Evidence:** `CLAUDE.md:23` reads "Four skills form the spec lifecycle. …the post-merge pair runs after code ships:". Both "Four skills" and "the post-merge pair" must change, but the spec scopes the lifecycle edit to `:25–31`. The test-plan grep cannot catch this because the sentence contains neither skill name.
**Suggested fix:** Widen the anchor to `CLAUDE.md:23–31` and explicitly state the intro rewrite.

### F-2: Decision 6 hedges "if any exist" — 43 ticketless-name archives exist; the spec is superseding the dominant de facto shape without saying so
**Severity:** P2
**Pre-ship recommended:** yes
**Where:** spec.md:49 (§ Decision 6), spec.md:154 (§ Out of scope)
**Convention violated:** "Always verify load-bearing claims against the actual codebase" (CLAUDE.md § Plan & Spec Reviews).
**Evidence:** `petasos\docs\specs\DONE\` contains **43** archived tickets, **all** ticketless (`spec.md`, `reconciliation.md`, `brief.md`, `reviews/`), **zero** full-named files. The wiki `log.md` carries matching `retire | PET/DYN/ADA` entries — the tail flow has run fleet-wide despite the brief's 0-invocation count for this repo's history. So (a) dual-shape read acceptance is load-bearing, not speculative, and (b) Decision 6 switches the write convention against a 43:0 corpus.
**Suggested fix:** Replace the hedge with the fact, state explicitly that full names supersede the de facto shape going forward (or conform to it), and confirm the dual-shape parser is required.

### F-3: Decision 7's verbatim inventory omits both skills' "Tool-use notes" and "Failure modes" sections — and several carried bullets contradict Decisions 2/5
**Severity:** P2
**Pre-ship recommended:** yes
**Where:** spec.md:51–52 (§ Decision 7), spec.md:130 (test plan)
**Evidence:** An implementer copying exactly the inventory ships a skill with no Tool-use notes and no Failure modes — yet the test plan requires a failure-mode bullet. A naive verbatim copy of the failure modes would reintroduce text Decisions 2/5 retire: `skills/spec-retire/SKILL.md:260` (report-missing hard halt), `:263` (wiki-missing unconditional halt), and spec-reconcile's non-completed-state halt rationale (`skills/spec-reconcile/SKILL.md:19`).
**Suggested fix:** Extend Decision 7 with the merged Tool-use notes + Failure modes and per-bullet disposition: carried as-is, reworded, or deleted.

### F-4: "partial-close auto-detected" (Goal, Done-when 1) no longer describes the designed behavior after Decision 2
**Severity:** P2
**Pre-ship recommended:** yes
**Where:** spec.md:8 (§ Goal), spec.md:142 (§ Done when), vs. spec.md:37 (Decision 2) and spec.md:84 (Phase 1)
**Evidence:** The brief's "partial-retire auto-detected" referenced spec-retire Phase 1's silent auto-entry. Decision 2 deliberately replaces that with a partial-or-abort prompt for non-completed groups; silent auto-entry survives only on the states.json-fallback/`--partial` path. Goal and Done-when 1 still echo the old wording.
**Suggested fix:** Reword Goal and Done-when 1 to "partial-close detected and offered when the Plane ticket isn't completed (Decision 2)."

### F-5: retire→close rebrand edits inside "verbatim" text are only partially enumerated
**Severity:** P3
**Where:** spec.md:114 (Phase 5), spec.md:131 (test plan), spec.md:80 (Phase 1)
**Evidence:** The `close |` log verb + idempotency guard appear only in the test plan — Phase 5 names only the commit-prefix swap. Unmentioned: the `=== RETIREMENT COMPLETE ===` banner (`skills/spec-retire/SKILL.md:231`), the "Entering partial-retire mode" notice (`:30`).
**Suggested fix:** Enumerate the rebrand set in Phase 5 or Decision 7: log verb + guard, completion banner, partial-mode notice, plan header, commit prefixes.

### F-6: Spec-level additions with rationale — surfaced for the human drift-check
**Severity:** P3
**Where:** spec.md:36–49 (Decisions 2, 4, 5, 6)
**Evidence:** Decisions 2, 4, 5, 6 are category-(c) additions: positions the brief doesn't explicitly authorize, each with stated rationale. Decisions 1 and 3 are brief-authorized.
**Suggested fix:** None required — listed for the drift-check.

### F-7: Phase 0 step 4 drops the canonical states.json path and the Windows-path parenthetical
**Severity:** P3
**Where:** spec.md:71 (Phase 0 step 4)
**Convention violated:** VHS-7 host-agnostic convention — both source skills state the full path with OS parentheticals.
**Suggested fix:** Restate the path with the OS parenthetical or cite spec-retire Phase 0 step 6 as the carried source.

### F-8: The completed_at-quirk failure-mode bullet should be phrased generically in the public skill
**Severity:** P3
**Where:** spec.md:130 (test plan)
**Convention violated:** Public-repo rule (vigil-skills is public; keep internals out).
**Suggested fix:** Generic phrasing: "some Plane workspaces have non-completed states that still set `completed_at`; never use it as a gate signal."

### F-9: `force_partial_retire` variable name keeps the retired verb
**Severity:** P4
**Where:** spec.md:71, spec.md:80
**Suggested fix:** Rename to `force_partial_close` in the new skill.

### F-10: Test-plan grep expectation is internally muddled
**Severity:** P4
**Where:** spec.md:132
**Evidence:** `docs/specs/` is not among the searched paths, so the command can never return mentions inside it. Verified: outside `docs/specs/` and the two to-be-deleted skill dirs, only `CLAUDE.md:29,31,55,56` match.
**Suggested fix:** Reword to "returns zero matches."

## Summary
P0: 0 | P1: 0 | P2: 4 | P3: 4 | P4: 2

Notes on what checked out clean: Decision 3 exactly follows the recorded memory/wiki posture; Decision 1's delete-no-shims aligns with the repo's backwards-compat stance and the brief's open question; synchronous plane-proxy state lookup matches prior art and the webhook-pivot decision's correctness-critical exception; `sync.py --prune` exists as claimed; `docs/spec-workflow-reference.md` leave-alone is sound; no premature abstractions; wiki lint/SCHEMA have no coupling to the `retire |` log verb, so the `close |` swap is safe wiki-side.

STATUS: GREEN
