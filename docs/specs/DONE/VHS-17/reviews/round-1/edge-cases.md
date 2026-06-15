# Edge-Cases Review — round 1

## Findings

### F-1: D5's stdlib parse recipe cannot handle the inline comments in its own §3 worked example
**Severity:** P1
The §3 example block uses trailing `#` comments on every line. D5's three-step recipe (find `requires:`, collect indented `key: value`, split flow sequences on commas) has no comment-stripping step — applied literally it captures comment text as values (and the comment commas as extra tokens). The applied annotation on spec-cycle has no comments, so the normative example and applied example disagree on whether comments are allowed.
**Fix:** Add a lexical rule: "a `#` preceded by whitespace begins a comment; strip to EOL before tokenizing; values must not contain a literal `#` (controlled vocabulary guarantees this)." Then keep comments in the §3 example (proving handled) or drop them to match the applied block — pick one.

### F-2: §3 does not define "available" for the required-capability pre-flight, making "fail clearly" undecidable
**Severity:** P1
"available" is undefined per role. A service can be transport-reachable but ACL-denied (the MCP server is ACL-gated and returns "Error:" in a 200), or plane-proxy reachable but project unmapped. No statement on check-then-use race. A harness will implement "available" = "reachable" and proceed into a service that errors mid-run, defeating the pre-flight.
**Fix:** Define availability per class (booleans = affordance exposed; filesystem = modes permitted in sandbox; services = provider bound to role AND cheap liveness probe succeeds). Add: "Pre-flight is fail-fast, not a guarantee; required/optional rules also apply at point of use."

### F-3: §5 dimension 1 references "declared outputs at declared paths" — a declaration the contract never defines
**Severity:** P1
The `requires` schema has no output/path field; outputs live only as prose in the body. §5 dim 1 tells VHS-21 to assert against a declaration that doesn't exist, forcing it to parse the body (the anti-pattern D3 forbids). Empty case (skill with no outputs) is unaddressed.
**Fix:** Narrow dim 1 to "outputs the skill's body names as deliverables exist with equivalent structure; vacuous pass where none are named" and state output-path declaration is out of scope for v1 (deferred to a future `produces:` key).

### F-4: Intent-over-implementation rule has no case for tool names in capability-inventory / fenced reference blocks
**Severity:** P2 — **Pre-ship recommended: yes**
D6 defines only two states (tagged example allowed / bare imperative prohibited). Shipped skills have a third: "Tools available" inventory bullets naming a Claude tool without the full "e.g./or-the-equivalent" envelope (spec-cycle:470, spec-close:378). A literal lint fires on these (contradicting "runs clean against shipped skills"); a relaxed lint creates a hole.
**Fix:** Classify THREE cases: (1) operative imperative naming a tool, no neutral capability → prohibited; (2) tagged illustrative example → allowed; (3) capability/tooling inventory or fenced reference naming the harness-neutral role → allowed. VHS-18 must recognize all three.

### F-5: `services`/`?` tokenization undefined for degenerate flow-sequence cases
**Severity:** P2 — **Pre-ship recommended: yes**
Unpinned: `[]` vs absent vs `[ ]`; space before `?`; quoted scalars (valid YAML, breaks naive reader); trailing comma. Each is a divergence point between Claude Code's YAML parser and VHS-18's stdlib reader.
**Fix:** Add tokenization spec: "split on `,`, trim each element; strip one optional trailing `?` as the optional flag; remaining token must match the controlled vocabulary exactly (lowercase, unquoted). Empty/`[]`/`[ ]`/absent all mean none; quoted scalars and trailing empty elements are violations."

### F-6: "Claude Code ignores unknown frontmatter keys" asserted without evidence — load-bearing for editing the orchestrator skill
**Severity:** P2 — **Pre-ship recommended: yes**
The whole safety argument for adding `requires:` to the live spec-cycle skill rests on this. The test gate (`sync.py --dry-run`) proves the file copies, not that Claude Code still loads it.
**Fix:** Add a manual verification step ("after install, confirm spec-cycle still loads / is invocable") and/or cite Claude Code docs for unknown-key tolerance.

### F-7: `sync.py install --dry-run` gate is a no-op when ~/.claude has no prior copy (or is already in sync)
**Severity:** P3
Same root as correctness F-2. `same` state → skipped (skill not listed); `src-only` on fresh machine. Pass condition keyed on `(differ)` can spuriously fail.
**Fix:** "exits 0; lists skill (differ/src-only) or reports in sync; no action targets sync.py."

### F-8: No idempotency/uniqueness invariant for the `requires:` block
**Severity:** P3
No stated guarantee of exactly one `requires:` key in a fixed position; re-runs could append a second.
**Fix:** "Exactly one `requires:` key, after existing scalar keys and before closing `---`; re-application replaces in place."

## Summary
P0: 0 | P1: 3 | P2: 3 | P3: 2 | P4: 0

STATUS: RED P0=0 P1=3 P2=3 P3=2 P4=0
