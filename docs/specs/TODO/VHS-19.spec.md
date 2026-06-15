# VHS-19 — Cross-harness: fork CE converter & establish vigil converter baseline

**Spec for:** docs/specs/TODO/VHS-19.brief.md · **Plane:** VHS-19 (child of VHS-16; blocked-by VHS-17 — merged `39006cc`)
**Ships:** a new, owned fork repo — **`vigil-converter`** — of EveryInc/compound-engineering-plugin's converter *engine*, stripped of CE-specific content, retargeted to read the canonical `SKILL.md` tree, with a **two-path smoke test in CI** and a documented supply-chain + upstream-diff posture. **vigil-skills footprint: this spec record + one README pointer — no code, no `sync.py` change.**
**Status:** spec authoring (spec-cycle), round 2

> **Correction carried from round-1 review (load-bearing).** The brief, `docs/compound-engineering-evaluation.md`, and the v1 of this spec all named **"OpenClaw"** as an inherited CE smoke-test target. Verified against the upstream tree (`src/targets/` = `codex.ts, gemini.ts, kiro.ts, opencode.ts, pi.ts`): **OpenClaw is NOT a CE converter target.** "OpenClaw" is the fleet's *own* harness (served by the MCP server) — unrelated to what CE emits. The real adapter is **OpenCode** (`opencode.ts`). This spec uses **OpenCode** (Codex fallback) throughout; the brief's OpenClaw mentions were corrected in round 1, and its separate **"Claude Code passthrough"** framing — also a category error (Claude Code is the converter's *input*, not a `--to` target) — was corrected alongside (brief Scope #4 / Done-when #3); see D6 path (a). `docs/compound-engineering-evaluation.md` still carries the OpenClaw conflation (lines 22/107/133) and should be corrected when next touched — flagged at the drift-check.

## Goal

Stand up `vigil-converter`: our owned, security-vetted fork of CE's Bun/TypeScript converter, as the engine that emits per-harness skill packages from canonical `SKILL.md` sources. It reads the `SKILL.md` tree `sync.py` installs (portability-contract §1), carries **no CE residue** (CE-specific skills/agents/personas/marketplace/branding removed), and is proven live by a CI smoke test — over a **pinned sample skill set committed to the fork** — that (a) ingests a canonical `SKILL.md` and (b) converts it end-to-end to one real inherited target. This is the engine every per-harness adapter (VHS-20 Hermes first) will build on; it is **not** an adapter and **not** a parity test.

## Repo topology & where the work lands (read this first)

VHS-19's **deliverable lives in a separate repository**, not vigil-skills. The brief's toolchain fence is load-bearing — vigil-skills is "no dependencies beyond Python 3.8+ stdlib, no build step" (`AGENTS.md`); the converter is Bun/TypeScript. They cannot share a tree without breaking that contract.

- **The deliverable (`vigil-converter`)** — fork, strip, retarget, smoke test, supply-chain vetting, CI, cadence — all lands in the **new fork repo**.
- **vigil-skills (this repo)** gets only: (a) **this spec record**, and (b) **one discoverability pointer** in `README.md`'s "Cross-harness portability" section linking to `vigil-converter`. `sync.py`, `skills/`, `agents/`, `lint.py`, `tests/`, and the stdlib-only contract are untouched.
- **ship-spec applicability (D7):** `/ship-spec` cuts a worktree from *this* repo and PRs to *this* repo; it cannot fork/strip/CI an external repo. So ship-spec's automated path applies **only** to the README pointer; the fork work is executed **in `vigil-converter` directly**. `Test command: N/A` makes ship-spec skip its automated gate. The deliverable's real acceptance is the fork's CI smoke test, bound as a blocking precondition in D7.

**Prerequisite (round-1 correctness F-4):** `docs/compound-engineering-evaluation.md` and `docs/cross-harness-spike-synthesis.md` — cited by this spec and the brief — are currently **untracked**. They must be committed to vigil-skills before/with this spec's PR so the citations resolve in the repo. (They are the VHS-16 epic's design record; tracking them is overdue regardless.)

## Scope

**New repository — `vigil-converter` (the deliverable; outside vigil-skills)**
1. The fork of CE's converter engine + its target adapters, at a recorded upstream fork-point SHA, with an `upstream` remote.
2. The strip: CE-specific skills, agents, personas, marketplace metadata, and branding removed — as a **documented, reproducible diff** off the fork point.
3. Input retargeted to read the canonical `SKILL.md` tree (`~/.claude/skills/` at runtime; a **pinned committed sample** in CI) — this requires a scoped edit to the input parser (see Design "Retarget input"), not just a path constant.
4. A committed dependency lockfile + a `README.md` supply-chain section (audit results, pinned versions, the "never executes skill content" assertion + its scope boundary, fork point, strip-diff pointer, repo home, upstream cadence).
5. A CI workflow running the two-path smoke test over the pinned sample on every push/PR.

**In vigil-skills (this repo)**
- `README.md` — add a sentence to the existing "Cross-harness portability" **prose** section pointing to `vigil-converter`, matching the section's paragraph style (it is prose, not a bullet list — `README.md:45–49`). Idempotent: skip if the substring `vigil-converter` is already present. This is the spec's *only* tracked code/doc edit here.
- `docs/specs/TODO/VHS-19.spec.md` (+ `.reviews/`) — this record.

**Left alone (load-bearing)**
- `sync.py`, `skills/`, `agents/`, `lint.py`, `tests/` — no change. Carrying adapters or multi-harness output into vigil-skills is **VHS-22**, out of scope.
- The stdlib-only, no-build-step contract of vigil-skills.
- portability-contract §3–§5 — those target VHS-20/VHS-21. The converter reads only §1 (canonical source) and §2 (portable frontmatter subset).

## Decisions

### D1 — Fork-and-own via mirror-clone into a new repo with an `upstream` remote
We **own** the engine so Hermes — absent from CE's roster (codex/opencode/pi/gemini/kiro + the README's Cursor/Copilot/Factory-Droid/Qwen/Windsurf-deprecated, verified 2026-06-14) — can be added (VHS-20); a vendored dependency we cannot extend would never gain a Hermes adapter. MIT permits this (`docs/compound-engineering-evaluation.md:116`). **Mechanism:** clone upstream, record the fork-point SHA, push to a new repo **named `vigil-converter`** (name pinned here so the README pointer is final; **GitHub owner/org confirmed: `ziomancer` → `https://github.com/ziomancer/vigil-converter`, public, MIT, created empty**), and add an `upstream` remote → `EveryInc/compound-engineering-plugin`. Mirror-clone over a GitHub fork object: lets us rebrand/restructure freely, retains full history for cherry-picks, avoids fork-PR defaults pointing upstream. The GitHub-fork-object alternative is viable but rejected for rebrand friction; either way the cherry-pick surface is the recorded diff (D3), not the GitHub fork relationship.

### D2 — Security-first: the converter never executes skill content during conversion
Three hard requirements, all asserted in the fork README: (1) the inherited dependency tree is **audited** (`bun audit` / advisory scan of the lockfile), results + date recorded; (2) versions **pinned** via a committed lockfile (CI installs `--frozen-lockfile`); (3) **the conversion path never `eval`s, shell-interpolates, or spawns skill content.** Verification is a code inspection of the conversion path for execution sinks — **the Bun-aware sink set**: `Bun.spawn`, `` Bun.$ `` / `` $` `` (Bun shell), `execSync`, plus the Node set (`eval`, `new Function`, `child_process`, `exec`, `spawn`) — asserted in the README with the inspection as evidence. A reachable sink fed skill content is a **strip blocker**, not a v2 note. **Scope boundary (explicit non-claim):** a converter is a code-gen step; it legitimately *emits* artifacts the **target runtime** later executes (e.g. CE's OpenCode adapter writes a `converted-hooks.ts` containing hook command strings). "Never executes skill content" covers the **conversion process**, not the emitted package's later execution by its host. The README states this boundary so the assertion is honest.

### D3 — Keep a documented, reproducible diff against upstream
The strip and any local change are a reviewable delta from the recorded fork-point SHA — not an opaque rewrite — so CE engine fixes stay cherry-pickable. The fork README records the fork-point SHA; the strip lands as labeled commits or a `STRIP.md` (each removal + why); `upstream` remote + recorded baseline make `git log upstream/main --since=<fork-point>` the cherry-pick review surface. **The authoritative removal surface is the actual `ce-*`/persona/marketplace/branding content present at the recorded fork-point SHA** (enumerate by grepping the fork tree) — not a hard-coded name list; the reject-list names below are illustrative from the 2026-06-14 eval snapshot. **Update cadence** documented (proposed: review upstream `main` monthly; engine/security fixes cherry-picked through the recorded diff; security patches expedited).

### D4 — Canonical source stays `SKILL.md`; the converter preserves portable frontmatter on passthrough
The converter's input is the same `SKILL.md` tree `sync.py` installs, per portability-contract §1 — never a per-harness source fork. It reads §1/§2 (canonical source + portable frontmatter subset) and is **agnostic to §3 `requires:` *semantics*** (pre-flight enforcement is the adapter's concern, VHS-20). Crucially, "agnostic to §3" does **not** mean "drops the key": `requires` is a **§2-Portable** key (`portability-contract.md:35`), so the converter **preserves the `requires:` block verbatim** when emitting — it merely does not act on its semantics. (The converter inherits `js-yaml` for frontmatter; the canonical block — including `services: [issue-tracker?, shared-memory?]` and inline `#` comments — round-trips through `js-yaml` cleanly, so no special handling is needed; round-1 edge-cases F-7.)

### D5 — The fork lives outside vigil-skills (toolchain isolation)
vigil-skills stays stdlib-only and build-step-free (`AGENTS.md`). The Bun toolchain, lockfile, and CI are isolated to `vigil-converter`. Settling the repo home, CI, and upstream cadence is **in scope here**, not deferred. vigil-skills' only acknowledgment of the fork is the README pointer.

### D6 — The smoke test is an engine-liveness check over a pinned sample: ingest + one real target
The smoke test proves the *engine runs end-to-end after the strip* — it does **not** certify any target's output (that is VHS-21). **The binding bar (brief #4) is "at least one inherited target"**, not a specific one. Two paths, both over a **pinned sample `SKILL.md` set committed to the fork** (so CI is deterministic and independent of any installed `~/.claude/skills/`):
- **(a) Source ingestion / parse check** — the converter loads a canonical `SKILL.md` and parses its frontmatter + body per §1/§2 **without error** (this replaces the v1 "Claude Code passthrough," which was a category error: Claude Code is the converter *input*, not a `--to` target — round-1 correctness F-2 / edge F-1). Proves the retargeted input adapter reads our source.
- **(b) One real inherited target, end-to-end** — convert the sample to **OpenCode** (`opencode.ts`; the richest implemented adapter — emits `opencode.json` + `.opencode/{agents,commands,skills}/`, giving the most assertable non-empty output). The converter exits 0 and emits non-empty, structurally well-formed target output. **Codex** (`codex.ts`) is the documented fallback if OpenCode's adapter is the one entangled with stripped content. OpenCode is a spec-level selection refining the brief's open "e.g."; any verified `--to` target satisfies the bar.
"End-to-end" = consumes a real `SKILL.md`, emits the package without error, output is non-empty and well-formed. **Output correctness is explicitly out of scope** (v2 / VHS-21). **Empty-input contract:** if the pinned sample is somehow empty (zero `SKILL.md`), the smoke test **fails** (it asserts non-empty output) — define this so "non-empty" has a contract and the test can't vacuously pass.

### D7 — This spec is a design+plan record; ship-spec's footprint is the README pointer, and the fork's CI is a blocking acceptance gate
The vigil-skills spec→ship-spec→PR lifecycle applies only to the one README pointer; the fork's fork/strip/CI work is executed in `vigil-converter` directly. `Test command: N/A` so ship-spec skips its automated gate. **Cross-repo acceptance binding (round-1 edge F-5):** VHS-19 does **not** close on the strength of the README-pointer PR merging. A **captured fork-CI-green artifact** — a CI run URL, or a `smoke-output.txt` committed in `vigil-converter` — is a **blocking precondition** recorded against Test-plan item 3 before VHS-19's Plane state flips. The README pointer's URL is filled in once the repo exists, so the pointer is written/merged after the repo home is settled.

## Design

### Repo home & fork mechanics (D1/D3/D5)
1. Clone `EveryInc/compound-engineering-plugin`; capture `git rev-parse HEAD` as the **fork-point SHA**.
2. Create `vigil-converter` (GitHub owner maintainer-confirmed), push the clone, add `upstream` → EveryInc.
3. Record in the fork README: fork-point SHA, repo home, `upstream` remote, cadence (D3).

### The strip (D2/D3) — documented diff to the engine
- **Remove (authoritative surface = the fork-point tree, grepped):** CE-specific skills (`ce-*`), agents/personas (the eval doc's 2026-06-14 snapshot names Rails/DHH, Swift, etc. — illustrative), marketplace/plugin metadata, branding, and the Slack/Figma/Proof/imagegen/Xcode/demo-reel long tail (eval reject-list, `compound-engineering-evaluation.md:109`).
- **Keep:** the conversion engine and its target adapters (inherited targets stay as unvalidated engine-exercise surface, D6).
- **Reproducibility:** each removal is a labeled commit or `STRIP.md` row (what + why); the delta from fork-point is reviewable and CE engine fixes stay cherry-pickable.
- **No-CE-residue check (structural, not judgment-laden — round-1 conventions F-6):** acceptance is a **path-scoped** assertion — no `ce-*` directories under the skills/agents trees, and `compound-engineering`/CE-branding strings appear **only** in `README.md`/`STRIP.md` (the documented-diff surface) — not a human-judged "is this hit doc or live."

### Retarget input (D4) — a scoped edit to the input parser, **not** a config change
The upstream input contract is a **Claude plugin directory**, not a bare skills tree: `loadClaudePlugin` (`src/parsers/claude.ts`) requires a `.claude-plugin/plugin.json` manifest (**throws** when absent) and reads skills from `<root>/skills/`. Our canonical tree (`~/.claude/skills/`) has **no manifest** and **is itself the skills root** (not its parent). So retargeting requires a **scoped engine edit**: (1) make the manifest **optional** — synthesize a minimal default when absent; (2) treat the configured path as the **skills root** directly. This is **permitted input-adapter surgery** — explicitly distinct from the entanglement rule's "do not decouple CE skills / do not rewrite the converter," which is about *content* coupling. Resolve the path portably (no hardcoded home). This is the one genuinely non-trivial code change in the fork; scope it as such, not as a path constant.

### Smoke test — two paths over a pinned sample (D6)
A script runnable locally and in CI that, against a **sample `SKILL.md` set committed to the fork** (representative of the `~/.claude/skills/` layout, deterministic):
1. **(a) Ingest/parse** — converter loads the sample and parses frontmatter + body per §1/§2; asserts no error **and that ≥1 `SKILL.md` was parsed (parsed-skill count > 0)** — so an empty/missing sample fails this path closed, independently of path (b) (the manifest-optional retarget in D4 removes the upstream throw on empty input, so this non-vacuity assertion is what guards it).
2. **(b) Convert to OpenCode** (fallback Codex) — asserts exit 0 + non-empty, structurally well-formed target output.
Neither asserts output *correctness* — liveness only. The pinned sample (not the maintainer's installed skills) is the single source of truth for every CI-exercised gate; reading the real `~/.claude/skills/` is *runtime* behavior (D4), exercised locally, not the CI gate.

### Supply-chain vetting (D2)
- `bun audit` (or advisory scan) on the committed lockfile; record results + date in the README.
- Pin all versions; CI installs `--frozen-lockfile`.
- Inspect the conversion path for the **Bun-aware sink set** (D2); assert "never executes skill content during conversion" in the README with the inspection as evidence + the emitted-artifact non-claim boundary.

### CI + cadence (D3)
- GitHub Actions on `vigil-converter`: `bun install --frozen-lockfile` → run the two-path smoke test over the pinned sample → green required on push/PR. The green run is the captured acceptance artifact (D7).
- README documents the upstream-review cadence and cherry-pick-through-recorded-diff process.

### vigil-skills pointer
- Add one sentence to `README.md`'s "Cross-harness portability" prose (lines 45–49) pointing to `vigil-converter` — "the owned converter engine that emits per-harness packages from `SKILL.md` (VHS-19)" — matching the paragraph style. Idempotent on the substring `vigil-converter`. URL: `https://github.com/ziomancer/vigil-converter` (repo exists — created empty, public, MIT; D7).

## Decision triggers for narrowing scope (broadened — round-1 edge F-6)

The brief's loop-note forbids expanding this into adapter work (VHS-20). Three triggers, each: **narrow scope, file a note, do not build a new adapter or rewrite the converter** —
1. **Stripping a CE skill breaks conversion** (content entanglement) → file the entanglement; switch the smoke-test target.
2. **The chosen smoke-test target isn't an implemented upstream adapter** → switch to a real `--to` target (OpenCode/Codex/gemini/kiro/pi); do **not** author a new adapter (that's VHS-20).
3. **Input retarget needs more than the scoped parser edit** (D4) → the manifest-optional / skills-root edit is permitted; decoupling individual CE skills or writing a new target is **not**.

## Test plan

**No code ships in vigil-skills** beyond the one-line README pointer, so there is nothing for a vigil-skills test suite to exercise. The deliverable's verification is the **fork's CI smoke test**, captured here as the human **review checklist** (the quality gate per the spec-cycle ops/external-spec convention):

1. **No CE residue** (structural) — no `ce-*` directories under `vigil-converter`'s skills/agents trees; `compound-engineering`/CE-branding strings appear only in `README.md`/`STRIP.md`.
2. **Builds & converts a pinned sample** — `bun install --frozen-lockfile` succeeds; the converter builds and converts the **pinned sample `SKILL.md` set** without error. (Reading the live `~/.claude/skills/` is verified locally, not in CI.)
3. **Smoke test green in CI** — both paths (ingest, asserting ≥1 skill parsed, + OpenCode/Codex) run end-to-end, exit 0, emit non-empty output, CI job green. **The captured green run (URL or committed `smoke-output.txt`) is the blocking acceptance artifact for VHS-19 (D7).** The artifact must carry the **fork commit SHA** it was produced against, be **recorded in VHS-19's spec record / ship-spec PR description** before the Plane flip, and be the run against the **fork tip at flip time** (not an earlier green).
4. **Supply-chain note present** — fork README contains: dependency audit results + date; pinned-version/lockfile statement; the explicit "converter never executes skill content during conversion" assertion **with its emitted-artifact scope boundary** and the Bun-aware inspection evidence; fork-point SHA; strip-diff pointer; repo home; upstream cadence.
5. **Documented diff** — the strip is a reviewable delta from the recorded fork point (labeled commits or `STRIP.md`); `upstream` remote configured.
6. **vigil-skills pointer** — `README.md` "Cross-harness portability" section references `vigil-converter`; `git diff --stat` on the ship-spec run shows only `README.md`, the spec artifacts, and (unless already committed in a prior PR) the two prerequisite design docs `docs/compound-engineering-evaluation.md` + `docs/cross-harness-spike-synthesis.md` — no `sync.py`/`skills/`/`agents/` change, no `test-output.txt` since the gate is skipped.

## Test command

```
N/A
```

The deliverable is the external `vigil-converter` repo; nothing runnable ships in vigil-skills. ship-spec skips its automated test gate (`Test command: N/A`); the review checklist above is the quality gate. The substantive verification — the two-path smoke test — runs in `vigil-converter`'s CI; its captured green run is the blocking acceptance artifact (D7, Test-plan #3).

## Done when

1. `vigil-converter` builds and converts a **pinned sample `SKILL.md` set** (representative of `~/.claude/skills/`) with **no CE residue** (structural check, Test-plan #1); reading the live `~/.claude/skills/` works locally. — brief "Done when" #1
2. The **dependency audit and version pinning are recorded**, and a supply-chain note — including the "never executes skill content" assertion and its emitted-artifact scope boundary — lives in the fork's README. — brief #2
3. A **smoke-test conversion runs in CI** — source ingestion plus at least one inherited target (OpenCode, Codex fallback), end-to-end, green; the green run is captured as VHS-19's blocking acceptance artifact. — brief #3
4. The **fork point (upstream SHA), the strip diff, the repo home, and the upstream update cadence** are documented in the fork's README. — brief #4
5. *(vigil-skills side)* `README.md`'s "Cross-harness portability" section references `vigil-converter` (URL final, written after the repo exists); no other vigil-skills change. — Scope (this repo)

## Out of scope

- **The Hermes adapter itself** — VHS-20. This ticket stands up the engine and proves it runs; it does not build Hermes output, nor any *new* adapter (incl. an OpenClaw target — OpenClaw is not a CE target and adding one is VHS-20-class work).
- **Conformance / behavioral-parity testing** (portability-contract §5) — VHS-21. The smoke test is engine liveness, not parity.
- **Validating the inherited OpenCode/Codex targets** (v2) and adding Gemini/Cursor/Copilot/others.
- **Any `sync.py` or vigil-skills functional change** to carry adapters or multi-harness output — distribution is VHS-22; vigil-skills stays stdlib-only. (The lone exception is the one-line README pointer.)
- **Porting CE's skills, agents, or knowledge-capture mechanisms** (the `ce-compound` lifts) — tracked separately off `docs/compound-engineering-evaluation.md`.

## Out-of-scope note on the evaluation doc's Tier-3 "watch"

`docs/compound-engineering-evaluation.md` listed "the multi-harness converter CLI" as a Tier-3 *watch-don't-lift* item, gated on "revisit if cross-harness skill parity ever becomes a goal." VHS-16's Hermes-first epic **is** that revisit trigger — so forking now is the planned escalation of that watch-item, not a contradiction. Recorded so a reader cross-referencing the eval doc sees no conflict. (That doc also carries the OpenClaw/OpenCode conflation — correct it when next touched.)

## Post-green polish

Green at round 2 (all three lenses GREEN, P0=P1=0). Folded the round-2 `Pre-ship recommended` P2 clarifications (no behavior/scope/Decision changes):
- **correctness/F-1 (R2)** — brief still said "Claude Code passthrough" (Scope #4 / Done-when #3); corrected the brief to "source ingestion / parse check" and tightened the spec's correction note (top) to state it accurately.
- **edge-cases/F-1 (R2)** — smoke-test path (a) now asserts **≥1 `SKILL.md` parsed (count > 0)**, so an empty/missing sample fails closed independently of path (b) (the D4 manifest-optional retarget removed the upstream empty-input throw). Design "Smoke test" + Test-plan #3.
- **edge-cases/F-2 (R2)** — Test-plan #3 now requires the blocking acceptance artifact to carry the **fork commit SHA**, be **recorded in VHS-19's spec record / PR** before the Plane flip, and be the run against the **fork tip at flip time** (checklist-row tightening of D7's gate; D7's decision unchanged).
- **conventions/F-2 (R2, P3)** — Test-plan #6's clean-diff expectation now includes the two prerequisite design docs.

## Deferred (P2+)

- **conventions/F-4 (R2, P3)** — wiki onboarding of `vigil-converter` (a `projects/vigil-converter/` page + a fork-and-own `decisions/` entry, per the per-owned-repo convention) is **`/spec-close`'s job**, not this spec's; recorded so the eventual close pass handles it and the drift-check doesn't read its absence as drift.
- All round-1 P1s were addressed in the v2 design; round-1 P2/P3s were folded (OpenClaw→OpenCode; passthrough→ingest; retarget-as-scoped-surgery; Bun-aware sink set; pinned-sample CI SSOT; fork-point-SHA removal surface; blocking acceptance artifact; prose-style idempotent pointer; pinned repo name; `requires:` preservation; structural no-residue check). Nothing else outstanding.
