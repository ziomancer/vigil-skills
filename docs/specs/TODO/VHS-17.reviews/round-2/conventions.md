# Conventions Review — round 2

## Closure of round 1 findings
All 17 prior findings across three lenses verified CLOSED against current spec text and the wiki. No REOPENED or PARTIAL items. Hermes mapping (D4/§2/§3) confirmed accurate against `tools/hermes-agent/skills-system.md` (`requires_toolsets`:58, `requires_tools`:60, `required_environment_variables`:131-140, `version`/`platforms`:53-54, gating semantic :120-123, HERMES_HOME :10/:453).

## Findings

No findings.

The round-2 additions hold against every convention re-checked:
- Hermes mapping accuracy — all cited wiki fields real; gating-vs-pre-flight distinction verbatim-supported (skills-system.md:120-123).
- stdlib-only — flat schema + line-oriented tokenization, no new dependency.
- Public-repo generalization — `services` vocabulary harness-neutral; Plane/MCP kept as examples (VHS-7 reconciliation), no internal leak.
- Reuse-don't-re-mint — `requires.services` is the structured form of VHS-7 prose; one frontmatter key, not a parallel manifest.
- Out-of-scope fences — no lint code, no adapter code, no sync.py change; Hermes mapping framed as a spec VHS-20 consumes, not shipped code.
- No VHS-20 scope creep from round-2 additions.
- No contradicting prior wiki decision; this spec is the precedent.
- Annotation genuinely additive (spec-cycle frontmatter holds only name/description/user_invocable today).

## Summary
P0: 0 | P1: 0 | P2: 0 | P3: 0 | P4: 0

STATUS: GREEN
