# Correctness Review — round 1

## Closure of round 0 findings
N/A — round 1.

## Findings

### F-1 (P2, Pre-ship recommended: yes): Tier-1 smoke assertion 3 internally contradictory on the `memory` toolset
§ Test plan → Tier 1, assertion 3 (spec.md:183-184). The assertion says `requires_toolsets` includes `terminal` and `memory` (from "required `shared-memory`"), but in the D8 fixture `shared-memory?` is **optional** → per D4 optional services emit no gating key, so `requires_toolsets: [memory]` must NOT appear. Followed literally the test asserts `memory` present AND (via the inline note) absent — unsatisfiable. Fix: drop the "and `memory` (from required `shared-memory`)" clause; assert only `terminal` present, `required_environment_variables` present for required `issue-tracker`, and that no requires_*/fallback_* key references the optional `shared-memory` mapping. Or make `shared-memory` the required service and adjust §3 examples + assertions accordingly.

### F-2 (P2): `copySkillDir` copies the source `SKILL.md` verbatim — per-skill emission must overwrite or copy selectively
§ Design → Per-skill emission (spec.md:158). `copySkillDir` (`src/utils/files.ts:165-193`) recursively copies the entire source dir incl. `SKILL.md`, transforming SKILL.md only when a `transformSkillContent` callback is passed (else `fs.copyFile` verbatim). The Hermes writer writes a *generated* SKILL.md separately; calling `copySkillDir` with no transform would write/overwrite the verbatim source SKILL.md (order-dependent footgun). OpenCode avoids this by passing `transformSkillContentForOpenCode` so SKILL.md is rewritten in place. Fix: either (a) copy subtrees excluding SKILL.md then write the generated file, or (b) pass a Hermes transform callback to `copySkillDir` (true mirror of opencode.ts:125-131).

### F-3 (P3): Stale anchor — `copySkillDir` call cited as `opencode.ts:125-130`; actual `125-131` (4-arg form)
The actual call is `copySkillDir(skill.sourceDir, targetDir, transformSkillContentForOpenCode, true)` ending line 131. The `transformSkillContentForOpenCode, true` args are load-bearing (see F-2). Cite 125-131.

### F-4 (P3): `convertClaudeToHermes` should return `HermesBundle | null`, take `ClaudeToOpenCodeOptions`, register via `as TargetHandler[...]` casts
`TargetHandler.convert` is `(plugin, options) => TBundle | null` (index.ts:46); each registry entry casts via `as TargetHandler["convert"]` (index.ts:60,69,76,81). `options` is the shared `ClaudeToOpenCodeOptions` (fields Hermes ignores, like gemini/kiro). Allow `null` return to match the `if (!bundle)` guard (convert.ts:166).

### F-5 (P4): Done-when 1 source phrasing ("`skills/` ≡ `~/.claude/skills/`") — harmless drift, worth one word
Engine ingests any bare skills root (claude.ts:24-35,66-71); repo `skills/` and installed `~/.claude/skills/` are byte-identical via sync.py — either is valid. Optional half-sentence to say so.

## Verification log (all confirmed TRUE)
- D2/Scope6 — `loadSkills` (claude.ts:124-145) captures only name/description/argumentHint/disableModelInvocation/ce_platforms; `data.requires` not stored though parseFrontmatter parses it (frontmatter.ts:29). ✓
- D7 — `formatYamlValue` (frontmatter.ts:60-71) renders nested object via String() → `[object Object]`; `load` imported frontmatter.ts:1; js-yaml ^4.1.0 (package.json:21) exports `dump`. ✓
- Scope7 — `targets` registry `{name,implemented,convert,write}` (index.ts:50-84), each via `as TargetHandler[...]`. ✓
- D6 — `resolveCodexHome` (resolve-home.ts:19-22) `$CODEX_HOME`→`~/.codex`. ✓
- convert.ts anchors — `--to` desc line 28; codexHome/piHome args 35-44; resolution 86-87; resolveTargetOutputRoot call sites 125-132,156-164,192-200. ✓
- resolve-output.ts — options-object fn with codexHome/piHome params + per-target branches (5-33). ✓
- smoke-test.ts — `Bun.spawnSync(["bun","run","src/index.ts","convert",samplePath,"--to",target,"--output",outDir])` (67-70); assertions 91-114 check count + opencode.json validity only. ✓
- D8 — capability-demo/SKILL.md:4-6 carries `requires:{services:[issue-tracker?,shared-memory?],tools:[bash]}`; `tools:` not a §3 key. ✓
- §3 mapping matches contract §3 (portability-contract.md:97-103). ✓
- D4/D5 — wiki skills-system.md:120-123 confirms requires_toolsets/fallback_for_toolsets semantics; toolsets terminal/memory/delegation in tools-and-toolsets.md:31. ✓
- ci.yml — `bun run scripts/smoke-test.ts` line 29 (spec says ~28). ✓
- Done-when 1-6 map 1:1 to brief. HEAD `14cdca4f` matches pin. ✓

## Summary
P0: 0 | P1: 0 | P2: 2 | P3: 2 | P4: 1

STATUS: GREEN
