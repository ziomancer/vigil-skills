---
name: spec-cycle
description: Author a spec from a brief, then run a 3-lens parallel review loop (correctness / edge-cases / conventions) until findings are clean or 4 passes complete. Halts at a session-boundary HARD STOP with a structural drift-check checklist before any implementation. Pair with /ship-spec to take an approved spec through implementation, PR, and Plane update.
user_invocable: true
---

# /spec-cycle — author and converge a spec

Invoked as: `/spec-cycle <brief-path>` (e.g., `/spec-cycle docs/specs/TODO/PROJ-123.brief.md`).

This skill does two things: author a v1 spec from a brief, then loop a 3-lens parallel review until the spec is clean or 4 passes complete. It does **not** implement anything. It halts at a session boundary so the user can review the spec on disk and invoke `/ship-spec` separately.

## Why split from /ship-spec

- Spec context grows linearly with rounds; impl context grows with the work itself. Combining them risks token-cap pressure.
- HARD STOP at a session boundary is robust: the user just runs the next command. No idle-context bloat, no auto-proceed footgun.
- Re-runnable: if `/ship-spec` aborts mid-flight, the green-lit spec on disk is unchanged.

## Phase 0 — Preflight

Before anything else:

1. Resolve `<brief-path>` from the user's invocation. The expected shape is `docs/specs/TODO/<TICKET-ID>.brief.md`. Extract `ticket_id` from the filename (uppercase, e.g., `PROJ-123`) and `project_root` from the cwd (the directory containing `CLAUDE.md`).
2. Confirm the brief exists. If not, halt with: `Brief not found at <path>. Provide a path relative to <project_root>.`
   **Local-only ticket IDs.** If the filename's ticket ID does not match an existing Plane issue (the MCP memory lookup in Phase 1 returns zero results, and no Plane issue is reachable), treat the brief as local-only. The skill proceeds using the brief alone — this is the normal fallback path, not an error. Create the Plane issue when scope is confirmed, then rename all `<TICKET-ID>.*` artifacts under `docs/specs/TODO/` (brief, spec, reviews directory, test output) to match the real ticket ID.
3. Read `<project_root>/CLAUDE.md`. Identify:
   - Test commands from the "Build & Run" section (e.g., for a TS monorepo: `npm test`, `npm run build`, `npm run lint` — use whatever your CLAUDE.md states).
   - The wiki path, if any. If CLAUDE.md hardcodes a username-bearing path that doesn't exist on this machine, replace the username segment with the current user (Windows: `$env:USERNAME`; Unix: `$USER`) and re-check.
   - The project's wiki slug, if a wiki is configured (often the repo name in kebab-case).
4. Upstream staleness check.

   a. **Detect upstream remote:**
      ```bash
      git remote get-url upstream 2>/dev/null
      ```
      If exit ≠ 0: log `upstream: skipped (no remote)` and continue to step 5.

   b. **Resolve default branch:**
      ```bash
      git symbolic-ref refs/remotes/upstream/HEAD 2>/dev/null | sed 's|^refs/remotes/upstream/||'
      ```
      Returns the bare branch name (`main`, `master`, etc.) — the `sed` strip is required because the long-form output is `refs/remotes/upstream/main`. If this errors or returns empty, try `main` then `master` as literal fallbacks (check existence with `git rev-parse --verify upstream/main` / `upstream/master`). Capture the result as `<default-branch>`. If none resolve, log `upstream: skipped (cannot resolve default branch)` and continue to step 5.

   c. **Refresh upstream refs:**
      ```bash
      timeout 30 git fetch upstream 2>/dev/null
      ```
      Network failure is non-fatal — proceed using whatever `upstream/*` refs are already local. The 30-second timeout bounds wall-clock cost on unresponsive remotes. Log `upstream: fetch failed (proceeding with available refs)` if exit ≠ 0; do not halt.

   d. **Extract search terms from `<TICKET-ID>.brief.md`:**
      Read the brief and extract:
      - **File paths** (priority 1): tokens matching `[A-Za-z0-9_./+-]+\.[a-z]{1,4}` that contain `/` or end with a known code extension (`.ts`, `.js`, `.py`, `.md`, `.json`, `.yaml`, `.yml`, `.toml`, `.sh`, `.go`, `.rs`). Take the top 5.
      - **Code identifiers** (priority 2): words inside backtick spans or fenced code blocks that match `[A-Za-z_][A-Za-z0-9_]{3,}` (camelCase, snake_case, PascalCase — ≥4 chars, avoids noise). Take the top 3.
      - **Title words** (priority 3, fallback): non-stopword tokens ≥4 characters from the brief's `# ...` heading. Used only if priorities 1 and 2 yield nothing.

      If no search terms can be extracted at all, log `upstream: skipped (no search terms extracted)` and continue to step 5.

   e. **Run git log queries (parallel when both tiers have results):**
      ```bash
      # Paths-based (only if file paths were extracted in 4d):
      git log upstream/<default-branch> --since="${SPEC_CYCLE_UPSTREAM_WINDOW:-90 days ago}" \
          --oneline -n 20 -- <path1> <path2> ...

      # Grep-based (only if code identifiers or title words were extracted in 4d):
      git log upstream/<default-branch> --since="${SPEC_CYCLE_UPSTREAM_WINDOW:-90 days ago}" \
          --oneline -n 20 --extended-regexp --grep="<term1>|<term2>|<term3>"
      ```
      If both tiers produced search terms, run both via two Bash tool calls in a single message (parallel). If only one tier produced terms, run that query alone. Union the results, deduplicate by SHA prefix.

      If all queries return empty: log `upstream: clean (no relevant commits)` and continue to step 5.

   f. **Behind-upstream check:**
      ```bash
      git rev-list --count HEAD..upstream/<default-branch>
      ```
      If count is 0: the fork is at or ahead of upstream. Even if relevant commits exist, they're already incorporated. Log `upstream: clean (at HEAD)` and continue to step 5.

   g. **Halt on staleness:** If commits were found (step 4e) AND behind-count > 0 (step 4f), present the findings to the user and ask whether to proceed — standard conversational prompting, same pattern as ship-spec's Phase 3 test-gate halt:

      ```text
      UPSTREAM STALENESS: <N> recent upstream commits touch files/terms relevant to this brief.
      Review before investing in a spec:
        <SHA>  <subject>
        ...

      The fork is <M> commits behind upstream/<default-branch>.

      What would you like to do?
      1. Proceed anyway
      2. Abort — re-evaluate brief or update fork
      ```

      Wait for the user's response.

      - On `Proceed`: log `upstream: N stale commits — user proceeded` and continue to step 5.
      - On `Abort`: halt with message `Spec-cycle aborted: upstream staleness — re-evaluate brief or update fork.`

5. Confirm plane-proxy is reachable: call the plane-proxy's project-list capability (e.g., `mcp__plane__list_projects` in Claude Code, or the equivalent in your host's Plane integration). On failure, **warn and proceed** — the brief is the local source of truth.
6. Read `~/.claude/skills/ship-spec/states.json` (`~/.claude/` on Unix; `%USERPROFILE%\.claude\` on Windows) (installed by `sync.py`). If the file is not found, default `namespace` to `"plane"` and warn — ticket lookup still works (MCP-33 fallback namespace is `"plane"` for unmapped projects); namespace-scoped precision is degraded but not broken. If the file exists but cannot be parsed (invalid JSON or unexpected shape), warn and default `namespace` to `"plane"`. Otherwise, extract the ticket prefix (the portion before the first hyphen in `ticket_id`, e.g., `"PROJ"` from `"PROJ-123"`) and look up that prefix in `states.json` to get the `namespace`. If the prefix is not in `states.json`, default `namespace` to `"plane"` and warn. Pass `namespace` to Phase 1's own `memory_search` call and to each reviewer agent in step 2b.

Print a one-line preflight summary — including the upstream check result token (clean / skipped / N stale — user proceeded) — then continue.

## Phase 1 — Author v1 spec

Output path: `docs/specs/TODO/<TICKET-ID>.spec.md`.

Read the brief, the linked Plane ticket (call the MCP memory server's search capability — e.g., `mcp__claude_ai_Vigil_Harbor_MCP_Server__memory_search` in Claude Code, or the equivalent semantic-search tool in your host — with `tags: ["plane_work_item", "<TICKET-ID>"]`, `namespace` from step 6, `source_system: "plane"`, `max_results: 1`; if the memory server is unavailable or returns zero results, proceed using the brief alone), and any files the brief points at. Write a spec that covers, at minimum:

- **Goal** — what this ships, in one paragraph
- **Scope** — files to change, new files to create, files to leave alone
- **Design** — the proposed implementation, including any non-obvious decisions and their rationale
- **Test plan** — what tests will be added, what existing tests will be updated, what regression tests guard against the bug class
- **Test command** — the exact shell command(s) to run the test plan. ship-spec treats this as source of truth for its test gate (see ship-spec Phase 0 step 4); if absent, ship-spec falls back to CLAUDE.md "Build & Run" and halts loudly if neither yields a runnable command. For Python work prefer module-form (`python -m pytest …`) over bare `pytest` to avoid multi-interpreter footguns. Pin the interpreter explicitly (e.g., `<full-path-to-python> -m pytest <files>`) when the project has multiple Python installs on PATH (common on Windows).
  For documentation-only or ops-only specs where no code ships (infrastructure configs, runbooks, wiki-only deliverables): set `## Test plan` to a review checklist describing what a human reviewer should verify. Set `## Test command` to `N/A`. When `ship-spec` encounters `Test command: N/A`, it skips the automated test gate (Phase 3) entirely. The review checklist in Test plan serves as the quality gate instead.
- **Done when** — bullet list mapped 1:1 to the brief's acceptance criteria
- **Out of scope** — explicit fences carried from the brief

If the brief identifies decisions ("rename, don't preserve"; "debuggable tripwire is hard constraint"), the spec must reflect each one with a **Decision** subsection that names it and explains how the design honors it.

Do not include implementation prescriptions in the spec that the brief deliberately left to the spec author — but do make those decisions explicit (e.g., "single source of truth: extract into shared module — rationale: eliminates drift; refactor cost is one file").

Save and continue.

## Phase 2 — Review loop (≤4 passes)

For each round 1..4:

### 2a. Cold-read the spec

Read `<TICKET-ID>.spec.md` from disk fresh. Do not rely on what you wrote — the file is the source of truth.

### 2b. Dispatch 3 reviewers in parallel

Single message, three Agent tool calls — they must run in parallel, not sequentially:

```
Agent(subagent_type="spec-reviewer-correctness", prompt=<context>)
Agent(subagent_type="spec-reviewer-edge-cases",  prompt=<context>)
Agent(subagent_type="spec-reviewer-conventions", prompt=<context>)
```

Each agent's prompt must include:
- `spec_path: docs/specs/TODO/<TICKET-ID>.spec.md`
- `brief_path: docs/specs/TODO/<TICKET-ID>.brief.md`
- `project_root: <absolute>`
- `ticket_id: <TICKET-ID>`
- `namespace: <resolved from preflight step 6, default "plane">`
- `round_number: <N>`

For the conventions reviewer additionally:
- `wiki_root: <absolute path to wiki, resolved in preflight>` (omit if no wiki configured)
- `project_slug: <e.g., myproject>`

### 2c. Persist findings

Save each agent's full report to:
```
docs/specs/TODO/<TICKET-ID>.reviews/round-<N>/correctness.md
docs/specs/TODO/<TICKET-ID>.reviews/round-<N>/edge-cases.md
docs/specs/TODO/<TICKET-ID>.reviews/round-<N>/conventions.md
```

### 2d. Parse STATUS lines and gate

Each reviewer's last non-blank line is `STATUS: GREEN` or `STATUS: RED P0=<n> P1=<n> ...`.

Compute:
```
total_p0p1 = sum of P0+P1 from RED status lines (GREEN contributes 0)
```

If `total_p0p1 == 0`: break the loop. Spec is green at round N.

A reviewer may return `STATUS: RED` with only P2+ findings (P0=0 P1=0). This does not block the loop since the gate checks `total_p0p1 == 0`. P2+ items are advisory — they are carried forward as spec notes in the `## Deferred (P2+)` section but do not prevent the spec from going green.

### 2e. Revise (rounds 1–3) or rewrite (round 4)

If still red and `round < 4`:
- Edit the spec in place.
- Address every P0 and P1 finding.
- For P2 findings, either fix or list them in a `## Deferred (P2+)` section at the end of the spec with one-line acknowledgments.
- Do not delete history of what changed; if a section is rewritten, that's fine, but the spec at end of round must stand on its own.

If still red and `round == 4`:
- **Targeted rewrite, not blank-slate.** Enumerate every section of the spec
  (Goal, Scope, Decisions, Design sub-sections, Test plan, Done-when, Out of
  scope, plus any spec-specific sections). For each, decide:
    - **FROZEN** — no unresolved P0/P1 in this section across rounds 1–3.
      Copy the section verbatim from the current spec. Do not touch.
    - **REWRITE** — has unresolved P0/P1 OR has cross-references to a REWRITE
      section that need re-aligning.
- Print the FROZEN/REWRITE manifest before editing. Sections in REWRITE may
  only modify themselves — they may not silently change content in FROZEN
  sections. If a REWRITE forces a FROZEN-section edit (e.g., changed function
  signature must propagate), explicitly promote that section to REWRITE first.
- Build a closed-issues manifest from rounds 1–3 and pass it to the rewrite
  phase as regression constraints. Construct it by scanning each round's three
  reviewer reports (`correctness.md`, `edge-cases.md`, `conventions.md`) and
  collecting every finding whose status resolved to CLOSED in a later round's
  closure table. Each entry has the shape:
  ```
  { finding_id: "correctness/R1/F-3", title: "process_divergent no-op",
    closed_in: "round-2", evidence: "spec § Out of scope line 14" }
  ```
  A finding counts as CLOSED when a subsequent round's closure table marks it
  CLOSED with evidence. Duplicates across lenses (same root issue surfaced by
  two reviewers) are merged — keep the first-seen ID, note the duplicate.
  The manifest is ephemeral (constructed in-context, not written to disk).
  Every entry is a regression constraint: the rewritten spec must preserve
  the fix that closed it.
- Blank-slate rewrites are forbidden at round 4. The historical "patches stop
  converging, restart" failure mode applied to plans, not to specs with
  established cross-section invariants.

### 2f. Halt condition

If after round 4 the spec is still red, do **not** auto-proceed. Print:
```
SPEC NOT GREEN AFTER 4 ROUNDS.
Remaining P0/P1:
  - <round 4 correctness P0/P1 titles>
  - <round 4 edge-cases P0/P1 titles>
  - <round 4 conventions P0/P1 titles>

Spec at: docs/specs/TODO/<TICKET-ID>.spec.md
Reviews at: docs/specs/TODO/<TICKET-ID>.reviews/

What would you like to do?
1. Patch manually and re-run /spec-cycle
2. Skip /ship-spec and ship by hand
3. Treat as scoped-down — narrow the brief
```

Wait for the user.

## Phase 3 — Drift-check checklist (HARD STOP)

When the spec is green, render this output verbatim, with sections populated from the brief:

```
=== SPEC READY: <TICKET-ID> ===
Path: docs/specs/TODO/<TICKET-ID>.spec.md
Rounds: <N> (green at round <N>)

=== DRIFT CHECK against brief ===

Decisions carried in brief:
  [ ] 1. <decision title from brief> — preserved in spec? (yes/no/note)
  [ ] 2. ...

Done-when criteria:
  [ ] 1. <criterion from brief> — mapped to spec section?
  [ ] 2. ...

Out-of-scope fences:
  [ ] 1. <fence from brief> — any spec section violates it?
  [ ] 2. ...

=== NEXT ===
When ready, run:
  /ship-spec docs/specs/TODO/<TICKET-ID>.spec.md
```

### Brief-section parsing rules

Parse the brief for these headers (case-insensitive, allow trailing punctuation):
- `Decisions carried forward` / `Decisions` / `Decisions made` → enumerate the numbered list under the header
- `Done when` / `Acceptance criteria` → enumerate
- `Out of scope` → enumerate

If a header is missing, render a single fallback bullet for that section: `[ ] Did the spec address everything in the brief? Anything in the brief absent from the spec?`

Use the **first paragraph** or **bolded clause** of each numbered item as its checklist label — keep it short.

After printing the checklist, **do not auto-proceed**. The user invokes `/ship-spec` separately when ready.

## Tool-use notes

- Read, Edit, Write for spec authorship and revision.
- Bash for `git fetch upstream` (ref update only, bounded by timeout), `git log` / `git remote` / `git rev-list` / `git symbolic-ref` / `sed` (read-only), and `mkdir` for review subdirs.
- Agent calls (parallel) for the three reviewers.
- MCP memory server's search capability (e.g., `mcp__claude_ai_Vigil_Harbor_MCP_Server__memory_search` in Claude Code, or the equivalent semantic-search tool in your host) for Plane ticket lookup (tags: [plane_work_item, <TICKET-ID>], namespace from states.json). Falls back to brief alone on zero results or error response.
- Do not commit. Do not push. Do not open PRs. That's `/ship-spec`'s job.

## Failure modes to watch for

- **Stale spec read.** Always re-read from disk at the start of each round. Do not trust the spec content from your own prior write.
- **Reviewer status drift.** If a reviewer doesn't end with a parseable `STATUS:` line, treat its report as `STATUS: RED P0=1 P1=0` (count one P0 for "missing status") and surface it as an issue.
- **Severity inflation.** If a single reviewer is producing >5 P1 findings consistently, that's a signal to re-check whether the reviewer is following the severity definitions. The fix is to push back through the prompt — but in v1 just trust the loop.
- **Ticket not in MCP memory cache.** When `memory_search` returns zero results or an error for the ticket, warn-and-proceed using only the brief. The brief is the local source of truth. This covers cold-cache (ticket untouched since MCP-33 shipped) and MCP memory outage.
- **Wiki path mismatch.** CLAUDE.md may hardcode a username-bearing wiki path. Try replacing the username with the current user (Windows: `$env:USERNAME`; Unix: `$USER`) and use whichever exists.
- **Upstream remote missing or unreachable.** Skip silently — vigil-harbor's own repos will hit this branch by design. CAL is the lone fork today. Cost: one sub-millisecond `git remote get-url` call.
- **Search-term extraction false negative.** The heuristic is best-effort. A missed upstream commit means the user pays the pre-VHS-6 wasted-rounds cost; no worse than today.
