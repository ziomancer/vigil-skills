# Reconciliation Report: VHS-20

> Date: 2026-06-18
> Spec: docs/specs/TODO/VHS-20.spec.md
> Merge: ziomancer/vigil-converter PR #1 — merge commit 4bf2de2 (off baseline 14cdca4f, PR head aac9353)
> Plane state: PR Review (group: completed)

## Summary

The Hermes output target shipped exactly as specified. All 15 files the spec enumerates appear in the diff, no unexpected files, none dropped; all 10 decisions are reflected in the shipped code; all 6 Done-when criteria are met (including the live-Hermes install/load proof captured in the acceptance trail). Clean full-close.

## Scope

| Spec file | In diff? | Notes |
|---|---|---|
| `src/types/hermes.ts` | Yes | New (81L) — `HermesBundle`/`HermesSkillFile` + normalized-capability shape |
| `src/converters/claude-to-hermes.ts` | Yes | New (271L) — §3 mapping, token normalization, pre-flight |
| `src/targets/hermes.ts` | Yes | New (57L) — `writeHermesBundle` |
| `HERMES-MAPPING.md` | Yes | New (153L) — §3 table + gaps + drift log |
| `src/types/claude.ts` | Yes | `requires?: Record<string, unknown>` (D2) |
| `src/parsers/claude.ts` | Yes | `loadSkills` captures `data.requires` (D2) |
| `src/targets/index.ts` | Yes | `hermes` handler registered (`implemented: true`) |
| `src/commands/convert.ts` | Yes | `--hermes-home` arg + resolution + `--to` desc |
| `src/utils/resolve-home.ts` | Yes | `resolveHermesHome` (D6) |
| `src/utils/resolve-output.ts` | Yes | `hermes` branch in `resolveTargetOutputRoot` |
| `scripts/smoke-test.ts` | Yes | Tier-1 Hermes assertion path (+165L) |
| `samples/skills/capability-demo/SKILL.md` | Yes | Contract-conformant `requires:` fixture (D8) |
| `README.md` | Yes | Target roster + `--to` example |
| `package.json` | Yes | Description roster string |
| `STRIP.md` | Yes | "Added" note linking HERMES-MAPPING.md |

Unexpected files in diff (not in spec): none.
Dropped (in spec, not in diff): none. (15/15 — diff stat: 15 files, +805/−13.)

## Decisions

| # | Decision | Status | Evidence |
|---|---|---|---|
| D1 | Implementation lands in vigil-converter, not vigil-skills (cross-repo) | Confirmed | PR #1 is in `ziomancer/vigil-converter`; vigil-skills carries only this spec record under `docs/specs/` |
| D2 | Surface `requires:` by extending the parser | Confirmed | `src/parsers/claude.ts:134-148` — captures `data.requires` (mapping-only) onto `ClaudeSkill`; `src/types/claude.ts` adds the field |
| D3 | Hard pre-flight is a generated body preamble + sentinel | Confirmed | `src/converters/claude-to-hermes.ts:34` — `PREFLIGHT_SENTINEL = "<!-- vigil-converter:hermes-preflight v1 -->"` |
| D4 | Optional (`?`) services emit no gating key (documented gap) | Confirmed | Smoke test `[c] OK — optional shared-memory ungated (advisory-only)` (`VHS-20.test-output.txt`) |
| D5 | `network`/`subagents`/`filesystem` → pre-flight only | Confirmed | Pre-flight names them (`VHS-20.test-output.txt` §Tier-1.3); HERMES-MAPPING.md gap entries |
| D6 | `HERMES_HOME` resolved, never hardcoded | Confirmed | `src/utils/resolve-home.ts` in diff (+13); smoke test drives `--hermes-home <tmp>` |
| D7 | Frontmatter serialized with js-yaml `dump`, not `formatFrontmatter` | Confirmed | `src/converters/claude-to-hermes.ts:19` `import { dump }`, `:265` `dump(frontmatter, …)` |
| D8 | CI exercises mapping via contract-conformant `capability-demo` | Confirmed | `samples/skills/capability-demo/SKILL.md` in diff (+24); smoke `[a]` parses capability-demo |
| D9 | Re-verify affordances against live harness before encoding | Confirmed | `src/converters/claude-to-hermes.ts:264` top-level `required_environment_variables`; `VHS-20.test-output.txt` "D9 RE-VERIFY" (placement RESOLVED top-level; toolset names + no-native-hook CONFIRMED) |
| D10 | Security-first: parse-and-transform only, never executes skill content | Unverifiable (structural invariant) | Inherited VHS-19 zero-exec-sink boundary; no exec sink added in the new converter/writer (consistent, no behavioral test in this diff) |

## Acceptance Criteria

| # | Criterion (Done-when) | Status | Evidence |
|---|---|---|---|
| 1 | `hermes` registered + converts the 4 skills | Met | `src/targets/index.ts:86-91` (`implemented: true`); Tier-2 converted review-pr/ship-spec/spec-close/spec-cycle |
| 2 | Installs + loads under live Hermes, with evidence | Met | `VHS-20.test-output.txt` Tier-2 — all 4 packages enabled in `skills_list`, parsed cleanly |
| 3 | Capability→affordance mapping documented, gaps enumerated | Met | `HERMES-MAPPING.md` (153L) — §3 table + gaps |
| 4 | Hard pre-flight for required capabilities in place | Met | Sentinel preamble (D3); `VHS-20.test-output.txt` §Tier-1.3 names required set |
| 5 | No-`requires:` case handled without error | Met | Smoke `[c] OK — hello-world ungated (no gating keys, no pre-flight)` |
| 6 | CI runs Hermes conversion where feasible; drift recorded | Met | `scripts/smoke-test.ts` Hermes path green; HERMES-MAPPING.md drift log + test-output D9 |

## Test Plan

| Test | Exists? | Location |
|---|---|---|
| Tier-1 CI smoke (Hermes path: shape, no-requires, full-mapping, optional-not-gated, verbatim desc, nested-block, robustness, temp-hygiene) | Yes | `scripts/smoke-test.ts` (Hermes block, +165L) — PASS (exit 0), `VHS-20.test-output.txt` Tier-1 |
| Tier-2 live-load proof (manual, captured) | Yes (captured evidence) | `VHS-20.test-output.txt` Tier-2 — `skills_list` shows 4 enabled |

## Wiki-ready

Decisions and comprehension worth extracting to the wiki:
- **Decision — the Hermes pre-flight is advisory-by-construction; §3 is lossy-in-kind (D3 + D4/D5).** Constraining and reusable for every future harness adapter: Hermes `requires_*` keys gate *visibility*, not a hard pre-flight, and Hermes exposes no native skill-load hook — so the strongest gate the adapter can emit is sentinel-marked prose, and `network`/`subagents`/`filesystem`/optional-services map to documented gaps, not keys. → `decisions/2026-06-18-vhs-20-hermes-preflight-advisory.md`.
- **Comprehension — the Hermes target on the vigil-converter engine.** Already created by `/wiki-after-merge` at `comprehension/2026-06-18-vhs-20-hermes-adapter.md` (covered; not re-derived).

RECONCILED: yes DRIFT: 0
