# Authoring Portable Skills

> **Status:** v1 · **Ticket:** VHS-18 (child of VHS-16) · **Enforces:** [`docs/portability-contract.md`](portability-contract.md)

Day-to-day discipline for writing skills that run on any harness in the fleet — the authoring-side companion to the [portability contract](portability-contract.md). The contract defines *what* portable means; this doc tells you *how to write it*, and `lint.py` mechanically guards the parts that can be checked deterministically.

## The four habits

1. **Lead with intent.** Write what the step *achieves*, not which tool performs it. "search the issue tracker for the ticket" — not "call `mcp__plane__retrieve_work_item`."
2. **Declare capabilities.** Every skill should carry a `requires:` block in its frontmatter so a harness can pre-flight what it needs. Copyable template (contract §3):
   ```yaml
   requires:
     shell: true                       # runs terminal/shell commands
     filesystem: [read, write]         # access modes; omit or [] if none
     network: true                     # makes its own outbound requests
     subagents: true                   # dispatches concurrent sub-agents
     services: [issue-tracker?, shared-memory?]   # external providers, by ROLE; '?' = optional
   ```
   Keep it flat (scalars + single-line flow sequences only — no nested mappings); that is what lets the stdlib lint validate it without a YAML dependency.
3. **Never name a harness's tools as the operative instruction.** When you must give an example, tag it: write the harness-neutral capability first, then "*(e.g. `mcp__plane__list_projects` in Claude Code, or the equivalent in your host)*." Keep bare tool-name inventories in a non-operative **"Tool-use notes"** section, never as an executed step.
4. **Don't assume one harness's affordances.** No hardcoded paths, no "the X panel," no reliance on a single harness's file layout beyond what `requires` declares.

## Running the lint

```bash
python lint.py                 # warn-only: prints findings, always exits 0
python lint.py --strict        # exits non-zero if any ERROR (WARNs never gate)
python lint.py skills/foo/SKILL.md   # lint specific files
```

Both modes print a summary to stderr: `lint: <E> error(s), <W> warning(s)`. **Automation should use `--strict`** — its exit code is the contract; the default mode's exit 0 is for advisory local runs.

What it flags:
- **ERROR `operative-tool-call`** — an `mcp__*` tool name used as an operative instruction (not a tagged example, not in a notes/fenced block).
- **ERROR `requires-malformed` / `requires-unknown-key`** — a `requires:` block that violates the contract §3 schema.
- **WARN `missing-requires`** — no `requires:` block (advisory; see promotion path).

## Promotion path: warn-only → blocking

The lint ships **warn-only**. To promote it to a hard gate:
1. **Clear the missing-`requires:` backlog.** Today three shipped skills (`ship-spec`, `spec-close`, `review-pr`) have no `requires:` block — they emit a `missing-requires` WARN. Annotate each with its capability block (VHS-17 annotated only `spec-cycle` as the worked reference). *This is the tracked backlog item.*
2. **Install a pre-commit hook** that runs `python lint.py --strict` (mirroring the wiki's `install-hooks` precedent in shape — stdlib Python, not its Node toolchain). Once step 1 is done, `--strict` is clean and the hook blocks regressions.

## Known v1 limitations (CodeRabbit backstops these)

The lint is the *mechanical* portability check; CodeRabbit's qualitative review covers the rest. Three detection gaps are deliberate v1 scope:
1. **Bare-name detection deferred** — only `mcp__*` identifiers are flagged, not ordinary tool names (`Read`, `Edit`, `Bash`), which are too generic to flag without false positives.
2. **Operative-imperative-under-a-notes-heading** — the contract says an operative call under a "Tool-use notes" heading is still prohibited, but the lint applies the heading presumption flat and won't catch a laundered call there.
3. **Case-2 window is ±1 non-blank line** — an operative call placed directly adjacent to an *unrelated* tagged sentence could be wrongly exempted. The ±1 window is the deliberate tradeoff that avoids false-positives on tags wrapping above/below the token.

The lint also rejects **tab indentation** in a `requires:` block for determinism — slightly stricter than contract §3's written letter.
