# Reconciliation Report: VHS-19

> Date: 2026-06-15
> Spec: docs/specs/TODO/VHS-19.spec.md
> Merge: vigil-skills PR #20 (squash `3e43d7c`) + external repo `ziomancer/vigil-converter` @ `14cdca4f` (CI run [27532395287](https://github.com/ziomancer/vigil-converter/actions/runs/27532395287))
> Plane state: Done (group: completed)

## Summary

Full-close. The deliverable is split by design (spec D7): the vigil-skills footprint (one README pointer + spec record + two cited design docs) shipped via PR #20; the substantive deliverable — the owned, stripped, retargeted converter engine with a CI smoke-test gate — shipped in the external `vigil-converter` repo. All five acceptance criteria are Met; the binding gate (fork CI smoke test green against the fork tip, D7) is satisfied. Two informational drifts: the "no CE residue" structural check is only partially met (engine-internal legacy-compat identifiers remain, filed in STRIP.md per the no-rewrite rule), and the spec's "preserves `requires:` verbatim on passthrough" claim is not exercised (output preservation is out of scope).

## Scope

**vigil-skills (this repo) — reconciled against PR #20 (`3e43d7c`):**
| Spec file | In diff? | Notes |
|---|---|---|
| `README.md` | Yes | Pointer to vigil-converter added to "Cross-harness portability" prose (`README.md:51`) |
| `docs/specs/TODO/VHS-19.spec.md` (+ `.reviews/`) | Yes | Spec record (green r2) |
| `docs/compound-engineering-evaluation.md` | Yes | Prerequisite design doc tracked (+ OpenClaw→OpenCode + anonymization fixes) |
| `docs/cross-harness-spike-synthesis.md` | Yes | Prerequisite design doc tracked |
| `sync.py`, `skills/`, `agents/`, `lint.py`, `tests/` | No | Correctly left untouched (stdlib-only contract preserved) |

**vigil-converter (external deliverable) — reconciled against the built repo:**
| Spec scope item | Shipped? | Evidence |
|---|---|---|
| Fork + `upstream` remote + recorded fork point | Yes | fork `0757e859`; `upstream`→EveryInc; tip `14cdca4f` |
| The strip (documented diff) | Yes | labeled `strip(ce)` commits + `STRIP.md` |
| Input retargeted (scoped parser edit) | Yes | `feat(parser)` `9c0a346a` — `src/parsers/claude.ts` |
| Committed lockfile + supply-chain README | Yes | `bun.lock` pinned; README "Supply chain & security posture" |
| CI two-path smoke test | Yes | `.github/workflows/ci.yml`; run 27532395287 green |

## Decisions
| # | Decision | Status | Evidence |
|---|---|---|---|
| D1 | Fork-and-own via mirror-clone + `upstream` remote | Confirmed | clone of EveryInc pushed to `ziomancer/vigil-converter`; `upstream` remote; fork SHA `0757e859` recorded in README |
| D2 | Security-first: never executes skill content during conversion | Confirmed | `bun audit` clean (2026-06-15); zero exec sinks in `src/` (grep over Bun-aware set); README assertion + emitted-artifact boundary |
| D3 | Documented, reproducible diff against upstream | Confirmed | `STRIP.md` + labeled commits; `upstream` remote for cherry-picks; cadence documented |
| D4 | Canonical `SKILL.md`; retarget; preserve portable frontmatter | Drifted | Retarget Confirmed (manifest-optional + skills-root, `claude.ts`); `requires:` round-trips through parse without error. But the parser does not capture/re-emit `requires:`, so "preserves verbatim on passthrough" is not exercised — output preservation is out of scope (VHS-21) |
| D5 | Fork lives outside vigil-skills (toolchain isolation) | Confirmed | separate repo; Bun toolchain isolated there; vigil-skills got only the README pointer |
| D6 | Smoke test = ingest + one real target over a pinned sample | Confirmed | `scripts/smoke-test.ts`, `samples/skills/`; OpenCode primary + Codex fallback; asserts ≥1 skill parsed + exit 0 + non-empty output |
| D7 | README-pointer footprint; fork CI = blocking acceptance gate | Confirmed | PR #20 pointer; CI run 27532395287 (headSha `14cdca4f`) recorded on VHS-19 before the Plane flip |

## Acceptance Criteria
| # | Criterion (brief "Done when") | Status | Evidence |
|---|---|---|---|
| 1 | Fork builds + converts pinned sample with no CE residue | Met (drift) | CI green (build + convert); product residue removed + CE registry emptied (inert). **Structural no-residue only partial** — ~30 legacy-compat identifiers remain in engine internals, filed in `STRIP.md` |
| 2 | Dependency audit + pinning recorded; supply-chain note in README | Met | `bun audit` clean 2026-06-15; `bun.lock` pinned (`--frozen-lockfile` in CI); README supply-chain section |
| 3 | Smoke-test conversion runs in CI (ingest + ≥1 target), green, captured | Met | run 27532395287 success, headSha `14cdca4f`; recorded on VHS-19 |
| 4 | Fork point + strip diff + repo home + cadence documented in README | Met | README "Fork provenance" + `STRIP.md` |
| 5 | (vigil-skills) README references vigil-converter | Met | `README.md:51` (PR #20) |

## Test Plan
| Test | Exists? | Location |
|---|---|---|
| Two-path engine-liveness smoke test | Yes | `vigil-converter:scripts/smoke-test.ts` (run in CI `.github/workflows/ci.yml`) |
| Inherited unit/parity suite | No | Removed (CE-fixture-coupled, out of scope per D6); re-introduction is a future enhancement (STRIP.md) |

## Wiki-ready
Decisions and comprehension worth extracting to the wiki:
- **Decision (D1/D2/D3): fork-and-own a third-party converter with a documented-diff + supply-chain posture** — non-obvious, reusable pattern for adopting external tooling (mirror-clone over GitHub fork, recorded fork point, `bun audit` + pinned lockfile + no-exec-sink inspection, no-rewrite entanglement rule). Wiki-worthy as a reusable decision.
- **Comprehension: `vigil-converter` is a new owned repo in the ecosystem** — the conversion engine that emits per-harness packages from canonical `SKILL.md`; the retarget (manifest-optional + skills-root) is the one load-bearing edit; CI smoke test is the acceptance gate. Needs a `projects/vigil-converter/` page (the deferred conventions/F-4 onboarding item).
- **State.md:** VHS-19 → What's Shipped, evidence triple below.

RECONCILED: yes DRIFT: 2
