---
name: spec-retire
description: Decompose a reconciled spec into wiki entries (decisions, comprehension, state.md updates), archive the spec and companions to DONE/, and append to wiki log.md. Checks Plane state to gate full-retire vs. partial-retire. Run /spec-reconcile first. Pair with /spec-cycle and /ship-spec for the full spec lifecycle.
user_invocable: true
---

Invoked as: `/spec-retire <spec-path>` or `/spec-retire <spec-path> --partial`.

## Phase 0 — Preflight

1. Resolve `<spec-path>`. Extract `ticket_id`, `project_prefix`, `issue_number`, and `project_root` using the same parsing rules as spec-reconcile Phase 0 step 1.
2. Confirm the spec exists. Halt if not.
3. Confirm the reconciliation report exists alongside the spec (same directory, `<TICKET-ID>.reconciliation.md` or `reconciliation.md`). If not: halt with `Reconciliation report not found. Run /spec-reconcile <spec-path> first.`
4. Read the reconciliation report's last non-blank line. Parse `RECONCILED: <yes|no> DRIFT: <n>`. If `RECONCILED: no`, warn: `Spec has unmet acceptance criteria. Review the reconciliation report before proceeding. Continue anyway? [y/N]`. Halt on N.
5. Read `<project_root>/CLAUDE.md`. Identify the wiki path. Confirm the wiki directory exists.
6. Read `~/.claude/skills/ship-spec/states.json`. Look up ticket prefix to get `project_id` and `namespace`. If prefix not found, warn: `Project prefix "<project_prefix>" not found in states.json. Skipping Plane state gate — entering partial-retire mode.` Set `force_partial_retire = true` and skip Phase 1 entirely (no `project_id` means Plane calls cannot proceed).
7. Check for `--partial` flag in invocation args. If present, set `force_partial_retire = true`.

Print a one-line preflight summary, then continue.

## Phase 1 — Plane state gate

If `force_partial_retire` is set (from `--partial` flag or missing prefix in preflight), skip Plane lookups and enter **partial-retire** directly. Print: `Entering partial-retire mode: archiving spec artifacts only, skipping wiki decomposition.`

Otherwise:

1. Call `mcp__claude_ai_Plane__list_states(project_id)` to get the full state map with groups.
2. Look up the ticket via `mcp__claude_ai_Plane__retrieve_work_item_by_identifier(project_identifier, issue_number)` (pass `issue_number` as integer).
3. Match the ticket's `state` UUID against the state map to determine the group.
4. Determine mode:
   - `group == "completed"` or `group == "cancelled"` -> **full-retire**.
   - Any other group -> **partial-retire** (auto-detected). Print: `Ticket <TICKET-ID> is in state "<state_name>" (group: <group>). Entering partial-retire mode: archiving spec artifacts only, skipping wiki decomposition.`

## Phase 2 — Analysis

### 2a. Duplicate detection

Search the wiki for existing entries related to this ticket:

```bash
grep -rl "<TICKET-ID>" "<wiki_root>/decisions/" "<wiki_root>/comprehension/"
grep -rli "<key-terms>" "<wiki_root>/decisions/" "<wiki_root>/comprehension/"
```

Where `<key-terms>` are 2-3 distinctive words from the spec's Goal section (not common words like "fix" or "update").

If matches found, read each matched file's title and first paragraph. Present to user:
```text
Pre-existing wiki entries found:
  1. decisions/2026-05-06-dyn-34-score-calibration-pipeline.md — "Decision: DYN-34a score calibration pipeline"
  2. comprehension/2026-05-06-dyn-34b-ui-calibration-overlay.md — "Comprehension: DYN-34b calibration UI overlay"

These may already cover some or all of the spec's content.
Duplicates will be excluded from wiki proposals below.
```

Track matched ticket IDs and decision titles as an exclusion list for Phase 2b.

### 2b. Wiki decomposition (full-retire only)

Skip entirely for partial-retire. For full-retire:

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
   - The ship date: try `completed_at` from the Plane ticket first; if null, fall back to the merge commit date from `git log --format=%ci <merge-sha>`, then to today's date as last resort (with a warning). The merge SHA comes from the reconciliation report. The verification line comes from the reconciliation report's acceptance criteria evidence.

### 2c. Compile proposals

Collect all proposed actions into a single summary:
- Wiki decisions to create (with filenames and content previews)
- Wiki comprehension entries to create
- `state.md` edits (as diffs)
- Files to archive (list of `TODO/` -> `DONE/` moves)
- `log.md` entry (full text)

For partial-retire, this section contains only the archive list and log.md entry.

## Phase 3 — User confirmation

Present the compiled proposals:
```text
=== RETIREMENT PLAN: <TICKET-ID> ===
Mode: <full-retire | partial-retire>

Wiki entries to create:
  1. decisions/YYYY-MM-DD-<slug>.md — "<title>"
     <3-line preview>
  2. comprehension/YYYY-MM-DD-<slug>.md — "<title>"
     <3-line preview>

State.md update:
  File: projects/<project>/state.md
  Move "<Title>" from What's Active → What's Shipped
  Evidence: (<TICKET-ID>, YYYY-MM-DD, commit <SHA>)

Archive (TODO/ → DONE/<TICKET-ID>/):
  - <TICKET-ID>.spec.md
  - <TICKET-ID>.brief.md
  - <TICKET-ID>.reconciliation.md
  - <TICKET-ID>.reviews/ (N files)

Log.md append:
  ## [YYYY-MM-DD] retire | <PROJECT> — <TICKET-ID>: <title>
  <summary>

Proceed? [y/N]
```

Halt for user confirmation. On `N`: exit without changes. On `y`: continue to Phase 4.

## Phase 4 — Execute

All file operations happen here, after user approval.

1. **Wiki entries** (full-retire only). Write each approved decision/comprehension file to `<wiki_root>/decisions/` or `<wiki_root>/comprehension/`.

2. **State.md update** (full-retire only). Apply the approved `state.md` edit. The edit must include the evidence triple — if the evidence is incomplete (no merge SHA, no verification grep), skip the `state.md` edit and warn: `state.md update skipped: incomplete evidence triple. Run /wiki-state-update manually.`

3. **Archive.** In the target repo:
   ```bash
   mkdir -p docs/specs/DONE/<TICKET-ID>
   ```
   For each artifact (`<TICKET-ID>.spec.md`, `<TICKET-ID>.brief.md`, `<TICKET-ID>.reconciliation.md`, `<TICKET-ID>.reviews/`, and any companions matching `<TICKET-ID>.*`):
   - Check tracking status: `git ls-files --error-unmatch <file> 2>/dev/null`
   - Tracked files: `git mv <source> <destination>`
   - Untracked files: `mv <source> <destination>` then `git add <destination>`

4. **Log.md.** Append the approved entry to `<wiki_root>/log.md`. Idempotency: `grep -F "<TICKET-ID>" <wiki_root>/log.md` first; skip if already present. Format:
   ```markdown
   ## [YYYY-MM-DD] retire | <PROJECT> — <TICKET-ID>: <spec title> (archived from TODO/)

   <1-3 sentences: what the spec covered, reconciliation status, wiki entries created.>
   ```

5. **Do not commit.** The skill writes to two separate repos (target repo for archive, wiki repo for entries). Neither is committed — the user controls commit timing.

Print at the end:
```text
=== RETIREMENT COMPLETE: <TICKET-ID> ===

Target repo (<project_root>):
  Archived: TODO/<TICKET-ID>.* → DONE/<TICKET-ID>/
  Status: uncommitted — review with `git diff --stat` then commit.

Wiki (<wiki_root>):
  Created: decisions/YYYY-MM-DD-<slug>.md
  Created: comprehension/YYYY-MM-DD-<slug>.md
  Updated: projects/<project>/state.md
  Appended: log.md
  Status: uncommitted — review with `git diff --stat` then commit.

Suggested commits:
  (in target repo)  git add docs/specs/ && git commit -m "retire(<ticket-lower>): archive spec to DONE/"
  (in wiki)         git add -A && git commit -m "retire(<ticket-lower>): wiki harvest from <TICKET-ID>"
```

## Tool-use notes

- Read, Grep for duplicate detection and evidence extraction.
- Write for wiki entries and log.md.
- Edit for state.md updates (surgical line replacement).
- Bash for `git mv`, `mkdir -p`, `grep -F` (idempotency check), `git ls-files --error-unmatch`, `git status`.
- `mcp__claude_ai_Plane__list_states` and `mcp__claude_ai_Plane__retrieve_work_item_by_identifier` for state gate.
- This skill mutates files in both the target repo and the wiki repo. All mutations happen in Phase 4, after user confirmation in Phase 3.

## Failure modes

- **Reconciliation report missing.** Hard halt at preflight. The user must run `/spec-reconcile` first.
- **Reconciliation report says `RECONCILED: no`.** Soft halt with user override. Some specs may have unmet criteria that are acceptable (e.g., descoped items). The user decides.
- **Plane ticket not found.** Warn and proceed. Default to partial-retire if the ticket can't be looked up — this is the safer path (archive only, no wiki writes or state.md edits). The user can re-run once Plane is available to get full-retire with wiki decomposition.
- **Wiki path not found.** Halt. The wiki is required for retirement — without it, there's nowhere to write entries. The user must configure the wiki path in their repo's CLAUDE.md.
- **`state.md` evidence incomplete.** Skip the `state.md` update, warn, and suggest `/wiki-state-update` as a follow-up. Don't block the rest of the retirement.
- **Untracked spec files.** Some spec artifacts may not be committed yet (e.g., VHS-1 through VHS-6 are untracked per `git status`). Use `mv` + `git add` instead of `git mv` for untracked files. Detect via `git ls-files --error-unmatch <file> 2>/dev/null`.
- **Cross-repo commit discipline.** The skill writes to two repos but commits to neither. Print explicit commit suggestions for both repos. The user controls when and how to commit.
