# Conventions Review — round 2

## Closure of round 1 findings
- conventions F-1 (P1) — CLOSED. D5 rewritten (spec:17,55-56): VHS-17 spec-text named CLAUDE.md but shipped PR added README "Cross-harness portability" section (CLAUDE.md gitignored). Verified vs branch README + VHS-17.brief.md:33.
- conventions F-2 (P1) — CLOSED. Precondition reframes "green (PR #17 open)"; good-skill fixture decouples tests from merge order.
- Positives F-3..F-7 HOLD (D1 hook point, install-hooks shape-only, complement-CodeRabbit, public-repo, scope fences). F-8 (taxonomy) unchanged.

## Findings

### F-1: Precondition prescribes a ship-spec base-branch override that ship-spec does not support
**Severity:** P1
spec line 15 says "VHS-18 ship-spec must base its worktree on `feat/vhs-17-portability-contract`, not main." But `skills/ship-spec/SKILL.md` Phase 1 hardcodes `git worktree add -b <branch> <path> origin/<default-branch>` (lines 31-37, 76) with no base override, flag, or stacked-PR option. The only ship-spec-executable path is the OR-branch ("merge #17 first"). As written, an implementer expects `/ship-spec` to stack and it silently cuts from main, where no anchors exist → run fails at the README edit / contract reference.
**Fix:** Reflect ship-spec's real capability: state VHS-17 (#17) must merge to main before VHS-18 ship-spec runs (the only automated path); demote stacking to a manual out-of-band alternative ("a maintainer can manually cut a worktree from the VHS-17 branch; `/ship-spec` always bases on the default branch"). Optionally file a follow-up to teach ship-spec a base-branch override.

### F-2: D5 "create the section if absent" can double-add the README section
**Severity:** P2 — **Pre-ship recommended: yes**
The fallback is conditioned on the section being "somehow absent" with no deterministic check. Under a mis-based worktree (F-1) or a timing race, the fallback fires and adds a second `## Cross-harness portability` heading + duplicate contract pointer.
**Fix:** Pin to a deterministic check: grep README for an existing `## Cross-harness portability` heading; if present, append the guidelines bullet inside it; only if grep finds none, create the section with both pointers.

### F-3: Silent scope addition — `tab-indented child → ERROR` is not in contract §3
**Severity:** P3
The lint rejects tab indentation (spec:76); contract §3's lexical rules don't mention it. Legitimate determinism hardening (originated as edge-cases F-6), but the lint is slightly stricter than §3's letter. Note it as a documented v1 lint determinism choice in D6/guidelines.

## Summary
P0: 0 | P1: 1 | P2: 1 | P3: 1 | P4: 0

STATUS: RED P0=0 P1=1 P2=1 P3=1 P4=0
