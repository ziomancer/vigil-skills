# Spec: VHS-12 — /spec-close: single post-merge skill replacing /spec-reconcile + /spec-retire

> Brief: docs/specs/TODO/VHS-12.brief.md · Plane: VHS-12 (Backlog, medium)
> Authored: 2026-06-11 · Revised: 2026-06-11 (round-1 findings addressed)

## Goal

Replace the two-step post-merge tail (`/spec-reconcile` → `/spec-retire`) with one skill, `/spec-close <spec-path>`, that takes a merged spec from `docs/specs/TODO/` to fully closed in a single invocation: reconciliation report written, wiki entries proposed and (on confirmation) applied, artifacts archived to `DONE/<TICKET-ID>/`, wiki `log.md` appended. Partial-close is detected and **offered** when the Plane ticket isn't in a completed-group state (Decision 2). Direct slash invocations of the tail are rare (5 + 0 in three months of typed history vs. 154 `/ship-spec`), and the user confirms the two-step shape is the friction; fleet evidence (42 archived tickets in petasos alone) shows the tail's *outputs* are established conventions the merged skill must preserve (Decision 6). One invocation with one consolidated confirmation checkpoint removes the friction while preserving the read-only-analysis-then-confirmed-mutations safety split *inside* the skill.

## Scope

**Create:**
- `skills/spec-close/SKILL.md` — the merged skill (new).

**Delete:**
- `skills/spec-reconcile/SKILL.md`
- `skills/spec-retire/SKILL.md`

**Edit:**
- `CLAUDE.md` — lifecycle section `:23–31`: the intro sentence at `:23` ("Four skills form the spec lifecycle… the post-merge pair runs after code ships") becomes "Three skills form the spec lifecycle… the post-merge close runs after code ships", and items 3+4 collapse into one item 3 describing `/spec-close`; file-layout lines `:55–56` (two entries → one `skills/spec-close/SKILL.md` entry).
- `skills/ship-spec/SKILL.md` — frontmatter `description` only: pair-with text gains "after the PR merges, run /spec-close".
- `skills/spec-cycle/SKILL.md` — frontmatter `description` only: "Pair with /ship-spec …" sentence extended to name `/spec-close` as the post-merge step.

**Leave alone:**
- `sync.py` — the `skills/` subtree is mirrored wholesale; a new skill directory requires no code change. Stale installed copies of the deleted skills are removed by `python sync.py install --prune` (call this out in the PR description).
- `docs/spec-workflow-reference.md` — deliberately documents only the authoring/implementation pair; its sole post-merge mention is generic.
- `agents/*` — reviewer agents are spec-cycle's concern.
- `skills/ship-spec/states.json` — consumed as-is. **Known repo↔installed drift** (verified 2026-06-11): the committed copy maps VHS → namespace `vhs` and lacks a CLT entry, while the installed copy maps VHS → `skills` (live-correct — the VHS-12 record resides there) and includes CLT. The PR description must instruct: run `python sync.py status` and reconcile this drift (push the installed copy's newer values via `python sync.py push`) **before** running `install --prune`, or the prune clobbers the live mapping. The content fix itself is outside this spec's file scope (see Deferred).
- The wiki repo and `/wiki-after-merge` — out of scope per brief.
- Previously archived `DONE/` artifacts in any repo — already conform to the naming this spec adopts (Decision 6).

## Decisions

### Decision 1 — Supersede and delete; no deprecation shims
`/spec-close` replaces both skills, and the old skill directories are deleted in the same PR. No "this skill has moved" stub files: the repo's own review convention flags unneeded backwards-compat shims, and typed-invocation data shows no muscle memory to protect. The standalone-reconcile use case survives as `/spec-close <spec-path> --report-only`; the forced-partial case survives as `--partial`. **Rationale:** wrapping (a thin orchestrator invoking two retained skills) keeps two files plus an indirection layer and invites duplicate-phase-text findings; the public repo is cleaner with one canonical skill.

### Decision 2 — Resolve the cross-skill state-gate contradiction in favor of prompted degradation
Today the two skills contradict each other: spec-reconcile Phase 0 step 5 **hard-halts** when the Plane ticket is not in a completed/cancelled group, while spec-retire's partial-retire mode exists precisely *for* non-completed tickets — yet requires a reconciliation report that the reconcile halt prevents from existing. The merged skill resolves this with a single Plane lookup and a mode branch (Design, Phase 1): completed/cancelled → **full-close**; any other resolvable group → prompt the user to choose partial-close or abort. The hard halt is retired; the prompt preserves its intent (premature invocation is surfaced, not silently absorbed). Silent entry into partial-close survives only where no prompt is possible or the user pre-decided: the `--partial` flag and the states.json-fallback path. The brief's "partial-retire auto-detected" criterion is deliberately superseded by "detected and offered" — recorded here so the drift-check sees it.

### Decision 3 — Gate on state group resolved from the state UUID, never on `completed_at`
The mode branch matches the ticket's `state` UUID against the project's state map and reads the `group` field — the mechanism spec-retire Phase 1 already uses. `completed_at` is explicitly forbidden as a gate signal. The skill text phrases this generically (public repo): *"some Plane workspaces have non-completed states that still set `completed_at`; never use it as a gate signal."* `completed_at` remains acceptable as a *date source* for the state.md evidence triple, with the existing fallback chain (merge-commit date, then today-with-warning).

### Decision 4 — The reconciliation report is the lone pre-confirmation write
Full-close always runs reconciliation fresh and writes `<TICKET-ID>.reconciliation.md` *before* the consolidated confirmation checkpoint. Every other mutation (wiki files, state.md, archive moves, log.md) happens strictly after the user approves the close plan. **Rationale:** the report is generated audit-trail output in the target repo's `TODO/` tree — the same posture the standalone read-only reconcile skill had — and it must exist for the plan presentation to quote evidence from it. A pre-existing report at the same path is overwritten without prompting (it is generated output, not user-authored content), with a one-line notice: `overwriting existing reconciliation report (was: RECONCILED: <old> DRIFT: <old-n>)`.

### Decision 5 — Partial-close drops the reconciliation-report precondition
In partial-close mode, reconciliation phases are skipped entirely — diffing spec intent against code that may not have merged is meaningless — and the close plan contains only the archive list and the close log entry (log entry subject to wiki availability, Decision 8). If a reconciliation report already exists on disk it is archived with the other companions. This formally removes spec-retire's hard requirement on the report, which Decision 2 shows was unsatisfiable for the partial path anyway.

### Decision 6 — Archive renames to ticketless filenames, conforming to the established fleet corpus
Artifacts move to `docs/specs/DONE/<TICKET-ID>/` with the ticket prefix stripped: `<TICKET-ID>.spec.md` → `spec.md`, `<TICKET-ID>.brief.md` → `brief.md`, `<TICKET-ID>.reconciliation.md` → `reconciliation.md`, `<TICKET-ID>.reviews/` → `reviews/`, and any other companion `<TICKET-ID>.<rest>` → `<rest>` (e.g., `VHS-3.test-output.txt` → `test-output.txt`). **Rationale:** existing `DONE/` archives across target repos use ticketless names *exclusively* — petasos alone has 42 archived tickets, all ticketless, zero full-named — and spec-reconcile's DONE-path parsing already expects exactly this shape (`DONE/<TICKET-ID>/spec.md`, companions `brief.md`/`reconciliation.md`). The directory name carries the ticket ID. spec-retire's Phase 3/Phase 4 plan text listing full names was descriptive drift from actual fleet behavior; the merged skill states the rename mapping explicitly (a sanctioned edit to the carried Phase 4 text — see Decision 7). No dual-shape parsing is needed: no skill has ever produced full-named DONE artifacts, and the carried DONE-path text works unchanged.

### Decision 7 — Carry inventory, rebrand set, and sanctioned deviations
**Carried with only renumbering, pronoun, and cross-reference edits:** spec-reconcile Phase 1 (gather shipped state), Phase 2 (reconcile walk), Phase 3 (report format incl. `RECONCILED:`/`DRIFT:` trailer); spec-retire 2a (duplicate detection), 2b fast-path (VHS-9 coverage check, all three stages) and normal derivation, 2c (compile proposals), Phase 3 (confirmation block), Phase 4 (execute incl. tracked/untracked `git mv` vs `mv`+`git add` branch, log.md idempotency guard, no-commit rule). The spec deliberately does not restate those texts; the implementer copies them from the two source files at HEAD.

**Carried with merge and disposition — Tool-use notes and Failure modes.** The new skill ends with merged `## Tool-use notes` and `## Failure modes` sections built from both sources (`spec-reconcile/SKILL.md:104–118`, `spec-retire/SKILL.md:249–267`), de-duplicated, with these dispositions:
- *Carried as-is:* merge-commit-not-found fallback; large-diff summarization; Plane-ticket-not-in-MCP-memory warn-and-proceed; cross-repo-specs note; `state.md` evidence-incomplete skip-and-warn; untracked-spec-files handling; cross-repo commit discipline; the read-only-vs-mutating tool boundary (restated as "no mutation before the Phase 4 confirmation except the reconciliation report, Decision 4").
- *Reworded for the new mode logic:* spec-retire's "Plane ticket not found → default to partial-retire" becomes the partial-or-abort prompt row (Phase 1); spec-retire's "Wiki path not found → halt" becomes the per-mode behavior of Decision 8.
- *Deleted (superseded by Decisions 2/5/8):* spec-retire's "Reconciliation report missing → hard halt"; spec-reconcile's non-completed-state hard halt.
- *New bullets:* the generic `completed_at` quirk (Decision 3); state-UUID-unresolvable prompt (Phase 1 row 4); interrupted-execute recovery ("re-run `/spec-close` with the DONE path — duplicate detection, the log guard, and already-moved archive steps make re-execution idempotent"); memory-namespace observability ("when the tag search returns zero results, the warning names the namespace and tags searched — a stale states.json `namespace` is the usual cause"); the log-guard's dependence on the literal em dash in the entry format.

**Rebrand set (retire → close), exhaustive:** log entry verb and idempotency guard (`## [date] close | <PROJECT> — <TICKET-ID>: …` / `grep -F "close | <PROJECT> — <TICKET-ID>:"`); completion banner `=== CLOSE COMPLETE: <TICKET-ID> ===`; partial-mode notice ("Entering partial-close mode: …"); plan header (`=== CLOSE PLAN … ===`, Phase 4); suggested-commit prefixes `close(<ticket-lower>):`; internal flag name `force_partial_close`.

**Sanctioned behavioral deviations from the carried text (each is a deliberate fix, not drift):**
1. Idempotency guard gains a trailing colon — `grep -F "close | <PROJECT> — <TICKET-ID>:"` — so `VHS-1` cannot match `VHS-11`'s entry (the entry format guarantees the colon). Old `retire |` entries are untouched by the new guard.
2. The 2a duplicate-detection and 2b coverage greps use word-boundary matching (`grep -rlw "<TICKET-ID>"` and the `-w` equivalents) for the same prefix-collision reason — live data: `TODO/` currently holds both VHS-1 and VHS-11, and backfill will close them in arbitrary order.
3. Phase 4's archive step applies Decision 6's rename mapping (source text moved files without renaming them — or rather, listed full names while fleet behavior renamed; the mapping is now explicit).
4. Strategy (b) of the merge-commit hunt warns with the namespace and tags searched when it returns zero results; strategy (a)'s `git log --grep` gains `-i` (the skill's own `close(<ticket-lower>):` convention produces lowercase subjects).

### Decision 8 — Wiki availability is resolved per mode, before the confirmation checkpoint
The wiki is needed by: full-close (decomposition + state.md + log.md) and partial-close's log entry. It is never needed by report-only. Behavior:
- **Preflight (Phase 0 step 3):** resolve the wiki path from CLAUDE.md (username-segment substitution per spec-cycle convention); set `wiki_available` = directory exists. Missing wiki at preflight is a *warning*, not a halt.
- **Full-close requires the wiki:** at mode resolution (Phase 1), if the resolved mode would be full-close and `wiki_available` is false, present the partial-or-abort prompt with the reason (`wiki not found at <path>`) — before any report write or user-facing reconciliation work.
- **Partial-close without the wiki degrades to archive-only:** the log.md entry is dropped from the close plan with a printed notice (`wiki not found — skipping log.md entry; archive only`), and the Phase 4 confirmation block shows the omission explicitly.
- No wiki-related halt or skip decision is ever made mid-execute (Phase 5); everything is settled in the plan the user confirms.
This replaces spec-retire's unconditional wiki-missing hard halt — necessary because the merged skill has modes that can complete useful work without a wiki, and no-wiki repos are an expected configuration for public-repo consumers.

## Design

`skills/spec-close/SKILL.md`, frontmatter `name: spec-close`, `user_invocable: true`, description naming both absorbed roles and the two flags. Invoked as:

```
/spec-close <spec-path>                  # full flow
/spec-close <spec-path> --report-only    # reconciliation report only, zero mutations beyond the report
/spec-close <spec-path> --partial        # force partial-close (archive only)
```

`--report-only` and `--partial` are mutually exclusive; if both are passed, halt with a one-line usage error.

### Phase 0 — Preflight (merged)

1. Resolve `<spec-path>`; extract `ticket_id`, `project_prefix`, `issue_number`, `project_root` (spec-reconcile Phase 0 step 1 rules: TODO shape `docs/specs/TODO/<TICKET-ID>.spec.md`, DONE shape `docs/specs/DONE/<TICKET-ID>/spec.md`). Confirm the spec exists; halt if not.
2. Tracking-status check (`git ls-files --error-unmatch`) with the untracked-file notice — carried from spec-retire Phase 0 step 2a.
3. Read `<project_root>/CLAUDE.md`; resolve the wiki path and set `wiki_available` per Decision 8.
4. Read `~/.claude/skills/ship-spec/states.json` (`~/.claude/` on Unix; `%USERPROFILE%\.claude\` on Windows). On missing/invalid/prefix-not-found: warn and set `force_partial_close = true` (spec-retire's posture — Decision 2 retires reconcile's hard halt). Capture `namespace` for memory lookups when available.
5. Parse flags; apply the mutual-exclusion check.

Print a one-line preflight summary: ticket, mode hints (flags, states.json status), wiki status.

### Phase 1 — Mode resolution (single Plane lookup)

Resolution table — no silent fallthrough. Rows are evaluated top-down and the first matching row wins; in particular, `--report-only` (row 1) takes precedence over `force_partial_close` (row 2) when states.json failed at preflight:

| # | Input | Mode |
|---|---|---|
| 1 | `--report-only` flag | **report-only** — skip the Plane lookup; the report's `> Plane state:` header reads `not checked (--report-only)` when no memory record supplies it |
| 2 | `--partial` flag, or `force_partial_close` from states.json fallback | **partial-close** — print the entering-partial notice |
| 3 | Plane lookup succeeds; state group `completed` / `cancelled` | **full-close** |
| 4 | Plane lookup succeeds; state UUID absent from the state map, or `state` null | Prompt: name the unmatched UUID, suggest a states.json refresh → `1. Partial-close (archive only)  2. Abort` |
| 5 | Plane lookup succeeds; any other resolvable group | Print current state and group → same partial-or-abort prompt ("I invoked this prematurely" exits via Abort) |
| 6 | Plane unreachable / ticket not found | Warn → same partial-or-abort prompt (the safer path) |
| 7 | Resolved mode would be full-close but `wiki_available` is false | Same partial-or-abort prompt with reason `wiki not found at <path>` (Decision 8) — checked after rows 3–6 |
| 8 | Partial-close (any row) and `wiki_available` is false | Proceed; log.md entry dropped from the plan with printed notice (Decision 8) |

The Plane mechanics are spec-retire Phase 1's: state-list capability + work-item lookup by `project_identifier`/`issue_number`, group resolved from the state UUID (Decision 3).

### Phase 2 — Reconciliation (full-close and report-only)

Skipped in partial-close. Otherwise: spec-reconcile Phases 1–3 carried per Decision 7 — find merge commit(s) (`git log --grep` → memory tag-lookup → user prompt), read the shipped diff (`gh pr view/diff` or `git show`), read the companion brief (`<TICKET-ID>.brief.md` for TODO paths, `brief.md` for DONE paths), walk Scope/Decisions/Acceptance/Test-plan, write the reconciliation report next to the spec (`<TICKET-ID>.reconciliation.md` for TODO paths, `reconciliation.md` for DONE paths) with the `RECONCILED: <yes|no> DRIFT: <n>` trailer and the Decision 4 overwrite notice when replacing an existing report.

- **report-only mode ends here**, printing the report path and a pointer to re-run without the flag to complete the close.
- `RECONCILED: no` → soft halt (spec-retire Phase 0 step 4 wording): `Spec has unmet acceptance criteria. … Continue anyway? [y/N]`. Halt on N.

### Phase 3 — Wiki analysis (full-close only)

spec-retire Phase 2 carried per Decision 7: 2a duplicate detection → 2b coverage fast-path (VHS-9) then scoped/normal derivation → 2c compile proposals — with the `-w` grep deviation (Decision 7 §deviations 2). Partial-close skips to Phase 4 with proposals = archive list + log entry (or archive list only, Decision 8 row 8).

### Phase 4 — Consolidated confirmation

One checkpoint, spec-retire Phase 3 format extended with a reconciliation summary header:

```text
=== CLOSE PLAN: <TICKET-ID> ===
Mode: <full-close | partial-close>
Reconciliation: <RECONCILED: yes|no, DRIFT: n | skipped (partial)>
Wiki: <available | not found — log.md entry omitted>
<wiki entries / state.md / archive / log.md blocks as in spec-retire Phase 3,
 archive block showing the Decision 6 rename mapping per file>
Proceed? [y/N]
```

Halt on N with zero post-report mutations.

### Phase 5 — Execute

spec-retire Phase 4 carried per Decision 7 (tracked/untracked branch, log.md idempotency guard with the trailing-colon deviation, no commits in either repo), applying Decision 6's rename mapping in the archive step and the rebrand set (banner, log verb, commit prefixes). Two clarifications of how the carry is realized:

- The rebrand applies to *all* retire-era strings in carried prose, including the mode names — `full-retire` → `full-close`, `partial-retire` → `partial-close`, "retirement log entry" → "close log entry" — wherever they appear in the carried 2b/2c/confirmation/execute text, not only the six items enumerated in Decision 7.
- The per-artifact archive loop skips artifacts whose source path no longer exists, printing `already archived: <name>` — this is what makes the interrupted-execute recovery promised in Decision 7's failure-mode bullets actually implementable (a re-run with sources already moved must not fail at `mv`).

The archive list includes the freshly written reconciliation report.

### Cross-reference edits

- `CLAUDE.md:23–31`: intro sentence rewritten ("Three skills form the spec lifecycle… the post-merge close runs after code ships:"); items 3+4 become one item 3 describing `/spec-close` with both flags and the detected-and-offered partial behavior.
- `CLAUDE.md:55–56`: single file-layout line for `skills/spec-close/SKILL.md`.
- `skills/ship-spec/SKILL.md` frontmatter description: append "After the PR merges, run /spec-close to reconcile and retire the spec."
- `skills/spec-cycle/SKILL.md` frontmatter description: extend the pairing sentence to name `/spec-close` as the post-merge close step.

## Test plan

Doc-only spec (markdown skill files + CLAUDE.md); per the VHS-7 convention the gate is a review checklist:

- [ ] `skills/spec-close/SKILL.md` exists; frontmatter has `name: spec-close`, `user_invocable: true`; both flags documented in the invocation block with the mutual-exclusion rule.
- [ ] Every phase in Decision 7's carried inventory appears with content matching its source at HEAD, modulo the enumerated rebrand set, the four sanctioned deviations, and the two Phase 5 carry clarifications (mode-name rebrand sweep; skip-if-source-missing) (spot-check: VHS-9 fast-path stages 1–3 present; tracked/untracked archive branch present).
- [ ] No `full-retire`, `partial-retire`, or "retirement log entry" strings remain anywhere in `skills/spec-close/SKILL.md` — carried prose uses the close-era mode names consistently.
- [ ] Mode-resolution table covers all eight rows of Phase 1 — including state-UUID-unresolvable (row 4) and both wiki-missing rows (7, 8) — with no silent fallthrough.
- [ ] Idempotency guard is `grep -F "close | <PROJECT> — <TICKET-ID>:"` (trailing colon); 2a/2b greps use `-w`; log entry format is `## [date] close | <PROJECT> — <TICKET-ID>: …`.
- [ ] Archive step states the Decision 6 rename mapping (spec.md / brief.md / reconciliation.md / reviews/ / generic `<rest>` rule); the Phase 4 plan block previews the mapping per file.
- [ ] Merged `## Tool-use notes` and `## Failure modes` sections exist; failure modes include the generic `completed_at` bullet (no internal project references), interrupted-execute recovery, the namespace-zero-result warning, and the em-dash dependence note; the two superseded halts (report-missing, wiki-missing-unconditional) do **not** appear.
- [ ] The skill nowhere uses `completed_at` as a gate signal.
- [ ] `skills/spec-reconcile/` and `skills/spec-retire/` directories deleted; `grep -ri "spec-reconcile\|spec-retire" CLAUDE.md README.md docs/customizing.md skills/ agents/` returns **zero matches** (historical mentions live only under `docs/specs/`, which is deliberately outside the searched paths).
- [ ] `CLAUDE.md:23` intro reads "Three skills…"; the lifecycle list has exactly three numbered items and still states all mutations require confirmation.
- [ ] `python sync.py status` lists the new skill as pending-install and the deletions as prune candidates; PR description tells installers to run `python sync.py status` first, reconcile any `states.json` repo↔installed drift (push the installed copy's newer values), and only then `python sync.py install --prune`.

## Test command

N/A

## Done when

- One invocation takes a merged spec from `TODO/` to fully closed: reconciliation report written, wiki proposals confirmed and applied, artifacts archived to `DONE/<TICKET-ID>/`, `log.md` appended; partial-close detected and offered when the Plane ticket isn't completed (Decision 2 supersedes the brief's "auto-detected" wording — prompted, not silent). *(brief: Done-when 1)*
- Read-only analysis and confirmed mutations remain strictly ordered; the reconciliation report is the only pre-confirmation write (Decision 4). *(brief: Done-when 2)*
- `--report-only` preserves the standalone-reconcile use case. *(brief: Done-when 3)*
- CLAUDE.md (including the `:23` intro) and the spec-cycle/ship-spec pair-with descriptions reference `/spec-close` consistently; no dangling references to the deleted skills outside `docs/specs/`. *(brief: Done-when 4)*
- `python sync.py status` clean after install; installed copies round-trip via `sync.py push`. *(brief: Done-when 5)*

## Out of scope

- Changes to `/spec-cycle` or `/ship-spec` beyond frontmatter description text.
- Any change to `/wiki-after-merge` (internal wiki repo).
- Auto-running spec-close (hooks, SessionStart scans, reminders).
- Backfilling the existing unretired VHS/other-project specs — operational follow-up once the skill ships.
- Renaming or reshaping previously archived `DONE/` artifacts (they already match Decision 6's convention).
- `sync.py` code changes.

## Deferred (P2+)

- *conventions/R1/F-6 (P3)* — informational inventory of spec-level additions for the drift-check; no spec change required, the additions are now each named in their Decision.
- *edge-cases/R1/F-6 (P3), factual sub-claim — corrected in round 2:* the round-1 drift assertion was **correct for the committed copy**: `skills/ship-spec/states.json:53` (repo) maps VHS → `vhs`, while the *installed* copy (`~/.claude/skills/ship-spec/states.json`) maps VHS → `skills` — which is where the VHS-12 record actually lives, so the installed copy is live-correct and the repo copy is stale (it also lacks the CLT entry). The observability fix was folded (Decision 7 §deviations 4); the drift-reconciliation instruction was folded into Scope and the test plan.
- *correctness/R2/F-1 + edge/R2/F-2 + conventions/R2/F-1 (P2, merged), residual* — the one-line repo `states.json` content fix (`vhs` → `skills`, plus the missing CLT entry) is **new file scope** and is not added to this spec post-green; the Scope/PR-description reconciliation instruction (folded) prevents the clobber. Resolve the drift via `python sync.py push` before or alongside the ship-spec PR.
- *edge/R2/F-4 (P3)* — ticket-ID prefix collision also affects merge-commit strategy (a); implementer may use `git log --all --oneline -i -E --grep="<TICKET-ID>([^0-9]|$)"` or filter the oneline output to exact-ID matches before selecting.
- *correctness/R2/F-3 (P3)* — prefer the plain label "Partial-close" in the invocation comment and prompt options; "(archive only)" is Decision 8 row 8's degraded shape, not the normal partial-close (which includes the close log entry).
- *conventions/R2/F-2 (P3)* — informational: Decision 8 is a category-(c) spec-level addition; listed for the drift-check.
- *correctness/R2/F-4 (P4)* — deviation 4's `-i` rationale should cite ship-spec's `<type>(<ticket-lower>):` commit convention as the primary lowercase producer (the skill's own `close(…)` commits are the re-run case).
- *edge/R2/F-5 (P4)* — a prior partial-close log entry suppresses the later full-close entry by design (idempotency guard matches on ticket); implementer may note this in failure modes or distinguish `close(partial) |` entries.
- *edge/R2/F-6 (P4)* — when `<wiki_root>/log.md` does not exist (fresh wiki), the guard treats it as not-present and creates the file on append.

## Post-green polish

Folded per skill step 2g (clarifications only; the green verdict stands):

- *correctness/R2/F-1 (part) + edge/R2/F-2 + conventions/R2/F-1 (P2)* — Deferred rebuttal corrected to state both states.json copies' values; drift-reconciliation instruction added to Scope's states.json bullet and the test-plan sync row. The repo-copy content fix itself is deferred (new scope — see Deferred).
- *correctness/R2/F-2 (P2)* — Phase 5 carry clarification: the rebrand sweep explicitly covers mode-name strings in carried prose; backstop checklist row added. (Decision 7's enumeration itself left untouched per 2g limits.)
- *edge/R2/F-1 (P2)* — Phase 5 carry clarification: per-artifact archive loop skips missing sources with `already archived: <name>` — realizes the recovery behavior Decision 7's failure-mode bullet already promised, resolving the internal contradiction; checklist row updated.
- *correctness/R2/F-5 + edge/R2/F-3 (P3/P4)* — Phase 1 wording: rows evaluated top-down, first match wins, `--report-only` over `force_partial_close` (fixes the internally false "exactly one row" claim).
- *conventions/R2/F-3 (P4)* — evidence-citation numeral corrected 43 → 42 (Goal and Decision 6; citation correction, not a decision change).
