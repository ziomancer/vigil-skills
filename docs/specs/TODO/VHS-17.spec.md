# VHS-17 — Cross-harness: portability contract & canonical skill format

**Spec for:** docs/specs/TODO/VHS-17.brief.md · **Plane:** VHS-17 (child of VHS-16)
**Ships:** one contract document, one worked skill annotation, two CLAUDE.md pointers.
**Status:** spec authoring (spec-cycle), round 2

## Goal

Ship `docs/portability-contract.md`: the single decision document that defines what makes a vigil skill *portable across agent harnesses*, so "just works on Claude Code and Hermes" becomes a checkable specification rather than a vibe. Every downstream item in the VHS-16 epic — the converter (VHS-19), the Hermes adapter (VHS-20), the conformance suite (VHS-21), the authoring lint (VHS-18), and the distribution change (VHS-22) — targets this one contract instead of inventing its own notion of "portable." The contract is paired with one worked annotation (a real shipped skill given its capability declaration) so the schema is proven against live code, not just prose.

## Scope

**New file**
- `docs/portability-contract.md` — the contract. Five normative sections (canonical source, portable frontmatter + body subset, capability declaration, intent-over-implementation rule, behavioral-parity definition), each written to be cited verbatim by a downstream item.

**Edited files**
- `skills/spec-cycle/SKILL.md` — add a `requires:` capability-declaration block to the YAML frontmatter (the worked reference annotation). Frontmatter only; the skill body and behavior are untouched.
- `CLAUDE.md` — add a pointer to `docs/portability-contract.md` in the "File layout" section adjacent to the existing `docs/customizing.md` pointer; also add a pointer to `docs/spec-workflow-reference.md` (see Design "The CLAUDE.md pointers" for why this second pointer is part of this spec).

**Left alone (load-bearing)**
- `sync.py` — must not change. The capability schema living inside the skill file and round-tripping untouched through `sync.py` is the proof obligation, not a thing to be enabled by a sync edit (sync edits are VHS-22).
- The other three skills (`ship-spec`, `spec-close`, `review-pr`) and all `agents/*.md` — exactly one reference annotation ships here (brief out-of-scope fence).
- The Plane/wiki evidence-triple model and all spec-lifecycle skill behavior.

## Decisions

### D1 — Canonical source = Claude Code `SKILL.md`; adapters are generated, never hand-maintained
The contract states plainly that the source of truth is the `SKILL.md` already installed to `~/.claude/skills/` via `sync.py`. Per-harness adapters (Hermes, later OpenClaw/Codex) are *generated* from the source and never edited downstream; there is no per-harness source fork. Honored by §1 of the contract.

### D2 — Parity is behavioral, not string-identical
Two harnesses pass on a skill when each achieves the skill's stated intent and reaches the same observable end-state, even if their tool calls and phrasing differ. Honored by §5, written as enumerable assertions so VHS-21 can operationalize it without reinterpretation.

### D3 — Capability requirements are declared, not inferred
A skill must *say* what it needs (shell, filesystem, network, sub-agents, external services); a harness must not have to guess by reading the body. The declaration is the contract's load-bearing new artifact (§3). A harness can then pre-flight: verify each required capability before running and fail clearly, naming the missing capability, if one is absent. "Available" is defined per capability class in §3 so "fail clearly" is decidable.

### D4 — The capability declaration is a single `requires:` frontmatter key (not a sibling manifest), and round-trips through `sync.py` untouched
The declaration lives in the `SKILL.md` frontmatter as one `requires:` key. Rationale: (a) the brief says reuse existing frontmatter, don't invent a parallel manifest; (b) `sync.py` mirrors each file byte-for-byte (`shutil.copy2`, `sync.py:96`) and only walks the `skills/`/`agents/` subtrees (`SUBTREES`, `sync.py:30`) — a frontmatter key is inside the file, inside the subtree, so it round-trips with zero sync changes by construction; (c) Claude Code ignores unknown frontmatter keys (verified by the post-install load-check in the Test plan), so adding `requires:` does not change how Claude Code loads the skill.

**Reconciliation with Hermes's existing frontmatter (the "don't re-mint" pressure).** Hermes — the v1 target (§1) — already ships capability-style frontmatter: `metadata.hermes.requires_toolsets` / `requires_tools` (and `fallback_for_*`, `required_environment_variables`) per wiki `tools/hermes-agent/skills-system.md:55-61,114-142`. We deliberately do **not** adopt those as the canonical form, for one substantive semantic reason: Hermes's `requires_*` are **visibility-gating hints** ("Skill hidden when listed toolsets unavailable; shown when present" — skills-system.md:120-123), i.e. they decide whether the skill *appears*. Our `requires:` is a **hard pre-flight contract** — it must cause a clear *failure* (not a silent hide) when a required capability is unmet, which is what a portability/conformance contract needs. The two are not interchangeable. The contract therefore defines the canonical `requires:` block AND, in §3, gives the Hermes adapter (VHS-20) an explicit mapping so it is not handed an unscoped translation problem.

### D5 — The canonical `requires:` block is a FLAT, stdlib-parseable schema; generated adapters may emit any shape
`requires:` contains only scalar values and single-line YAML flow sequences — **no nested mappings**. Rationale: the repo is "no dependencies beyond Python 3.8+ stdlib" (`CLAUDE.md`), and stdlib has **no YAML parser**. VHS-18's lint must validate this block with stdlib only; a flat shape is parseable by a small line-oriented stdlib reader (lexical rules pinned in §3) while remaining valid YAML that Claude Code's own parser accepts. **Scope of the flatness rule:** it is a property of the *canonical source* block so VHS-18 can lint it — it is **not** a claim that every harness's format is flat. Generated adapters emit whatever their target requires; e.g. the Hermes adapter (VHS-20) nests under `metadata.hermes`. This decision is made *here* so VHS-18 is not handed a schema it cannot parse within the repo's constraints.

### D6 — The intent rule binds *operative* instructions; bare-imperative tool calls are prohibited, but tool names survive in tagged examples and non-operative tool-notes sections
This is the precise, enforceable form of the intent-over-implementation rule (§4), and it is load-bearing for VHS-18. The distinguishing axis is **operativeness** — whether the text is an instruction the agent executes to achieve the skill's intent, or non-operative documentation/example. The four shipped skills name harness tools in two *non-prohibited* ways, both of which a naive "never mention a tool name" lint would wrongly flag — making it fire on all four skills and contradict VHS-18's acceptance criterion that it runs clean against them:
- **tagged illustrative examples inside operative prose** — e.g. `skills/spec-cycle/SKILL.md:228` names `mcp__plane__list_projects` inside an "(e.g., … or the equivalent in your host's Plane integration)" clause; and
- **non-operative "Tool-use notes" sections** that document the skill's *own* tool surface with bare harness tool names — e.g. `skills/spec-cycle/SKILL.md:467,469` ("Read, Edit, Write …"; "Agent calls (parallel) …"), `skills/ship-spec/SKILL.md:263,264`, `skills/spec-close/SKILL.md:377,381`.

The contract therefore classifies **three** body constructs (§4): (1) a bare harness tool call as the *operative instruction* → **prohibited**; (2) a tagged illustrative example within operative prose → **allowed**; (3) a non-operative meta/reference section (e.g. "Tool-use notes") documenting the skill's own tool surface → **allowed** (bare tool names fine there — it is documentation, not portable behavior). Tool names thus legitimately survive in cases 2 and 3; only case 1 is prohibited. VHS-18 must recognize all three.

## Design

### The contract document — `docs/portability-contract.md`

A normative spec doc with a short preamble (what portability means and why: model-capability parity arrived in 2026; the remaining problem is clarity of intent and harness-neutral packaging — sourced from the brief and `docs/compound-engineering-evaluation.md`) followed by five numbered sections.

**§1 Canonical source format.** The source of truth is Claude Code `SKILL.md` under `skills/<name>/SKILL.md`, installed to `~/.claude/skills/` by `sync.py`. Adapters for other harnesses are generated artifacts; the source is never forked per harness and adapters are never hand-edited (D1). States that Hermes is the v1 generated target: Hermes skills live under the per-profile Hermes home (`~/.hermes/skills/` by default, resolved via `HERMES_HOME` — never hardcode the path; wiki `tools/hermes-agent/skills-system.md:10,453`), every installed skill auto-becomes a slash command (skills-system.md:14), and the loader does "discovery and progressive disclosure" (wiki `tools/hermes-agent/architecture.md:138`). Claude Code is the native baseline needing no conversion. Cites `tools/hermes-agent/skills-system.md` as the canonical Hermes-format reference.

**§2 Portable frontmatter + body subset.** A table classifying each frontmatter key, with the Hermes mapping noted so VHS-20 inherits it:

| Key | Class | Note / Hermes mapping |
|-----|-------|------|
| `name` | Portable | Required everywhere; the skill's stable identifier (Hermes: `name`). |
| `description` | Portable | Required everywhere; drives progressive disclosure on both Claude Code and Hermes (Hermes Level-0 `skills_list`, skills-system.md:37) — must be self-contained and intent-rich. |
| `user_invocable` | Portable (mapped) | The intent "a user can invoke this directly" is portable; Claude Code → slash command; Hermes → every skill is already a slash command (skills-system.md:14), so the flag is informational there. |
| `requires` | Portable (new, defined by §3) | The capability declaration. Hermes adapter maps it per §3's mapping table (→ `metadata.hermes.requires_toolsets`/`requires_tools` + `required_environment_variables`, with the gating-vs-pre-flight caveat of D4). |
| `allowed-tools`, `argument-hint`, `disable-model-invocation`, `model` | Claude-Code-only | Not guaranteed elsewhere; none used by the four shipped skills today. Adapters may drop or translate them. |
| `version`, `platforms` | Harness-extension (Hermes) | Not in the canonical source today; an adapter may add them (e.g. Hermes `version`, `platforms`). Not required by the contract. |

Body conventions that **survive** conversion: Markdown structure (headers, lists, fenced code), phase/step numbering, intent-phrased imperatives, and the allowed tool-name constructs of §4. Body conventions that **do not** survive and must be avoided: literal tool-call syntax used as the operative imperative (§4 case 1), and assumptions about a specific harness's filesystem layout or affordances beyond what `requires` declares.

**§3 Capability / tool-requirement declaration.** Defines the `requires:` frontmatter block — the contract's load-bearing new artifact (D3, D4, D5). Closed, flat schema:

```yaml
requires:
  shell: true                       # executes terminal/shell commands
  filesystem: [read, write]         # access modes needed; omit or [] if none
  network: true                     # makes outbound network requests of its own
  subagents: true                   # dispatches concurrent sub-agents / parallel tasks
  services: [issue-tracker?, shared-memory?]   # external capability providers, by ROLE
```

*Field semantics*
- `shell`, `network`, `subagents` — booleans. Absent = `false`.
- `filesystem` — a flow sequence drawn from `{read, write}`. Absent or `[]` = no filesystem access.
- `services` — a flow sequence of **role** tokens from a controlled vocabulary (`issue-tracker`, `shared-memory`, `code-review-bot`, `vcs-host`; extensible by future contract revision). Roles are harness-neutral: a harness maps `issue-tracker` → Plane (or its own), `shared-memory` → the MCP memory server, etc. A trailing `?` marks the service **optional** — the skill degrades gracefully (warn-and-proceed) when it is absent. No `?` = **required**.

*Relationship to existing prose convention (VHS-7).* These role tokens are the structured form of the host-agnostic capability prose already used in skill bodies since VHS-7 — `issue-tracker` ≙ the "the Plane MCP server's project-list capability … or the equivalent in your host" construction. The vocabulary is not a new taxonomy; it is the machine-readable encoding of one that already ships.

*Availability (so D3's "fail clearly" is decidable).* A capability is "available" when:
- boolean (`shell`/`network`/`subagents`) — the harness exposes that affordance;
- `filesystem` — the declared modes are permitted in the run sandbox;
- `services` — a provider is bound to the role **and** a cheap liveness probe succeeds (transport reachability alone is *not* sufficient — an ACL-denied or misconfigured provider counts as unavailable).
A harness MUST verify each **required** capability (no `?`) before any mutation and fail clearly, naming the unmet capability. Optional services (`?`) need not be probed at pre-flight; a harness MAY probe them early for an advisory warning, but their absence never blocks. Pre-flight is a fail-fast gate, not a guarantee: a capability that passes pre-flight may still fail at point of use, at which point the same rules apply (required → fail; optional → warn-and-proceed). Parity (§5 / VHS-21) is judged on point-of-use behavior, not on whether an early advisory was emitted.

*Lexical / tokenization rules (so VHS-18 parses with stdlib only).* The block is parsed by: locate the `requires:` line in the frontmatter; collect the contiguous more-indented lines; for each, strip a trailing comment (a `#` preceded by whitespace begins a comment — strip from there to end-of-line; values in the controlled vocabulary never contain `#`); split on the first `:` into key/value; for flow-sequence values, strip the surrounding `[` `]`, split on `,`, and trim each element; strip one optional trailing `?` from a service element and record it as the optional flag; the remaining token must match the controlled vocabulary **exactly** (lowercase, unquoted). The first-`:` split separates key from value once per line; a `:` *inside* a flow-sequence element is not a separator and (being outside the controlled vocabulary) makes that element a violation. After bracket-strip and per-element trim, empty elements are discarded; a sequence that reduces to zero elements means "none," so `[ ]` ≡ `[]` ≡ an absent key. Quoted scalars, trailing empty elements (`[read, write,]`), nested mappings, and unknown keys under `requires` are violations (flagged by VHS-18, not here).

*Uniqueness / position.* Exactly one `requires:` key per skill, placed after the existing scalar frontmatter keys and before the closing `---`. Re-application replaces it in place rather than appending a second block.

*Hermes mapping (for VHS-20).* `requires.services` → `metadata.hermes.requires_toolsets` / `requires_tools` (and `required_environment_variables` for credentialed services); `requires.shell` → a `terminal`-toolset requirement; `requires.network`/`subagents`/`filesystem` have no direct Hermes frontmatter equivalent and are enforced by the adapter's own pre-flight. The mapping is lossy in *kind* (Hermes gates visibility; our contract gates execution — D4), so the adapter must add a hard pre-flight even where it also emits the Hermes gating keys.

**§4 Intent-over-implementation rule.** *Operative* skill-body instructions carry *intent*, never a harness-specific tool name or call syntax as the operative instruction (D6). The lint boundary classifies three constructs by operativeness:
1. **Prohibited** — an operative instruction whose imperative *is* a harness tool call, with no harness-neutral capability stated (e.g. a step that says "call `mcp__plane__retrieve_work_item`").
2. **Allowed** — a tagged illustrative example inside operative prose: states the harness-neutral capability and offers an example tagged with "or the equivalent in your host." The canonical shipped example is `skills/spec-cycle/SKILL.md:228`, whose exact text is: "call the plane-proxy's project-list capability (e.g., `mcp__plane__list_projects` in Claude Code, or the equivalent in your host's Plane integration)".
3. **Allowed** — a **non-operative** meta/reference section (e.g. a "Tool-use notes" / "Tool-use rules" section, or a fenced reference block) that documents the skill's *own* tool surface. Bare harness tool names are permitted here when they appear as *declarative documentation* (an inventory or reference list), because that documents implementation rather than driving portable behavior. **The exemption covers non-operative content only:** an *operative imperative* — a step the agent executes to achieve the skill's intent — remains case 1 regardless of the heading it sits under. A notes/reference heading raises a *presumption* of non-operativeness; it does not override an operative imperative placed there (so VHS-18 should treat a bare tool name under an allowlisted heading as case 3 unless the line is in imperative-instruction form, which is case 1). Worked proof in the shipped skills: `skills/spec-cycle/SKILL.md:467,469`, `skills/ship-spec/SKILL.md:263,264`, `skills/spec-close/SKILL.md:377,381` — all *declarative* bare-tool-name bullets under a "Tool-use notes" heading, all classified **allowed** by this case.

The distinguishing test for VHS-18 is therefore *operativeness*, not whether a neutral role is named: a tool name in an executed step is case 1 (prohibited) unless wrapped as a case-2 tagged example; a tool name in a documentation/notes section is case 3 (allowed). §4 reproduces the line-228 string exactly (rather than citing a step number, which spec-cycle renumbers) so the load-bearing example does not go stale. VHS-18 enforces exactly this three-way boundary.

**§5 Behavioral-parity definition.** States parity as four checkable dimensions (so VHS-21 builds assertions directly):
1. **Output artifacts** — the artifacts the skill's body names as deliverables exist at their stated paths with equivalent structure/content. Where a skill names no output artifacts (pure side-effect skills), this dimension passes vacuously. (v1 reads declared outputs from the body prose; a machine-readable `produces:` path declaration is explicitly **out of scope for v1** and noted as a candidate future key, so VHS-21 does not expect one.)
2. **Honored gates** — declared control-flow gates fire identically (e.g. a HARD STOP halts; a missing *optional* service warns-and-proceeds; a missing *required* capability fails before mutation).
3. **Side-effect scope** — no mutations outside the skill's declared scope (`requires.filesystem`, named services).
4. **Intent achieved** — the skill's own "done" condition is met.
Parity is judged on these outcomes plus honored control-flow, **not** on string-identical transcripts or identical tool-call sequences (D2).

### The worked annotation — `skills/spec-cycle/SKILL.md`

`spec-cycle` is chosen as the reference because it exercises **every** field of the schema, making it the strongest proof the schema is sufficient: it runs `git fetch` (`shell`, `network`), reads briefs and writes spec/review files (`filesystem: [read, write]`), dispatches three reviewers in parallel (`subagents`), and calls Plane + the MCP memory server, both warn-and-proceed (`services: [issue-tracker?, shared-memory?]`). The exact block added to its frontmatter (one block, after the existing scalar keys, before the closing `---`):

```yaml
requires:
  shell: true
  filesystem: [read, write]
  network: true
  subagents: true
  services: [issue-tracker?, shared-memory?]
```

This is a frontmatter-only addition; no step, phrasing, or gate in the body changes.

### The CLAUDE.md pointers

The brief asks for the contract to be referenced "alongside the existing `docs/customizing.md` and `docs/spec-workflow-reference.md` pointers." Verified against the current file: CLAUDE.md's "File layout" section points to `docs/customizing.md` only — there is **no** `docs/spec-workflow-reference.md` pointer yet (the file exists on disk but is untracked/unreferenced). To make the brief's intended "alongside" grouping real, this spec adds **two** pointers in the File-layout section: one to `docs/portability-contract.md` (e.g. *"what makes a skill portable across harnesses (VHS-17); the contract every cross-harness item targets"*) and one to `docs/spec-workflow-reference.md`. Both edits are confined to the File-layout pointer list; no other CLAUDE.md content changes.

## Test plan

No code ships beyond a frontmatter key and doc edits; the repo has no test suite (`CLAUDE.md`). The gate is a mechanical smoke check plus a review checklist plus one manual load-check.

**Mechanical (runnable):**
- `python sync.py install --dry-run --verbose` exits 0 and reports `skills/spec-cycle/SKILL.md` as either a `[WRITE/dry]` action (state `differ` or `src-only`, depending on whether the skill is already installed locally) or as in-sync (`same`, skipped) — and **no** action targets `sync.py`. The load-bearing assertion is "no `sync.py` change required," which holds in all three states; the exact state tag is incidental.

**Load-check with a recordable artifact (covers the D4(c) risk):**
- After `python sync.py install`, (a) grep the installed `~/.claude/skills/spec-cycle/SKILL.md` for the `requires:` block — the captured match line is the recordable pass artifact for the PR audit trail; and (b) confirm a fresh `/spec-cycle` invocation in a new session reaches Phase 0 without a frontmatter parse error. The dry-run only proves the file copies; (b) is the only check that proves the unknown-key tolerance the annotation relies on.

**Review checklist (human gate, the substantive one):**
- The `requires:` block in §3 **and** the one added to `spec-cycle` are valid YAML *and* conform to D5 (scalars + single-line flow sequences, no nested maps) *and* parse correctly under §3's stated lexical/tokenization rules (including the comment-strip rule).
- All five contract sections are present and concrete enough to be cited verbatim downstream (§3 has a worked block + availability + tokenization rules + Hermes mapping; §4 classifies three constructs; §5 enumerates four dimensions).
- §4's three-way boundary is consistent with the four shipped skills *as they exist today* — no shipped skill is retroactively in violation: tagged `mcp__*` examples are case 2, and the bare-tool-name "Tool-use notes" bullets (spec-cycle:467/469, ship-spec:263/264, spec-close:377/381) are case 3 (non-operative). Only an operative bare tool call (case 1) would violate, and none exists.
- Internal links and the two new CLAUDE.md pointers resolve to real paths (`docs/portability-contract.md`, `docs/spec-workflow-reference.md`, `skills/spec-cycle/SKILL.md`).
- The Hermes mapping (§3) and citations (`skills-system.md`, `architecture.md:138`) match the wiki.

## Test command

```bash
python sync.py install --dry-run --verbose
```

(Smoke check only — confirms the annotated skill round-trips through sync with no `sync.py` change, in any of the differ/src-only/same states. The substantive gate is the review checklist + manual load-check above. ship-spec runs this command for its Phase 3 gate; a clean exit with no `sync.py` action is the pass condition.)

## Done when

1. `docs/portability-contract.md` is merged and referenced from `CLAUDE.md` alongside the `docs/customizing.md` and `docs/spec-workflow-reference.md` pointers (this spec adds both the contract pointer and the spec-workflow-reference pointer, since the latter did not yet exist — see Design). — brief "Done when" #1
2. The portable frontmatter subset (§2 table, with Hermes mappings) **and** the capability-declaration schema (§3, with a worked block, availability rules, and tokenization rules) are both specified with concrete examples, not just prose. — brief #2
3. `skills/spec-cycle/SKILL.md` is annotated with its `requires` block; `python sync.py install --dry-run` shows it round-tripping with no `sync.py` change; and the manual load-check confirms it still loads in Claude Code. — brief #3
4. The behavioral-parity definition (§5) is stated as four explicit dimensions, specific enough for VHS-21 to build assertions without reinterpretation (including the vacuous-pass and out-of-scope-`produces:` notes). — brief #4

## Out of scope

- Building the converter or any per-harness adapter (VHS-19 / VHS-20). The Hermes mapping in §3 is a *specification* for VHS-20 to consume, not adapter code shipped here.
- Writing the authoring lint (VHS-18) — VHS-17 defines the rules (D5/D6, §3 tokenization, §4 three-way boundary); VHS-18 enforces them. No lint code ships here.
- Annotating more than the one reference skill, or otherwise changing any skill's behavior.
- Any `sync.py` change to carry adapters or multi-harness output (VHS-22).
- A machine-readable output/`produces:` declaration (noted as a future candidate in §5; not specified here).
- Changing the Plane/wiki evidence-triple model or the spec-lifecycle skills' behavior.

## Deferred (P2+)

- (round 1, edge-cases F-7 / correctness F-2) The exact `sync.py` dry-run state tag is environment-dependent — resolved by softening the Test-plan assertion to "no `sync.py` action, any of differ/src-only/same."
- A machine-readable `produces:` output-path declaration (round 1, edge-cases F-3) — deferred to a future contract revision; §5 dimension 1 reads output paths from body prose for v1.

## Post-green polish

- (round 3, edge-cases F-1, Pre-ship recommended) §4 case 3 — scoped the notes-section exemption to *declarative* (non-operative) content; an operative imperative under a notes heading is still case 1. Closes the by-heading false-negative hole and resolves the case-3-vs-closing-paragraph tension, keeping VHS-18's case-1 prohibition sound.
