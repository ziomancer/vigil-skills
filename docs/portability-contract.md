# Skill Portability Contract

> **Status:** v1 · **Ticket:** VHS-17 (child of the VHS-16 cross-harness epic)
> **Audience:** authors of vigil skills, and the downstream cross-harness items (converter VHS-19, Hermes adapter VHS-20, conformance suite VHS-21, authoring lint VHS-18, distribution VHS-22).

This document defines what makes a vigil skill **portable across agent harnesses** — so "it just works on Claude Code and Hermes" becomes a checkable specification rather than a vibe. Every downstream cross-harness item targets *this* contract instead of inventing its own notion of "portable."

Model-capability parity arrived in 2026; the remaining problem is **clarity of intent** and harness-neutral packaging — not lowest-common-denominator dumbing-down. Portability here means: a skill authored once carries enough declared intent and capability information that any conforming harness can run it to the same observable outcome.

The contract is five normative sections. Each is written to be cited verbatim by a downstream item.

---

## §1 Canonical source format

The source of truth for every vigil skill is the **Claude Code `SKILL.md`** under `skills/<name>/SKILL.md`, installed to `~/.claude/skills/` by `sync.py`.

- **Adapters are generated, never hand-maintained.** Per-harness output (Hermes today; OpenClaw / Codex later) is *generated* from the canonical `SKILL.md`. The source is never forked per harness, and generated adapters are never hand-edited downstream.
- **Claude Code is the native baseline** and needs no conversion.
- **Hermes is the v1 generated target.** Hermes skills live under the per-profile Hermes home (`~/.hermes/skills/` by default, resolved via `HERMES_HOME` — never hardcode the path). Every installed Hermes skill automatically becomes a slash command, and the Hermes loader performs "discovery and progressive disclosure." (Refs: wiki `tools/hermes-agent/skills-system.md`, `tools/hermes-agent/architecture.md`.)

A skill is portable when its canonical `SKILL.md` conforms to §2–§4; whether two harnesses *agree* on its behavior is judged by §5.

---

## §2 Portable frontmatter + body subset

### Frontmatter

| Key | Class | Note / Hermes mapping |
|-----|-------|------|
| `name` | **Portable** | Required everywhere; the skill's stable identifier (Hermes: `name`). |
| `description` | **Portable** | Required everywhere; drives progressive disclosure on both Claude Code and Hermes (Hermes Level-0 `skills_list`). Must be self-contained and intent-rich. |
| `user_invocable` | **Portable (mapped)** | The intent "a user can invoke this directly" is portable. Claude Code → slash command; Hermes → every skill is already a slash command, so the flag is informational there. |
| `requires` | **Portable (new — defined in §3)** | The capability declaration. The Hermes adapter maps it per §3's mapping table. |
| `allowed-tools`, `argument-hint`, `disable-model-invocation`, `model` | **Claude-Code-only** | Not guaranteed elsewhere; none are used by the shipped vigil skills today. Adapters may drop or translate them. |
| `version`, `platforms` | **Harness-extension (Hermes)** | Not part of the canonical source; an adapter may add them (e.g. Hermes `version`, `platforms`). Not required by this contract. |

### Body conventions

**Survive conversion:** Markdown structure (headers, lists, fenced code), phase/step numbering, intent-phrased imperatives, and the allowed tool-name constructs of §4.

**Do not survive — avoid them:** literal tool-call syntax used as the *operative* imperative (§4 case 1), and assumptions about a specific harness's filesystem layout or affordances beyond what `requires` declares.

---

## §3 Capability / tool-requirement declaration

A skill must **declare** what it needs; a harness must not have to infer it by reading the body. The declaration is a single `requires:` key in the `SKILL.md` frontmatter — **not** a sibling manifest file.

### Schema (flat, by design)

```yaml
requires:
  shell: true                       # executes terminal/shell commands
  filesystem: [read, write]         # access modes needed; omit or [] if none
  network: true                     # makes outbound network requests of its own
  subagents: true                   # dispatches concurrent sub-agents / parallel tasks
  services: [issue-tracker?, shared-memory?]   # external capability providers, by ROLE
```

**Field semantics**
- `shell`, `network`, `subagents` — booleans. Absent = `false`.
- `filesystem` — a flow sequence drawn from `{read, write}`. Absent or `[]` = no filesystem access.
- `services` — a flow sequence of **role** tokens from a controlled vocabulary (`issue-tracker`, `shared-memory`, `code-review-bot`, `vcs-host`; extensible by a future revision of this contract). Roles are harness-neutral: a harness maps `issue-tracker` → Plane (or its own), `shared-memory` → the shared-memory/MCP service, etc. A trailing `?` marks the service **optional** — the skill degrades gracefully (warn-and-proceed) when it is absent. No `?` = **required**.

**Why flat.** The repo is "no dependencies beyond Python 3.8+ stdlib," and stdlib has no YAML parser. The `requires:` block is restricted to scalars and single-line flow sequences (**no nested mappings**) so the authoring lint (VHS-18) can validate it with a small line-oriented stdlib reader, while it remains valid YAML that Claude Code's own parser accepts. Flatness is a property of the **canonical source** block only — generated adapters may emit whatever shape their target requires (the Hermes adapter nests under `metadata.hermes`).

**Relationship to existing prose convention (VHS-7).** These role tokens are the *structured form* of the host-agnostic capability prose already used in skill bodies since VHS-7 — `issue-tracker` ≙ the "the Plane MCP server's project-list capability … or the equivalent in your host" construction. The vocabulary is not a new taxonomy; it is the machine-readable encoding of one that already ships.

### Availability (so "fail clearly" is decidable)

A capability is **available** when:
- boolean (`shell` / `network` / `subagents`) — the harness exposes that affordance;
- `filesystem` — the declared modes are permitted in the run sandbox;
- `services` — a provider is bound to the role **and** a cheap liveness probe succeeds (transport reachability alone is *not* sufficient — an ACL-denied or misconfigured provider counts as unavailable).

A harness MUST verify each **required** capability (no `?`) before any mutation and fail clearly, naming the unmet capability. Optional services (`?`) need not be probed at pre-flight; a harness MAY probe them early for an advisory warning, but their absence never blocks. Pre-flight is a fail-fast gate, not a guarantee: a capability that passes pre-flight may still fail at point of use, at which point the same rules apply (required → fail; optional → warn-and-proceed). Parity (§5) is judged on point-of-use behavior, not on whether an early advisory was emitted.

### Lexical / tokenization rules (for a stdlib-only validator)

A validator parses the block by: locate the `requires:` line in the frontmatter; collect the contiguous more-indented lines; for each line —
1. strip a trailing comment — a `#` *preceded by whitespace* begins a comment; strip from there to end-of-line (controlled-vocabulary values never contain `#`);
2. split on the first `:` into key/value (the first-`:` split applies **once per line**; a `:` inside a flow-sequence element is not a separator and, being outside the controlled vocabulary, makes that element a violation);
3. for flow-sequence values, strip the surrounding `[` `]`, split on `,`, and trim each element; discard empty elements (so `[ ]` ≡ `[]` ≡ an absent key, all meaning "none");
4. for a `services` element, strip one optional trailing `?` and record it as the optional flag;
5. the remaining token must match the controlled vocabulary **exactly** (lowercase, unquoted).

Quoted scalars, trailing empty elements (`[read, write,]`), nested mappings, and unknown keys under `requires` are **violations**.

### Uniqueness / position

Exactly one `requires:` key per skill, placed after the existing scalar frontmatter keys and before the closing `---`. Re-application replaces it in place rather than appending a second block.

### Hermes mapping (for the VHS-20 adapter)

| Canonical `requires` | Hermes target | Note |
|----------------------|---------------|------|
| `services` | `metadata.hermes.requires_toolsets` / `requires_tools` (+ `required_environment_variables` for credentialed services) | role → toolset/tool |
| `shell` | a `terminal`-toolset requirement | |
| `network`, `subagents`, `filesystem` | (no direct Hermes frontmatter equivalent) | adapter's own pre-flight enforces |

The mapping is **lossy in kind**: Hermes's `requires_*` keys *gate visibility* (they hide/show the skill), whereas this contract's `requires` is a *hard pre-flight contract* (it must cause a clear failure when a required capability is unmet). The adapter must therefore add a hard pre-flight even where it also emits the Hermes gating keys.

---

## §4 Intent-over-implementation rule

*Operative* skill-body instructions carry **intent**, never a harness-specific tool name or call syntax as the operative instruction. The distinguishing axis is **operativeness** — whether the text is an instruction the agent executes to achieve the skill's intent, or non-operative documentation/example.

Three body constructs, classified for the lint (VHS-18):

1. **Prohibited** — an operative instruction whose imperative *is* a harness tool call, with no harness-neutral capability stated (e.g. a step that says "call `mcp__plane__retrieve_work_item`").

2. **Allowed** — a tagged illustrative example inside operative prose: it states the harness-neutral capability and offers an example tagged with "or the equivalent in your host." The canonical shipped example is in `spec-cycle`'s preflight: *"call the plane-proxy's project-list capability (e.g., `mcp__plane__list_projects` in Claude Code, or the equivalent in your host's Plane integration)"*.

3. **Allowed** — a **non-operative** meta/reference section (e.g. a "Tool-use notes" / "Tool-use rules" section, or a fenced reference block) that documents the skill's *own* tool surface. Bare harness tool names are permitted here when they appear as *declarative documentation* (an inventory or reference list). **The exemption covers non-operative content only:** an *operative imperative* — a step the agent executes to achieve the skill's intent — remains case 1 regardless of the heading it sits under. A notes/reference heading raises a *presumption* of non-operativeness; it does not override an operative imperative placed there.

**The discriminator for a lint is operativeness, not whether a neutral role is named:** a bare tool name in an executed step is case 1 (prohibited) unless wrapped as a case-2 tagged example; a bare tool name in a documentation/notes section is case 3 (allowed). The shipped vigil skills satisfy this today — every `mcp__*` mention is a case-2 tagged example, and the bare-tool-name bullets (`Read`, `Edit`, `Write`, `Bash`, `Agent`, `Grep`, `gh …`) live under "Tool-use notes" headings (case 3). Only an operative bare tool call would violate, and none exists.

---

## §5 Behavioral-parity definition

Parity is **behavioral, not string-identical**. Two harnesses pass on a skill when each achieves the skill's stated intent and reaches the same observable end-state, even if their tool calls and phrasing differ. Operationalized as four checkable dimensions (the conformance suite, VHS-21, builds assertions directly from these):

1. **Output artifacts** — the artifacts the skill's body names as deliverables exist at their stated paths with equivalent structure/content. Where a skill names no output artifacts (pure side-effect skills), this dimension passes vacuously. *(v1 reads declared outputs from the body prose. A machine-readable `produces:` path declaration is **out of scope for v1** — a candidate future key — so VHS-21 does not expect one.)*
2. **Honored gates** — declared control-flow gates fire identically (e.g. a HARD STOP halts; a missing *optional* service warns-and-proceeds; a missing *required* capability fails before mutation).
3. **Side-effect scope** — no mutations outside the skill's declared scope (`requires.filesystem`, named services).
4. **Intent achieved** — the skill's own "done" condition is met.

Parity is judged on these outcomes plus honored control-flow — **not** on string-identical transcripts or identical tool-call sequences.

---

## Worked reference

`skills/spec-cycle/SKILL.md` carries the first capability declaration as a worked reference. It exercises every field of the schema: `git fetch` (`shell`, `network`), reading briefs and writing spec/review files (`filesystem: [read, write]`), dispatching reviewer subagents in parallel (`subagents`), and calling Plane + the shared-memory service, both warn-and-proceed (`services: [issue-tracker?, shared-memory?]`):

```yaml
requires:
  shell: true
  filesystem: [read, write]
  network: true
  subagents: true
  services: [issue-tracker?, shared-memory?]
```

The block is frontmatter-only; it round-trips through `sync.py` untouched (sync mirrors each file byte-for-byte and only walks the `skills/`/`agents/` subtrees), so carrying it requires no change to `sync.py`.
