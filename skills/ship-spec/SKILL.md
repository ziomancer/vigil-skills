---
name: ship-spec
description: Take a green-lit spec through implementation, test gate, PR, and Plane update. Cuts an isolated git worktree from your default branch (your primary working tree is never touched), implements + tests in a tight loop, captures test output for the PR audit trail, and pushes a PR. Pair with /spec-cycle which produces the spec.
user_invocable: true
---

# /ship-spec — implement a green-lit spec end-to-end

Invoked as: `/ship-spec <spec-path>` (e.g., `/ship-spec docs/specs/TODO/PROJ-123.spec.md`).

This skill assumes `/spec-cycle` has already produced a converged spec. It implements, tests, pushes a PR, and updates Plane. It does **not** update any project wiki — that happens post-merge via your own wiki-update workflow, which the final summary will remind you to run.

## Phase 0 — Preflight

1. Resolve `<spec-path>`. Confirm it exists and follows shape `docs/specs/TODO/<TICKET-ID>.spec.md`. Extract `ticket_id` (uppercase) from filename.
2. Confirm sibling brief exists at `docs/specs/TODO/<TICKET-ID>.brief.md`. If missing, warn but proceed using the spec alone.
3. Read `<project_root>/CLAUDE.md`. Note project-level conventions (build, lint, test, etc.) — used as fallback in step 4 and as reference during Phase 2 implementation.
4. **Resolve the test command (single source of truth).**
   1. **Spec § Test command first.** Read `<spec-path>` for a `## Test command` section. If present, use the command(s) listed there verbatim. The spec is authoritative because the spec author chose it for *this* change (TS vs. Python, single test file vs. full suite, specific interpreter, etc.).
      **Exception: `N/A` test command.** After reading the `## Test command` section, extract its raw text content (strip markdown code fences if present, trim leading/trailing whitespace). If the resulting string matches `N/A` (case-insensitive), record the resolved test command as `N/A` and do not fall through to step 4.2 or 4.3. When Phase 3 encounters a resolved test command of `N/A`, skip the test gate loop entirely — Phase 2 (implementation) still runs normally, then proceed directly to Phase 4 (commit). The spec's `## Test plan` review checklist is the quality gate for doc-only and ops-only changes.
   2. **CLAUDE.md "Build & Run" second.** If the spec has no `## Test command` section, fall back to project-level commands. Form a combined command: `<build> && <test> && <any extra checks>`. For a TS monorepo this might be `npm run build && npm test && npm run lint`.
   3. **Fail loud if neither yields a runnable command.** Halt with:
      ```
      No test command found.
      - Spec at <spec-path> has no `## Test command` section.
      - CLAUDE.md "Build & Run" did not produce a parseable command.

      Add a `## Test command` section to the spec, then re-run.
      ```
      Phase 3 must not run without a resolved command.
5. **Discover the default branch.** The branch name is not always `main` — some repos use `master`, `trunk`, etc.
   ```bash
   git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's|^refs/remotes/origin/||'
   # Fallback if origin/HEAD isn't set locally:
   git remote show origin | sed -n '/HEAD branch/s/.*: //p'
   ```
   Capture the result as `<default-branch>`. Used in Phase 1 (branch cut from) and Phase 5 (PR base, implicit). Halt at preflight if both commands return empty.
6. `git status --short` — informational only; the worktree flow in Phase 1 doesn't touch the user's primary tree, so uncommitted changes there don't gate this skill.
7. `gh auth status` — confirm GitHub CLI is authenticated. Halt if not.
8. Confirm plane-proxy is reachable: call the plane-proxy's project-list capability (e.g., `mcp__plane__list_projects` in Claude Code, or the equivalent in your host's Plane integration). Warn-and-proceed on failure.
9. Read `skills/ship-spec/states.json` (from `~/.claude/skills/ship-spec/states.json` — `~/.claude/` on Unix; `%USERPROFILE%\.claude\` on Windows — as installed by `sync.py`). Look up the ticket prefix (e.g., `MCP` from `MCP-33`). Confirm the prefix exists and has a `project_id` and `states` map. If the prefix is missing entirely, **halt** — the project must be added to states.json before ship-spec can manage it. If `review_state_id` is missing or empty, continue — Phase 6 will warn and skip the state flip.

**Preflight notes:**
- **Python tests, prefer module-form invocation.** When the resolved test command is Python-based, write it as `<interpreter> -m pytest …` (e.g., `python -m pytest`, or pin the interpreter with a full path like `<full-path-to-python> -m pytest`) rather than bare `pytest`. Bare `pytest` resolves to whichever `pytest` executable is first on `PATH`, which on multi-Python systems often points to an interpreter that doesn't have the project's deps installed. Module-form forces resolution into the same interpreter that has the deps. This is discipline at the spec/CLAUDE.md authoring layer; ship-spec passes the command through as-is.

Print a one-line preflight summary, then continue.

## Phase 1 — Worktree setup

Implementation runs in an isolated git worktree, not in the user's primary working tree. This sidesteps stash-and-restore ceremony, leaves the user's tree untouched (uncommitted changes, branch state, untracked files all preserved), and enables parallel `/ship-spec` invocations on different tickets.

1. Form branch name: `<type>/<ticket-id-lower>-<slug>`.
   - `<type>` — derive from the spec's commit-style prefix or from the ticket type. Default: `fix` for bug-class tickets, `feat` for new features, `chore` for refactors. If unsure, ask the user.
   - `<slug>` — 3–5 lowercase hyphenated words from the ticket title or spec goal.
   - Example: `fix/proj-123-feature-slug`.

2. Form worktree path: `<worktree-path>` = `<project-root>/../<TICKET-ID>-worktree` (sibling to the project root). For `<project-root>` = `~/code/myproject`, this resolves to `~/code/PROJ-123-worktree`.

3. Pre-create checks (halt if either trips):
   - **Worktree path conflict.** If `<worktree-path>` already exists as a directory, halt:
     ```
     Worktree path <worktree-path> already exists.
     Resolve with `git worktree remove <worktree-path>` (or `--force` if it's broken),
     or rename the existing dir, then re-run.
     ```
   - **Branch conflict.** Check for collisions:
     ```bash
     git rev-parse --verify <branch> 2>/dev/null     # local existence
     git ls-remote --heads origin <branch>           # remote existence
     ```
     If either returns non-empty, halt and ask the user how to resolve (reuse / delete / rename).

4. Fetch latest and create the worktree:
   ```bash
   git fetch origin <default-branch>
   git worktree add -b <branch> <worktree-path> origin/<default-branch>
   ```
   Creates a fresh checkout at `<worktree-path>`, on the new branch `<branch>`, based on the up-to-date remote tip of `<default-branch>`. The user's primary checkout is never modified.

5. **All subsequent phases run with `<worktree-path>` as the working directory.** Use `cd <worktree-path>` for shell commands, or absolute paths for tool calls. The spec at `<project-root>/<spec-path>` is read by absolute path — the spec stays in the user's primary tree throughout (it's metadata about the work, not part of the code change).

## Phase 2 — Implement + author tests

Working directory: `<worktree-path>`. File edits target paths inside the worktree; the spec is read from `<project-root>/<spec-path>` (absolute, in the user's primary tree).

Read the spec and implement the changes described. Concretely:

- Make every code change the spec calls for.
- Author the tests the spec's "Test plan" lists. If the spec calls for regression tests, ensure each one has a clear `// Regression for <TICKET-ID>: <one-line>` comment.
- Project-specific guardrails (await rules, lint exclusions, ordering constraints) live in `<project_root>/CLAUDE.md`. Read them in Phase 0 step 3 and respect them through Phase 2 + Phase 3.

Do not commit yet. Implementation and tests are one logical unit; the test gate runs across the full set.

## Phase 3 — Test gate loop (≤5 iterations)

Working directory: `<worktree-path>`. The test command runs against worktree files. The captured output path `docs/specs/TODO/<TICKET-ID>.test-output.txt` is relative to cwd, so it lands inside the worktree and gets staged in Phase 4.

Loop:

```
for iter in 1..5:
    run combined test command from preflight discovery
    capture exit code and full stdout+stderr
    if exit == 0:
        save full output to docs/specs/TODO/<TICKET-ID>.test-output.txt
        break
    else:
        identify the smallest blocking failure (one assertion, one type error)
        fix it
        do not bundle multiple fixes in one iteration — sequence fixes by value, re-run between each, so the evidence trail stays intact
        continue
```

If after 5 iterations tests are still red:
```
TESTS STILL RED AFTER 5 ITERATIONS.
Most recent failure:
  <last failing line(s)>

Branch: <branch>
Spec: <spec_path>

What would you like to do?
1. Continue with more iterations (specify count)
2. Drop into manual debug — I'll print state and pause
3. Roll back the branch and re-spec
```

Halt and wait for user input.

## Phase 4 — Commit

Working directory: `<worktree-path>`. All `git` operations are scoped to the worktree (it has its own HEAD; the user's primary tree is unaffected).

Stage the changed files explicitly (do not `git add -A` or `.`). For each modified file in the diff, `git add <file>`.

Form the commit body using this pattern:

```
<type>(<ticket-id-lower>): <one-line summary, ≤72 chars>

<2–4 sentence narrative — what shipped and the problem it solves.>

<If the change has distinct layers or stages, enumerate them. Otherwise list the
key file-level changes.>

Co-Authored-By: Claude <noreply@anthropic.com>
```

For multi-layered changes, the body should enumerate layers:
```
1. <Layer name> (<file>): <description>.
2. <Layer name> (<file>): <description>.
3. <Layer name> (<file>): <description>.
```

Pass via HEREDOC:
```bash
git commit -m "$(cat <<'EOF'
<body>
EOF
)"
```

Do not skip hooks. Do not bypass signing.

## Phase 5 — Push and open PR

Working directory: `<worktree-path>`.

```bash
git push -u origin <branch>
```

Open the PR via `gh pr create`. The body should follow this ceremony:

```markdown
## Summary
- <bullet — main change>
- <bullet — secondary effect>
- <bullet — wiring or test impact>

[Optional second section if the change has notable structure:
## Two-check interaction
or
## Layered defense
— concrete walkthrough of how the layers compose.]

## Files changed

| File | Change |
|------|--------|
| `path/to/file.ts` | <New / Adds / Defensive / Wires / Refactors> |

## Test plan

(When the resolved test command is `N/A`, replace the first bullet with `- [x] Tests: N/A — doc-only/ops-only change, no test artifacts produced` and omit the test-output file link.)
- [x] `<combined test command>` — <N>/<N> pass (full output: docs/specs/TODO/<TICKET-ID>.test-output.txt)
- [x] `<build command, if separate>` — clean
- [x] [smoke check on real data, if applicable]
- [x] [post-merge verification step, if applicable]

[Optional trailing line:]
🤖 Generated with [Claude Code](https://claude.com/claude-code)
```

Pass the body via HEREDOC to preserve formatting:
```bash
gh pr create --title "<type>(<ticket-id-lower>): <one-line>" --body "$(cat <<'EOF'
<body>
EOF
)"
```

Capture the returned PR URL.

## Phase 6 — Plane update

1. **Re-check Plane reachability.** Call the same plane-proxy project-list capability used in preflight step 8 (e.g., `mcp__plane__list_projects` in Claude Code, or the equivalent in your host's Plane integration). If it fails, skip all remaining Phase 6 steps and print:
   ```
   Plane unreachable — skipping state update and PR comment.
   To complete manually:
     1. Move <TICKET-ID> to review state in Plane
     2. Comment on the ticket: "PR opened: <pr-url>"
   ```
2. Read `states.json` (already loaded at preflight). Look up the ticket prefix to get `project_id` and `review_state_id`.
3. Use `review_state_id` directly as the target state for the flip. If `review_state_id` is absent or empty, warn and skip the state flip — print available state names from `states.json` so the user can update manually.
4. Call the plane-proxy's work-item state-update capability (e.g., `mcp__plane__update_work_item` in Claude Code, or the equivalent in your host's Plane integration) — set the ticket's state to the resolved review state.
5. Call the plane-proxy's work-item comment capability (e.g., `mcp__plane__create_work_item_comment` in Claude Code, or the equivalent in your host's Plane integration) — add: `PR opened: <pr-url>`.

## Phase 7 — Final summary (worktree stays alive)

Do **not** remove the worktree. It stays alive so `/review-pr` (and manual fixes) can push to the branch without recreating it. Cleanup happens post-merge.

Print final summary:
```
=== SHIPPED: <TICKET-ID> ===

PR:       <pr-url>
Spec:     docs/specs/TODO/<TICKET-ID>.spec.md
Tests:    docs/specs/TODO/<TICKET-ID>.test-output.txt  (omit this line when test command is N/A)
Branch:   <branch>
Worktree: <worktree-path> (kept alive for review fixes)

Plane: <ticket-id> → <new state>
       <pr-url> commented on ticket

User's primary working tree: untouched.

To address PR review comments:
  cd <worktree-path>
  /review-pr

After merge, clean up:
  git worktree remove <worktree-path>
  # Then run /wiki-after-merge <merge-sha> from the wiki dir
```

Do not auto-update any project wiki — that happens post-merge once the merge SHA exists on `<default-branch>`. Run your project's post-merge wiki/docs update flow if you have one.

## Tool-use notes

- Read, Edit, Write for implementation.
- Bash for git, gh, package-manager commands — fully scripted, no interactive prompts.
- plane-proxy tools (project listing, work-item state update, work-item comment) — or the equivalent capabilities in your host's Plane integration.
- Do not run `git rebase -i`, `git add -i`, or any interactive command.
- Do not push to `<default-branch>`. Do not force-push the feature branch unless the user explicitly asks.
- Do not skip pre-commit hooks (`--no-verify`). If a hook fails, fix the underlying issue.

## Failure modes to watch for

- **Spec not green.** If the spec doesn't have `## Done when` / `## Test plan` / `## Test command` / etc., it likely hasn't been through `/spec-cycle`. Halt and ask the user.
- **Worktree path conflict.** The sibling `<worktree-path>` already exists. Could be a leftover from a previous ship-spec run, or unrelated. Halt with the manual cleanup command (`git worktree remove …` or rename). Don't auto-remove — the dir might hold work in progress.
- **Branch conflict.** The target branch already exists locally or on origin. Halt and ask the user how to resolve. Don't auto-delete branches.
- **Push rejected.** Should be rare in worktree mode (branch is freshly cut from the remote tip), but possible if the user pushed manually during Phase 2/3. Halt; do not force-push.
- **gh pr create fails.** Most often: gh CLI not authenticated, or the user lacks repo write. Halt with the error.
- **Plane state mismatch.** If no state matches review-equivalent, skip the state flip and report. Don't fail the whole skill.
- **Stale worktree from prior run.** Phase 1 checks for worktree path conflicts. If the path exists, it's likely a leftover from a previous `/ship-spec` whose PR already merged. Halt with the cleanup command — don't auto-remove, since it might hold uncommitted review fixes.
