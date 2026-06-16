# AGENTS.md

Project instructions for any AI agent working in the **vigil-skills** repo. Harness-neutral by intent — written for Claude Code, Hermes, or any agent that reads an `AGENTS.md`. Machine-local paths and personal tips live in a gitignored `CLAUDE.md` (or your harness's local config) that points here.

## What this repo is

Cross-machine agent skills and subagents. Not an application — no build step, no test suite, no dependencies beyond Python 3.8+ stdlib. The repo is a source-of-truth mirror for files that get installed into your agent's config dir (for Claude Code: `~/.claude/skills/` and `~/.claude/agents/`).

## Sync commands

```bash
python sync.py install          # repo → ~/.claude/ (daily driver after git pull)
python sync.py push             # ~/.claude/ → repo (commit back in-place edits)
python sync.py status           # diff between repo and ~/.claude/
```

Flags: `--dry-run`, `--verbose`, `--prune` (install only), `--claude-dir <path>`.

## Architecture

### Workflow: spec lifecycle

Three skills form the spec lifecycle. The authoring/impl pair runs in separate sessions to avoid token-cap pressure; the post-merge close runs after code ships:

1. **`/spec-cycle <brief-path>`** — Authors a spec from a brief, then runs a parallel review loop — three default lenses plus an optional fourth scalability lens — up to 4 rounds. Halts at a session boundary with a drift-check checklist. Does not implement or commit anything.

2. **`/ship-spec <spec-path>`** — Takes the green-lit spec through implementation in an isolated git worktree, test gate (up to 5 iterations), commit, PR via `gh`, and Plane ticket state update. The user's primary working tree is never touched.

3. **`/spec-close <spec-path> [--report-only | --partial]`** — After ship-spec's PR merges, close the spec in one pass: reconcile it against shipped code (writes `<TICKET-ID>.reconciliation.md` — the lone pre-confirmation write), propose wiki entries (decisions, comprehension, state.md updates), archive spec artifacts from `TODO/` to `DONE/<TICKET-ID>/` (ticket prefix stripped from filenames), and append to wiki `log.md`. Partial-close is detected and offered when the Plane ticket isn't in a completed state; `--report-only` writes just the reconciliation report; `--partial` forces archive-only. All mutations after the report require user confirmation before execution.

### Parallel review agents

`spec-cycle` dispatches read-only reviewer subagents **in parallel** (single message — three by default, plus an optional fourth when the brief declares scale):

| Agent | Lens | Key concern |
|-------|------|-------------|
| `spec-reviewer-correctness` | Does it solve the brief? | Nonexistent references, unmet acceptance criteria, internal contradictions |
| `spec-reviewer-edge-cases` | What breaks it? | Empty inputs, concurrency, external-system failures, observability gaps |
| `spec-reviewer-conventions` | Does it follow the repo? | AGENTS.md / CLAUDE.md rules, wiki decisions, premature abstractions, duplicate code |
| `spec-reviewer-scalability` | Does it hold at N×? *(optional — dispatched only when the brief declares scale)* | Batching, algorithmic complexity, unbounded accumulation, per-instance state collision, uncapped fan-out, cost/token budget |

Each agent emits a `STATUS: GREEN` or `STATUS: RED P0=<n> P1=<n> ...` last line. The orchestrator parses this to gate the loop.

### /review-pr

Standalone skill for triaging CodeRabbit review comments. Reads findings, verifies against current code, fixes real issues, pushes, posts per-thread commit-hash replies (`Resolved in <sha>`), conditionally waits for CodeRabbit's incremental re-review, and polls for auto-approval. Non-fix threads (skip/duplicate/already-fixed) are left open for CodeRabbit and the user to handle naturally. Checks `.coderabbit.yaml` for `request_changes_workflow: true` to determine whether auto-approval is expected.

### File layout

- `skills/<name>/SKILL.md` — Skill definitions (YAML frontmatter + markdown body). Installed to `~/.claude/skills/<name>/SKILL.md`.
- `skills/ship-spec/states.json` — Committed config mapping project identifiers to state UUIDs, MCP namespaces, and review-state IDs. Synced alongside SKILL.md by `sync.py`.
- `agents/<name>.md` — Subagent definitions (YAML frontmatter + markdown body). Installed to `~/.claude/agents/<name>.md`.
- `sync.py` — Bidirectional file sync. Stdlib only, cross-platform via `pathlib`.
- `skills/spec-close/SKILL.md` — Post-merge close skill (reconciliation + wiki harvest + archive in one pass). Installed to `~/.claude/skills/spec-close/SKILL.md`.
- `docs/customizing.md` — How downstream projects configure these skills via their own `AGENTS.md` / `CLAUDE.md`.
- `docs/portability-contract.md` — What makes a skill portable across harnesses (VHS-17); the contract every cross-harness item targets.
- `docs/authoring-portable-skills.md` — Authoring discipline for portable skills + the `lint.py` portability lint (VHS-18).

## Plan & Spec Reviews

- Always verify load-bearing claims against the actual codebase, wiki, and current file state before critiquing — never review from memory or stale buffers.
- Re-read files at the start of each new review pass; the user iterates plans frequently and stale context produces false-positive findings that require retraction.
- Deliver findings as severity-ranked lists (critical/high/medium/low) with specific `file:line` references.

## Conventions

- Skills use `name`, `description`, `user_invocable`; agents use `name`, `description`.
- Reviewer agents are **read-only** — they must never edit files or mutate git state.
- Severity scale is shared across all reviewers (the three default lenses plus the optional scalability lens): P0/P1 block shipping; P2+ do not. Reserve P0/P1 for genuinely load-bearing issues.
- `sync.py` mirrors only the `skills/` and `agents/` subtrees (defined in `SUBTREES`). Adding a new top-level subtree requires updating that tuple.
- Specs, briefs, and reviews live in the **target project** at `docs/specs/TODO/<TICKET-ID>.*`, not in this repo.
- A brief may carry an optional `## Scale` section to turn on the scalability reviewer: `**Factor:** yes` plus a `**Target:**` line (the target N the design must hold at — requests/sec, records, tenants, $/op, etc.) enables the lens; `**Factor:** no` (or `none` / `n/a`) records scale as an explicit non-factor. Absent the section, the lens stays off and the loop runs the three default lenses unchanged. See `docs/spec-workflow-reference.md` § "Optional scalability lens" for the full grammar.
- `CLAUDE.md` is gitignored (it holds machine-local absolute paths). Anything that must ship in a PR — including "referenced from project guidance" pointers — belongs in a **tracked** file (`AGENTS.md`, `README.md`, or `docs/`), not `CLAUDE.md`.

## Post-merge wiki update

After a PR merges, run `/wiki-after-merge <commit-sha>` **from the wiki directory**. It appends to `log.md`, deltas the filemap, scaffolds comprehension entries for large changes, and chains to `/wiki-state-update` for status flips. Idempotent — safe to re-run for the same SHA. Manual edits are fine for trivial single-file fixes; the skill handles everything else.

State.md edits require an evidence triple (Plane ID, date, commit hash) — the wiki's pre-commit hook enforces this. See the wiki's `CLAUDE.md` § "Editing state.md safely" for field rules per section.

## Git Hygiene

- Before committing, audit staged paths for stale skill copies, backup files, and large binaries; add to `.gitignore` rather than committing.
- After context compaction or long sessions, verify no orphaned cron jobs or background tasks were left running.

## External dependencies (runtime, not build)

- **plane-proxy** — state updates (write) and reachability checks (preflight). Ticket reads now flow through MCP memory via `memory_search` (cached by MCP-33 webhook receiver). Skills warn-and-proceed on cache miss.
- **`gh` CLI** — PR creation, CodeRabbit thread management. Must be authenticated.
- **CodeRabbit** — configured on target repos for `/review-pr`.

## Machine-local config

Absolute paths specific to your machine — your installed-config dir and the `vigil-harbor-wiki` checkout location (the latter is what the skills' preflight resolves as `wiki_root`) — live in your local, gitignored `CLAUDE.md`, which points here for everything else.
