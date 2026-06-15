# VHS-17 — Cross-harness: portability contract & canonical skill format

**Status:** Backlog · **Priority:** High · **Assignee:** Unassigned
**Created:** 2026-06-14 · **Plane:** VHS-17 (child of VHS-16)
**Origin:** VHS-16 needs one contract that every downstream adapter (VHS-19/20), the conformance suite (VHS-21), the authoring lint (VHS-18), and the distribution change (VHS-22) can target. Without it, each of those items would invent its own notion of "portable," and they would drift. This is the foundational decision doc and it **blocks** the converter and adapter work.

> **Loop note.** This is the unblocker — `/ship-spec` it first. The deliverable is primarily a decision/spec document plus one worked annotation, so the "test gate" is lighter than a code change: validation is markdown/link integrity, the capability-declaration schema parsing cleanly, and the one annotated reference skill still installing via `sync.py` unchanged. Do not let the loop expand this into building the converter or a lint (those are VHS-19 and VHS-18).

## Goal

Define what makes a vigil skill portable, expressed as a contract document in `docs/`, so "just works across harnesses" becomes a checkable specification rather than a vibe.

## Scope

The contract must specify all five of the following:

1. **Canonical source = Claude Code `SKILL.md`.** State plainly that the source of truth is the `SKILL.md` already installed to `~/.claude/skills/` via `sync.py`; adapters for other harnesses are *generated*, never hand-maintained, and never edited downstream.
2. **The portable subset of frontmatter + body conventions.** Enumerate which `SKILL.md` frontmatter keys are portable (e.g. `name`, `description`, `user_invocable` — the keys the repo's skills already use, per `CLAUDE.md` "Conventions") versus Claude-Code-only, and which body conventions survive conversion.
3. **A capability / tool-requirement declaration.** A machine-readable block by which a skill states what it needs — tools, filesystem access, network, MCP servers — so a harness can check availability *before* running and fail clearly if a requirement is unmet. This is the "clarity of intent" principle made machine-checkable.
4. **The intent-over-implementation rule.** Skill bodies carry *intent* ("search the issue tracker for the ticket"), never harness-specific tool names or call syntax ("call `mcp__plane__retrieve_work_item`"). VHS-18 turns this rule into an automated lint; VHS-17 only has to define it precisely enough to be enforceable.
5. **The definition of behavioral parity** used to judge "just works" — the same definition VHS-21's conformance suite will operationalize. Parity is behavioral, not string-identical output.

## Decisions carried forward

- **Source of truth = `SKILL.md`; adapters are generated.** No per-harness source forks.
- **Parity is behavioral, not string-identical.** Two harnesses pass if they achieve the skill's stated intent, even if their tool calls and phrasing differ.
- **Capability requirements are declared, not inferred.** A skill must say what it needs; a harness must not have to guess. The declaration is the contract's load-bearing new artifact.
- **The capability schema must round-trip through `sync.py` untouched.** `sync.py` mirrors `skills/` verbatim (`SUBTREES`, `sync.py:30`); whatever the declaration looks like, it lives inside the skill directory and must not require changes to the sync mechanism to be carried (sync changes are VHS-22).
- **Reuse existing frontmatter; don't invent a parallel manifest** where a frontmatter key already does the job — the conventions reviewer will flag gratuitous new structure.

## Done when

- The contract doc is merged in `docs/` (suggested `docs/portability-contract.md`) and **referenced from `CLAUDE.md`** (alongside the existing `docs/customizing.md` and `docs/spec-workflow-reference.md` pointers).
- The portable frontmatter subset **and** the capability-declaration schema are specified with concrete examples (a worked declaration block, not just prose).
- **One existing vigil skill is annotated against the contract as a worked reference** — pick one of the four shipped skills (`spec-cycle` / `ship-spec` / `spec-close` / `review-pr`), add its capability declaration, and confirm it still installs cleanly via `sync.py install` (or `--dry-run`) with no change to `sync.py`.
- The behavioral-parity definition is stated explicitly and is specific enough that VHS-21 can build assertions from it without reinterpretation.

## Out of scope

- Building the converter or any per-harness adapter (VHS-19 / VHS-20).
- Writing the authoring lint (VHS-18) — VHS-17 defines the rules; VHS-18 enforces them.
- Annotating more than the one reference skill, or otherwise modifying the skills' behavior.
- Any `sync.py` change to carry adapters or multi-harness output (VHS-22).
- Changing the Plane/wiki evidence-triple model or the spec-lifecycle skills' behavior.

## References

- Plane: VHS-17 (child of VHS-16, priority High, created 2026-06-14).
- `docs/compound-engineering-evaluation.md` (merged 2026-06-14) — origin of the parity goal; "just works" / behavioral-parity framing.
- `sync.py:30` — `SUBTREES = ("skills", "agents")`; the declaration must ship inside the skill dir and round-trip unchanged.
- `CLAUDE.md` "Conventions" — current frontmatter keys (`name`, `description`, `user_invocable`); existing `docs/` pointers to extend.
- Shipped skills available as the reference-annotation candidate: `skills/{spec-cycle,ship-spec,spec-close,review-pr}/SKILL.md` (read 2026-06-14).
- Wiki: `tools/hermes-agent/architecture.md` — Hermes "Skill loader: discovery and progressive disclosure," informing which body conventions must survive conversion.
