# Correctness Review — round 2

## Closure of round 1 findings
All round-1 P0/P1 CLOSED (verified against the current spec on disk + re-verified upstream `src/targets/`, `loadClaudePlugin`, `js-yaml`, `opencode.ts`):
- correctness/F-1 (OpenClaw not emittable) — CLOSED: OpenCode/Codex throughout; OpenClaw only as the named non-target.
- correctness/F-2 (Claude Code passthrough) — CLOSED (spec); see F-1 below for the brief lag.
- correctness/F-3 (one target vs at least one) — CLOSED: D6 binds on "at least one inherited target."
- correctness/F-4 (docs untracked) — CLOSED (spec): Prerequisite note added.
- correctness/F-5 (reject-list version-dependent) — CLOSED: D3 fork-point-SHA removal surface.
- edge/F-1..F-7, conventions/F-1..F-6 — all CLOSED per cross-lens verification.

## Findings

### F-1: Brief still carries the "Claude Code passthrough" framing the spec calls a category error
**Severity:** P2 · **Pre-ship recommended:** yes
**Where:** brief.md:26, brief.md:43 vs spec D6 path (a), spec Done-when #3
**Why:** Round-1 fix corrected the brief's *OpenClaw* mentions but not "Claude Code passthrough," which survives at brief:26/43. The spec (D6) calls that exact framing a category error (Claude Code is the converter input, not a `--to` target). Spec Done-when #3 and brief Done-when #3 disagree; spec line 7's "brief mentions corrected" overstated for this phrase. Spec is internally consistent + implementable — this is brief-vs-spec artifact drift on a Done-when criterion.
**Fix:** Correct brief:26/43 to "source ingestion / parse check" (fold into this PR) and narrow spec line 7's claim. [Addressed in 2g.]

### F-2: OpenCode output-shape claim accurate — positive verification, no change
**Severity:** P3
Verified `src/targets/opencode.ts` emits `opencode.json` + `.opencode/{agents,commands,skills,plugins}/`. Codex fallback + roster (codex/gemini/kiro/opencode/pi) confirmed. No change.

## Summary
P0: 0 | P1: 0 | P2: 1 | P3: 1 | P4: 0

Upstream re-verified 2026-06-14: `src/targets/` (no openclaw.ts), `src/parsers/claude.ts` loadClaudePlugin (manifest-required, throws, reads `<root>/skills/`), `src/utils/frontmatter.ts` (js-yaml load), `claude-to-opencode.ts` convertHooks emits `converted-hooks.ts` with `await $`...`` (validates D2 Bun-aware sink set + non-claim), `opencode.ts` output shape. No new contradiction/nonexistent-ref/stale-anchor from the round-2 revision; sole residual is the brief-artifact lag in F-1.

STATUS: GREEN
