# VHS-12 — Merge /spec-reconcile + /spec-retire into a single post-merge skill

**Status:** Backlog · **Priority:** Medium · **Assignee:** Unassigned
**Created:** 2026-06-11 · **Plane:** VHS-12
**Origin:** Session-history analysis across 7,310 prompts (2026-03-05 → 2026-06-11): the spec lifecycle's front half is heavily adopted (`/spec-cycle` 142 invocations, `/ship-spec` 154) while the tail is effectively abandoned (`/spec-reconcile` 5, `/spec-retire` 0). `/wiki-after-merge` (123 invocations) absorbed the post-merge habit. User confirmed the cause is friction, not lack of value: two separate skills, run in sequence, for one logical act ("close out a shipped spec").

## Problem

Closing a shipped spec today requires two invocations with a hand-carried artifact between them:

1. `/spec-reconcile <spec-path>` (`skills/spec-reconcile/SKILL.md`, 118 lines) — read-only diff of spec vs. shipped code, emits `<TICKET-ID>.reconciliation.md`.
2. `/spec-retire <spec-path>` (`skills/spec-retire/SKILL.md`, 266 lines) — consumes the reconciliation report, gates on Plane state, decomposes into wiki entries, archives `TODO/` → `DONE/<TICKET-ID>/`, appends wiki `log.md`.

The split exists for a clean read-only/mutating boundary, but in practice the boundary cost a second session-and-context spin-up per spec, and the tail never gets run. Consequences:

- `docs/specs/TODO/` accumulates shipped-but-unretired specs (vigil-skills alone currently carries VHS-1, -3, -4, -5, -6, -7, -8, -9, -11 artifacts in `TODO/`, several already merged).
- The wiki knowledge layer is starved of the decisions/comprehension entries spec-retire was designed to extract.
- Drift between spec intent and shipped code is never measured, so spec-cycle's reviewer agents lose the feedback signal reconciliation was meant to provide.

## Direction (user-confirmed 2026-06-11)

One skill — working name `/spec-close <spec-path>` — that runs reconcile-then-retire in a single invocation, preserving the existing safety split *inside* the skill:

- Phases 1–N (analysis): everything `spec-reconcile` does today, read-only. The reconciliation report is still written to disk (audit trail, and `--report-only` early exit replaces standalone reconcile).
- A single consolidated user-confirmation checkpoint (the pattern `spec-retire` Phase 3, `:170–203`, already implements) before any mutation.
- Mutating phases: wiki entries, archive to `DONE/`, `log.md` append — all of `spec-retire` Phase 4 (`:203–249`), including the Plane full-vs-partial-retire gate (Phase 1, `:28–41`) and the wiki-coverage fast-path (VHS-9, `:70–143`).

Open design questions for the spec author (do not pre-decide in this brief):

- Whether `/spec-close` supersedes both skills (deprecation/removal) or wraps them (thin orchestrator invoking shared phase text). Beware duplicate-code findings from the conventions reviewer if phase text is copied.
- Whether `/wiki-after-merge` (lives in the internal wiki repo, not vigil-skills) should print a one-line nudge when the merged commit ships a spec — cross-repo coupling is a known boundary; per the public-repo rule, vigil-skills must not depend on wiki-repo internals.
- Whether the Plane state gate keys on state ID rather than `completed_at` (per the known VHS quirk: PR Review state sets `completed_at`).

## Done when

- One invocation takes a merged spec from `TODO/` to fully closed: reconciliation report written, wiki proposals confirmed and applied, artifacts archived to `DONE/<TICKET-ID>/`, `log.md` appended, partial-retire auto-detected when the Plane ticket isn't completed.
- Read-only analysis and confirmed mutations remain strictly ordered; no mutation before the consolidated confirmation.
- A `--report-only` flag (or equivalent) preserves the standalone-reconcile use case.
- CLAUDE.md and skill cross-references (`spec-cycle`, `ship-spec` pair-with text) updated consistently.
- `python sync.py status` clean; installed copies round-trip via `sync.py push`.

## Out of scope

- Changes to `/spec-cycle` or `/ship-spec` beyond cross-reference text.
- Any change to `/wiki-after-merge` itself (internal wiki repo; separate change if the nudge is wanted).
- Auto-running spec-close without user invocation (no hooks, no SessionStart scans).
- Backfilling the existing unretired VHS specs (operational task, not skill work — run the new skill on them once it ships).

## References

- Plane: VHS-12 (created 2026-06-11, priority Medium)
- Skills: `skills/spec-reconcile/SKILL.md` (118 lines), `skills/spec-retire/SKILL.md` (266 lines) — both read 2026-06-11
- Usage evidence: `~/.claude/history.jsonl` slash-command frequency analysis, 2026-06-11
- Precedent: VHS-9 (wiki-coverage fast-path, already merged into spec-retire 2b), VHS-7 (host-agnostic conventions)
- Memory: `project_vhs_pr_review_sets_completed.md` (Plane state-group quirk — gate on state ID, not completed_at)
