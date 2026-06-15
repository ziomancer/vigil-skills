# Vigil Skills

Cross-machine skills and subagents for Claude Code. A Plane.so-aware spec → review → ship workflow with parallel reviewers, plus a CodeRabbit triage handler.

## What's here

### Skills

- **`/spec-cycle <brief-path>`** — Author a spec from a brief, then run a 3-lens parallel review loop (correctness / edge-cases / repo-conventions) until findings clean or 4 passes complete. Halts at a session boundary with a structural drift-check checklist before any implementation. Pair with `/ship-spec`.
- **`/ship-spec <spec-path>`** — Take a green-lit spec through implementation, test gate, PR, and Plane update. Cuts an isolated git worktree from your default branch (your primary working tree is never touched), implements + tests in a tight loop, captures test output for the PR audit trail, and pushes a PR.
- **`/review-pr [<num>]`** — Process one round of CodeRabbit review findings on a GitHub PR. Triages by severity, fixes real issues, pushes, resolves threads, and verifies the resolve actually took.

### Subagents

The `spec-cycle` skill dispatches three reviewers in parallel:

- **`spec-reviewer-correctness`** — Does the spec actually solve the brief's problem? Verifies every claim about current code by reading the actual files.
- **`spec-reviewer-edge-cases`** — Empty/null/zero-length inputs, concurrency, external-system failures, runtime preconditions, observability/tripwire requirements.
- **`spec-reviewer-conventions`** — Repo conventions (CLAUDE.md), prior decisions (your wiki, if any), premature abstractions, reuse vs. duplicate, unneeded backwards-compat.

## Install

```bash
git clone https://github.com/<your-username>/vigil-skills.git
cd vigil-skills
python sync.py install
```

This copies repo content into `~/.claude/skills/` and `~/.claude/agents/`. Files in those directories that aren't in this repo (e.g., third-party skills installed separately) are preserved by default.

## Sync workflow

| Command | Direction | Use case |
|---------|-----------|----------|
| `python sync.py install` (or `pull`) | repo → `~/.claude/` | Daily driver after `git pull`. |
| `python sync.py push` | `~/.claude/` → repo | When you've edited a skill in place and want to commit back. Only touches files already tracked in the repo. |
| `python sync.py status` | (none, diff only) | Show what differs between repo and `~/.claude/`. |

Flags: `--dry-run`, `--verbose`, `--prune` (install only — deletes files in `~/.claude/` not in repo, off by default), `--claude-dir <path>` (overrides `$CLAUDE_CONFIG_DIR` / `~/.claude`).

## Customizing for your project

These skills delegate project-specific rules (test commands, await guardrails, lint conventions) to your project's `CLAUDE.md`. The skills read it during preflight and respect what's there. See [`docs/customizing.md`](docs/customizing.md) for details.

## Cross-harness portability

Skills are authored once as Claude Code `SKILL.md` and meant to run on any harness in the fleet. [`docs/portability-contract.md`](docs/portability-contract.md) defines what makes a skill portable — the canonical source format, the portable frontmatter subset, the `requires:` capability declaration, the intent-over-implementation rule, and the behavioral-parity definition. It is the contract every cross-harness item targets.

## Requirements

- **Python 3.8+** for `sync.py` (stdlib only — no pip install).
- **Claude Code** — skills and subagents are Claude Code features.
- For `/spec-cycle` and `/ship-spec`: a Plane.so workspace with the plane-proxy MCP server, and `gh` CLI authenticated.
- For `/review-pr`: `gh` CLI authenticated, CodeRabbit configured on your repo.

## License

MIT — see [LICENSE](LICENSE).
