# Conventions Review — round 2

## Closure of round 1 findings
All round-1 findings across the three lenses CLOSED (verified against disk). conventions/F-1 (item 13 roster lists) CLOSED — README.md:11-12, README.md:23-27, package.json:4 anchors confirmed. conventions/F-10 (env-var nesting) CLOSED — provisional in D9 + table + template. conventions/F-6 (dump import site) CLOSED.

## Findings

### F-1 (P4, verification): Malformed-YAML handling consistent with the engine's js-yaml parser
Confirmed empirically: js-yaml `load` parses `[issue-tracker?, shared-memory?]` and `[issue-tracker ?]` fine, throws only on bare `[?]`. So the live `spec-cycle` block (which the VHS-17 decision flags as non-strict-YAML for PyYAML) is well-formed under js-yaml — the engine does not choke; Done-when 1 is achievable with no engine fix. Spec's malformed-YAML framing accurate; honors VHS-17's "adapter must transform the block" via D7 dump. No drift.

### F-2 (P2, Pre-ship recommended: yes): Clean-replace mechanic diverges from inherited manifest-gated cleanup without naming the divergence
spec.md:178. The four inherited skill writers (opencode/codex/pi/gemini) avoid orphans via manifest-gated per-skill replacement (`managed-artifacts.ts:183-191`: `if (!manifest?.groups[group]?.includes(entryName)) return` before `rm`), only deleting dirs their own prior install created. The spec's unconditional `rm` is justified only against `copySkillDir`'s additive-merge, not against the manifest pattern its siblings use. Kiro (manifest-free, additive) is the closest structural sibling. Fix (spec-text only): add a sentence stating the Hermes writer deliberately omits the manifest machinery (tree is wholly generated, not merged with user content; Kiro is the sibling), scope clean-replace to the per-skill `<name>/` dir (never the `skills/` parent), and note a manifest is a deferred enhancement if multi-plugin installs land (VHS-22 territory). Pairs with edge-cases round-2 F-1.

### F-3 (P4, drift-check): Round-1 additions stay within the brief's fences — no scope creep, no premature abstraction
D1 ship-mechanics/partial-close (authorized by Done-when 2 + VHS-19 pattern); service-token normalization (restates the VHS-18 validator slice, routes out-of-vocab to a gap — not a new lint); writer mechanics (direct opencode mirrors, no new abstraction; clean-replace divergence = F-2); assertions 5-8 (coverage for required behavior). No silent additions. Honors VHS-19 no-rewrite, stdlib/Bun split, "adapters generated".

### F-4 (P4): README `--to` anchor (spec:37) — README.md:23-27 is a multi-line example block; add a `hermes` sibling line rather than editing line 27 (gemini) in place. Intent unambiguous; flagged for the implementer's eye.

## Summary
P0: 0 | P1: 0 | P2: 1 | P3: 0 | P4: 3

STATUS: GREEN
