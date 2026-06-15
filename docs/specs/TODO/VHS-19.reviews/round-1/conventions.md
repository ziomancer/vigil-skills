# Conventions Review — round 1

## Closure of round 0 findings
N/A — round 1.

## Findings

### F-1: README "Cross-harness portability" section is prose paragraphs, not a bullet list — "append one bullet" mismatches its shape
**Severity:** P2
**Where:** spec § Design "vigil-skills pointer"; § Scope "In vigil-skills"
**Evidence:** `README.md:45–49` is two prose paragraphs (portability-contract pointer; authoring-lint/lint.py pointer), not a list. Spec says "Append **one bullet** … if the bullet exists, leave it" — assumes a list structure that isn't there. This is the spec's only tracked edit here, so exact shape matters for a clean ship-spec diff.
**Fix:** Reword to "add a sentence (or short bullet) to the existing 'Cross-harness portability' prose pointing to `vigil-converter`, matching the section's paragraph style; do not restructure into a list." Phrase idempotency against substring presence of `vigil-converter`.

### F-2: Spec commits smoke-test target to OpenClaw with Codex fallback; brief leaves it open — flag as spec-level (c) addition
**Severity:** P3
**Where:** spec § D6, § Design "Smoke test"
**Evidence:** Brief #4 (line 26): "at least one inherited CE target (e.g. OpenClaw or Codex)" — illustrative. Spec elevates to a committed primary + fallback. Model-(c) addition (spec-level, with rationale); recorded so the drift-check sees it. (Note: superseded by edge/correctness F-1 — OpenClaw isn't a real target.)
**Fix:** None required; optionally state "OpenClaw-primary is a spec-level selection refining the brief's open e.g." (now: OpenCode-primary).

### F-3: D6's rationale "the fleet already serves OpenClaw via the MCP server" is stale — OpenClaw was parked for Hermes/Petasos
**Severity:** P2
**Where:** spec § D6
**Evidence:** `decisions/2026-06-12-openclaw-fork-update-archive-and-reset.md` — the `ziomancer/openclaw` fork was archived+reset, parked "as part of shutting OpenClaw down for Hermes/Petasos development." So "the fleet already serves OpenClaw" is partially stale; the choice's *justification* leans on relevance the shutdown undercuts.
**Fix:** Re-ground the target-selection rationale on the durable fact (the target is in CE's inherited roster → exercises the engine with zero new adapter work), not "the fleet serves OpenClaw." (Compounds with F-1: OpenCode replaces OpenClaw entirely.)

### F-4: D4 "agnostic to §3 requires:" could read as "may drop the requires: key" — clarify it's preserved on passthrough
**Severity:** P3
**Where:** spec § D4, § Design "Retarget input"
**Evidence:** `requires` is a **Portable** key in §2's table (`portability-contract.md:35`). "Agnostic to §3" (correct division of labor — §3 enforcement is VHS-20) could be misread as license to drop the key on passthrough, silently stripping a §2-portable key.
**Fix:** Add a clause: "the converter **preserves** the `requires:` block verbatim on passthrough (§2-portable); it merely does not *act on* §3 semantics."

### F-5: Repo name "to be confirmed" but the README pointer (the one tracked edit) hard-links `vigil-converter`
**Severity:** P2 · **Pre-ship recommended:** yes
**Where:** spec § D1, § Design "Repo home", § Design "vigil-skills pointer", Done-when #5
**Evidence:** D1 says name is maintainer-confirmed at implementation; yet the pointer + Done-when #5 commit README to link "`vigil-converter`" — the only thing ship-spec merges. If the name changes, the merged pointer is wrong with no sequenced follow-up.
**Fix:** Either pin the name `vigil-converter` in this spec, or sequence the pointer write/merge **after** the repo name is settled so the link target is final.

### F-6: "No CE residue" grep allowlist ("documented-diff/cadence references") is judgment-laden — tighten to a structural assertion
**Severity:** P3
**Where:** spec § Test plan item 1, Done-when #1
**Evidence:** "grep … returns only the documented-diff/cadence references, not live engine content" requires a human to judge which hits are doc vs live — same failure mode as VHS-18's heading-allowlist. For an external repo with no automated gate in this lifecycle, a fuzzy allowlist is the weakest link.
**Fix:** Tighten to a path-scoped structural check: "no `ce-*` dirs under skills/agents trees; `compound-engineering` appears only in `README.md`/`STRIP.md`."

## Summary
P0: 0 | P1: 0 | P2: 3 | P3: 3 | P4: 0

What the spec gets right (for the drift-check to weigh): stdlib-only / no-build-step contract honored (Bun isolated to the external repo; sync.py/skills/agents/lint.py/tests untouched); CLAUDE.md-is-gitignored convention followed (pointer → tracked README, not CLAUDE.md — the trap that bit VHS-17/18); Tier-3 watch-item escalation flagged with a faithful reading of eval doc line 107; cross-repo ship-spec handling consistent with VHS-7's N/A escape hatch; all load-bearing anchors verified (VHS-17 39006cc, VHS-18 7ec40ca, README section).

STATUS: RED P0=0 P1=0 P2=3 P3=3 P4=0
