# VHS-20 — Cross-harness: Hermes target adapter (v1 headline)

**Status:** Backlog · **Priority:** High · **Assignee:** Devin
**Created:** 2026-06-14 · **Plane:** VHS-20 (child of VHS-16)
**Origin:** VHS-16's "Hermes-first" cross-harness epic names Hermes as the v1 target harness *because no CE adapter exists for it* — so the Hermes adapter is the defining new deliverable of v1, not an inherited freebie. It is built on the owned conversion engine stood up in VHS-19 and targets the portability contract authored in VHS-17.

> **Blockers — both now cleared (verified).** The ticket text says "Blocked by the fork baseline (VHS-19) and contract (VHS-17)." Both are **merged and closed**:
> - **VHS-17** (portability contract) — merged `39006cc` (PR #17), closed 2026-06-14. The contract lives at `docs/portability-contract.md`; §3 already carries the **canonical→Hermes mapping table** this adapter implements.
> - **VHS-19** (fork baseline) — closed 2026-06-15. The engine is `ziomancer/vigil-converter` (public, MIT) @ `14cdca4f`, CI run 27532395287 green. It emits per-harness packages from canonical `SKILL.md`; the Hermes adapter is the next target registered on it.
>
> This item is therefore **unblocked**.

> **Correction carried in (verify before encoding).** The Plane ticket body says to "mirror how CE's existing adapters target **OpenClaw/Codex**." The verified upstream CE target roster is **OpenCode, Codex, Cursor, Gemini, Pi, Kiro** (and related) — **OpenClaw is not a CE target**; it is the fleet's own harness (Calvin). This is the same naming slip VHS-19 caught and corrected in its spec-cycle. The adapters to mirror for structure are **OpenCode and Codex**; treat any "OpenClaw" reference in the ticket as "OpenCode."

> **Loop note.** The deliverable is *a working Hermes adapter on the vigil-converter engine plus a documented capability mapping*, not a parity proof. "The vigil skill set installs and loads under Hermes" is an **install/load liveness** bar, not a behavioral-parity assertion — parity is the conformance suite (VHS-21, contract §5). Do not let the loop expand this into writing conformance tests, validating the inherited OpenCode/Codex targets (v2), or backfilling `requires:` blocks onto the three skills that currently lack one (that is authoring/lint work, VHS-18, tracked separately). If a skill cannot be cleanly mapped because Hermes lacks an affordance, **surface the gap explicitly** (per the contract) and file it — do not invent a Hermes feature or silently drop the capability.

## Goal

Write the **Hermes output adapter** for the owned `vigil-converter` engine — the one target CE never shipped — so that the canonical `SKILL.md` shape emits **installable, loadable Hermes skill packages** for the vigil skill set, with every declared capability mapped to a real Hermes affordance and every unmappable capability surfaced as an explicit, documented gap.

## Context (verified)

The engine to extend is **`ziomancer/vigil-converter`** (VHS-19), a fork of `EveryInc/compound-engineering-plugin` reduced to its Bun/TypeScript conversion engine. It already emits OpenCode, Codex, Gemini, Pi, and Kiro packages from a bare `SKILL.md` skills root (`src/parsers/claude.ts`, manifest-optional). Hermes is absent from that inherited roster — which is exactly why VHS-16 chose fork-and-own: a new `--to hermes` target gets added to an engine we control. The existing OpenCode/Codex target adapters are the structural template to mirror.

**The contract has already done the design work.** `docs/portability-contract.md` §3 specifies the canonical `requires:` declaration *and* its Hermes mapping. The adapter implements that table; it does not re-derive it:

| Canonical `requires` | Hermes target | Note |
|----------------------|---------------|------|
| `services` (role tokens) | `metadata.hermes.requires_toolsets` / `requires_tools` (+ `required_environment_variables` for credentialed services) | role → toolset/tool |
| `shell: true` | a `terminal`-toolset requirement | |
| `network`, `subagents`, `filesystem` | (no direct Hermes frontmatter equivalent) | the adapter's own hard pre-flight enforces |

**The mapping is lossy in kind, and the contract says so.** Hermes's `requires_*` keys *gate visibility* (they hide/show a skill), whereas the contract's `requires` is a *hard pre-flight contract* (a missing **required** capability must cause a clear failure before any mutation; a missing **optional** `?` service warns-and-proceeds). The adapter therefore must emit the Hermes gating keys **and** add a hard pre-flight for required capabilities — the two are not interchangeable.

**Hermes affordances (documented from the live harness — wiki `tools/hermes-agent/`, snapshot 2026-05-23, re-verify against the running harness before encoding):**
- **Skill home & layout** — `~/.hermes/skills/` is the single source of truth, resolved via `HERMES_HOME` (**never hardcode the path** — contract §1). Each skill is its own directory with `SKILL.md` plus optional `references/`, `templates/`, `scripts/`, `assets/`. Category directories are supported.
- **Frontmatter** — `name`, `description`, `version`, optional `platforms`, and a nested `metadata.hermes.*` block (`tags`, `category`, `requires_toolsets`, `requires_tools`, `fallback_for_toolsets`, `fallback_for_tools`, `config`, `required_environment_variables`). The canonical-source `requires:` is *flat by design*; the adapter **nests** it under `metadata.hermes` (contract §3 explicitly permits generated adapters to reshape).
- **Invocation** — every installed skill automatically becomes a slash command, so canonical `user_invocable: true` is informational on Hermes (contract §2). Progressive disclosure: Level-0 `skills_list` reads `description` (so it must stay self-contained and intent-rich).
- **Toolsets to map roles onto** — `terminal`, `web`, `file`, `browser`, `memory`, `delegation`, `skills`, `cronjob`, `code_execution`, etc. Relevant role mappings: `shell` → `terminal`; `services: shared-memory` → the `memory` toolset; `services: issue-tracker` / `vcs-host` / `code-review-bot` → an MCP-backed tool/toolset (+ `required_environment_variables` where credentialed). `subagents` ≈ the `delegation` toolset affordance — confirm whether it is gateable before relying on it.
- **Secrets** — credentialed services map to `required_environment_variables` (`name`, `prompt`, `help`, `required_for`); Hermes prompts for these only when the skill loads in the local CLI and never in chat surfaces.

**The vigil skill set the adapter must convert (verified in `skills/`).** Four skills today — `spec-cycle`, `ship-spec`, `spec-close`, `review-pr`. Only `spec-cycle` carries a `requires:` block (the contract's worked reference: `shell`, `filesystem: [read, write]`, `network`, `subagents`, `services: [issue-tracker?, shared-memory?]`). The other three declare only `name` / `description` / `user_invocable`. **This is a load-bearing input gap:** a skill with no `requires:` maps to a Hermes package with no toolset gating and no capability pre-flight — which is *correct adapter behavior* (declare-don't-infer, contract §3), but means those three skills install on Hermes ungated. The adapter must handle the no-`requires:` case cleanly; backfilling declarations onto those skills is **out of scope** (VHS-18 authoring work) and should be filed, not done here.

## Scope

1. **Add a `hermes` target to the engine.** Implement a Hermes output adapter in `vigil-converter` mirroring the structure of the existing OpenCode/Codex target adapters (target registration + emitter). Drive it via the engine's existing `--to`-style target selection so a single canonical `SKILL.md` source produces a Hermes package.
2. **Emit the Hermes package shape.** Per skill, produce a `~/.hermes/skills/<name>/SKILL.md` (path resolved via `HERMES_HOME`, never hardcoded) with portable frontmatter translated to Hermes's nested form: `name`, `description` (preserved verbatim — it drives Level-0 disclosure), and a `metadata.hermes` block. Carry supporting subtrees (`references/`, `scripts/`, etc.) if any canonical skill has them. Markdown body passes through unchanged (intent-over-implementation already holds in the source per contract §4).
3. **Implement the §3 mapping table.** Translate the flat canonical `requires:` to `metadata.hermes.requires_toolsets` / `requires_tools` / `required_environment_variables` exactly as §3 specifies (`shell`→`terminal`; `services` roles → toolsets/tools/env-vars). Handle the absent-`requires:` case (emit no gating keys, no pre-flight) without error.
4. **Add the hard pre-flight the gating keys can't express.** Because Hermes `requires_*` only gate *visibility*, generate (or wire) a pre-flight for **required** (no-`?`) capabilities — `network`, `subagents`, `filesystem`, and required `services` — that fails clearly, naming the unmet capability, before any mutation; **optional** (`?`) services warn-and-proceed. This is the contract-§3 "must add a hard pre-flight even where it also emits the Hermes gating keys" requirement.
5. **Document the capability-to-affordance mapping, gaps included.** Produce a mapping doc (in `vigil-converter`, alongside `STRIP.md`) recording, for each canonical capability, its Hermes target — and for anything Hermes cannot express (e.g. a `filesystem`/`network`/`subagents` hard contract with no native gating key, or a `services` role with no Hermes toolset), an **explicit gap entry** stating what is unsupported and how the adapter compensates (pre-flight) or that it cannot. No silent drops.
6. **Prove install + load.** Convert the four vigil skills and demonstrate the emitted packages **install and load under a live Hermes** (skills appear in `skills_list`, resolve as slash commands, `skill_view` renders them). Capture the evidence (command output / run log) for the acceptance trail. Wire this into the fork's CI alongside the VHS-19 smoke test where feasible.
7. **Re-verify Hermes affordances against the live harness before encoding.** The mapping is built from the wiki snapshot (2026-05-23); confirm the toolset names, `metadata.hermes` keys, and `HERMES_HOME` resolution against the running Hermes before hardcoding any of them. Record any drift from the wiki.

## Decisions carried forward

- **Hermes affordances are documented from the live harness, not assumed.** The wiki (`tools/hermes-agent/skills-system.md`, `tools-and-toolsets.md`) is the starting reference; the adapter's mappings are confirmed against what Hermes actually exposes before they are encoded. Any drift from the wiki snapshot is recorded.
- **Any capability a skill needs but Hermes lacks is surfaced as an explicit gap, never silently dropped.** The §3 mapping is *lossy in kind* (visibility-gating ≠ hard pre-flight); the adapter compensates with its own pre-flight and documents every unmappable capability.
- **Adapters are generated, never hand-maintained** (contract §1). The Hermes package is emitted from canonical `SKILL.md`; it is never hand-edited downstream, and the source is never forked per harness.
- **Canonical `requires:` is flat; the adapter reshapes it** (contract §3) — nesting under `metadata.hermes` is expected and permitted; flatness is a property of the source block only.
- **Declare-don't-infer.** A skill with no `requires:` yields an ungated Hermes package by design; the adapter does not infer capabilities from the body. Backfilling declarations is VHS-18, out of scope here.
- **Security-first (pairs with the Petasos posture).** The adapter is parse-and-transform only — it **never executes skill content** during conversion (inherited from the VHS-19 engine invariant). New Hermes code stays within that boundary; credentialed services route through `required_environment_variables`, never inlined secrets.
- **`HERMES_HOME` is resolved, never hardcoded** (contract §1).

## Done when

- A `hermes` target is registered on `vigil-converter` and converts the four canonical vigil skills to Hermes packages from `~/.claude/skills/` (the same source the VHS-19 engine ingests).
- The emitted vigil skill set **installs and loads under a live Hermes** — skills appear in `skills_list`, resolve as slash commands, and `skill_view` renders them — with the evidence captured.
- The **capability-to-affordance mapping is documented**, implementing contract §3 and enumerating every **unsupported gap** with how (or whether) the adapter compensates.
- The hard pre-flight for required capabilities (the part Hermes's visibility-gating keys cannot express) is in place: required-capability-missing fails clearly before mutation; optional (`?`) services warn-and-proceed.
- The no-`requires:` input case is handled without error (the three undeclared skills convert and load ungated).
- The Hermes conversion runs in the fork's CI where feasible; Hermes-affordance drift from the wiki snapshot is recorded.

## Out of scope

- **Behavioral-parity proof** that a vigil skill produces the same observable outcome on Claude Code and Hermes — that is the conformance suite, VHS-21 (contract §5). This item proves install + load, not parity.
- **Validating the inherited OpenCode/Codex targets** and adding Gemini/Cursor/Copilot — v2 (the sibling "Validate inherited CE targets" item).
- **Backfilling `requires:` declarations** onto `ship-spec`, `spec-close`, and `review-pr` — VHS-18 authoring/lint work; file the gap, don't fix it here.
- **Any change to vigil-skills' distribution spine** (`sync.py`, multi-harness install/output) — that is VHS-22; vigil-skills stays stdlib-only and the Bun toolchain stays isolated in `vigil-converter`.
- **Rewriting the engine to decouple the inherited CE legacy-compat code** — the VHS-19 no-rewrite/entanglement rule stands; the residual identifiers in `STRIP.md` are a separate tracked scrub.
- **Changing the portability contract** — §3's mapping is the spec this adapter targets; a mismatch is surfaced as a gap/feedback to VHS-17, not patched ad hoc.

## References

- Plane: VHS-20 (child of VHS-16 epic; blocked-by VHS-19 + VHS-17, both now closed). Siblings: VHS-21 (conformance suite), VHS-22 (distribution), "Validate inherited CE targets" (v2).
- `docs/portability-contract.md` (VHS-17, merged `39006cc` PR #17) — **§3** canonical→Hermes mapping table + the "must add a hard pre-flight" requirement; §1 `HERMES_HOME` rule; §2 frontmatter classes; §4 intent rule; §5 parity (out of scope here).
- `ziomancer/vigil-converter` @ `14cdca4f` (VHS-19) — the engine this target plugs into; `src/parsers/claude.ts` (skills-root input), existing OpenCode/Codex target adapters (structural template), `STRIP.md` (where the mapping doc lands), `.github/workflows/ci.yml` (CI to extend). CI run 27532395287 green.
- Wiki `tools/hermes-agent/skills-system.md` + `tools-and-toolsets.md` (snapshot 2026-05-23) — Hermes SKILL.md format, `metadata.hermes.*` keys, toolset roster, `HERMES_HOME`, progressive disclosure, `required_environment_variables`. **Re-verify against the live harness.**
- Wiki `comprehension/2026-06-15-vhs-19-vigil-converter-engine.md` + `decisions/2026-06-15-vhs-19-fork-and-own-converter.md` + `projects/vigil-converter/state.md` — engine baseline, the one load-bearing retarget edit, and the CE-entanglement debt.
- `skills/spec-cycle/SKILL.md` — the only skill carrying a `requires:` block (contract worked reference); `ship-spec`, `spec-close`, `review-pr` carry none (the no-`requires:` input case the adapter must handle).
- `docs/compound-engineering-evaluation.md` — adapt-don't-adopt analysis; verified CE roster (Hermes absent; "OpenClaw" is not a CE target).
