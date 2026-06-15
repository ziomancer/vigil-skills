# Edge-Cases Review — round 2

## Closure of round 1 findings
All round-1 P0/P1 CLOSED (verified against current spec):
- edge/F-1 (OpenClaw fictional, P0) — CLOSED: OpenCode/Codex; brief corrected.
- edge/F-2 (retarget = surgery, P1) — CLOSED: Design "Retarget input" scopes manifest-optional + skills-root as permitted input-adapter surgery; scope-narrow trigger 3.
- edge/F-3 (Bun sinks, P1) — CLOSED: D2 Bun-aware sink set + emitted-artifact non-claim.
- edge/F-4 (CI no ~/.claude/skills/, P1) — CLOSED: pinned committed sample is CI SSOT; live tree is runtime/local; empty-input contract in D6.
- edge/F-5 (cross-repo binding, P2) — CLOSED: D7 blocking artifact precondition.
- edge/F-6 (scope-creep, P2) — CLOSED: Decision-triggers section (3 triggers).
- edge/F-7 (js-yaml, P3) — CLOSED.
- correctness/F-4 (docs untracked) — PARTIAL: spec bound it as a prerequisite (all a spec can do); still `??` on disk.

## Findings

### F-1: Smoke-test path (a) asserts "no error" only — no non-empty backstop; manifest-optional retarget lets a zero-skill sample pass (a) vacuously
**Severity:** P2 · **Pre-ship recommended:** yes
**Where:** spec Design "Smoke test" path (a); D6 empty-input contract; Design "Retarget input"
**Edge case:** The F-2 fix (manifest-optional) removes the upstream throw, so an empty skills root parses to an empty-but-valid plugin instead of erroring. Path (a) asserts only "no error" → passes vacuously on zero skills. The empty-input contract holds at the *suite* level via path (b)'s non-empty assertion, but path (a) — meant to prove "the retargeted input adapter reads our source" — green-lights reading nothing. A future change running (a) alone, or with a different fixture, loses the guard.
**Fix:** Add to path (a) a non-vacuity assertion: "no error AND ≥1 SKILL.md parsed (count > 0)." [Addressed in 2g.]

### F-2: D7's blocking artifact specified as "URL or smoke-output.txt" with no location/SHA/freshness binding — weakly enforceable
**Severity:** P2 · **Pre-ship recommended:** yes
**Where:** spec D7, Test-plan #3, Done-when #3
**Edge case:** Three failure modes — (1) a fresh-repo Actions URL can 404/point at a force-pushed commit, nothing pins which SHA was green; (2) a committed smoke-output.txt can be stale (committed once, engine changes, CI goes red, file still shows old green); (3) the artifact lives in the external repo with no place to carry the URL/SHA in VHS-19's vigil-skills audit trail. Re-opens the F-5 gap through under-specification.
**Fix:** Require the artifact carry the fork commit SHA, be recorded in VHS-19's spec record/PR before the Plane flip, and be the run against the fork tip at flip time. [Addressed in 2g via Test-plan #3.]

### F-3: No contradiction between scope-narrow triggers and permitted retarget surgery — positive verification
**Severity:** P3
Trigger 3 ("manifest-optional/skills-root edit permitted; decoupling CE skills or writing a new target is not") mirrors D4's framing. Consistent. No change.

## Summary
P0: 0 | P1: 0 | P2: 2 | P3: 1 | P4: 0

Empty-input contract holds at suite level via path (b); F-1 is the path-(a) self-guard gap. Pinned-sample/runtime split fully consistent across Goal, D6, Done-when #1, Test-plan #1-2. Upstream-contract facts rest on round-1 web verification (upstream/fork not present locally).

STATUS: GREEN
