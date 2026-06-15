# Reconciliation Report: VHS-17

> Date: 2026-06-14
> Spec: docs/specs/TODO/VHS-17.spec.md
> Merge: PR #17 (commit 39006cc)
> Plane state: PR Review (group: completed)

## Summary
VHS-17 shipped as specified: the portability contract (`docs/portability-contract.md`, 5 sections), the `requires:` worked annotation on `spec-cycle`, and a discoverability pointer — with one well-understood deviation. The spec's Scope assigned the pointer edits to `CLAUDE.md`, but `CLAUDE.md` is gitignored/machine-local in this repo, so the contract pointer shipped in `README.md` instead, and the bundled `spec-workflow-reference.md` pointer was not shipped. All four acceptance criteria are met (criterion #1 met via README rather than CLAUDE.md). RECONCILED: yes.

## Scope
| Spec file | In diff? | Notes |
|---|---|---|
| `docs/portability-contract.md` | Yes | New, 149 lines. Five sections §1–§5 + Worked reference, as specified. |
| `skills/spec-cycle/SKILL.md` | Yes | +6 lines: the `requires:` block, frontmatter-only. Body untouched. |
| `CLAUDE.md` | No | **Dropped** — `CLAUDE.md` is gitignored/machine-local; the spec's pointer edit shipped in `README.md` instead (see Unexpected). |

Unexpected files in diff (not in spec scope):
- `README.md` (+4) — carries the contract pointer the spec assigned to `CLAUDE.md`. Line 47: `docs/portability-contract.md` pointer with a one-line description. This is the relocation of the spec's intended `CLAUDE.md` edit, not new scope. The planned second pointer (`docs/spec-workflow-reference.md`) was **not** shipped here (that target file is itself untracked).

(Spec artifacts `VHS-17.brief.md`, `VHS-17.spec.md`, `VHS-17.reviews/`, `VHS-17.test-output.txt` also appear in the PR diff — expected; they are this spec being archived, not reconciliation targets.)

## Decisions
| # | Decision | Status | Evidence |
|---|---|---|---|
| D1 | Canonical source = Claude Code `SKILL.md`; adapters generated | Confirmed | `docs/portability-contract.md:14` §1 "Canonical source format" |
| D2 | Parity is behavioral, not string-identical | Confirmed | `docs/portability-contract.md:123` §5 "Behavioral-parity definition" |
| D3 | Capabilities declared, not inferred | Confirmed | `docs/portability-contract.md:47` §3 "Capability / tool-requirement declaration" |
| D4 | One `requires:` frontmatter key, round-trips through sync.py | Confirmed | `skills/spec-cycle/SKILL.md:5` `requires:` block present; `sync.py` unchanged in diff; load-check passed (no `sync.py` action). |
| D5 | `requires:` is a flat, stdlib-parseable schema | Confirmed (wording nuance) | `docs/portability-contract.md:51` §3 Schema is flat (scalars + single-line flow seqs). **Nuance:** spec/§3 calls the block "valid YAML that Claude Code's own parser accepts"; in fact `services: [issue-tracker?, shared-memory?]` is *not* strict-YAML-valid (PyYAML raises on the bare `?`), but Claude Code accepts it anyway because it parses only recognized frontmatter keys (field-level), ignoring the unknown `requires:` key. Schema shipped as designed; the "valid YAML" phrasing is imprecise but harmless. |
| D6 | Intent rule binds operative instructions; 3-way construct classification | Confirmed | `docs/portability-contract.md:107` §4 classifies three constructs (operative call / tagged example / non-operative notes) |

## Acceptance Criteria
| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | Contract merged + referenced alongside customizing.md / spec-workflow-reference.md pointers | Met (deviation) | Contract merged (`docs/portability-contract.md`). Referenced from `README.md:47` (not `CLAUDE.md` — gitignored). `customizing.md` pointer present (`README.md:43`); **`spec-workflow-reference.md` pointer not shipped** (that file is untracked). Core intent — contract is discoverable — is met. |
| 2 | §2 portable-frontmatter table + §3 capability schema specified with examples | Met | `docs/portability-contract.md:26` §2 table; `:51` §3 worked schema block + availability + tokenization rules |
| 3 | spec-cycle annotated; dry-run round-trips with no sync.py change; manual load-check confirms it loads | Met | `skills/spec-cycle/SKILL.md:5` block; `sync.py install --dry-run` → `[WRITE/dry] spec-cycle/SKILL.md (differ)`, exit 0, no `sync.py` action; post-install grep confirmed `requires:` block; unknown-key tolerance confirmed (Claude Code ignores unknown frontmatter keys → skill loads). |
| 4 | §5 behavioral parity as four explicit dimensions | Met | `docs/portability-contract.md:123` §5 lists 4 dimensions (output artifacts / honored gates / side-effect scope / intent achieved) incl. vacuous-pass + out-of-scope `produces:` notes |

## Test Plan
| Test | Exists? | Location |
|---|---|---|
| `sync.py install --dry-run` smoke (no sync.py action) | Yes (manual, captured) | `docs/specs/TODO/VHS-17.test-output.txt`; re-verified at close: `[WRITE/dry] spec-cycle/SKILL.md (differ)`, exit 0 |
| Post-install load-check (requires: block + loads) | Yes (manual, captured at close) | Installed `~/.claude/skills/spec-cycle/SKILL.md:5` requires block; unknown-key tolerance confirmed via Claude Code frontmatter behavior |

No automated test suite ships (repo has none; VHS-18 later adds `lint.py`). Gate was the dry-run smoke + manual load-check + review checklist — all satisfied.

## Wiki-ready
Decisions and comprehension worth extracting to the wiki:
- **Decision (D4/D5 nuance): unknown frontmatter keys are tolerant in Claude Code, not strict-YAML-validated.** The `requires:` block is accepted by Claude Code's loader *despite* not being strict-YAML-valid (`[issue-tracker?, shared-memory?]`), because the loader parses only recognized keys and ignores unknown ones. This is the load-bearing fact that makes the whole annotation strategy safe — worth recording so future skills can rely on it (and so the contract's "valid YAML" wording is read with this caveat).
- **Decision: gitignored `CLAUDE.md` forces "reference from CLAUDE.md" deliverables into `README.md`.** Any spec that says "reference X from CLAUDE.md" in this repo must ship the pointer in `README.md` (the tracked, portable instructions surface) because `CLAUDE.md` is machine-local. VHS-17 is the worked instance. (Already captured in project memory; reinforce in wiki.)
- **Comprehension: the portability contract is the anchor for the VHS-16 epic.** `docs/portability-contract.md` is the single normative target for VHS-18 (lint), VHS-19 (converter), VHS-20 (Hermes adapter), VHS-21 (conformance), VHS-22 (distribution). Records what the five sections pin down so downstream items cite sections, not re-invent.

RECONCILED: yes DRIFT: 2
