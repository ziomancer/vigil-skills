---
name: spec-close
description: Close a shipped spec in one pass — diff it against shipped code (reconciliation report), decompose into wiki entries (decisions, comprehension, state.md updates), archive spec artifacts from TODO/ to DONE/, and append to wiki log.md. Plane state gates full-close vs partial-close; --report-only writes just the report, --partial archives without wiki decomposition. Supersedes the former two-step reconcile/retire flow. Pair with /spec-cycle and /ship-spec for the full spec lifecycle.
user_invocable: true
---

Invoked as:

```
/spec-close <spec-path>                  # full flow
/spec-close <spec-path> --report-only    # reconciliation report only, zero mutations beyond the report
/spec-close <spec-path> --partial        # force partial-close (skip reconciliation and wiki decomposition)
```

`--report-only` and `--partial` are mutually exclusive. If both are passed, halt with: `Usage: --report-only and --partial are mutually exclusive — pick one.`

The skill preserves the read-only-analysis-then-confirmed-mutations split internally: everything before the Phase 4 confirmation is analysis, with one exception — the reconciliation report, which is generated audit-trail output written before the checkpoint so the close plan can quote evidence from it. Every other mutation (wiki files, state.md, archive moves, log.md) happens strictly after the user approves the plan.

## Phase 0 — Preflight

1. Resolve `<spec-path>`. Expected shapes: `docs/specs/TODO/<TICKET-ID>.spec.md` or `docs/specs/DONE/<TICKET-ID>/spec.md`. Extract `ticket_id` (uppercase): from TODO paths, the filename stem before `.spec.md`; from DONE paths, the parent directory name. Derive `project_prefix` (portion before the first hyphen, e.g., `ADA` from `ADA-17`) and `issue_number` (integer portion after the hyphen, e.g., `17`). Set `project_root` to the repo root (the directory containing `CLAUDE.md`). Confirm the spec exists. Halt if not.
2. Check tracking status: `git ls-files --error-unmatch <spec-path> 2>/dev/null`. If exit ≠ 0 (file is untracked/gitignored), print:
   `Note: Spec file is untracked (gitignored). Archive step will use mv + git add instead of git mv.`
   Continue regardless — the file exists on disk, which is sufficient.
3. Read `<project_root>/CLAUDE.md`. Resolve the wiki path (resolve username-bearing paths per spec-cycle convention: replace the username segment with the current user — Windows: `$env:USERNAME`; Unix: `$USER` — and re-check). Set `wiki_available` = the wiki directory exists. A missing wiki here is a **warning**, not a halt — Phase 1 applies the per-mode behavior (rows 7–8).
4. Read `~/.claude/skills/ship-spec/states.json` (`~/.claude/` on Unix; `%USERPROFILE%\.claude\` on Windows). Handle failure modes — all warn and set `force_partial_close = true` (Plane lookups cannot proceed without `project_id`):
   - **File missing or unreadable:** Warn: `states.json missing or unreadable — skipping Plane state gate, entering partial-close mode.`
   - **Invalid JSON:** Warn: `states.json contains invalid JSON — skipping Plane state gate, entering partial-close mode.`
   - **Prefix not found:** Warn: `Project prefix "<project_prefix>" not found in states.json. Skipping Plane state gate — entering partial-close mode.`
   Otherwise capture `project_id`, `namespace`, and the states map.
5. Parse flags. Apply the mutual-exclusion check above. `--partial` sets `force_partial_close = true`.

Print a one-line preflight summary (ticket, flags, states.json status, wiki status), then continue.

## Phase 1 — Mode resolution

One Plane lookup decides the mode. Rows are evaluated **top-down and the first matching row wins** — in particular, `--report-only` (row 1) takes precedence over `force_partial_close` (row 2):

| # | Input | Mode |
|---|---|---|
| 1 | `--report-only` flag | **report-only** — skip the Plane lookup; the report's `> Plane state:` header reads `not checked (--report-only)` unless a memory record supplies it |
| 2 | `force_partial_close` (from `--partial` or a states.json failure) | **partial-close** — print: `Entering partial-close mode: archiving spec artifacts only, skipping reconciliation and wiki decomposition.` |
| 3 | Plane lookup succeeds; state group `completed` or `cancelled` | **full-close** |
| 4 | Plane lookup succeeds; ticket's state UUID absent from the state map, or `state` is null | Prompt, never infer a group — **missing UUID:** name the unmatched UUID and suggest a states.json refresh; **null state:** report that the ticket has no state UUID and suggest a states.json refresh. Either branch: `1. Partial-close  2. Abort` |
| 5 | Plane lookup succeeds; any other resolvable group | Print the current state name and group, then the same partial-or-abort prompt ("I invoked this prematurely" exits via Abort) |
| 6 | Plane unreachable or ticket not found | Warn, then the same partial-or-abort prompt (the safer path) |
| 7 | Resolved mode would be full-close but `wiki_available` is false | Same partial-or-abort prompt with reason `wiki not found at <path>` — checked after rows 3–6, before any reconciliation work |
| 8 | Partial-close (via any row) and `wiki_available` is false | Proceed; the log.md entry is dropped from the close plan with a printed notice: `wiki not found — skipping log.md entry; archive only` |

Plane mechanics (rows 3–6): call the plane-proxy's state-list capability (e.g., `mcp__plane__list_states` in Claude Code, or the equivalent in your host's Plane integration) with `project_id` to get the full state map with groups. Look up the ticket via the plane-proxy's work-item-lookup capability (e.g., `mcp__plane__retrieve_work_item_by_identifier`, or the equivalent in your host) with `project_identifier` and `issue_number` (pass `issue_number` as integer). Match the ticket's `state` UUID against the state map to determine the group.

**Never use `completed_at` as a gate signal** — some Plane workspaces have non-completed states that still set `completed_at`. The state UUID → group match is the only gate. (`completed_at` remains acceptable later as a *date source* for the state.md evidence triple.)

## Phase 2 — Reconciliation (full-close and report-only)

Skipped entirely in partial-close — diffing spec intent against code that may not have merged is meaningless. If a reconciliation report already exists on disk in partial-close, it is archived with the other companions in Phase 5.

### 2a. Gather shipped state

Goal: identify what code actually shipped for this ticket.

1. **Find the merge commit(s).** Three strategies, tried in order:
   a. `git log --all --oneline -i -E --grep="<TICKET-ID>([^0-9]|$)" -- .` — matches commit messages containing the ticket ID. Case-insensitive because conventional-commit subjects lowercase the ticket ID (ship-spec's `<type>(<ticket-lower>):` prefix is the primary producer; this skill's own `close(<ticket-lower>):` commits appear on re-runs). The `([^0-9]|$)` suffix prevents prefix collisions — `VHS-1` must not match `VHS-11`'s commits.
   b. Look up the Plane ticket via the MCP memory server's search capability (e.g., `mcp__claude_ai_Vigil_Harbor_MCP_Server__memory_search` in Claude Code, or the equivalent semantic-search tool in your host) with `tags: ["plane_work_item", "<TICKET-ID>"]`, `namespace` from preflight. Parse the description for PR references (`PR #N`, `#N`, `github.com/.../pull/N`). If the search returns zero results, warn naming what was searched: `no plane_work_item record for <TICKET-ID> in namespace "<namespace>" — states.json namespace may be stale.`
   c. If neither yields results, prompt the user: `Could not find merge commit for <TICKET-ID>. Enter PR number or commit SHA:`

2. **Read the shipped diff.** Branch on identifier type:
   - **PR number:** `gh pr view <N> --json files,additions,deletions` for file-level diff stat, then `gh pr diff <N>` for full diff content.
   - **Commit SHA:** `git show --stat <SHA>` for file-level diff stat, then `git show <SHA>` for full diff content.
   If the diff is large (>500 lines), summarize by file rather than reading every line — focus grep on the specific code paths the spec's decisions describe.

3. **Read the spec's companion brief** at the same directory as the spec (`<TICKET-ID>.brief.md` for TODO paths, `brief.md` for DONE paths), if it exists. The brief's acceptance criteria are the primary reconciliation targets.

### 2b. Reconcile

Walk the spec section by section:

1. **Scope (files changed).** Compare the spec's "Scope" or "Edit" section against the PR's actual diff stat. For each file the spec says to change: confirm it appears in the diff. For each file in the diff that the spec doesn't mention: flag as "Added (not in spec)." For each file the spec mentions but the diff doesn't touch: flag as "Dropped."

2. **Decisions.** For each `### Decision` in the spec: read the relevant code (using the file paths from the diff) and confirm the decision is reflected. Use grep/file reads, not inference. Mark each as: Confirmed (code matches), Drifted (code diverges — describe how), or Unverifiable (decision is about behavior/performance, not structure).

3. **Acceptance criteria.** For each "Done when" bullet in the spec (or "Acceptance" in the brief): produce a grep or file-read that confirms the criterion is met. Mark as: Met (with evidence), Unmet (with explanation), or Unverifiable.

4. **Test plan.** Check whether the tests described in the spec's "Test plan" section exist in the codebase. Grep for test file names, function names, or describe blocks.

### 2c. Report

Write the reconciliation report alongside the spec. If the spec is at `docs/specs/TODO/<TICKET-ID>.spec.md`, write to `docs/specs/TODO/<TICKET-ID>.reconciliation.md`. If the spec is at `docs/specs/DONE/<TICKET-ID>/spec.md`, write to `docs/specs/DONE/<TICKET-ID>/reconciliation.md`.

If a report already exists at the target path, overwrite it (it is generated output, not user-authored content) and print one line first: `overwriting existing reconciliation report (was: RECONCILED: <old> DRIFT: <old-n>)`.

Report format:

```markdown
# Reconciliation Report: <TICKET-ID>

> Date: YYYY-MM-DD
> Spec: docs/specs/TODO/<TICKET-ID>.spec.md
> Merge: <PR number or commit SHA>
> Plane state: <state_name> (group: <group>)

## Summary
<1-2 sentences: overall reconciliation status.>

## Scope
| Spec file | In diff? | Notes |
|---|---|---|
| `path/to/file.ts` | Yes | As specified |
| `path/to/other.ts` | No | Dropped — <reason> |

Unexpected files in diff (not in spec):
- `path/to/surprise.ts` — <what it does>

## Decisions
| # | Decision | Status | Evidence |
|---|---|---|---|
| 1 | <title> | Confirmed | `file:line` — '<excerpt>' |
| 2 | <title> | Drifted | <explanation> |

## Acceptance Criteria
| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | <criterion> | Met | `file:line` — '<excerpt>' |
| 2 | <criterion> | Unmet | <explanation> |

## Test Plan
| Test | Exists? | Location |
|---|---|---|
| <test description> | Yes | `path/to/test.ts:line` |

## Wiki-ready
Decisions and comprehension worth extracting to the wiki:
- <Decision N>: <why it's wiki-worthy — non-obvious, reusable, or constraining>
- <Comprehension>: <what changed and why, for the comprehension layer>

RECONCILED: <yes|no> DRIFT: <n>
```

The `RECONCILED: yes` status requires: all acceptance criteria Met or Unverifiable, zero Unmet. Drifted decisions alone don't block — drift is informational. `DRIFT: <n>` counts Drifted + Dropped + Unexpected items.

**report-only mode ends here.** Print the report path and a pointer: `Re-run /spec-close <spec-path> (without --report-only) to complete the close.`

**`RECONCILED: no` soft halt.** Warn: `Spec has unmet acceptance criteria. Review the reconciliation report before proceeding. Continue anyway? [y/N]`. Halt on N.

## Phase 3 — Wiki analysis (full-close only)

Partial-close skips to Phase 4 with proposals = archive list + close log entry (or archive list only, Phase 1 row 8).

### 3a. Duplicate detection

Search the wiki for existing entries related to this ticket:

```bash
grep -rlw "<TICKET-ID>" "<wiki_root>/decisions/" "<wiki_root>/comprehension/"
grep -rli "<key-terms>" "<wiki_root>/decisions/" "<wiki_root>/comprehension/"
```

The `-w` (word-boundary) flag on the ticket-ID grep prevents prefix collisions — `VHS-1` must not match files mentioning only `VHS-11`. `<key-terms>` are 2-3 distinctive words from the spec's Goal section (not common words like "fix" or "update").

If matches found, read each matched file's title and first paragraph. Present to user:
```text
Pre-existing wiki entries found:
  1. decisions/2026-05-06-dyn-34-score-calibration-pipeline.md — "Decision: DYN-34a score calibration pipeline"
  2. comprehension/2026-05-06-dyn-34b-ui-calibration-overlay.md — "Comprehension: DYN-34b calibration UI overlay"

These may already cover some or all of the spec's content.
Duplicates will be excluded from wiki proposals below.
```

Track matched ticket IDs and decision titles as an exclusion list for Phase 3b.

### 3b. Wiki decomposition

#### Fast-path: check existing wiki coverage

Before drafting any wiki proposals, check whether `/wiki-after-merge` has already created wiki entries for this ticket. This is a grep-based pre-check (no LLM analysis) that can skip or narrow the derivation pipeline.

**Stage 1 — Determine applicable derivation categories.**

Extract the `## Wiki-ready` section from the reconciliation report, then grep for category markers within that section only (scoping avoids false positives from the `## Decisions` table header):

```bash
sed -n '/^## Wiki-ready/,/^##\|^RECONCILED/p' "<reconciliation_report_path>" > /tmp/wiki-ready-section.txt
grep -c "Decision" /tmp/wiki-ready-section.txt
grep -c "Comprehension" /tmp/wiki-ready-section.txt
```

Classify applicability:

| Category | Applicable when |
|----------|----------------|
| `comprehension/` | Wiki-ready section contains "Comprehension" (grep count > 0) |
| `decisions/` | Wiki-ready section contains "Decision" (grep count > 0) |
| `state.md` "What's Shipped" | Always (evidence triple is mandatory for full-close) |

If the reconciliation report has no `## Wiki-ready` section (sed produces empty output), treat all categories as applicable and fall through to normal derivation.

Note: `log.md` is not included in the coverage model. The close log entry is a distinct event from the merge log entry that wiki-after-merge writes. Phase 3c always compiles a close log entry, and Phase 5's idempotency guard (`grep -F "close | <PROJECT> — <TICKET-ID>:"`) prevents duplicates while allowing the close entry to coexist with wiki-after-merge's merge entry.

**Stage 2 — Check existing coverage.**

For each applicable category, run a targeted grep with echo delimiters for unambiguous per-category classification:

```bash
echo "::COMP::"; grep -rlw "<TICKET-ID>" "<wiki_root>/comprehension/" 2>/dev/null
echo "::DECI::"; grep -rlw "<TICKET-ID>" "<wiki_root>/decisions/" 2>/dev/null
echo "::STATE::"; grep -rlw --include="state.md" "<TICKET-ID>" "<wiki_root>/projects/" 2>/dev/null
```

Run all applicable greps in a single Bash call (semicolon-separated). Classify each applicable category by checking the output between its delimiter and the next: non-empty output after the delimiter = `covered`, no output after the delimiter = `missing`.

**Stage 3 — Branch on coverage level.**

1. **Full coverage** (all applicable categories are `covered`):

   Print a summary of what was found (only list applicable categories):
   ```text
   Wiki coverage already exists (likely created by /wiki-after-merge):
     [found] comprehension/ — <matched-filename>
     [found] decisions/ — <matched-filename>
     [found] state.md — entry found

   All derivation categories covered. Skip wiki proposal derivation? [y/N]
   ```

   - On `y`: set derivation proposals to empty (no decisions, no comprehension, no state.md edit). Proceed to Phase 3c, which still compiles the archive list and the close log entry.
   - On `N`: fall through to the normal derivation flow.

2. **Partial coverage** (some applicable categories are `covered`, some are `missing`):

   Print what's covered and what's missing:
   ```text
   Partial wiki coverage found:
     [found]   comprehension/ — <matched-filename>
     [missing] decisions/ — not found
     [found]   state.md — entry found

   Deriving proposals for missing categories only.
   ```

   Then run the normal derivation logic below, but scoped to only the `missing` categories. Read all necessary inputs (reconciliation report, spec) as usual — only the drafting/proposal step is scoped to missing categories. The Phase 3a exclusion list still applies within the derivation scope.

3. **No coverage** (no applicable categories are `covered`):

   No output from the fast-path. Fall through to the normal derivation flow unchanged.

#### Normal derivation (when fast-path does not fully exit)

1. Read the reconciliation report's "Wiki-ready" section and the spec's "Decisions" sections.
2. For each decision worth extracting (non-trivial, reusable, or constraining — skip implementation-detail decisions like "use `git mv` not `mv`"):
   - Check against the duplicate exclusion list. Skip if covered.
   - Draft a wiki decision entry following SCHEMA.md's standard or multi-judgment format. Include: Context (from spec's Goal), Options Considered (from spec's Decision rationale), Decision (what was chosen), Consequences, Related links.
3. If the spec describes a significant architectural change (new module, new data flow, new integration):
   - Draft a comprehension entry following SCHEMA.md's template. Include: What Changed, Why, What Would Break, Files Touched, Judgment Calls.
4. For `state.md` updates:
   - If the ticket was in "What's Next" or "What's Active", propose moving it to "What's Shipped" with the evidence triple:
     ```markdown
     ### <Title> (<TICKET-ID>, <ship-date>, commit <merge-sha>)
     Verification: <file>:<line> -- '<excerpt>'.
     ```
   - The ship date: try `completed_at` from the Plane ticket first (date source only — never a gate signal); if null, fall back to the merge commit date from `git log --format=%ci <merge-sha>`, then to today's date as last resort (with a warning). The merge SHA comes from the reconciliation report. The verification line comes from the reconciliation report's acceptance criteria evidence.

### 3c. Compile proposals

Collect all proposed actions into a single summary:
- Wiki decisions to create (with filenames and content previews)
- Wiki comprehension entries to create
- `state.md` edits (as diffs)
- Files to archive (list of `TODO/` -> `DONE/` moves, showing the rename mapping per file)
- `log.md` entry (full text)

For partial-close, this section contains only the archive list and the log.md entry (or the archive list alone when the wiki is unavailable, Phase 1 row 8).

## Phase 4 — Consolidated confirmation

One checkpoint covers every post-report mutation. Present the compiled proposals:

```text
=== CLOSE PLAN: <TICKET-ID> ===
Mode: <full-close | partial-close>
Reconciliation: <RECONCILED: yes|no, DRIFT: n | skipped (partial-close)>
Wiki: <available | not found — log.md entry omitted>

Wiki entries to create:
  1. decisions/YYYY-MM-DD-<slug>.md — "<title>"
     <3-line preview>
  2. comprehension/YYYY-MM-DD-<slug>.md — "<title>"
     <3-line preview>

State.md update:
  File: projects/<project>/state.md
  Move "<Title>" from What's Active → What's Shipped
  Evidence: (<TICKET-ID>, YYYY-MM-DD, commit <SHA>)

Archive (TODO/ → DONE/<TICKET-ID>/, ticket prefix stripped):
  - <TICKET-ID>.spec.md → spec.md
  - <TICKET-ID>.brief.md → brief.md
  - <TICKET-ID>.reconciliation.md → reconciliation.md
  - <TICKET-ID>.reviews/ → reviews/ (N files)

Log.md append:
  ## [YYYY-MM-DD] close | <PROJECT> — <TICKET-ID>: <title>
  <summary>

Proceed? [y/N]
```

Halt for user confirmation. On `N`: exit with zero post-report mutations. On `y`: continue to Phase 5.

## Phase 5 — Execute

All post-report file operations happen here, after user approval.

1. **Wiki entries** (full-close only). Write each approved decision/comprehension file to `<wiki_root>/decisions/` or `<wiki_root>/comprehension/`.

2. **State.md update** (full-close only). Apply the approved `state.md` edit. The edit must include the evidence triple — if the evidence is incomplete (no merge SHA, no verification grep), skip the `state.md` edit and warn: `state.md update skipped: incomplete evidence triple. Run /wiki-state-update manually.`

3. **Archive.** In the target repo:
   ```bash
   mkdir -p docs/specs/DONE/<TICKET-ID>
   ```
   For each artifact, apply the rename mapping — the ticket prefix is stripped because the `DONE/<TICKET-ID>/` directory name already carries the ID (and the fleet's existing archives use exactly this shape):
   - `<TICKET-ID>.spec.md` → `spec.md`
   - `<TICKET-ID>.brief.md` → `brief.md`
   - `<TICKET-ID>.reconciliation.md` → `reconciliation.md`
   - `<TICKET-ID>.reviews/` → `reviews/`
   - any other companion `<TICKET-ID>.<rest>` → `<rest>` (e.g., `VHS-3.test-output.txt` → `test-output.txt`)

   Per artifact:
   - If the source path no longer exists, skip it and print `already archived: <name>` — this is what makes an interrupted run re-runnable.
   - Check tracking status: `git ls-files --error-unmatch <file> 2>/dev/null`
   - Tracked files: `git mv <source> <destination>`
   - Untracked files: `mv <source> <destination>` then `git add <destination>`

4. **Log.md** (skipped when Phase 1 row 8 dropped it). Append the approved entry to `<wiki_root>/log.md`. Idempotency: `grep -F "close | <PROJECT> — <TICKET-ID>:" <wiki_root>/log.md` first; skip if already present. The trailing colon is load-bearing — without it, closing `<PROJECT>-1` after `<PROJECT>-11` would false-match and silently skip the entry. If `log.md` does not exist (fresh wiki), treat as not-present and create the file on append. `<PROJECT>` is `project_prefix` from Phase 0 step 1. This `close |`-prefixed match distinguishes close entries from wiki-after-merge's merge-event entries (which also contain the ticket ID). Format:
   ```markdown
   ## [YYYY-MM-DD] close | <PROJECT> — <TICKET-ID>: <spec title> (archived from TODO/)

   <1-3 sentences: what the spec covered, reconciliation status, wiki entries created.>
   ```

5. **Do not commit.** The skill writes to two separate repos (target repo for archive, wiki repo for entries). Neither is committed — the user controls commit timing.

Print at the end:
```text
=== CLOSE COMPLETE: <TICKET-ID> ===

Target repo (<project_root>):
  Reconciliation: docs/specs/DONE/<TICKET-ID>/reconciliation.md
  Archived: TODO/<TICKET-ID>.* → DONE/<TICKET-ID>/ (ticket prefix stripped)
  Status: uncommitted — review with `git diff --stat` then commit.

Wiki (<wiki_root>):
  Created: decisions/YYYY-MM-DD-<slug>.md
  Created: comprehension/YYYY-MM-DD-<slug>.md
  Updated: projects/<project>/state.md
  Appended: log.md
  Status: uncommitted — review with `git diff --stat` then commit.

Suggested commits:
  (in target repo)  git add docs/specs/ && git commit -m "close(<ticket-lower>): archive spec to DONE/"
  (in wiki)         git add -A && git commit -m "close(<ticket-lower>): wiki harvest from <TICKET-ID>"
```

For partial-close, omit the wiki block (or show only the log.md line when it was written) and the reconciliation line unless a pre-existing report was archived.

## Tool-use notes

- Read, Grep for code verification, duplicate detection, and evidence extraction. `gh pr view` / `gh pr diff` for PR data.
- MCP memory server's search capability (e.g., `mcp__claude_ai_Vigil_Harbor_MCP_Server__memory_search` in Claude Code, or the equivalent semantic-search tool in your host) for Plane ticket lookup.
- plane-proxy's state-list and work-item-lookup capabilities (e.g., `mcp__plane__list_states` and `mcp__plane__retrieve_work_item_by_identifier` in Claude Code, or the equivalents in your host's Plane integration) for the mode gate.
- Bash for `git log --grep` (read-only), `git show`, `git mv`, `mkdir -p`, `grep -F` (idempotency check), `grep -rlw` / `grep -c` (duplicate detection and fast-path coverage checks), `sed` (Wiki-ready section extraction), `git ls-files --error-unmatch`, `git status`.
- Write for the reconciliation report, wiki entries, and log.md. Edit for state.md updates (surgical line replacement).
- **Mutation boundary:** no file mutation before the Phase 4 confirmation except the reconciliation report (generated audit-trail output, Phase 2c). All other writes — wiki entries, state.md, archive moves, log.md — happen in Phase 5, after explicit user approval.
- This skill never commits. Do not push. Do not open PRs.

## Failure modes

- **Merge commit not found.** Fall back through the three strategies to the user prompt. Common for tickets where commit messages don't include the ticket ID (older conventions).
- **Large diffs.** PRs with >500 lines of diff: summarize by file, don't try to read every line. Focus grep on the specific code paths the spec's decisions describe.
- **Plane ticket not in MCP memory.** Warn and proceed using only git log + brief. The brief is the local source of truth for acceptance criteria. When the tag search returns zero results, the warning names the namespace and tags searched — a stale states.json `namespace` is the usual cause.
- **Plane unreachable or ticket not found.** Surface the partial-or-abort prompt (Phase 1 row 6) — partial-close is the safer path (archive only, no wiki writes or state.md edits). Re-run once Plane is available to get full-close with wiki decomposition.
- **`completed_at` is not a gate.** Some Plane workspaces have non-completed states that still set `completed_at`; the state UUID → group match is the only gate signal (Phase 1). `completed_at` is used solely as a ship-date source, with merge-commit-date and today-with-warning fallbacks.
- **State UUID unresolvable.** A ticket state UUID missing from the state map (stale `project_id` in states.json, or a null state field) lands on Phase 1 row 4 — prompt, never infer a group.
- **Wiki path missing.** Per-mode behavior (Phase 1 rows 7–8): full-close prompts partial-or-abort before any reconciliation work; partial-close degrades to archive-only with a printed notice. Never discovered mid-execute.
- **Interrupted execute.** If Phase 5 dies mid-sequence (a move fails, user interrupts), re-run `/spec-close` with the **DONE** path (`docs/specs/DONE/<TICKET-ID>/spec.md`). Duplicate detection, the log idempotency guard, and the skip-if-source-missing archive steps make re-execution idempotent.
- **Partial-then-full re-run.** A prior partial-close wrote a `close |` log entry; the later full-close's idempotency guard matches it and skips a second entry by design — the wiki-harvest event is visible in the created entry files and state.md, not in a second log line.
- **Log-guard encoding.** The `grep -F` idempotency pattern depends on the literal em dash (`—`) in the entry format; tools that normalize it to `--`/`-` will break dedup and produce duplicate entries on re-run.
- **`state.md` evidence incomplete.** Skip the `state.md` update, warn, and suggest `/wiki-state-update` as a follow-up. Don't block the rest of the close.
- **Untracked spec files.** Some spec artifacts may not be committed yet. Use `mv` + `git add` instead of `git mv` for untracked files. Detect via `git ls-files --error-unmatch <file> 2>/dev/null`.
- **Cross-repo commit discipline.** The skill writes to two repos but commits to neither. Print explicit commit suggestions for both repos. The user controls when and how to commit.
- **Cross-repo specs.** The skill runs in the target repo (where the spec lives). Wiki path comes from that repo's CLAUDE.md. No cross-repo file access is needed during reconciliation.
