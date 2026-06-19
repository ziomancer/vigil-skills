# VHS-20 — Hermes target adapter for the vigil-converter engine

> **Status:** v1 spec (spec-cycle) · **Ticket:** VHS-20 (child of VHS-16; blocked-by VHS-19 + VHS-17, both closed) · **Priority:** High
> **Brief:** `docs/specs/TODO/VHS-20.brief.md`
> **Implementation repo:** `ziomancer/vigil-converter` @ `14cdca4f` (NOT this repo — see Decision D1)
> **Targets:** portability-contract §3 (`docs/portability-contract.md`), built on the VHS-19 engine baseline.

---

## Goal

Add a `hermes` output target to the owned `vigil-converter` engine — the one target CE never shipped — so a single canonical `SKILL.md` source emits **installable, loadable Hermes skill packages** for the vigil skill set. Every declared capability (`requires:`) is mapped to a real Hermes affordance per contract §3; every capability Hermes cannot express is surfaced as an explicit, documented gap and compensated by a generated hard pre-flight — never silently dropped. The deliverable is a working adapter + a documented capability mapping + captured install/load evidence, **not** a behavioral-parity proof (that is VHS-21).

---

## Scope

All code changes land in the **`vigil-converter`** repository. This repo (`vigil-skills`) receives only the spec record under `docs/specs/TODO/` (the brief/spec/reviews); no Bun/TypeScript code lands here, and `sync.py` / the stdlib-only spine are untouched (Decision D1).

### Files to CREATE (in vigil-converter)

1. `src/types/hermes.ts` — `HermesBundle` / `HermesSkillFile` types and the normalized-capability shape the converter produces.
2. `src/converters/claude-to-hermes.ts` — `convertClaudeToHermes(plugin: ClaudePlugin, options: ClaudeToOpenCodeOptions): HermesBundle | null`. Reads each skill's `requires:`, applies the §3 mapping, builds the Hermes `metadata.hermes` frontmatter, and generates the pre-flight preamble. (Takes the engine's shared `ClaudeToOpenCodeOptions` type — its fields, `agentMode`/`inferTemperature`/`permissions`/`codexIncludeSkills`, are Hermes-irrelevant and ignored, exactly as `gemini`/`kiro` ignore them.) **`null` contract:** return a (possibly empty) `HermesBundle` for any successfully-parsed plugin — an empty / no-`requires` skills root must emit ungated, **not** abort. Reserve `null` only for the same genuinely-unconvertible condition the inherited converters use, because the `if (!bundle)` guard at `convert.ts:166–168` **throws and aborts** (it is not a graceful skip); never use `null` as an "empty" signal.
3. `src/targets/hermes.ts` — `writeHermesBundle(outputRoot, bundle, scope?)`. Resolves the Hermes home, writes `<home>/skills/<name>/SKILL.md`, and copies supporting subtrees.
4. `HERMES-MAPPING.md` (repo root, alongside `STRIP.md`) — the capability→affordance mapping doc. Records: (a) the §3 table as implemented; (b) the enumerated **gaps** — optional-service not gateable (D4), `network`/`subagents`/`filesystem` no-gating-key (D5), and the **advisory-by-construction enforceability gap** for the pre-flight (D3); (c) the env-var placeholder(s) emitted for credentialed services when names are unconfirmed (D9); (d) the live-harness **drift log** vs the 2026-05-23 snapshot. (vigil-converter has no `docs/` dir — root placement matches `STRIP.md`.)

### Files to CHANGE (in vigil-converter)

5. `src/types/claude.ts` (`ClaudeSkill`, lines 47–55) — add one additive optional field `requires?: Record<string, unknown>` to carry the raw parsed block (Decision D2).
6. `src/parsers/claude.ts` (`loadSkills`, lines 124–145) — capture `data.requires` into the constructed `ClaudeSkill`. This is the load-bearing parser fix: `requires:` is currently parsed by `parseFrontmatter` but **discarded** by `loadSkills`.
7. `src/targets/index.ts` (`targets` registry, lines 50–84) — register `hermes` (`implemented: true`, `convert`, `write`) with `as TargetHandler["convert"]` / `as TargetHandler["write"]` casts, exactly like the `codex`/`gemini`/`kiro` entries (the bundle type is narrower than the handler's generic).
8. `src/commands/convert.ts` — add a `--hermes-home` arg (mirroring `codexHome`/`piHome`, lines 35–44); resolve it (line 86–87 region); pass it into `resolveTargetOutputRoot` (lines 125–132, 156–164, 192–200); add `hermes` to the `--to` description string (line 28).
9. `src/utils/resolve-home.ts` — add `resolveHermesHome(value)` mirroring `resolveCodexHome` (lines 19–22): `$HERMES_HOME` → `~/.hermes`.
10. `src/utils/resolve-output.ts` (`resolveTargetOutputRoot`) — add a `hermesHome` parameter + a `hermes` branch so the writer's `outputRoot` is the resolved Hermes home (parallel to the `codexHome`/`piHome` branches).
11. `scripts/smoke-test.ts` — add a Hermes conversion + assertion path over `samples/skills/` (see Test plan).
12. `samples/skills/capability-demo/SKILL.md` — replace the current non-contract `requires:` (`tools: [bash]`) with a contract-conformant block so CI exercises the full §3 mapping (Decision D8).
13. Doc roster update — the target roster is enumerated in three places: `README.md:11–12` (targets list), `README.md:27` (the `--to` example), and `package.json:4` (the description string). Add `hermes` to the README targets list + `--to` example and to `package.json:4`, and add a one-line "Added" note in `STRIP.md` linking `HERMES-MAPPING.md`. (Updating all three keeps the roster from drifting.)

### Files to LEAVE ALONE

- The inherited `opencode` / `codex` / `pi` / `gemini` / `kiro` converters and target writers — no behavior change (the `ClaudeSkill.requires` field is additive and ignored by them).
- The CE legacy-compat code (`utils/legacy-cleanup.ts`, legacy markers) — the VHS-19 no-rewrite rule stands.
- `.github/workflows/ci.yml` — **no change needed**: the existing step `bun run scripts/smoke-test.ts` (ci.yml line ~28) runs the extended script in place; the Hermes path rides the same invocation.
- This `vigil-skills` repo's `skills/`, `sync.py`, and stdlib-only tree — the Bun toolchain stays isolated in the fork (VHS-19 D5).

---

## Decisions

### D1 — Implementation lands in vigil-converter, not vigil-skills (cross-repo)

The adapter is Bun/TypeScript engine code; it belongs in `ziomancer/vigil-converter`, not the stdlib-only `vigil-skills` tree. The PR targets vigil-converter; its CI smoke run is the blocking gate. This mirrors VHS-19 exactly (spec authored in vigil-skills `docs/specs/`, engine code shipped in vigil-converter, vigil-skills' only footprint a README pointer). The spec/brief/reviews remain in vigil-skills per the spec-lifecycle convention (AGENTS.md: "Specs … live in the target project at `docs/specs/TODO/`").

**Ship mechanics (operational, not just intent).** `/ship-spec` cuts its worktree from the repo it runs in and runs the Test command there; run from vigil-skills it would land in a tree that has no `package.json`, no `scripts/smoke-test.ts`, and no Bun — the gate would fail opaquely (or, worse, code would land in the wrong repo). Therefore: **run `/ship-spec` from the `vigil-converter` checkout** (or otherwise point its worktree at vigil-converter), exactly as VHS-19 was shipped. The implementation worktree, the Test command, and the PR all execute against vigil-converter; the vigil-skills footprint (this spec record under `docs/specs/TODO/`, plus an optional one-line README/state pointer) is committed separately in vigil-skills. The implementer should treat "which repo is the worktree rooted in?" as a preflight check before the test gate.

**Partial-close posture if no live Hermes is reachable.** Done-when 2 (live install/load) requires a reachable Hermes (a `HERMES_HOME` / running harness). If none is reachable at ship time, **Tier-1 (CI smoke) is the blocking gate that ships** and the PR merges on Tier-1 green alone; Done-when 2 is explicitly deferred to a partial-close follow-up, with the unmet criterion recorded in `HERMES-MAPPING.md` and noted in the acceptance trail (`VHS-20.test-output.txt`) so `/spec-close` reconciles cleanly. The live-load proof is never faked to satisfy the gate.

### D2 — Surface `requires:` by extending the parser, not by re-reading files

`loadSkills` (`src/parsers/claude.ts:124–145`) extracts only known keys (`name`, `description`, `argument-hint`, `disable-model-invocation`, `ce_platforms`) and drops everything else; `requires:` is parsed into `data` by `parseFrontmatter` but never stored on `ClaudeSkill`. The fix is a minimal additive field — `ClaudeSkill.requires?: Record<string, unknown>` — populated from the already-parsed `data.requires`. The raw block is carried **harness-neutrally**; all §3 interpretation (role-token parsing, `?`-optionality, vocabulary validation) lives in `claude-to-hermes.ts`, so future adapters can reuse the field. Rationale: one small change in the parser vs. re-opening and re-parsing each `SKILL.md` inside the adapter (drift risk, double I/O).

### D3 — The hard pre-flight is a generated body preamble, not a side file or a gating key

Contract §3 requires "a hard pre-flight even where it also emits the Hermes gating keys," and §5 dim. 2 requires declared gates to "fire identically … a missing required capability fails before mutation." On Hermes a skill is the markdown the agent reads at `skill_view` (progressive disclosure); the converter only emits files — it has no load-time callback. So the strongest gate the *adapter* can emit is a clearly-delimited generated section, carrying a machine-detectable sentinel, prepended to the body:

```
<!-- vigil-converter:hermes-preflight v1 -->
## Capability pre-flight (generated by the Hermes adapter — do not edit)

Before any action that mutates state, confirm each REQUIRED capability below is
available. If any is unavailable, halt immediately and report which one — do not
proceed. OPTIONAL capabilities: if unavailable, warn and continue.

Required: <enumerated from requires — e.g. terminal/shell, network, subagents,
filesystem [read, write], service:issue-tracker>
Optional (warn-and-proceed): <enumerated optional services>
```

- Emitted **only** when the skill declares ≥1 capability; the "required" enumeration appears only when ≥1 required (no-`?`) capability exists. A skill with no `requires:`, or with only optional services, gets **no** pre-flight section (Decision D2 + Done-when criterion 5).
- The original author body is emitted **verbatim after** the generated section — Scope item 2's "body passes through unchanged" is preserved (the pre-flight is an *addition*, not a rewrite).
- **Heading is distinct + sentinel-marked.** The generated heading is `## Capability pre-flight …` (not bare `## Preflight`) and is preceded by the HTML-comment sentinel `<!-- vigil-converter:hermes-preflight v1 -->`. This matters because the worked-reference skill (`spec-cycle`) already has its own `## Phase 0 — Preflight` workflow section (contract §4 cites "spec-cycle's preflight"). The two coexist intentionally: the generated section is the capability gate; the author's is the skill's own procedure. The sentinel disambiguates them and is what the smoke test asserts on (so the gate is detectable even though `## Preflight`-like headings recur).
- **Rejected alternative:** a `scripts/preflight.*` or `references/preflight.md` file — supporting files are not auto-loaded at skill view, so the gate would never fire; and a `scripts/` pre-flight cannot run when `shell` itself is the missing capability.
- **Enforceability is advisory-by-construction — stated honestly.** Because the converter has no Hermes load-time hook, this gate is *prose the agent is asked to honor*, not a runtime callback / exit code. That is materially weaker than the contract's "a harness MUST verify each required capability before any mutation and fail clearly" (§3 availability) — which is a **harness** obligation. The adapter discharges *its* half (emit the gate, emit the gating keys where Hermes has them, document the gap); full runtime enforcement depends on Hermes honoring the prose, which is the documented **lossy-in-kind** §3 gap, fed back to VHS-17 — it is **not** a runtime hard gate that the adapter can guarantee. `HERMES-MAPPING.md` and Done-when 4 state this explicitly; the spec does not claim a hard runtime fail the adapter cannot deliver.
- **Required re-verify (D9):** confirming whether the live Hermes exposes a **native** skill-load pre-flight / validation hook is a *required* re-verify item, not optional — it is the difference between a real gate and a suggestion. If such a hook exists, wire the check there (in addition to the preamble) per the brief's "generate (or wire)" and record it in `HERMES-MAPPING.md`.

### D4 — Optional services (`?`) emit NO gating key — they are a documented gap

Grounded in the live affordance semantics (wiki `tools/hermes-agent/skills-system.md:120–123`):
- `requires_toolsets` → "Skill **hidden** when listed toolsets **unavailable**." Using it for an optional service would hide the skill whenever the optional service is absent — violating warn-and-proceed (the skill must still load and run).
- `fallback_for_toolsets` → "Skill **hidden** when listed toolsets **available**" — the inverse (a fallback skill); semantically wrong for "use-if-available."

Neither key expresses "always shown; use the service if present, warn if not." So **optional services are not emitted as any `requires_*`/`fallback_*` key.** They are surfaced as an advisory line in the generated preamble (warn-and-proceed) and recorded as an explicit gap in `HERMES-MAPPING.md`, fed back to VHS-17 as a §3 clarification request (brief out-of-scope: "a mismatch is surfaced as a gap/feedback to VHS-17, not patched ad hoc"). Required services (no `?`) **do** map to `requires_toolsets`/`requires_tools` (hiding-when-absent is acceptable — a missing required capability should make the skill unavailable, and the pre-flight hard-fails it anyway).

### D5 — `network` / `subagents` / `filesystem` → pre-flight only (per §3 table)

The §3 table maps these three to "(no direct Hermes frontmatter equivalent) — adapter's own pre-flight enforces." Hermes does have `file` and `delegation` toolsets, but those are **visibility** affordances, not hard-contract equivalents; gating on them would only hide the skill, not hard-fail before mutation. So the adapter emits **no gating key** for these three and relies on the D3 pre-flight. `subagents` ≈ the `delegation` toolset: per the brief, gateability is to be confirmed at re-verify; because gating ≠ the required hard-fail semantics, the pre-flight stands regardless. (If re-verify shows value in *also* emitting `requires_toolsets: [delegation]` as a belt-and-suspenders visibility gate, that is permitted and recorded — non-normative; the pre-flight remains the hard guard.) Each of the three gets an explicit gap entry in `HERMES-MAPPING.md`.

### D6 — `HERMES_HOME` resolved, never hardcoded (contract §1)

Add `resolveHermesHome(value)` to `src/utils/resolve-home.ts`, mirroring `resolveCodexHome`: precedence `--hermes-home` flag → `$HERMES_HOME` → `~/.hermes`. The resolved value is the **profile home**; skills are written under `<home>/skills/<name>/SKILL.md` (wiki: `~/.hermes/skills/` is the single source of truth, per-profile via `HERMES_HOME`). The path is never a string literal in the converter or writer. Mirror `resolveCodexHome` exactly: it expands **both** the explicit flag (via `resolveTargetHome` → `expandHome`) **and** the env-var default (`path.resolve(expandHome(defaultPath))`, resolve-home.ts:21), so `HERMES_HOME=~/foo` resolves correctly on POSIX and Windows (`expandHome` uses `path.sep`); empty / whitespace `HERMES_HOME` falls back to the default via the same `.trim() || default` guard. (No divergence from codex is needed — codex already expands its env value.)

### D7 — Frontmatter is serialized with js-yaml `dump`, not the engine's `formatFrontmatter`

The engine's `formatFrontmatter`/`formatYamlLine` (`src/utils/frontmatter.ts:39–71`) handles only scalars and one-level arrays — a nested object value falls through `formatYamlValue` to `String(value)` and renders as `"[object Object]"`. Hermes requires a **nested** `metadata.hermes.*` block, so the Hermes converter must serialize its frontmatter with js-yaml's `dump` (js-yaml is already a dependency — `load` is imported at `frontmatter.ts:1`), then concatenate `---\n<dump>---\n\n<preamble?>\n<body>`. Do not route Hermes frontmatter through `formatFrontmatter`.

### D8 — CI exercises the mapping via a contract-conformant `capability-demo` sample

CI runs on GitHub Actions (ubuntu) and has no `~/.claude/skills/`; the smoke test ingests the in-repo `samples/skills/`. The current `samples/skills/capability-demo/SKILL.md` carries `requires: { services: [issue-tracker?, shared-memory?], tools: [bash] }` — `tools:` is **not** a contract §3 key, so it would exercise nothing real. Replace it with a contract-conformant block that drives every §3 branch (terminal gate, env-var, pre-flight, required-vs-optional service). Recommended fixture:

```yaml
requires:
  shell: true
  filesystem: [read, write]
  network: true
  subagents: true
  services: [issue-tracker, shared-memory?]   # issue-tracker REQUIRED+credentialed; shared-memory optional
```

Editing this fixture is safe: the existing smoke assertions check only skill **count** and `opencode.json` validity (smoke-test.ts:91–114), never capability-demo's specific frontmatter. The four real vigil skills (whose `services` are all optional in `spec-cycle`) are exercised separately by the live-load proof.

### D9 — Re-verify Hermes affordances against the live harness before encoding

The mapping is authored from the wiki snapshot (2026-05-23). Per Scope item 7, the implementer confirms against the running Hermes before hardcoding. Required re-verify items (each, if it drifts, recorded in `HERMES-MAPPING.md`'s drift section):

- **Toolset names** — `terminal`, `memory`, `delegation`, … (tools-and-toolsets.md:31).
- **The exact `metadata.hermes.*` keys** and their nesting.
- **Placement of `required_environment_variables`** — *provisional default: nested under `metadata.hermes`* (per the brief). But the snapshot is genuinely ambiguous: skills-system.md describes it in a standalone section and omits it from the `metadata.hermes.*` field table — suggesting it may be **top-level** frontmatter. If re-verify shows top-level, **move it out of `metadata.hermes`** in the emitter. The Tier-1 YAML round-trip assertion cannot distinguish the two placements, so this must be checked against the live harness, not the smoke test. The emission template (Design) marks this field provisional for the same reason.
- **Toolset/tool names backing `issue-tracker` / `vcs-host` / `code-review-bot`**, and their credential env-var names. *Provisional default when a name is unconfirmed:* emit a deterministic documented placeholder (e.g. `requires_tools: [issue-tracker]` and a `required_environment_variables` entry with a placeholder `name` like `ISSUE_TRACKER_TOKEN`), and record the placeholder in `HERMES-MAPPING.md` so it is visibly provisional rather than silently guessed. The smoke test asserts the *shape*, not the exact name (Test plan).
- **Native skill-load pre-flight / validation hook** — whether one exists (D3). Required, not optional.

The mapping values below are **provisional pending this re-verify**.

### D10 — Security-first: parse-and-transform only, never executes skill content

Carried from the brief and inherited from the VHS-19 engine invariant (zero exec sinks across `src/`; the conversion path never runs skill content). The new Hermes code stays strictly within that boundary: it reads frontmatter + body, reshapes them, and writes files — it **never** evaluates, sources, or executes any part of a skill during conversion. Credentialed services route through `required_environment_variables` (name/prompt/help/required_for), **never** inlined secrets in the emitted package; Hermes prompts for them only at local-CLI load (wiki `skills-system.md:129–142`), never in chat surfaces. Pairs with the Petasos session-sanitization posture. This is a constraint on the *adapter*, orthogonal to the advisory-by-construction nature of the runtime pre-flight (D3).

---

## Design

### Capability → Hermes mapping (the §3 table, as implemented)

| Canonical `requires` | Required (no `?`) | Optional (`?`) |
|---|---|---|
| `shell: true` | `metadata.hermes.requires_toolsets: [terminal]` **+ pre-flight** | (n/a — `shell` is a boolean, never optional) |
| `services: shared-memory` | `requires_toolsets: [memory]` **+ pre-flight** | advisory-only (D4): no gating key; preamble warn |
| `services: issue-tracker` | `requires_tools`/`requires_toolsets` (MCP-backed; re-verify name) **+ `required_environment_variables`** (credentialed; placement provisional — D9) **+ pre-flight** | advisory-only (D4) |
| `services: vcs-host` / `code-review-bot` | same shape as issue-tracker (MCP-backed, credentialed) **+ pre-flight** | advisory-only (D4) |
| `network: true` | **pre-flight only** — gap (D5) | (n/a) |
| `subagents: true` | **pre-flight only** — gap (D5); optionally also `requires_toolsets:[delegation]` if re-verify confirms value | (n/a) |
| `filesystem: [read, write]` | **pre-flight only** — gap (D5) | (n/a) |

Frontmatter classes carried/dropped (contract §2): `name`, `description` preserved verbatim (description drives Level-0 `skills_list` disclosure — must stay intact). `user_invocable` is **dropped** — every Hermes skill is already a slash command, so the flag is informational there. `allowed-tools`, `argument-hint`, `disable-model-invocation`, `model`, `ce_platforms` are dropped (Claude-only / CE-legacy; none load-bearing for the four skills). `version` / `platforms` are optional Hermes extensions; v1 does **not** synthesize them (no source value to derive — avoid inventing data).

### Per-skill emission (`writeHermesBundle`)

For each `ClaudeSkill` in the plugin, write `<hermesHome>/skills/<sanitizedName>/SKILL.md` where the file is:

```
---
name: <name>
description: <description verbatim>
metadata:
  hermes:
    requires_toolsets: [<...>]        # only if non-empty
    requires_tools: [<...>]           # only if non-empty
    required_environment_variables:   # only for credentialed required services
      - {name, prompt, help, required_for}   # placement provisional — D9 (may be top-level)
---

<!-- vigil-converter:hermes-preflight v1 -->
## Capability pre-flight (generated …)   # only if ≥1 required capability (D3)
<generated gate>

<author body, verbatim>
```

**Frontmatter is serialized with js-yaml `dump`** (D7), not `formatFrontmatter` — `import { dump } from "js-yaml"` in `claude-to-hermes.ts`; the resulting block must satisfy the Tier-1 YAML round-trip assertion.

**Writer mechanics (collision-safe, non-destructive of user content):**
- Resolve `<sanitizedName>` via the engine's `sanitizePathName` (the same helper the OpenCode writer uses). Guard name collisions with a `seen` Set: on a sanitized-name collision, **skip-with-warning** rather than silently overwrite. (Pattern borrowed from `src/targets/opencode.ts:94–101` — note that range is OpenCode's *agent* guard; the OpenCode *skill* loop has no `seen` Set, so the Hermes skill writer adds the guard the inherited skill loops lack.) Can't occur for the four distinct vigil-skill names, but the writer must be generic.
- **Re-emission is non-destructive of unknown content (default).** Always (over)write the generated `SKILL.md` and copy the source's own subtrees; do **not** blanket-`rm` the target skill dir, because `<hermesHome>/skills/` is Hermes's *single source of truth* where agent-created and user-edited skills live (wiki `skills-system.md:10,192`) — an unconditional `rm` of `<name>/` would delete a user's edited `SKILL.md`/`references/`/local `config.yaml` under that name, not just converter orphans. Stale converter-orphan files (a source subtree file later deleted) are a documented v1 limitation — they cannot occur for the four single-file vigil skills, and a manifest-scoped cleanup (the mechanism the inherited writers use; see next bullet) is a deferred enhancement if multi-skill orphan churn ever matters. A **blanket clean-replace is acceptable only against a freshly-created / dedicated / temp `HERMES_HOME`** (the CI Tier-1 path uses a `mkdtemp` home), never the user's live `~/.hermes`.
- **Deliberate divergence from the inherited manifest cleanup.** OpenCode/Codex/Pi/Gemini avoid orphans via an *install-manifest-gated* removal (`src/targets/managed-artifacts.ts` `cleanupCurrentManagedDirectory` — only deletes dirs the converter's own prior install recorded). The Hermes writer deliberately **omits** that machinery for v1 (the Hermes tree is wholly generated per skill and not merged into a multi-target project root; `kiro` is the manifest-free structural sibling). Adopting the manifest is the deferred enhancement noted above (VHS-22 territory if multi-plugin Hermes installs land), not in scope here.
- **The generated `SKILL.md` must win, not the verbatim source.** `copySkillDir` (`src/utils/files.ts:165–193`) copies the *entire* source dir including `SKILL.md`, additive-merge (never deletes target-only files), and only rewrites `SKILL.md` when a `transformSkillContent` callback is passed (else it copies it verbatim). The true mirror of the OpenCode path — `copySkillDir(skill.sourceDir, targetDir, transformSkillContentForOpenCode, true)` (`src/targets/opencode.ts:125–131`) — is to pass a Hermes transform callback that closes over the precomputed per-skill metadata and returns the reshaped SKILL.md (nested frontmatter + pre-flight + verbatim body). That copies supporting subtrees (`references/`, `templates/`, `scripts/`, `assets/`) **and** produces the generated SKILL.md in one call. Equivalent alternative: write the generated SKILL.md, then copy only the supporting subdirs (never the source SKILL.md). Do **not** copy the source SKILL.md verbatim and then separately write the generated one — order-dependent clobber.

### Service-token normalization (adapter-side)

The §3 lexical rules live in the VHS-18 *validator*; the adapter must restate the slice it depends on, because js-yaml hands it raw scalars (`[issue-tracker?, shared-memory?]` → `["issue-tracker?", "shared-memory?"]`, and `[issue-tracker ?]` → `["issue-tracker ?"]` — internal space preserved). For each `services` element the converter: `trim()` → strip **exactly one** trailing `?` (record the optional flag) → `trim()` again → lowercase-exact-match against the controlled vocabulary `{issue-tracker, shared-memory, code-review-bot, vcs-host}`. An element that does **not** match after normalization is **warned and recorded as a gap** in `HERMES-MAPPING.md` (never silently dropped — the no-silent-drop rule) and emits no gating key. This applies identically to required and optional services. After vocab-matching, **deduplicate roles**: if the same role appears twice, emit one gating entry; if it appears both required and optional (`[issue-tracker, issue-tracker?]`), **required wins** — the role is gated and the pre-flight lists it required. (A bare `?` or other YAML-significant token that breaks the *parse* is handled one layer up — see "malformed YAML" below.)

### Absent / malformed `requires` handling (declare-don't-infer)

- **No `requires:` key** (3 of 4 real skills; `hello-world`): emit `name` + `description` and an empty-or-omitted `metadata.hermes` (a minimal block, or none if no tags/category) — **no** `requires_*` keys, **no** pre-flight section, no error.
- **`requires:` present but empty / all-optional** (`spec-cycle`: `services: [issue-tracker?, shared-memory?]` plus required booleans): required booleans drive the pre-flight; optional services are advisory-only (D4).
- **Unrecognized keys under `requires`** (e.g. the legacy `tools:`): the converter **ignores them with a warning** and continues — it does not crash and does not infer. (The contract's "unknown keys are violations" is the VHS-18 lint's job, not the adapter's; the adapter must be robust to well-formed-but-non-conformant input.)
- **`requires` that is a well-formed non-mapping** (scalar / list value): treat as no usable declaration, warn, emit ungated.
- **Malformed *YAML* in the frontmatter** (a `requires:` block that doesn't parse — e.g. `services: [?]`, which makes js-yaml throw): this is **not** something the adapter intercepts. `parseFrontmatter` raises a clear, located error (`frontmatter.ts:35`) and `loadSkills` (`claude.ts:128–130`) has no try/catch, so the whole `convert` run **fails loudly** before the adapter executes — the same fail-clear behavior the engine already has for *any* malformed `SKILL.md`. That is acceptable (a broken source file should fail loudly, not be silently degraded), and the adapter's graceful-degradation contract above is therefore scoped to **well-formed-but-non-conformant** shapes only, never to un-parseable YAML. (Making malformed-YAML skip-with-warning would require wrapping the per-skill parse in `loadSkills` — a larger, engine-wide change and out of scope here; flag to VHS-18 if desired.)

### The two evidence tiers (see Test plan)

1. **CI smoke (automated, blocking)** over `samples/skills/` — proves the engine emits a structurally correct, mapping-correct Hermes package after the change. Mirrors the VHS-19 gate.
2. **Live-load proof (manual, captured)** over the four real vigil skills against a running Hermes — proves install + load (`skills_list` / slash command / `skill_view`). This is the part CI cannot run (no live Hermes on the runner), captured as evidence for the acceptance trail.

---

## Test plan

### Tier 1 — CI smoke path (automated; the ship-spec test gate)

Extend `scripts/smoke-test.ts` with a Hermes conversion of `samples/skills/` into a temp Hermes home (`--hermes-home <tmp>`), then assert:

All structural assertions parse the emitted SKILL.md with `parseFrontmatter` / a YAML `load` and assert on **parsed values**, never on raw frontmatter lines (js-yaml `dump` is free to reflow scalars — a long/colon-bearing `description` may emit as a folded `>-` block, so a raw line-compare would false-fail; see assertion 5).

1. **Package shape** — for each parsed sample skill, `<tmp>/skills/<sanitizedName>/SKILL.md` exists and is non-empty.
2. **No-`requires` case** (`hello-world`) — emitted frontmatter parses; has `name` + `description`; **no** `requires_toolsets`/`requires_tools`/`required_environment_variables`; **no** pre-flight sentinel.
3. **Full-mapping case** (`capability-demo`, per D8 fixture: `shell`, `filesystem`, `network`, `subagents`, `services: [issue-tracker, shared-memory?]` — `issue-tracker` required+credentialed, `shared-memory` optional):
   - `metadata.hermes.requires_toolsets` includes `terminal` (from `shell`).
   - the **required** service `issue-tracker` is gated: it appears in `requires_tools`/`requires_toolsets` (provisional name, D9) **and** a `required_environment_variables` entry exists for it — asserted **structurally** (the array exists and each entry has `{name, prompt, help, required_for}`), **not** by exact var name (D9 leaves the name unconfirmed; the adapter emits a documented placeholder).
   - the generated pre-flight sentinel (`<!-- vigil-converter:hermes-preflight v1 -->`) is present and the section names each required capability: `terminal`/`shell`, `network`, `subagents`, `filesystem`, and `issue-tracker` (the full required set the D3 template emits — `shell` included).
4. **Optional service is NOT gated** (D4) — the optional `shared-memory?` (which would map to the `memory` toolset) appears in **no** `requires_*` **or** `fallback_*` key; it appears only as an advisory line in the pre-flight section.
5. **`description` preserved verbatim (by value)** — re-parse the emitted frontmatter with `load`; the `description` **value** byte-equals the source value (subsumes a "frontmatter parses" check). Use a fixture description containing a colon (and ideally a newline) so the reflow path is exercised — `hello-world`/`capability-demo` descriptions already contain colons.
6. **Nested block is well-formed** — the re-parse in (5) also confirms `metadata.hermes` is a real nested mapping (not the string `"[object Object]"`), guarding the D7 `dump` requirement.
7. **Robustness** — a skill carrying a well-formed unrecognized `requires` key (e.g. legacy `tools:`) or a **well-formed** out-of-vocab service token (e.g. `services: [nonexistent-role]` — a quoted/plain scalar, *not* a bare `?`) does **not** abort the run and emits ungated-with-warning (fold into the capability-demo path or a tiny inline fixture). (Malformed *YAML* like `services: [?]` is expected to fail the run loudly — not asserted here; see Design "malformed YAML".)
8. **Temp-dir hygiene** — the Hermes temp home is created with `mkdtemp` and removed in a `finally` (`fs.rmSync(..., {recursive:true, force:true})`); a slight improvement over the existing no-cleanup pattern, harmless on CI.

The Hermes path is additive — the existing OpenCode/Codex assertions (smoke-test.ts:60–114) stay green unchanged. Add `hermes` so a failure in it fails CI.

### Tier 2 — Live-load proof (manual; captured evidence, not the automated gate)

1. Convert the four vigil skills (source = the vigil-skills repo `skills/` directory ≡ what `sync.py` installs to `~/.claude/skills/`) into a Hermes home: `bun run src/index.ts convert <vigil-skills>/skills --to hermes --hermes-home <HERMES_HOME>`.
2. Load under a live Hermes and capture: `skills_list` shows all four; each resolves as a slash command; `skill_view <name>` renders each (including `spec-cycle`'s generated preamble).
3. Save the transcript / run log to the acceptance trail (e.g. `docs/specs/TODO/VHS-20.test-output.txt`, the same convention VHS-13 used, and/or attach to the PR).
4. Record any Hermes-affordance drift from the wiki snapshot in `HERMES-MAPPING.md` (Done-when criterion 6 + D9).

> Tier 2 requires a reachable live Hermes (a `HERMES_HOME`). If none is reachable at implementation time, that is a ship blocker to surface — not something to fake.

## Test command

```bash
# Run from the vigil-converter repo root (the implementation tree — Decision D1):
bun run scripts/smoke-test.ts
```

This is the automated, blocking gate ship-spec keys on (Tier 1). Tier 2 (live-load) is a manual checklist item captured as evidence, not part of this command.

---

## Done when

1. **`hermes` target registered + converts the four skills** — `targets.hermes` is `implemented: true` (`src/targets/index.ts`); `--to hermes` converts the four canonical vigil skills into Hermes packages. (Source = the vigil-skills repo `skills/` tree, which is byte-identical to the installed `~/.claude/skills/<those>` via `sync.py`, so either path is a valid `--to hermes` source — the brief names `~/.claude/skills/`.) *(Brief Done-when 1)*
2. **Installs + loads under a live Hermes, with evidence** — the emitted packages appear in `skills_list`, resolve as slash commands, and render under `skill_view`; the transcript is captured to the acceptance trail. **If no live Hermes is reachable at ship time, this criterion is deferred to a partial-close** (D1) with the gap recorded in `HERMES-MAPPING.md` + the test-output trail; it is never marked met without captured evidence. *(Brief Done-when 2; Tier-2 test)*
3. **Capability→affordance mapping documented, gaps enumerated** — `HERMES-MAPPING.md` implements the §3 table and lists every unsupported gap (optional-service-not-gateable, `network`/`subagents`/`filesystem` no-gating-key) with how the adapter compensates (pre-flight / advisory). *(Brief Done-when 3)*
4. **Pre-flight in place** — the generated pre-flight section (D3) enumerates every required (no-`?`) capability and instructs a halt-before-mutation when any is unavailable, naming it; optional (`?`) services warn-and-proceed. On Hermes this gate is **advisory-by-construction** (agent-honored prose) unless the live harness exposes a native skill-load hook to wire into (D3, D9) — a documented §3 lossiness, not a runtime hard-fail the adapter can guarantee. The adapter's obligation is met when the gate + gating keys are emitted and the residual enforcement gap is documented in `HERMES-MAPPING.md`. *(Brief Done-when 4)*
5. **No-`requires:` case handled without error** — the three undeclared skills convert and load **ungated** (no gating keys, no preamble), no error. *(Brief Done-when 5)*
6. **CI runs the Hermes conversion where feasible; drift recorded** — `scripts/smoke-test.ts` exercises the Hermes path on every CI run; affordance drift from the 2026-05-23 snapshot is recorded in `HERMES-MAPPING.md`. *(Brief Done-when 6)*

---

## Out of scope

- **Behavioral-parity proof** (same observable outcome on Claude Code and Hermes) — that is the conformance suite, VHS-21 (contract §5). This item proves install + load only.
- **Validating the inherited OpenCode/Codex/Gemini/Pi/Kiro targets** and adding Cursor/Copilot — v2.
- **Backfilling `requires:` declarations** onto `ship-spec`, `spec-close`, `review-pr` — VHS-18 authoring/lint work; the no-`requires` path here handles them ungated, and the gap is filed, not fixed.
- **Any change to vigil-skills' distribution spine** (`sync.py`, multi-harness install/output) — VHS-22. vigil-skills stays stdlib-only; the Bun toolchain stays isolated in vigil-converter.
- **Rewriting the engine to decouple the inherited CE legacy-compat code** — the VHS-19 no-rewrite/entanglement rule stands; the `STRIP.md` residue scrub is separate.
- **Changing the portability contract** — §3 is the spec this adapter targets; a mismatch (e.g. §3's table being silent on the optional-service mapping, D4) is surfaced as feedback to VHS-17, not patched here.
- **A general capability-validation framework / a `requires` lint in the engine** — the adapter reads `requires` and is robust to malformed input, but validation/linting is VHS-18.

---

## Deferred (P2+)

_None deferred — every round-1 and round-2 P0/P1/P2 finding was folded into the spec (see revision history in `VHS-20.reviews/` and the Post-green polish below). The only standing v1 limitations are explicitly documented in-place: the pre-flight is advisory-by-construction (D3), optional-service/network/subagents/filesystem gaps (D4/D5), and converter-orphan cleanup is non-destructive-but-additive (Design § Writer mechanics) — a manifest-scoped cleanup is a deferred enhancement (VHS-22 territory)._

## Post-green polish

Green at round 2 (all three lenses GREEN). The bounded post-green polish folded these clarifications (no behavior reversals, no scope/Decision/Done-when changes):

- **edge-cases R2/F-1 + conventions R2/F-2 (P2, Pre-ship)** — Writer mechanics reworked to be **non-destructive of user content**: default is overwrite-generated-`SKILL.md` + copy source subtrees, **no blanket `rm`** of the per-skill dir (Hermes `~/.hermes/skills/` is the user/agent source of truth); blanket clean-replace allowed only against a temp/dedicated `HERMES_HOME` (CI). Added the deliberate-divergence-from-manifest-cleanup rationale (kiro is the manifest-free sibling).
- **edge-cases R2/F-2 (P2)** — `convertClaudeToHermes` `null` contract stated: empty/no-`requires` plugins emit an (empty) bundle, never `null`; `null` ⇒ hard abort at `convert.ts:166`.
- **correctness R2/F-1 (P3)** — D6 corrected: `resolveCodexHome` already expands its env value; mirror it exactly, dropped the false "improvement" rationale.
- **correctness R2/F-2 (P3)** — Tier-1 assertion 3 now names `terminal`/`shell` in the required-capability enumeration (matching the D3 template).
- **correctness R2/F-3 (P3)** — collision-guard anchor reframed: `opencode.ts:94–101` is the *agent* guard borrowed as a pattern; the Hermes skill writer adds the guard the inherited skill loops lack.
- **edge-cases R2/F-3 (P3)** — service-token normalization gains role **dedup** + required-wins precedence.
- **edge-cases R2/F-4 (P3)** — Tier-1 assertion 7's out-of-vocab fixture pinned to a well-formed scalar (`[nonexistent-role]`, not a bare `?`).
