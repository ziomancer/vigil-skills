# Conventions Review — round 1

## Closure of round 0 findings
N/A — round 1.

## Findings

### F-1 (P3): README/STRIP/package.json "targets" enumeration — item 13 underspecifies which lists to update
The roster is enumerated in three places: README.md:11-12, README.md:27 (`--to` example), package.json:4 (description string). Item 13 names "STRIP.md and/or README.md" but not package.json. Fix: name package.json:4 explicitly (update or consciously exclude with a note).

### F-2 (P4): `HERMES-MAPPING.md` at repo root is correct — vigil-converter has no `docs/` dir (stripped; STRIP.md:20). Matches brief + repo layout. Confirmed.

### F-3 (P4): Spec-record placement in vigil-skills `docs/specs/TODO/` correct per AGENTS.md:70. Mirrors VHS-19 spec/code split. Confirmed.

### F-4 (P4): Naming (`resolveHermesHome`/`--hermes-home`/`HermesBundle`/`requires`) consistent with `resolveCodexHome`/`--codex-home`/`OpenCodeBundle`. D6 mirrors `resolveCodexHome` (env-read inside resolver) — right one to mirror since `$HERMES_HOME` is an env-precedence level like `$CODEX_HOME`. Confirmed.

### F-5 (P4): `ClaudeSkill.requires` additive field justified, not an over-built shim. loadSkills discards data.requires today; field is required for the adapter to see requires at all; `?`-optional, ignored by the five inherited converters. "future adapters can reuse" is a rationale for the raw shape, not a mandate to build a framework now (correctly fenced out of scope). Confirmed.

### F-6 (P3): js-yaml `dump` for nested frontmatter (D7) correctly avoids the scalar-only `formatFrontmatter`; divergence justified by a real limitation. Recommend naming the import site (`import { dump } from "js-yaml"` in claude-to-hermes.ts) and noting `dump` output must satisfy the Tier-1 YAML round-trip assertion (already present).

### F-7 (P4): D8 fixture edit is in-bounds CI-fixture work — touches a vigil-converter sample, not a shipped vigil skill; does not breach the "backfill requires onto 3 skills" fence (those are in vigil-skills). Current `tools:[bash]` is not a §3 key so the fixture exercises nothing real today; replacing it is necessary. Safety claim verified vs smoke-test.ts:91-114. Confirmed.

### F-8 (P4): "No CI change needed" correct — package.json:16 `test`/`smoke` both run `bun run scripts/smoke-test.ts`; extending the script in place rides the existing CI invocation (consistent with VHS-18's net-new-CI aversion + VHS-19 baseline). Leaving legacy-cleanup.ts untouched honors the no-rewrite rule. Confirmed.

### F-9 (P4): Dropping `user_invocable` (contract §2: informational on Hermes) and not synthesizing `version` (contract §2: optional extension; declare-don't-infer) consistent with contract. Confirmed.

### F-10 (P2, Pre-ship recommended: yes): D9 leaves `required_environment_variables` nesting unresolved, but the emission template + mapping table hardcode the nested placement as settled
The wiki snapshot is genuinely ambiguous: skills-system.md:129-140 describes `required_environment_variables` in a standalone section with no nesting; the metadata.hermes.* fields table (skills-system.md:49-61) does NOT list it — suggesting top-level. The spec's template (spec:144-150) and mapping table (spec:128) place it under `metadata.hermes`. Fix: state the provisional default + fallback explicitly with a cross-ref to D9 ("if re-verify shows top-level, move it out of metadata.hermes; the YAML round-trip assertion does not distinguish the two — must be checked against the live harness").

### F-11 (P3): Spec-level additions beyond the brief, classified for the drift-check
- D3 (preamble not side-file) — authorized-with-rationale; brief says "generate (or wire)", D3 adds the *where* with reasoning grounded in progressive disclosure. Flagged, not silent.
- D4 (optional services → no gating key) — authorized-with-rationale; §3 is silent on optional mapping; D4 grounds it in skills-system.md:120-123 and routes it as feedback to VHS-17 (the brief-authorized path).
- D5 (network/subagents/filesystem → pre-flight only) — authorized by contract §3 table (line 101) + brief:31. Not an addition.
- No silent (unflagged) additions found.

## Summary
P0: 0 | P1: 0 | P2: 1 | P3: 3 | P4: 7

STATUS: GREEN
