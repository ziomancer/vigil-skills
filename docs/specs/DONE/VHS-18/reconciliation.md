# Reconciliation Report: VHS-18

> Date: 2026-06-14
> Spec: docs/specs/TODO/VHS-18.spec.md
> Merge: PR #18 (commit 7ec40ca)
> Plane state: PR Review (group: completed)

## Summary
VHS-18 shipped exactly as specified: the stdlib `lint.py`, the `docs/authoring-portable-skills.md` guidelines, the repo's first test suite (`tests/test_lint.py`) with its fixture set, and a README pointer in the "Cross-harness portability" section. Verified live at close: `python tests/test_lint.py` → 6 tests OK; `python lint.py` → 0 errors / 3 warnings (the tracked missing-`requires:` advisories on ship-spec/spec-close/review-pr); `python lint.py --strict` → exit 1 on the bad fixture. Scope is clean with one justified extra (`tests/fixtures/.gitattributes`, required so the CRLF fixture keeps its endings through git). RECONCILED: yes.

## Scope
| Spec file | In diff? | Notes |
|---|---|---|
| `lint.py` | Yes | New, 295 lines. Stdlib-only; importable API + CLI with `--strict`. |
| `docs/authoring-portable-skills.md` | Yes | New, 51 lines. Restates contract as authoring discipline; running-the-lint, promotion path, v1 limitations; links the contract. |
| `tests/test_lint.py` | Yes | New, 85 lines. stdlib `unittest`; 6 tests incl. the 4-skill inventory tripwire. |
| `tests/fixtures/` | Yes | bad-skill, good-skill + 11 malformed/edge fixtures, as specified. |
| `README.md` | Yes | +2: guidelines pointer in the "Cross-harness portability" section (D5). |

Unexpected files in diff (not explicitly in spec scope):
- `tests/fixtures/.gitattributes` (+7) — justified: pins `crlf-skill/SKILL.md` (and siblings) line endings so the CRLF/BOM robustness fixtures survive git normalization. Implied by the `crlf-skill` fixture the spec lists; a necessary companion, not new scope.

(`sync.py`, the four skills, and `CLAUDE.md` are untouched, exactly as the spec's "Left alone" section requires. Spec artifacts `VHS-18.brief.md`/`.spec.md`/`.reviews/`/`.test-output.txt` also appear in the PR — expected; this is the spec being archived.)

## Decisions
| # | Decision | Status | Evidence |
|---|---|---|---|
| D1 | Standalone stdlib `lint.py` at repo root (not a sync.py subcommand, not new CI) | Confirmed | `lint.py` is a top-level sibling of `sync.py`; `sync.py` unchanged in diff |
| D2 | Two severities: ERROR (blocking-eligible) / WARN (advisory) | Confirmed | Live run: `lint: 0 error(s), 3 warning(s)`; bad fixture yields ERROR `operative-tool-call` |
| D3 | Warn-only default (exit 0); `--strict` is the promotion switch | Confirmed | `lint.py` references `--strict` (3×); `python lint.py --strict tests/fixtures/bad-skill` → exit 1; default mode exits 0 with stderr summary |
| D4 | Missing-`requires:` are tracked WARNs, not a blocking backlog | Confirmed | 3 WARNs on ship-spec/spec-close/review-pr; recorded in the guidelines promotion path |
| D5 | Guidelines linked from README.md, not CLAUDE.md (gitignored) | Confirmed | `README.md` +2 in the "Cross-harness portability" section; `CLAUDE.md` untouched |
| D6 | `mcp__*`-token detection; three v1 detection gaps documented | Confirmed | `lint.py` documents its limitations; spec D6 enumerates bare-name / operative-under-notes / case-2-window |

## Acceptance Criteria
| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | Guidelines doc merged + linked from README "Cross-harness portability" section | Met | `docs/authoring-portable-skills.md` shipped; `README.md` pointer in that section |
| 2 | `lint.py` runs against all 4 skills, zero-ERROR backlog; missing-`requires:` WARNs tracked in guidelines | Met | `python lint.py` → 0 errors / 3 warnings; promotion-path backlog documented in the guidelines doc |
| 3 | Concrete stdlib `lint.py`, `python lint.py` / `--strict`, warn-only + stderr summary + documented promotion path & optional pre-commit hook | Met | `lint.py` CLI; `--strict` exit-code contract verified; authoring doc covers promotion path + pre-commit hook |
| 4 | Known-bad fixture fires; good fixture + 4 skills pass — demonstrated in captured test output | Met | `python tests/test_lint.py` → Ran 6 tests, OK; `docs/specs/TODO/VHS-18.test-output.txt` is the captured artifact |

## Test Plan
| Test | Exists? | Location |
|---|---|---|
| Negative: bad-skill yields ERROR `operative-tool-call` + WARN `missing-requires` | Yes | `tests/test_lint.py` (case 1) |
| Positive: good-skill zero ERRORs, no missing-requires | Yes | `tests/test_lint.py` (case 2) |
| Shipped skills clean + 4-skill inventory tripwire | Yes | `tests/test_lint.py::test_shipped_skills_clean` |
| Robustness: 11 malformed/edge fixtures, deterministic, no exception | Yes | `tests/test_lint.py` (case 4) + `tests/fixtures/*` |

Live at close: `python tests/test_lint.py` → `Ran 6 tests … OK` (exit 0). This is the repo's first automated test suite.

## Wiki-ready
Decisions and comprehension worth extracting to the wiki:
- **Comprehension: VHS-18 makes the portability contract enforceable.** `lint.py` + `docs/authoring-portable-skills.md` turn VHS-17's contract from prose into a mechanical, stdlib-only guard (warn-only now, `--strict` promotion path) and ship the repo's first test suite. Records what the lint catches (R1 `requires:` validity, R2 `mcp__*` operative-call detection), its deliberate v1 gaps, and the warn→block promotion path.
- **Decision: lint is warn-only with a `--strict` promotion gate, and `mcp__*`-only detection by design.** The advisory-then-blocking rollout (default exit 0; `--strict` exits non-zero on ERROR) plus the three documented detection gaps (bare-name, operative-under-notes, case-2 window) are deliberate false-positive-avoidance choices that CodeRabbit's qualitative pass backstops. Load-bearing for anyone tightening the gate later (the promotion path is: annotate the 3 remaining skills → install the pre-commit hook calling `--strict`).
- **State/promotion note:** the open follow-up — annotate `ship-spec`/`spec-close`/`review-pr` with `requires:` blocks, then flip `lint.py` to a `--strict` pre-commit hook — is the documented backlog (3 current WARNs).

RECONCILED: yes DRIFT: 1
