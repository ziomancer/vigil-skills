# Edge-Cases Review — round 1

## Closure of round 0 findings
N/A — round 1.

## Findings

### F-1: Smoke-test target "OpenClaw" does not exist in the upstream converter — D6's two-path design names a fictional target
**Severity:** P0
**Where:** spec § D6, § "Smoke test — two paths", § Done-when #3, Test plan #3; brief lines 17 & 26
**Edge case:** Upstream `src/targets/` = `codex.ts, gemini.ts, kiro.ts, opencode.ts, pi.ts`; README roster = Cursor, Codex, Copilot, Factory Droid, Qwen, **OpenCode**, Pi, Gemini, Kiro. **"OpenClaw" appears nowhere.** The fleet's OpenClaw harness (served by the MCP server) is unrelated to what CE converts *to*.
**What happens:** Implementer follows D6, finds no OpenClaw adapter; the "entangled → fallback to Codex" rule fires for the wrong reason (non-existence, not entanglement), masking the real error. D6's "most relevant inherited target" rationale collapses.
**Why missed:** Brief (17/26/37) and eval doc (22) wrote "OpenClaw" where upstream says "OpenCode" — sustained conflation; spec inherited it without checking `src/targets/`.
**Fix:** Replace "OpenClaw" with **"OpenCode"** throughout D6/Design/Done-when #3/Test plan #3 (richest implemented adapter — emits `opencode.json` + `.opencode/{agents,commands,skills}/`, most assertable output); correct the rationale; keep Codex (`codex.ts`) as documented fallback. Fix the same error in the brief for archived-record consistency. If the fleet's OpenClaw harness needs a target, that's new adapter work (VHS-20-class), out of scope here.

### F-2: Retargeting input to `~/.claude/skills/` is engine surgery, not a config change — collides with the spec's "do not rewrite the converter" rule
**Severity:** P1
**Where:** spec § D4, § "Retarget input (D4)", § "Entanglement rule", Done-when #1, Test plan #2
**Edge case:** Upstream input contract is a **Claude plugin directory**, not a skills tree. `loadClaudePlugin` (`src/parsers/claude.ts`) requires `.claude-plugin/plugin.json` and **throws** when absent, then reads skills from `<root>/skills/`. `~/.claude/skills/` has no manifest and *is* the skills root (not its parent) → throws + looks in `~/.claude/skills/skills/`.
**What happens:** "Retarget input" needs editing `parsers/claude.ts` (manifest-optional + treat path as skills root) — exactly the in-engine surgery the entanglement rule says not to do. Spec frames it as cosmetic and is silent on the manifest/skills-root assumption.
**Why missed:** Spec treats input source as a config knob; never inspected `loadClaudePlugin` preconditions. The retarget is the one genuinely non-trivial code change and is under-scoped to a one-liner.
**Fix:** Add a Design subsection acknowledging the upstream input contract; scope the retarget as *permitted engine surgery* (manifest-optional, path-as-skills-root), distinct from the content-decoupling entanglement rule.

### F-3: The "never executes skill content" grep omits `Bun.spawn`/`Bun.$` — the upstream's actual exec sinks
**Severity:** P1
**Where:** spec § D2, § "Supply-chain vetting"
**Edge case:** Spec greps `eval`/`Function(`/`child_process`/`exec`/`spawn`. In Bun the real primitives are `Bun.spawn(...)` and `` Bun.$`...` `` (no `child_process` import; `Bun.$` matches nothing in the list). Upstream `src/commands/install.ts` uses `Bun.spawn(["git","clone",...])`; the OpenCode converter *emits* `converted-hooks.ts` with `` await $`${hook.command}` ``.
**What happens:** Grep returns clean, README asserts "never executes skill content" — verified-but-incomplete. Separately, the converter emitting shell-executing output (`converted-hooks.ts`) is a downstream surface the "conversion is inert" framing doesn't address.
**Fix:** Extend allowlist to `Bun\.spawn`, `Bun\.\$`, `` \$\` ``, `execSync` + Node set. Distinguish (a) conversion path executing skill content (must be absent) from (b) converter *emitting* artifacts the target runtime later executes (inherent; document as explicit non-claim).

### F-4: CI has no `~/.claude/skills/`, but Done-when #1 / Test plan #2 require converting "the vigil skill set from `~/.claude/skills/`"
**Severity:** P1
**Where:** spec Done-when #1, Test plan #2, Goal; vs § "Smoke test" ("sample input is pinned in the fork repo")
**Edge case:** CI runs on a fresh runner — `~/.claude/skills/` empty/absent. Spec pins a deterministic sample *for the smoke test* but two acceptance gates phrase the requirement against the live tree.
**What happens:** Gates unsatisfiable in CI (empty dir → converter errors on no-input, or "succeeds" converting nothing). Implementer might wire CI to read a real home dir, reintroducing the maintainer-machine dependency the pinned sample eliminated. Empty-input edge unhandled (and F-2's manifest-throw means empty likely throws).
**Fix:** Make the pinned committed sample the single source of truth for all CI gates; reword Done-when #1 / Test plan #2 to "a pinned sample SKILL.md set (committed to the fork)"; keep "reads `~/.claude/skills/` when present" as runtime behavior tested locally. Define empty-input expectation (error vs clean no-op) so "non-empty output" has a contract.

### F-5: The fork's CI is the acceptance authority but lives in another repo the lifecycle can't see — no binding artifact/ordering
**Severity:** P2
**Where:** spec § D7, Test plan, Test command
**Edge case:** Substantive signal (CI green) is produced in `vigil-converter`; audit trail + Plane flip live in vigil-skills. Nothing binds them — no specified artifact (run URL? pasted log? fork SHA?) nor what happens to VHS-19's Plane state if fork CI is red while the README-pointer PR is green.
**What happens:** README-pointer PR merges, VHS-19 flips done on a one-line doc change while the deliverable's CI is red or the fork doesn't exist.
**Fix:** Make the captured fork-CI-green artifact (run URL or committed `smoke-output.txt`) a *blocking* precondition recorded against checklist item 3 before VHS-19's Plane flips; state the README-pointer PR merging does **not** by itself satisfy VHS-19.

### F-6: Scope-creep tripwire — non-existent target (F-1) + retarget surgery (F-2) is exactly the pressure toward building an adapter the loop-note forbids
**Severity:** P2 · **Pre-ship recommended:** yes
**Where:** spec § "Entanglement rule", brief loop-note, § Out of scope
**Edge case:** Discovering OpenClaw isn't real + input retarget needs edits, the natural recovery is "I'll write the OpenClaw adapter / decouple input properly" → slide into VHS-20. The entanglement rule covers only "stripping breaks conversion," not these two triggers.
**Fix:** Broaden the scope-narrow rule to all three triggers: (a) strip breaks conversion → file + switch target; (b) named target isn't an implemented upstream adapter → switch to a real one (OpenCode/Codex), don't author one; (c) input retarget needs more than path resolution → manifest/skills-root edit permitted, decoupling CE skills or writing a new target is not. Make the VHS-20 boundary explicit at each.

### F-7: No finding — strict-YAML `requires:` concern is unfounded (recorded so it isn't re-raised)
**Severity:** P3
Frontmatter parsed by `js-yaml` `load()` (`src/utils/frontmatter.ts`). `?` *suffix* in a flow scalar (`issue-tracker?`) is a plain-scalar char, not the mapping-key indicator (`? ` at node start); inline `#` comments are standard YAML. Neither errors. No change; optionally note the converter inherits js-yaml and the canonical `requires:` block round-trips cleanly.

## Summary
P0: 1 | P1: 3 | P2: 2 | P3: 1 | P4: 0

Upstream verified (read-only, web): `src/targets/` (no `openclaw.ts`; `opencode.ts` present), `src/parsers/claude.ts` (manifest-required `loadClaudePlugin`), `src/utils/frontmatter.ts` (js-yaml), `src/commands/install.ts` (`Bun.spawn`).

STATUS: RED P0=1 P1=3 P2=2 P3=1 P4=0
