---
name: spec-cycle
description: Author a spec from a brief, then run a 3-lens parallel review loop (correctness / edge-cases / conventions) until findings are clean or 4 passes complete. Halts at a session-boundary HARD STOP with a structural drift-check checklist before any implementation. Pair with /ship-spec to take an approved spec through implementation, PR, and Plane update, then /spec-close after the PR merges.
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

1. Resolve `<brief-path>` from the user's invocation and normalize it to a
   project_root-relative path with forward slashes (this normalized form is
   what later phases — including the 2b reviewer prompts — carry). The
   canonical shape is `docs/specs/TODO/<TICKET-ID>.brief.md`, but two
   alternates are tolerated on input:
   - **Alternate directories** — the brief may live anywhere in the repo
     (e.g., `docs/briefs/`).
   - **Descriptive-suffix filenames** — `<TICKET-ID>-some-slug.md`.

   If the resolved path is not under `project_root`, halt and ask the user
   to either move the brief into the repo or confirm proceeding; on
   confirm, carry the absolute path instead of the normalized relative
   form (reviewer access to out-of-root paths is host-dependent).

   Extract `ticket_id` with an anchored prefix match on the filename:
   `^[A-Z][A-Z0-9]*-[0-9]+` (e.g., `PROJ-86-fix-API-33-regression.md` →
   `PROJ-86`; anchoring disambiguates embedded ID-shaped tokens, and the
   `[A-Z0-9]*` tail admits digit-bearing project prefixes like `WEB3-12`).
   If the filename has no match, ask the user for the ticket ID before
   continuing.

   `project_root` is the cwd (the directory containing `CLAUDE.md`).

   **Canonical artifact location:** regardless of where the brief lives,
   every spec-cycle artifact — `<TICKET-ID>.spec.md`, the
   `<TICKET-ID>.reviews/` tree, and downstream ship-spec outputs — lands
   in `docs/specs/TODO/`. A brief outside that directory stays where it
   is: tolerated on input, never moved or promoted. If brief and spec end
   up in different trees, that is a documented consequence of the brief's
   location, not an accident.
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

5. Origin sync check. Sibling of step 4 — same skip-silently / warn-and-prompt
   idiom, applied to the local-branch-vs-origin axis. Reviewers cold-read the
   local tree, so a merged-but-unpulled change is a false-positive generator
   that pollutes the convergence signal. This step contains the skill's lone
   git-level mutation of existing tracked files, and it is strictly opt-in.
   Catch-all: any git command failure inside this step not handled by an
   explicit branch below → log `origin: skipped (git error)` and continue to
   step 6; never halt on this step's account.

   a. **Detect origin remote:**
      ```bash
      git remote get-url origin 2>/dev/null
      ```
      If exit ≠ 0: log `origin: skipped (no remote)` and continue to step 6.

   b. **Refresh origin refs:**
      ```bash
      timeout 30 git fetch origin 2>/dev/null
      ```
      Ref update only — never touches the working tree. Network failure is
      non-fatal: log `origin: fetch failed (proceeding with available refs)`
      if exit ≠ 0 and continue with whatever `origin/*` refs are already
      local. (Fetch runs before branch resolution — unlike step 4's b/c
      order — so a counterpart branch fetched for the first time is visible
      to the existence check in 5c.)

   c. **Resolve branches:**
      ```bash
      git symbolic-ref --short -q HEAD
      ```
      - Empty output (detached HEAD): log `origin: skipped (detached HEAD)`
        and continue to step 6.
      - Otherwise capture the output as `<branch>` (the current branch),
        then bind the comparison branch `<cmp>`:
        - If `git rev-parse --verify -q origin/<branch>` succeeds:
          `<cmp>` = `<branch>` — a **counterpart comparison**.
        - Otherwise fall back to the default branch: `git symbolic-ref
          refs/remotes/origin/HEAD 2>/dev/null | sed 's|^refs/remotes/origin/||'`;
          on error or empty output try `main` then `master` as literals
          (existence via `git rev-parse --verify origin/main` /
          `origin/master`) — the same fallback chain as step 4b. Set `<cmp>`
          to the first that resolves — a **fallback comparison**. If none
          resolve: log `origin: skipped (no comparison branch)` and continue
          to step 6.

   d. **Behind count:**
      ```bash
      git rev-list --count HEAD..origin/<cmp>
      ```
      If 0: log `origin: in-sync` and continue to step 6. (A local branch
      that is *ahead* of `origin/<cmp>` with no incoming commits also
      counts 0 — in-sync for staleness purposes.)

   e. **Warn; offer a fast-forward only for a counterpart comparison:**

      - **Fallback comparison (`<cmp>` ≠ `<branch>`) — informational only.**
        Warn: `local <branch> has no origin counterpart; the local tree is
        <N> commits behind origin/<cmp> — reviewers may cold-read stale
        files.` Log `origin: behind-N (informational — no counterpart)` and
        continue to step 6. No update is offered: fast-forwarding `<branch>`
        onto `origin/<cmp>`'s tip would move a topic branch onto another
        branch's history — a mutation outside this step's mandate.

      - **Counterpart comparison (`<cmp>` = `<branch>`):** check feasibility:
        ```bash
        git merge-base --is-ancestor HEAD origin/<branch>
        ```
        - **Exit 0 — HEAD is an ancestor; fast-forward is possible.** Prompt:

          ```text
          ORIGIN SYNC: local <branch> is <N> commits behind origin/<branch>.
          Reviewers cold-read the local tree; merged-but-unpulled changes
          generate false-positive findings.

          What would you like to do?
          1. Fast-forward update now (git merge --ff-only origin/<branch>)
          2. Proceed on the stale tree
          ```

          Wait for the user's response.
          - On update: run `git merge --ff-only origin/<branch>`. On
            success, log `origin: behind-N (updated)`, then re-validate the
            preflight reads the update may have staled: re-confirm the brief
            exists at the resolved path (step 2) and re-read CLAUDE.md
            (step 3); if `docs/specs/TODO/<TICKET-ID>.spec.md` arrived with
            the update, halt and ask before Phase 1 would overwrite it. If
            git aborts the merge (e.g., uncommitted local changes would be
            overwritten), print git's error verbatim, log `origin: behind-N
            (update failed — proceeded)`, and continue on the stale tree —
            never retry with merge, rebase, or stash.
          - On proceed: log `origin: behind-N (user proceeded)`.
        - **Exit 1 — histories have diverged; fast-forward is impossible.**
          Do not offer an update. Warn:
          `local <branch> and origin/<branch> have diverged (<N> behind);
          fast-forward impossible — proceeding on the local tree.`
          Log `origin: behind-N (diverged — proceeded)` and continue. No
          merge, no rebase, ever.
        - **Exit > 1 — git error** (bad ref, shallow-clone history boundary):
          handled by the step-level catch-all — log `origin: skipped (git
          error)` and continue to step 6.

6. Confirm plane-proxy is reachable: call the plane-proxy's project-list capability (e.g., `mcp__plane__list_projects` in Claude Code, or the equivalent in your host's Plane integration). On failure, **warn and proceed** — the brief is the local source of truth.
7. Read `~/.claude/skills/ship-spec/states.json` (`~/.claude/` on Unix; `%USERPROFILE%\.claude\` on Windows) (installed by `sync.py`). If the file is not found, default `namespace` to `"plane"` and warn — ticket lookup still works (MCP-33 fallback namespace is `"plane"` for unmapped projects); namespace-scoped precision is degraded but not broken. If the file exists but cannot be parsed (invalid JSON or unexpected shape), warn and default `namespace` to `"plane"`. Otherwise, extract the ticket prefix (the portion before the first hyphen in `ticket_id`, e.g., `"PROJ"` from `"PROJ-123"`) and look up that prefix in `states.json` to get the `namespace`. If the prefix is not in `states.json`, default `namespace` to `"plane"` and warn. Pass `namespace` to Phase 1's own `memory_search` call and to each reviewer agent in step 2b.

Print a one-line preflight summary — including the upstream check result token (clean / skipped / N stale — user proceeded) and the origin check result token (in-sync / behind-N (updated) / behind-N (user proceeded) / behind-N (update failed — proceeded) / behind-N (diverged — proceeded) / behind-N (informational — no counterpart) / skipped (<reason>)) — then continue.

## Phase 1 — Author v1 spec

Output path: `docs/specs/TODO/<TICKET-ID>.spec.md`.

Read the brief, the linked Plane ticket (call the MCP memory server's search capability — e.g., `mcp__claude_ai_Vigil_Harbor_MCP_Server__memory_search` in Claude Code, or the equivalent semantic-search tool in your host — with `tags: ["plane_work_item", "<TICKET-ID>"]`, `namespace` from step 7, `source_system: "plane"`, `max_results: 1`; if the memory server is unavailable or returns zero results, proceed using the brief alone), and any files the brief points at. Write a spec that covers, at minimum:

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
- `brief_path: <the brief path resolved and normalized in Phase 0 step 1 — project_root-relative, forward slashes — not the canonical template>`
- `project_root: <absolute>`
- `ticket_id: <TICKET-ID>`
- `namespace: <resolved from preflight step 7, default "plane">`
- `round_number: <N>`

For the conventions reviewer additionally:
- `wiki_root: <absolute path to wiki, resolved in preflight>` (omit if no wiki configured)
- `project_slug: <e.g., myproject>`

For rounds N > 1, each agent's prompt must additionally include a
closure-manifest block — the author's stated disposition of every
round-(N−1) P0/P1 finding, one line each:

```text
closure_manifest (round <N-1> → <N>):
  - <lens>/<finding-id> (P<sev>) "<title>" — <how addressed, with spec § anchor>
  - correctness/F-2 (P1) "stale anchor in § Design" — fixed: re-anchored to SKILL.md:142
```

P0/P1 findings only (P2 dispositions are visible in the spec's edits or
its `## Deferred (P2+)` section). A synthetic missing-STATUS P0 (per
`## Failure modes`) appears as
`<lens>/STATUS (P0) "missing STATUS line" — <disposition, e.g. report
regenerated in round N>` so the manifest always reconciles with the prior
round's gate arithmetic. This block complements — does not replace — the
reviewers' step-7 disk-read closure verification: the agents verify the
author's claims against the current spec instead of inferring intent from
a spec diff. Build it from the revision work you just did in 2e. Map each
P0/P1 finding to exactly one line: finding ID, severity, the title copied
from the prior-round report, then a concise disposition phrase — e.g.,
`fixed: edited § <section>`, `reworked: deliberate direction change, see
§ <Decision n>`, or `not applicable: <one-line reason>` — always with a
spec § anchor the reviewer can verify.

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

If `total_p0p1 == 0`: break the loop. Spec is green at round N. Run the post-green polish step (2g) before Phase 3.

A reviewer may return `STATUS: RED` with only P2+ findings (P0=0 P1=0). This does not block the loop since the gate checks `total_p0p1 == 0`. P2+ items are advisory — they are carried forward as spec notes in the `## Deferred (P2+)` section but do not prevent the spec from going green. On the green round, the carry into `## Deferred (P2+)` is performed by the post-green polish step (2g); P2s tagged `Pre-ship recommended` by a reviewer are 2g candidates.

### 2e. Revise (rounds 1–3) or rewrite (round 4)

If still red and `round < 4`:
- Edit the spec in place.
- Address every P0 and P1 finding.
- For P2 findings, either fix or list them in a `## Deferred (P2+)` section at the end of the spec with one-line acknowledgments. P2s carrying a reviewer's `Pre-ship recommended` tag become 2g candidates once the spec goes green.
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

### 2g. Post-green polish (bounded)

Runs exactly once, immediately after the gate breaks green (2d) and before
Phase 3. This is not a review round and cannot reopen the loop — the green
verdict stands regardless of what happens here. Note: the round that goes
green never runs 2e, so the final round's P2s exist only in the persisted
reports; this step performs their carry-forward bookkeeping. If a
`## Post-green polish` section already exists in the spec, treat 2g as
already-run: reconcile (merge/dedup) rather than append.

1. Collect candidates: P2 findings carrying the explicit
   `**Pre-ship recommended:** yes` marker (see the reviewer output
   contracts) from **all rounds'** persisted reports — not only the final
   round's. Skip any already addressed by an earlier revision; merge
   duplicates across lenses. Fallback for reports without the marker: a P2
   whose prose explicitly recommends folding the change in before
   /ship-spec.
2. If there are no candidates: print `post-green polish: none tagged`,
   record any remaining final-round P2s in `## Deferred (P2+)` (creating
   the section if absent), and proceed to Phase 3.
3. Apply each candidate only if it is a clarification — wording, file:line
   anchors, examples, error-message text, checklist rows. Hard limits: no
   behavior reversals, no new scope, no edits to the spec's Decisions,
   Out-of-scope, or Done-when sections (Done-when may gain parenthetical
   annotations only, never reworded criteria). A candidate that exceeds
   these limits is recorded in `## Deferred (P2+)` (creating the section
   or entry if absent) with a one-line reason.
4. Record each folded P2 in a `## Post-green polish` section at the end of
   the spec: one line each — finding ID and what changed. If the finding
   already has an entry in `## Deferred (P2+)`, remove that entry. Record
   every remaining untouched final-round P2 in `## Deferred (P2+)`.
5. No re-review round runs after polish.

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
- Bash for `git fetch upstream` / `git fetch origin` (ref updates only, bounded by timeout), `git log` / `git remote` / `git rev-list` / `git rev-parse` / `git symbolic-ref` / `git merge-base --is-ancestor` / `sed` (read-only), `mkdir` for review subdirs, and — the lone git-level mutation of existing tracked files in this skill — `git merge --ff-only origin/<branch>`, run only after explicit user confirmation in Phase 0 step 5e.
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
- **Origin remote missing or unreachable.** Skip silently (token
  `origin: skipped (no remote)`); fetch failure is non-fatal and proceeds
  with available refs; any other git failure in step 5 not handled by an
  explicit 5e branch (the ff-abort keeps its own token) maps to
  `origin: skipped (git error)`. Same posture as the upstream check.
- **Diverged local branch.** Fast-forward is impossible — warn and proceed;
  never merge or rebase. Likewise, a user-confirmed ff update that git
  aborts (uncommitted changes in the way) proceeds on the stale tree after
  printing git's error. In both cases reviewers may still produce
  stale-tree false positives; the warning names the cause, which is the
  bulk of the value.
