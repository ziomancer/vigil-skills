# Customizing Vigil Skills for your project

These skills are intentionally generic. Project-specific rules live in your project's `CLAUDE.md` — the skills read it during preflight and apply what's there.

## What to put in your `CLAUDE.md`

### Build & Run section

`/ship-spec` and `/spec-cycle` look for a "Build & Run" section to discover your default test command. Example:

````markdown
## Build & Run

```bash
npm install
npm run build       # tsc -> dist/
npm test            # all tests
npm run lint        # eslint
```
````

`/ship-spec` will form a combined command like `npm run build && npm test && npm run lint` as its test-gate fallback. Per-spec overrides go in the spec's `## Test command` section, which takes precedence.

### Project guardrails

If your project has load-bearing rules — async handling, error patterns, ordering constraints — list them here. The reviewers and `/ship-spec` will respect them. Example:

```markdown
## Conventions

- All `recorder.record*` calls must be `await`ed; unawaited calls cause sequence-index collisions.
- Tools return text strings, never throw exceptions.
- TypeScript ESM with `.js` extensions in imports.
```

### Wiki integration (optional)

The `spec-reviewer-conventions` agent can read a wiki for prior decisions. If you have one, point at it:

```markdown
## Wiki

Path: `~/code/myproject-wiki`
Slug: `myproject`
```

The agent will read `<wiki>/projects/<slug>/architecture.md`, `state.md`, `filemap.md`, and scan `<wiki>/decisions/` for relevant prior decisions.

If you don't have a wiki, omit `wiki_root` from the orchestrator prompt and the agent skips this step gracefully.

## Spec & brief layout

Skills assume:

- Briefs at `docs/specs/TODO/<TICKET-ID>.brief.md` (loose: just enough to get started)
- Specs at `docs/specs/TODO/<TICKET-ID>.spec.md` (`/spec-cycle` writes here)
- Reviews at `docs/specs/TODO/<TICKET-ID>.reviews/round-<N>/<lens>.md`
- Test output captured to `docs/specs/TODO/<TICKET-ID>.test-output.txt`

Adjust the layout in your fork if needed; the skills hardcode these paths today.

## Plane.so integration

`/spec-cycle` and `/ship-spec` use the Plane MCP server for ticket lookup and state updates. Configure it per Plane's docs.

`/ship-spec` flips a ticket to a review-equivalent state after PR open. The skill reads `skills/ship-spec/states.json` and uses the `review_state_id` field for the project. If your project isn't in `states.json` or has no `review_state_id`, the skill skips the flip and reports the available state names so you can update manually. To add a new project, call the Plane MCP server's state-list capability (e.g., `mcp__plane__list_states` in Claude Code, or the equivalent in your host's Plane integration) for the project and add an entry to `states.json`.

## Default branch

`/ship-spec` discovers your default branch via `git symbolic-ref refs/remotes/origin/HEAD` (with a `git remote show origin` fallback). Works for `main`, `master`, `trunk`, etc. — no hardcoding required.

## Worktree path

`/ship-spec` cuts a sibling worktree at `<project-root>/../<TICKET-ID>-worktree`. Your primary working tree is never touched. If you want a different convention, fork and adjust Phase 1 step 2 of the skill.
