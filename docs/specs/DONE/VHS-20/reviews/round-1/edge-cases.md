# Edge-Cases Review — round 1

## Closure of round 0 findings
N/A — round 1.

## Findings

### F-1 (P1): Malformed-YAML `requires` makes `parseFrontmatter` throw, aborting the entire conversion — not the "warn, emit ungated" the spec promises
§ "Absent / malformed requires handling" (spec.md:160-166), Done-when 5. A `services: [?]` (or other YAML-significant bare token) makes js-yaml `load` throw `YAMLException: missed comma…`; `parseFrontmatter` re-throws (frontmatter.ts:35); `loadSkills` calls it with no try/catch (claude.ts:128-130) → the throw aborts the whole `convert` run before the adapter executes. The spec's malformed-handling path ("warn and continue, emit ungated") never runs for malformed YAML. Fix: scope the robustness claim down — malformed-*YAML* is a hard, clear parse error owned by parseFrontmatter/VHS-18 lint; adapter graceful handling covers only *well-formed-but-non-conformant* shapes (scalar/list/unknown-keys/out-of-vocab). Or add a try/catch in loadSkills (larger change).

### F-2 (P2): `description` verbatim assertion (Test 5) mismatches on serialized form
js-yaml `dump` preserves the value through load→dump→load but reflows a long/colon/newline description to a `>-` folded block, so a raw line-compare against the source fails on the real `spec-cycle` description. Fix: assert the emitted frontmatter, when re-parsed with `load`, yields a `description` value byte-equal to the source value (compare parsed values, not raw lines); subsumes assertion 6. Add a fixture description with a colon + newline.

### F-3 (P2): Generated `## Preflight` heading can collide with an author body heading
spec-cycle's body carries its own preflight concept (contract §4:115 cites "spec-cycle's preflight"). Prepending `## Preflight …` yields two preflight sections; an author "warn and proceed" can contradict the generated "halt immediately." Fix: use a unique sentinel line for the generated section (detectable by smoke test), and state that coexistence with an author preflight is intentional/known.

### F-4 (P2): D3 "fire before mutation" is advisory-by-trust prose with no enforcement — Done-when 4 overclaims a hard gate
The gate is generated Markdown the agent is asked to self-honor; no callback/exit-code/loader hook (D3's own words: converter "only emits files"). This is weaker than contract §3 availability (line 77) "MUST verify each required capability before any mutation and fail clearly." Done-when 4 presents the prose as a satisfied hard-fail. Fix: state the enforceability gap explicitly in HERMES-MAPPING.md + Done-when 4 (advisory-by-construction unless a native load hook exists; documented §3 lossiness fed back to VHS-17); make the re-verify of "native pre-flight/validation hook" a *required* D9 check, not optional.

### F-5 (P2): Service-token normalization is brittle; `issue-tracker ?` (space) yields a trailing-space token
js-yaml parses `[issue-tracker ?]` as `"issue-tracker ?"`. The spec never states the adapter's normalization (trim, strip one trailing `?`, trim, exact-vocab match) nor the out-of-vocab path. A naive trailing-`?` strip leaves `"issue-tracker "` → unknown role → silent drop (violates no-silent-drop) or garbage toolset. Fix: add an explicit normalization step to Design: per element `trim()` → strip one trailing `?` → `trim()` → lowercase-exact-match vocab `{issue-tracker, shared-memory, code-review-bot, vcs-host}`; no match → warn + record gap (not silent), emit no key. Required + optional.

### F-6 (P2): D8 fixture's required+credentialed `issue-tracker` drives Test 3's `required_environment_variables` assertion, but the var name is unconfirmed (D9) — assertion has no defined target
If the credentialed-service env-var name is unknown at impl time, the adapter must still emit something deterministic. Fix: make Test 3 structural (assert the array exists, each entry shaped `{name,prompt,help,required_for}`, no specific name); define what the adapter emits for a credentialed required service when the live var name is unconfirmed (documented placeholder recorded in drift log).

### F-7 (P3): Flat `<home>/skills/<name>/` has no name-collision guard
OpenCode guards with a `seen` set + skip-with-warning (opencode.ts:94-101); the Hermes writer as specified does not — two skills with the same sanitized name silently overwrite. Can't happen for the four distinct names (→ P3) but the writer "must be generic." Fix: add a `seen` Set, skip-with-warning.

### F-8 (P3): `copySkillDir` is additive-merge — re-emission leaves orphaned files
copySkillDir (files.ts:165-193) never deletes target files absent from source; OpenCode/Codex compensate with cleanup scaffolding. Hermes writer defines none → stale subtree files accrete on re-emit. Fix: clean-replace `<home>/skills/<name>/` before copy (the whole dir is generated), or document orphan-cleanup out of scope for v1.

### F-9 (P3): `resolveHermesHome` env-var tilde expansion
`resolveCodexHome` trims env but does not `expandHome` the env value — `HERMES_HOME="~/foo"` would resolve to a literal `~/foo`. Fix: state `resolveHermesHome` runs `expandHome` on the env value too, or accept the codex parity quirk explicitly. CI uses explicit `--hermes-home <tmp>` so this never bites the gate.

### F-10 (P4): Smoke test temp Hermes home has no cleanup
Existing smoke test never removes its mkdtemp dirs; the Hermes extension follows suit → temp trees accrete locally (harmless on CI). Optional: wrap in try/finally rm, or note intentional skip.

### F-11 (P2): Cross-repo ship mechanics — if ship-spec cuts its worktree from vigil-skills, the Test command runs against a tree with no smoke-test/package.json/Bun
ship-spec cuts the worktree from the repo it runs in (vigil-skills); `bun run scripts/smoke-test.ts` is meaningless there. D1 states the intent but no mechanism. Fix: add an explicit "Ship mechanics" note to D1 — ship-spec must run from/point at the vigil-converter checkout (as VHS-19 shipped); worktree + Test command execute there; the vigil-skills spec-record committed separately. Flag the Tier-2 live-Hermes dependency as an explicit ship gate.

### F-12 (P2): Done-when 2 (live-Hermes load) unverifiable in CI; no fallback if no live Hermes reachable
The defining deliverable may be undischargeable if no live Hermes is reachable. Spec says "don't fake it" but no partial-close posture. Fix: pre-decide — if no live Hermes, Tier-1 (CI smoke) is the blocking gate that ships, Done-when 2 deferred to partial-close with the gap recorded in HERMES-MAPPING; state whether the PR merges on Tier-1 alone.

## Summary
P0: 0 | P1: 1 | P2: 6 | P3: 3 | P4: 1

STATUS: RED P0=0 P1=1 P2=6 P3=3 P4=1
