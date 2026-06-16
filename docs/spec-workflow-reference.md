# Spec Workflow — Clean-Room Reference

Two AI-driven skills that split spec authoring from implementation into separate sessions. The split is load-bearing: spec context grows with review rounds, implementation context grows with the codebase — combining them risks hitting the context window ceiling mid-flight. The session boundary also means a green-lit spec on disk is a stable artifact: if implementation aborts, you re-run without re-reviewing.

---

## Skill 1: spec-cycle

**Purpose:** Take a short brief (a half-page problem statement with acceptance criteria) and produce a converged engineering spec, reviewed by independent AI agents (three by default, plus an optional fourth scalability lens when scale is declared).

**Invocation:** `/spec-cycle <path-to-brief>`

### Phase 0 — Preflight

Before writing anything:

1. **Read the brief.** Expected location: `docs/specs/TODO/<TICKET-ID>.brief.md`. Extract the ticket ID from the filename.
2. **Read your project's CLAUDE.md** (or equivalent project-instructions file). Note test commands, conventions, and any wiki path.
3. **Look up the ticket in your issue tracker** (Jira, Linear, Plane, etc.) for canonical acceptance criteria. If the tracker is unreachable, proceed using the brief alone — it's the local source of truth.
4. **Upstream staleness check** (for forks). If the repo has an `upstream` remote, extract file paths and code identifiers from the brief, then `git log upstream/<default-branch>` for recent commits touching those paths. If the fork is behind and relevant commits exist, warn the user and ask whether to proceed or abort. For non-fork repos, skip this.

### Phase 1 — Author v1 spec

Write a spec at `docs/specs/TODO/<TICKET-ID>.spec.md` covering at minimum:

- **Goal** — one paragraph: what ships and why.
- **Scope** — files to change, files to create, files explicitly untouched.
- **Design** — the proposed implementation. Non-obvious decisions get their own subsection with rationale. If the brief carries forward explicit decisions (e.g., "rename, don't alias"), the spec must reflect each one.
- **Test plan** — what tests to add/update, what regression tests guard against the bug class.
- **Test command** — the exact shell command(s) to run. This becomes the single source of truth for the implementation skill's test gate. For doc-only or ops-only work where no code ships, set this to `N/A` and provide a review checklist instead.
- **Done when** — bullet list mapped 1:1 to the brief's acceptance criteria.
- **Out of scope** — explicit fences carried from the brief.

### Phase 2 — Parallel review loop (up to 4 rounds)

Each round:

1. **Re-read the spec from disk.** Never trust your own prior write — the file is truth.
2. **Dispatch the reviewer agents in parallel** (one message, multiple agent calls — three by default; a fourth, scalability, when the brief declares scale). Each reviews through a different lens:

   **Correctness reviewer** — Does the spec actually solve the brief? Verifies every claim about current code by reading the actual files. Checks: unmapped acceptance criteria, internal contradictions, references to nonexistent symbols, stale file:line anchors, cross-section consistency (function signatures declared in one section match call sites in another), library API correctness against the project's pinned versions.

   **Edge-cases reviewer** — What breaks it? Probes: empty/null/zero-length inputs, concurrency and races on shared state, external-system failures (down, slow, malformed response), partial-failure consistency, config drift, observability gaps, persistence atomicity/idempotency/size-bounds (for any spec that introduces persisted state). For each axis, asks what the spec says happens and whether that's adequate.

   **Conventions reviewer** — Does it follow the repo? Reads CLAUDE.md, the project wiki (if any), and greps the codebase for established patterns. Checks: stated conventions followed, no contradiction with prior decisions, no premature abstractions (registry/factory at N=1), reuse vs. duplication, no unneeded backwards-compat shims, silent spec additions not authorized by the brief. Also classifies every spec decision as authorized-by-brief, authorized-by-ticket, spec-addition-with-rationale, or silent-addition.

   **Scalability reviewer** *(optional — dispatched only when the brief declares scale a factor)* — Does the design hold at the brief's declared target N? Probes: per-item work that should be batched, O(N) where O(1)/O(log N) exists, unbounded accumulation, per-instance state that collides across instances, fan-out without a concurrency cap, a singular config/path where a power user needs many, plus operational scale (cost-per-op, latency, token/context budget). The differentiator from edge-cases: edge-cases asks "is it correct under one adverse input?"; scalability asks "does the design hold at N×?"

3. **Each reviewer emits a severity-ranked report** with findings at P0-P4 and a machine-parseable last line: `STATUS: GREEN` or `STATUS: RED P0=<n> P1=<n> ...`. P0/P1 block shipping; P2+ are advisory.
4. **Save each report to disk** at `docs/specs/TODO/<TICKET-ID>.reviews/round-<N>/<lens>.md`.
5. **Gate check:** Sum P0+P1 across all dispatched reviewers. If zero, the spec is green — break the loop.
6. **If still red (rounds 1-3):** Edit the spec in place. Address every P0 and P1. P2+ items either get fixed or listed in a `## Deferred (P2+)` section.
7. **If still red at round 4:** Targeted rewrite — classify each spec section as FROZEN (no unresolved P0/P1) or REWRITE. Build a closed-issues manifest from rounds 1-3 as regression constraints. No blank-slate rewrites.
8. **If still red after round 4:** Halt. Present remaining P0/P1 and ask the user what to do (patch manually, ship by hand, or narrow the brief).

**Round 2+ closure tracking:** Each reviewer reads all prior-round reviewer reports present (the three default lenses, plus `scalability.md` when the scaling lens ran) and produces a closure table showing which findings are CLOSED, PARTIAL, REOPENED, or NEW. Reopened items are P0 unless the spec deliberately changed direction with rationale.

### Phase 3 — Drift-check checklist (hard stop)

When the spec goes green, render a structured checklist comparing the spec back to the brief:

- **Decisions carried in brief** — is each one preserved in the spec?
- **Done-when criteria** — is each one mapped to a spec section?
- **Out-of-scope fences** — does any spec section violate one?

Then stop. The user reviews the checklist and invokes the implementation skill separately.

### Optional scalability lens

By default the loop runs the three standing lenses. A brief can turn on a **fourth, scalability lens** — the "case of N" advocate — by declaring scale a factor. The lens is **opt-in per brief**: absent the declaration the loop is unchanged (three standing lenses, identical gate arithmetic and closure-table output). There is no auto-detection — spec-cycle never guesses scale relevance from the spec body.

The toggle is an optional top-level `## Scale` section in the brief. Worked forms:

```markdown
## Scale
- **Factor:** yes
- **Target:** 10^6 records/day; 500 concurrent tenants; ≤ $0.002/op
- **Dimensions:** throughput, multi-tenant fan-out, cost-per-op
```

```markdown
## Scale
- **Factor:** no — single-invocation skill edit; N=1 by nature.
```

How it is read (Phase 0):

- **Heading** — a whole-word `## Scale` or `## Scaling` heading enables detection. `## Scaling considerations` / `## Scale-out plan` do **not** match, so an unrelated prose heading never becomes a false toggle.
- **Factor** — `**Factor:** yes` (or `on` / `true`) turns the lens **on** (a target is required, below); `**Factor:** no` (or `none` / `n/a`) records scale an explicit **non-factor**; anything else, or a missing `**Factor:**` line, leaves the lens **off**.
- **Target** — `**Target:** <N>` states the scale the design must hold at, in any unit (requests/sec, records, tenants, concurrent agents, $/op). It is what lets the lens score blocking (P0/P1) vs. advisory (P2+). `**Factor:** yes` with **no** `**Target:**` does **not** enable the lens — declare-don't-infer.
- **Dimensions** *(optional)* — `**Dimensions:** <free text>` names the scaling axes.

When on, the scalability reviewer is dispatched in the same parallel message as the standing lenses, saves to `round-<N>/scalability.md`, emits the same `STATUS:` contract, and folds its P0/P1 into the same gate and round-2+ closure tracking. A design architecturally unable to reach the declared target N is P1 (the scaling analogue of non-functional code); a self-contradiction against a declared scale "Done when" is P0; a concern that only bites *beyond* the declared target stays P2+. A declared non-factor is surfaced in the Phase 3 drift-check for human confirmation.

---

## Skill 2: ship-spec

**Purpose:** Take a green-lit spec through implementation, test gate, commit, PR, and issue-tracker update. Uses an isolated git worktree so the user's primary working tree is never touched.

**Invocation:** `/ship-spec <path-to-spec>`

### Phase 0 — Preflight

1. **Read the spec.** Confirm it has the expected sections (Goal, Scope, Design, Test plan, Test command, Done when). If it doesn't, it probably hasn't been through spec-cycle — halt and tell the user.
2. **Resolve the test command.** Priority: spec's `## Test command` section (authoritative for this change) > project's CLAUDE.md Build & Run section (fallback). If neither yields a runnable command, halt. If the test command is `N/A`, the automated test gate is skipped entirely.
3. **Discover the default branch** via `git symbolic-ref refs/remotes/origin/HEAD` (fallback: `git remote show origin`). Works for main, master, trunk, etc.
4. **Confirm GitHub CLI is authenticated** (`gh auth status`).
5. **Check issue-tracker reachability.** Warn and proceed on failure.

### Phase 1 — Worktree setup

Implementation runs in an isolated git worktree, not the user's checkout. This avoids stash/restore ceremony, preserves the user's uncommitted changes and branch state, and enables parallel ship-spec runs on different tickets.

1. Form branch name: `<type>/<ticket-id-lower>-<slug>` (e.g., `fix/proj-123-handle-empty-input`).
2. Worktree path: `<project-root>/../<TICKET-ID>-worktree` (sibling directory).
3. Check for worktree-path and branch conflicts — halt if either exists, don't auto-delete.
4. `git fetch origin <default-branch>` then `git worktree add -b <branch> <worktree-path> origin/<default-branch>`.

All subsequent phases run inside the worktree. The spec stays in the user's primary tree (it's metadata, not part of the code change).

### Phase 2 — Implement + author tests

Read the spec and implement everything it describes. Author the tests from the test plan. Tag regression tests with comments like `// Regression for <TICKET-ID>: <one-line>`. Don't commit yet.

### Phase 3 — Test gate loop (up to 5 iterations)

Run the resolved test command. On failure: identify the smallest blocking issue, fix it, re-run. One fix per iteration — keeps the evidence trail clean. Capture full output to `docs/specs/TODO/<TICKET-ID>.test-output.txt`.

If still red after 5 iterations, halt and ask the user: continue with more iterations, drop into manual debug, or roll back and re-spec.

### Phase 4 — Commit

Stage files explicitly (no `git add -A`). Commit with a conventional-commits message:

```
<type>(<ticket-id>): <summary, <=72 chars>

<2-4 sentence narrative>

<File-level change list or layer enumeration>

Co-Authored-By: Claude <noreply@anthropic.com>
```

Don't skip pre-commit hooks.

### Phase 5 — Push and open PR

`git push -u origin <branch>`, then `gh pr create` with a structured body: summary bullets, files-changed table, test plan section linking the captured test output.

### Phase 6 — Issue tracker update

Move the ticket to a review/in-review state. Comment on the ticket with the PR URL. If the tracker is unreachable, print manual instructions and continue.

### Phase 7 — Summary

Print the PR URL, spec path, branch, worktree path. The worktree stays alive for review fixes (the user can `cd` into it and push follow-up commits). Remind the user to clean up the worktree after merge and run any post-merge wiki/docs update workflow.

---

## Adapting to your stack

The skills are designed to be tool-agnostic. The integration points to swap:

| This workflow uses | You'd replace with |
|---|---|
| Plane (issue tracker) | Jira, Linear, Asana, GitHub Issues, etc. |
| `mcp__plane__*` tools | Your tracker's API/MCP/CLI |
| `states.json` (maps ticket prefixes to project IDs and state UUIDs) | Your tracker's project/workflow config |
| `gh` CLI (PRs) | Your git host's CLI (`gh`, `glab`, Bitbucket API, etc.) |
| MCP memory server (cached ticket lookup) | Direct API call to your tracker, or skip |
| Wiki (conventions reviewer reads `decisions/`, `architecture.md`, etc.) | Your team's docs, ADRs, Confluence, Notion — or omit `wiki_root` |
| `docs/specs/TODO/<TICKET-ID>.*` file layout | Whatever path convention you prefer |

The things **not** to change (they're load-bearing):

- **Session boundary between spec-cycle and ship-spec.** Combining them is the #1 failure mode — context exhaustion mid-implementation with no recovery point.
- **Parallel multi-lens review.** Sequential reviews let later reviewers anchor on earlier findings instead of reading independently. Parallel dispatch forces independent reads.
- **Reviewers are read-only.** They never edit files. The orchestrator (spec-cycle) owns all edits. This prevents reviewers from "fixing" things in ways that introduce new issues.
- **STATUS line protocol.** Machine-parseable last line (`GREEN` or `RED P0=<n> P1=<n> ...`) gates the loop. The orchestrator sums P0+P1 across all dispatched reviewers.
- **Round 2+ closure tracking.** Each reviewer reads all prior-round reviewer reports present (the three default lenses, plus `scalability.md` when the scaling lens ran) and produces a closure table. Without this, the loop doesn't converge — reviewers re-raise issues that were already fixed.
- **Targeted rewrite at round 4, not blank-slate.** Blank-slate rewrites regress closed findings. The FROZEN/REWRITE manifest preserves converged sections.
- **Worktree isolation in ship-spec.** Working in the user's checkout means you're one bad `git stash pop` away from losing their uncommitted work.
- **One test fix per iteration.** Bundling multiple fixes makes it impossible to attribute which fix resolved which failure.
