# Edge-Cases Review — round 2

## Closure of round 1 findings
All twelve round-1 edge-cases findings CLOSED in current spec text (F-1 malformed-YAML scoping; F-2 description-by-value; F-3 sentinel heading; F-4 advisory framing; F-5 normalization; F-6 structural env-var assertion; F-7 seen-Set; F-8 clean-replace [see new F-1]; F-9 env tilde; F-10 temp cleanup; F-11 ship mechanics; F-12 partial-close). F-8's fix opened the new F-1 below.

## Findings

### F-1 (P2, Pre-ship recommended: yes): Clean-replace clobbers agent-created / user-modified files in Hermes's single source of truth
spec.md:178. The spec says "remove `<hermesHome>/skills/<sanitizedName>/` if present, then recreate." Per wiki skills-system.md:10,192, `~/.hermes/skills/` is the single source of truth where agent-created skills land and "existing skills are modified where found." A blanket `rm -rf` of the target skill dir deletes user/agent content (edited SKILL.md, added references/, local config), not just converter orphans. Unlike OpenCode's manifest-scoped `cleanupCurrentManagedDirectory` (only removes paths the converter's own manifest recorded — opencode.ts:124), this is unconditional. The Tier-2 live-load step writes into exactly such a home. Fix: scope the destructive step — either (a) narrow to converter-generated entries (overwrite SKILL.md + source-carried subtrees only, leave unknown files), or (b) keep blanket clean-replace but document destructive-of-target and gate Tier-2 to a dedicated/temp HERMES_HOME. Pick one in the spec (don't defer "pick one in code") — it's a data-loss surface, not a stylistic call.

### F-2 (P2): `convertClaudeToHermes` returning `null` is a hard throw, not a graceful skip
spec.md:23. The `if (!bundle)` guard at convert.ts:166-168 THROWS and aborts the run — not a skip. If Hermes returns null on a real input (e.g. empty skills root), the whole convert hard-fails. Fix: state Hermes returns a (possibly empty) HermesBundle for any successfully-parsed plugin (empty/no-requires → ungated, not abort), reserving null for the inherited unconvertible condition; note null ⇒ hard abort.

### F-3 (P3): Duplicate service roles are not deduplicated
spec.md:181-183. Per-element normalization with no dedup → `[memory, memory]` for `services: [shared-memory, shared-memory]`; and `[issue-tracker, issue-tracker?]` (same role required+optional) has undefined precedence. Fix: dedup roles after vocab match; required wins over optional (gate it; pre-flight lists it required).

### F-4 (P3): Assertion 7 out-of-vocab fixture must be well-formed YAML
spec.md:217. The "out-of-vocab service token" sub-case must be a well-formed scalar (e.g. `services: [nonexistent-role]`) to reach the warn-and-gap path; if written as `[?]` it's the malformed-YAML throw case and assertion 7 false-fails. Fix: pin the fixture to a quoted/well-formed scalar.

### F-5 (P4, verification): "advisory-by-construction" framing consistent across D3 / Done-when 4 / HERMES-MAPPING scope. Confirmed; no gap.

## Summary
P0: 0 | P1: 0 | P2: 2 | P3: 2 | P4: 1

STATUS: GREEN
