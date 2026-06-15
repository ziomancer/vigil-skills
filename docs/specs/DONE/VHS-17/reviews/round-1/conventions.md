# Conventions Review — round 1

## Findings

### F-1: §3 `requires:` schema ignores Hermes's existing capability-declaration frontmatter convention
**Severity:** P1
Brief decision: "Reuse existing frontmatter; don't invent a parallel manifest where a frontmatter key already does the job." Hermes — the spec's named v1 target (§1) — already ships capability-declaration frontmatter (wiki `tools/hermes-agent/skills-system.md:55-61,114-142`): `metadata.hermes.requires_tools`/`requires_toolsets`, `fallback_for_tools`/`fallback_for_toolsets`, `required_environment_variables`. The spec invents a different top-level `requires:` vocabulary with no mapping to Hermes's, so VHS-20 inherits an unscoped translation problem the contract was meant to close. §2 maps `user_invocable` to a Hermes equivalent but §3's new block has no such mapping note despite Hermes having the closest native equivalent.
**Fix:** Either (a) justify the new flat top-level shape over Hermes's nested `metadata.hermes.*` (legitimate semantic difference: Hermes keys are *visibility-gating* hints, ours is a hard *pre-flight* contract) AND add a §2 mapping row (`requires.services`/`requires.shell` → `metadata.hermes.requires_toolsets`/`requires_tools`); or (b) adopt the Hermes vocabulary directly.

### F-2: D5 "flat, no nested mappings" collides with Hermes's nested `metadata.hermes.*` — name the tension
**Severity:** P2
D5 mandates flat frontmatter; the v1 target mandates nested. D5's stdlib rationale is sound for linting the *canonical source*, but the spec never acknowledges the generated Hermes artifact is nested — so "flat" is a property of the source, not the portable format in general.
**Fix:** Add one sentence: "Flatness is a property of the canonical-source `requires:` block (so VHS-18 lints with stdlib only); generated adapters may emit whatever shape their target needs — e.g. the Hermes adapter nests under `metadata.hermes`."

### F-3: `services` vocabulary partially re-mints VHS-7's host-agnostic capability prose — reconcile
**Severity:** P2
VHS-7 established the prose convention ("the Plane MCP server's project-list capability … or the equivalent in your host"). `services` is a machine-readable re-encoding of the same roles but is never linked, so a reader can't tell if it's the structured form of VHS-7 or an independent taxonomy.
**Fix:** Cross-reference: "These role tokens are the structured form of the host-agnostic capability prose already used in skill bodies (VHS-7) — `issue-tracker` ≙ the 'Plane … or the equivalent in your host' construction."

### F-4: D6 cites "Phase 0 step 6" — fragile; spec-cycle has been renumbered twice
**Severity:** P3
VHS-6 and VHS-11 renumbered spec-cycle Phase 0 steps. The phrase at line 228 is stable; the step number is not.
**Fix:** Quote the construction (`e.g. \`mcp__plane__list_projects\` … or the equivalent in your host`) rather than citing a step number.

### F-5: §1 under-cites Hermes sources
**Severity:** P4
architecture.md:138 is the loader row only; `~/.hermes/skills/` is in cli-guide.md:164 / skills-system.md:10, and the canonical format reference is skills-system.md:43-142 (uncited).
**Fix:** Add `tools/hermes-agent/skills-system.md` to §1/§2 citations.

## What the spec gets right (no findings)
- Stdlib-only rule honored (D5 ties to no-stdlib-YAML).
- Frontmatter convention (name/description/user_invocable) classified correctly.
- sync.py anchors verified exact (sync.py:30, sync.py:96); "round-trips untouched by construction" correct.
- One-skill annotation respects brief out-of-scope; spec-cycle exercises every schema field.
- Scope fences vs VHS-18/19/20/22 held cleanly.
- Public-repo generalization honored; no private details leak.
- No contradicting prior wiki decision exists — this spec is the precedent.

## Summary
P0: 0 | P1: 1 | P2: 2 | P3: 1 | P4: 1

STATUS: RED P0=0 P1=1 P2=2 P3=1 P4=1
