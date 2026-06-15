# Correctness Review — round 1

## Closure of round 0 findings
N/A — round 1.

## Findings

### F-1: Primary smoke-test target "OpenClaw" is not a target the inherited CE converter can emit
**Severity:** P1
**Where:** spec § Decisions D6; § Design "Smoke test — two paths"; § Test plan #3; § Done when #3
**Why wrong:** Upstream CE converter's actual `--to` roster is **codex, opencode, pi, gemini, kiro** (verified against github.com/EveryInc/compound-engineering-plugin, 2026-06-14, two fetches). **OpenClaw does not appear anywhere in the upstream converter.** The spec conflates "the fleet serves OpenClaw via the MCP server" (true) with "the CE converter can target OpenClaw" (false). Naming OpenClaw the primary smoke-test target points the implementer at a conversion the engine cannot produce; the Codex fallback is gated on the wrong condition ("entangled with stripped CE content"), never anticipating "OpenClaw isn't a target at all."
**Fix:** Make **OpenCode** or **Codex** (verified `--to` targets) the primary; drop OpenClaw; correct D6's rationale. Re-verify the chosen target name against the fork's actual CLI at implementation.

### F-2: "Claude Code passthrough" describes a converter mode that does not exist upstream
**Severity:** P1
**Where:** spec § D6; § Design smoke-test path 1; § Test plan #3; § Done when #3
**Why wrong:** There is no `--to claude-code` target and no passthrough/identity conversion. Claude Code is the *input/native format everything converts from* — never a converter *output* (upstream FAQ: Bun/converter only needed for converter-backed targets; Claude Code installs directly, no conversion). So "runs the Claude Code passthrough … emits non-empty target output" is not implementable as written.
**Fix:** Redefine path (a) as a **source-ingestion/parse check** ("loads a real SKILL.md and parses frontmatter+body per §1/§2 without error"), or drop it and make the two-path test two real targets. Update D6, Design, Test plan #3, Done-when #3 in lockstep.

### F-3: D6 says "OpenClaw the one target" while Design/entanglement treat Codex as a peer fallback — internal inconsistency
**Severity:** P2
**Where:** spec § D6 heading; § Design entanglement rule; § Test plan #3; § Done when #3
**Why wrong:** Spec is inconsistent about whether the smoke test requires a *specific* target or *any one* inherited target. Done-when ("at least one inherited target") is the correct looser bar; D6's "the one target" over-commits.
**Fix:** Reword D6 to "one inherited target (a real `--to` target) as the smoke-test exemplar"; keep Done-when's "at least one inherited target" as binding.

### F-4: Two load-bearing source docs are untracked in git
**Severity:** P2 · **Pre-ship recommended:** yes
**Where:** spec § D1, D3, strip reject-list, Out-of-scope note cite `docs/compound-engineering-evaluation.md`; brief cites it + `cross-harness-spike-synthesis.md`.
**Why wrong:** Both docs exist on disk but are **untracked** (`git status` → `??`). If VHS-19's PR lands before they're committed, every citation resolves to a non-repo file, weakening the audit trail. Content of citations is accurate (eval line 109 reject-list, line 116 MIT, line 107 Tier-3) — tracking-state gap, not factual.
**Fix:** Commit the two docs before/with this spec's PR, or have the spec note they're prerequisites to commit first.

### F-5: Strip reject-list cites version-dependent CE persona names unverified against the fork point
**Severity:** P2
**Where:** spec § Design "The strip" Remove list.
**Why wrong:** Names lifted from the eval doc, which itself flags counts as version-dependent. The strip is meant to be a reproducible diff off the recorded fork-point SHA, but the specific inventory at that SHA is unverified; relies on a 2026-06-14 snapshot.
**Fix:** Make the recorded fork-point SHA (grep the actual fork tree) the authoritative removal surface; mark the reject-list names illustrative.

### F-6: Done-when mapping to brief is faithful and complete (positive verification, no change)
**Severity:** P3
Spec Done-when #1–#4 map 1:1 to brief #1–#4; added #5 (README pointer) is justified. `Test command: N/A` + ship-spec-skip framing is internally coherent (ship-spec Phase 0 step 4.1 N/A exception at `skills/ship-spec/SKILL.md:20` skips the gate; Phase 2 still adds the bullet; Phase 4 commits). No change needed.

## Summary
P0: 0 | P1: 2 | P2: 3 | P3: 1 | P4: 0

STATUS: RED P0=0 P1=2 P2=3 P3=1 P4=0
