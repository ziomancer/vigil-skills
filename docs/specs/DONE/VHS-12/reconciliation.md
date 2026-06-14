# Reconciliation Report: VHS-12

> Date: 2026-06-14
> Spec: docs/specs/TODO/VHS-12.spec.md
> Merge: aeecc86 (PR #15)
> Plane state: PR Review (group: completed)

## Summary

Full match on every tracked file. `/spec-close` shipped as a single new skill; `/spec-reconcile`
and `/spec-retire` were deleted in the same PR; `ship-spec`/`spec-cycle` frontmatter descriptions
were extended. One caveat (not drift): the spec's `CLAUDE.md` edit is realized in the working tree
("Three skills…", no dangling refs) but `CLAUDE.md` is **gitignored** in vigil-skills, so the change
is absent from the tracked merge — repo policy, pre-existing, not introduced by VHS-12.

## Scope

| Spec file | In diff? | Notes |
|---|---|---|
| `skills/spec-close/SKILL.md` | Yes (new, +392) | `name: spec-close`, `user_invocable: true`; the merged skill |
| `skills/spec-reconcile/SKILL.md` | Yes (deleted, −118) | as specified (Decision 1 — supersede + delete, no shims) |
| `skills/spec-retire/SKILL.md` | Yes (deleted, −266) | as specified |
| `skills/ship-spec/SKILL.md` | Yes (+4/−) | frontmatter description: "after the PR merges, run /spec-close" |
| `skills/spec-cycle/SKILL.md` | Yes (+2/−) | frontmatter description: names /spec-close as the post-merge step |
| `CLAUDE.md` | **No (gitignored)** | edit realized on disk (`:23` "Three skills…", items 3+4 collapsed, file-layout line) but the file is gitignored in vigil-skills → not in the tracked commit. Intent met locally; not propagated to fresh clones (repo policy). |

Unexpected files in diff (not in spec): none.

## Decisions

| # | Decision | Status | Evidence |
|---|---|---|---|
| 1 | Supersede + delete, no deprecation shims | Confirmed | both skill dirs gone; standalone-reconcile → `--report-only`, forced-partial → `--partial` documented in spec-close |
| 2 | Prompted degradation over hard-halt (state-gate contradiction) | Confirmed | spec-close Phase 1 8-row mode table (completed/cancelled → full-close; else partial-or-abort prompt) |
| 3 | Gate on state-group from UUID, never `completed_at` | Confirmed | spec-close Phase 1 + "Never use `completed_at` as a gate signal"; 0 gate uses of completed_at |
| 4 | Reconciliation report is the lone pre-confirmation write | Confirmed | spec-close mutation-boundary note; Phase 2c |
| 5 | Partial-close drops the report precondition | Confirmed | spec-close Phase 2 "Skipped entirely in partial-close" |
| 6 | Archive renames to ticketless filenames | Confirmed | spec-close Phase 5 rename mapping (spec.md/brief.md/reconciliation.md/reviews/) |
| 7 | Carry inventory + rebrand set + sanctioned deviations | Confirmed | `close \| <PROJECT>` rebrand present (4×); zero `full-retire`/`partial-retire`/"retirement log" strings |
| 8 | Wiki availability resolved per mode before checkpoint | Confirmed | spec-close Phase 1 rows 7–8 |

## Acceptance Criteria

| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | One invocation TODO→closed; partial detected & offered | Met | spec-close Phases 0–5; this very close ran PET-119 + VHS-12 through it |
| 2 | Read-only-then-confirmed split; report is the only pre-confirmation write | Met | spec-close mutation-boundary; Phase 2c/Phase 4 |
| 3 | `--report-only` preserves standalone reconcile | Met | spec-close Phase 1 row 1 + invocation block |
| 4 | CLAUDE.md + pair-with descriptions reference /spec-close; no dangling refs to deleted skills | Met (working tree) | `grep -rl "spec-reconcile\|spec-retire" skills/ CLAUDE.md` → zero; CLAUDE.md `:23` "Three skills" (gitignored caveat above) |
| 5 | `sync.py status` clean after install; round-trips via `push` | Unverifiable (here) | operational (install-time); states.json drift reconciliation is a PR-description instruction |

## Test Plan

Doc-only spec — gate is the spec's review checklist (VHS-7 convention). Spot-checks confirmed:
`name: spec-close` + `user_invocable: true` present; 8-row mode table; `grep -F "close | <PROJECT> — <TICKET-ID>:"`
idempotency guard (trailing colon); zero retire-era mode strings; both deleted dirs absent; zero dangling refs.

## Wiki-ready

- Comprehension: the consolidation — merge `/spec-reconcile` + `/spec-retire` into one `/spec-close`, driven by adoption data (tail abandoned: 5 + 0 uses vs 154 `/ship-spec`); the prompted-degradation resolution of the cross-skill state-gate contradiction; supersede-and-delete (no shims). **Supersedes** the VHS-8 comprehension (`2026-05-16-vhs-8-spec-retirement-pipeline.md`), whose Judgment Call "two skills rather than one" VHS-12 reverses.
- (No separate decision entry — VHS skill-pipeline work is comprehension-tracked in this project, per the VHS-8 precedent; the wire-level decisions live in the comprehension's Why + Judgment Calls.)

RECONCILED: yes DRIFT: 0
