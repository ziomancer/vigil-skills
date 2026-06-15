# Conventions Review — round 1

## Findings

### F-1: D5 / Done-when #1 rest on a README section that doesn't exist; VHS-17 spec text put pointers in CLAUDE.md
**Severity:** P1
Current README has no "Cross-harness portability" section (grep: no matches). VHS-17.spec.md says "two CLAUDE.md pointers" in CLAUDE.md's File-layout section; VHS-17's spec text never touches README. So VHS-18's premise ("VHS-17's contract pointer landed in README under a Cross-harness portability section") is not reflected in the VHS-17 *spec*. (Note: VHS-17's *shipped PR* did add the README section, deviating from its own spec text per the gitignored-CLAUDE.md finding — but that's on the unmerged branch.)
**Fix:** Rewrite D5 to state the actual history: VHS-17's PR (not its spec text) added the README section because CLAUDE.md is gitignored; VHS-18 stacks on that branch so the section is present, and adds the guidelines pointer there (creating both pointers if needed).

### F-2: "VHS-17 is green and shipped (PR #17)" — PR #17 is OPEN, not merged; no live requires: block
**Severity:** P1
`gh pr view 17` → OPEN. `grep -rn "requires:" skills/` → no matches. Spec relies on spec-cycle's requires: block (D4, Design, Test 2) which isn't in the tree on main. Soften "shipped" → "green (PR #17 open)"; make Test 2 robust to merge order (dedicated fixture); state the stacking prerequisite.

### F-3 (positive): D1 hook-point choice consistent with "sync.py mirrors only"
No action. D1 correctly rejects a sync.py subcommand and keeps lint.py a sibling top-level stdlib script; names + justifies the hook point per the brief's mandate; defers CI to the promotion path.

### F-4 (positive): install-hooks precedent treated as shape-only, not toolchain
No action. Correctly borrows the installable-pre-commit shape while keeping stdlib Python, not the wiki's Node wiki-lint.mjs toolchain.

### F-5 (positive): "complement CodeRabbit" holds; stdlib-only honored
No action. `.coderabbit.yaml` has skills/** qualitative path_instructions + sync.py "no pip dependencies"; the mcp__/requires: deterministic lint complements it. lint.py + unittest are stdlib; no yaml/pytest.

### F-6 (positive): public-repo generalization respected
No action. R2 steers authors to harness-neutral "(e.g. … or the equivalent in your host)"; no internal paths/specifics leak.

### F-7 (positive): scope fences vs VHS-17/19/20/21 clean
No action.

### F-8: Silent addition — ERROR/WARN taxonomy + --strict exit semantics are spec-authored (with rationale)
**Severity:** P3
The two-tier model and --strict-gates-on-ERROR-only are spec-level additions (brief only says "advisory-then-blocking"). Legitimate, idiomatic (mirrors P0/P1-vs-P2 discipline); flagged for the drift-check only. No change required.

## Summary
P0: 0 | P1: 2 | P2: 0 | P3: 5 | P4: 0

STATUS: RED P0=0 P1=2 P2=0 P3=5 P4=0
