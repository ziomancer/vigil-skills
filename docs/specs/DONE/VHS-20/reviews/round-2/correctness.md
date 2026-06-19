# Correctness Review — round 2

## Closure of round 1 findings
All round-1 findings CLOSED, verified against current spec text + real vigil-converter sources at HEAD `14cdca4f`:
- correctness/F-1 (assertion 3 `memory` contradiction) — CLOSED; assertions 3/4 rewritten, mutually consistent with D8 fixture + D4.
- correctness/F-2 (copySkillDir clobber) — CLOSED; transform-callback mirror (opencode.ts:125-131) + "generated SKILL.md must win". Verified feasible vs real `copySkillDir(content)=>string` (files.ts:165-170).
- correctness/F-3 (stale anchor) — CLOSED; now 125-131.
- correctness/F-4 (signature/null/casts) — CLOSED.
- correctness/F-5 (Done-when 1 phrasing) — CLOSED.
- edge/F-1 (malformed-YAML) — CLOSED; parser claim verified (parseFrontmatter throws frontmatter.ts:35; loadSkills no try/catch claude.ts:128-130).
- all other edge/conventions round-1 findings — CLOSED (verified in spec text).

## Findings

### F-1 (P3): D6 rationale misdescribes `resolveCodexHome` — it already expands the env value
spec.md:100. `resolveCodexHome` (resolve-home.ts:19-22) returns `resolveTargetHome(value, path.resolve(expandHome(defaultPath)))` — the env-derived default IS passed through `expandHome`. So the "improvement over codex (which expands only the flag)" claim is false; the prescribed behavior is correct but the rationale is wrong. Fix: state `resolveHermesHome` mirrors `resolveCodexHome` exactly (both expand flag + env); drop the "improvement" framing.

### F-2 (P3): Tier-1 assertion 3 pre-flight enumeration omits `shell`/`terminal`
spec.md:213 vs D3 template spec.md:74. The D8 fixture declares `shell: true` (required), so the generated `Required:` line should name terminal/shell alongside network/subagents/filesystem/issue-tracker. Assertion 3 drops it. Not a hard contradiction (substring presence check passes on a superset) but it under-pins the emitter. Fix: add `shell`/`terminal` to assertion 3's list, or state it checks a representative subset.

### F-3 (P3): collision-guard anchor mis-framed — opencode.ts:94-101 is the *agent* guard, not the skill loop
spec.md:177. The OpenCode skill loop (120-132) has no `seen` Set; 94-101 guards agents. The cited range is a valid *pattern* to copy (skip-with-warning), so the instruction is implementable, but the framing implies OpenCode guards skill collisions this way. Fix: note 94-101 is the agent guard borrowed as a pattern (the Hermes skill writer adds the guard the OpenCode skill loop lacks).

## Summary
P0: 0 | P1: 0 | P2: 0 | P3: 3 | P4: 0

STATUS: GREEN
