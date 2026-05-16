---
name: spec-reconcile
description: Diff a closed spec against shipped code. Produces a reconciliation report confirming implementation matches spec intent, or flags drift. Read-only — never edits code or spec files. Pair with /spec-retire to archive reconciled specs into the wiki.
user_invocable: true
---

Invoked as: `/spec-reconcile <spec-path>` (e.g., `/spec-reconcile docs/specs/TODO/ADA-17.spec.md`).

## Phase 0 — Preflight

1. Resolve `<spec-path>`. Expected shapes: `docs/specs/TODO/<TICKET-ID>.spec.md` or `docs/specs/DONE/<TICKET-ID>/spec.md`. Extract `ticket_id` (uppercase): from TODO paths, the filename stem before `.spec.md`; from DONE paths, the parent directory name. Derive `project_prefix` (portion before the first hyphen, e.g., `ADA` from `ADA-17`) and `issue_number` (integer portion after the hyphen, e.g., `17`). Set `project_root` to the repo root (the directory containing `CLAUDE.md`).
2. Confirm the spec exists. Halt if not.
3. Read `<project_root>/CLAUDE.md`. Identify the wiki path (resolve username-bearing paths per spec-cycle convention).
4. Read `~/.claude/skills/ship-spec/states.json`. Look up ticket prefix to get `project_id` and `namespace`. If prefix not found, warn and default `namespace` to `"plane"`.
5. Verify Plane ticket state. Call `mcp__claude_ai_Plane__list_states(project_id)` to get the state map. Then look up the ticket via `mcp__claude_ai_Plane__retrieve_work_item_by_identifier(project_identifier, issue_number)` (pass `issue_number` as integer). Check whether the ticket's state falls in a `group == "completed"` or `group == "cancelled"` state. If not: halt with `Ticket <TICKET-ID> is not in a completed state (current: <state_name>). Reconciliation requires a completed ticket. Close the ticket in Plane or verify the correct spec path.` This matches the brief's "warn-and-halt" requirement — reconciliation targets shipped work, so a non-completed ticket signals the wrong spec or premature invocation.

Print a one-line preflight summary, then continue.

## Phase 1 — Gather shipped state

Goal: identify what code actually shipped for this ticket.

1. **Find the merge commit(s).** Three strategies, tried in order:
   a. `git log --all --oneline --grep="<TICKET-ID>" -- .` — matches commit messages containing the ticket ID.
   b. Look up the Plane ticket via `mcp__claude_ai_Vigil_Harbor_MCP_Server__memory_search` with `tags: ["plane_work_item", "<TICKET-ID>"]`, `namespace` from preflight. Parse the description for PR references (`PR #N`, `#N`, `github.com/.../pull/N`).
   c. If neither yields results, prompt the user: `Could not find merge commit for <TICKET-ID>. Enter PR number or commit SHA:`

2. **Read the shipped diff.** For each identified PR/commit:
   - `gh pr view <N> --json files,additions,deletions` for file-level diff stat.
   - `gh pr diff <N>` (or `git show <SHA>`) for the full diff content. If the diff is large (>500 lines), summarize by file rather than reading every line.

3. **Read the spec's companion brief** at the same directory as the spec (`<TICKET-ID>.brief.md` for TODO paths, `brief.md` for DONE paths), if it exists. The brief's acceptance criteria are the primary reconciliation targets.

## Phase 2 — Reconcile

Walk the spec section by section:

1. **Scope (files changed).** Compare the spec's "Scope" or "Edit" section against the PR's actual diff stat. For each file the spec says to change: confirm it appears in the diff. For each file in the diff that the spec doesn't mention: flag as "Added (not in spec)." For each file the spec mentions but the diff doesn't touch: flag as "Dropped."

2. **Decisions.** For each `### Decision` in the spec: read the relevant code (using the file paths from the diff) and confirm the decision is reflected. Use grep/file reads, not inference. Mark each as: Confirmed (code matches), Drifted (code diverges — describe how), or Unverifiable (decision is about behavior/performance, not structure).

3. **Acceptance criteria.** For each "Done when" bullet in the spec (or "Acceptance" in the brief): produce a grep or file-read that confirms the criterion is met. Mark as: Met (with evidence), Unmet (with explanation), or Unverifiable.

4. **Test plan.** Check whether the tests described in the spec's "Test plan" section exist in the codebase. Grep for test file names, function names, or describe blocks.

## Phase 3 — Report

Write the reconciliation report alongside the spec. If the spec is at `docs/specs/TODO/<TICKET-ID>.spec.md`, write to `docs/specs/TODO/<TICKET-ID>.reconciliation.md`. If the spec is at `docs/specs/DONE/<TICKET-ID>/spec.md`, write to `docs/specs/DONE/<TICKET-ID>/reconciliation.md`.

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

## Tool-use notes

- Read, Grep for code verification. `gh pr view` / `gh pr diff` for PR data.
- `mcp__claude_ai_Vigil_Harbor_MCP_Server__memory_search` for Plane ticket lookup.
- `mcp__claude_ai_Plane__list_states` and `mcp__claude_ai_Plane__retrieve_work_item_by_identifier` for state verification.
- Bash for `git log --grep` (read-only).
- Write for the reconciliation report.
- This skill is read-only. It must never edit code files, spec files, or wiki files.

## Failure modes

- **Merge commit not found.** Fall back to user prompt. Common for tickets where commit messages don't include the ticket ID (older conventions).
- **Large diffs.** PRs with >500 lines of diff: summarize by file, don't try to read every line. Focus grep on the specific code paths the spec's decisions describe.
- **Plane ticket not in MCP memory.** Warn and proceed using only git log + brief. The brief is the local source of truth for acceptance criteria.
- **Cross-repo specs.** The skill runs in the target repo (where the spec lives). Wiki path comes from that repo's CLAUDE.md. No cross-repo file access needed during reconciliation.
