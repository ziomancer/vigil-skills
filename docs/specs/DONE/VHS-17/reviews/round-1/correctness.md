# Correctness Review — round 1

## Findings

### F-1: Spec "Done when" #1 drops `spec-workflow-reference.md` from the pointer set the brief requires
**Severity:** P1
**Where:** spec § Done when (vs. brief § Done when line 33)
The brief requires the contract be referenced "alongside the existing `docs/customizing.md` AND `docs/spec-workflow-reference.md` pointers." Both files exist on disk. The spec narrows to one anchor and makes co-location with spec-workflow-reference optional. NOTE: the actual CLAUDE.md File-layout section currently has only a `docs/customizing.md` pointer — neither spec-workflow-reference.md nor compound-engineering-evaluation.md is pointed to there. So the brief's premise is itself slightly inaccurate, but the binding obligation is the brief's "Done when"; reconcile explicitly rather than silently narrow.
**Fix:** Make Done-when #1 match the brief; add the contract pointer next to customizing.md and (since it exists) a spec-workflow-reference pointer too, or state the reconciliation explicitly.

### F-2: Test-plan "(differ)" assertion is environment-dependent (may read "(src-only)" or "same")
**Severity:** P2
`file_state()` returns `differ` only when both src+dst exist and differ; `src-only` on a fresh machine; `same` (skipped) when already in sync. The exact-string `(differ)` expectation is brittle.
**Fix:** Soften to "lists the skill as a `[WRITE/dry]` action (differ or src-only) with no sync.py change," or "exits 0 and reports no sync.py change."

### F-3: §1's flat `~/.hermes/skills/` omits the wiki's multi-profile caveat
**Severity:** P3
Wiki contributing.md warns never to hardcode `~/.hermes` — use `get_hermes_home()`/`HERMES_HOME`. A contract VHS-20 cites verbatim risks propagating a hardcoded path.
**Fix:** Phrase as "per-profile Hermes home (`~/.hermes/skills/` by default; resolved via `HERMES_HOME`)."

### F-4: Plane cache lists 3 Done-when; brief has 4 — informational only
**Severity:** P3
Cached chunk is an abridged mirror; brief carries all four. No conflict. No change.

## Grounding ledger (verified)
- sync.py byte-for-byte: `shutil.copy2` at sync.py:96, `filecmp.cmp(shallow=False)` at sync.py:59. D4 anchors accurate.
- `SUBTREES = ("skills","agents")` at sync.py:30: confirmed.
- Frontmatter keys exactly name/description/user_invocable for all four skills: confirmed.
- spec-cycle Phase 0 names `mcp__plane__list_projects` inside "e.g. … or the equivalent": confirmed at SKILL.md:228.
- Worked-annotation justifications confirmed (git fetch 75/144; 3 reviewers 262/264; Plane 228 + memory fallback 470). No pre-existing `requires:` key.
- Wiki architecture.md:138 "discovery and progressive disclosure": confirmed verbatim.
- All five contract sections present; all four Done-when mapped (subject to F-1).

## Summary
P0: 0 | P1: 1 | P2: 1 | P3: 2 | P4: 0

STATUS: RED P0=0 P1=1 P2=1 P3=2 P4=0
