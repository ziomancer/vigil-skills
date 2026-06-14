# Correctness Review — round 1

## Closure of round 0 findings
N/A — round 1

## Grounding verification summary

Verified accurate against current files:
- CLAUDE.md `:55–56` anchor — exactly the two file-layout lines for spec-reconcile/spec-retire (`CLAUDE.md:55-56`).
- Decision 2's contradiction claim — spec-reconcile Phase 0 step 5 hard-halts on non-completed tickets (`skills\spec-reconcile\SKILL.md:19`) while spec-retire Phase 0 step 3 requires the report that halt prevents (`skills\spec-retire\SKILL.md:16`). Real, well-characterized.
- Decision 3 — spec-retire Phase 1 steps 3–4 gate on state UUID → group (`skills\spec-retire\SKILL.md:36-39`); `completed_at` quirk matches project memory.
- Decision 6's disagreement claim — spec-retire's archive plan lists full names (`skills\spec-retire\SKILL.md:189-192`) vs spec-reconcile's ticketless DONE parsing (`skills\spec-reconcile\SKILL.md:11,53`). Confirmed.
- Decision 7 inventory — every named phase exists at HEAD (reconcile Phases 1–3; retire 2a/2b incl. all three fast-path stages/2c/Phase 3/Phase 4 incl. tracked/untracked branch, idempotency guard, no-commit rule).
- `sync.py` claims — `SUBTREES` wholesale mirror (`sync.py:30`), `--prune` install-only deleting dst-only files (`sync.py:81-84,197-201`), `status` showing src-only/dst-only states (`sync.py:155-173`).
- Repo-wide grep (excluding `docs/specs/`): the only `spec-reconcile|spec-retire` mentions are inside the two to-be-deleted skill files. README.md, docs/customizing.md, agents/, and the ship-spec/spec-cycle bodies are clean — the frontmatter-only edit scope is sufficient.
- `docs/spec-workflow-reference.md` — no reconcile/retire mentions; "leave alone" is safe.
- Brief Done-when 1–5 all map to spec sections; all three of the brief's open design questions are resolved (Decisions 1 and 3 explicitly; the wiki-after-merge nudge via Out-of-scope, consistent with the brief's own out-of-scope list).

## Findings

### F-1: Partial-close claims it never needs the wiki, but its close plan appends to wiki log.md
**Severity:** P0
**Where:** spec.md:70 (Phase 0 step 3) vs spec.md:46 (Decision 5), spec.md:96 (Phase 3), spec.md:114 (Phase 5)
**Claim:** "Wiki missing: halt only when the resolved mode will need it — i.e., warn here, halt at the start of wiki decomposition. `--report-only` and partial-close never need the wiki."
**Why this is wrong:** Decision 5 and Phase 3 say the partial-close plan "contains only the archive list and the retirement log entry," and Phase 5 executes spec-retire Phase 4 verbatim — whose step 4 appends the log entry to `<wiki_root>/log.md` (`skills\spec-retire\SKILL.md:220`). The log entry lives in the wiki, so partial-close *does* need the wiki. As written, a partial-close with a missing wiki passes every halt point (wiki decomposition — the only stated halt site — is skipped entirely in partial mode), archives the artifacts, then hits an unwritable log.md append: a half-executed close with mutations already applied. This also silently reverses spec-retire's current hard-halt-on-missing-wiki posture (`skills\spec-retire\SKILL.md:18,263`) without saying what replaces it for the partial path.
**Suggested fix:** Pick one and state it: (a) partial-close with missing wiki drops the log.md entry from the plan (archive-only, with a warning shown in the Phase 4 confirmation block), or (b) the missing-wiki halt also fires before Phase 4 whenever the compiled plan contains any wiki write, including the log entry. Either way, make the halt/skip decision happen before the confirmation checkpoint, never mid-execute.

### F-2: Decision 6's dual DONE-shape acceptance contradicts the verbatim-carried shape logic in Phase 2, and Decision 7 forbids the fix
**Severity:** P1
**Where:** spec.md:49 (Decision 6), spec.md:52 (Decision 7), spec.md:89 (Phase 2)
**Claim:** "The merged skill's spec-path resolution accepts **both** shapes for DONE paths…" combined with "spec-reconcile Phases 1–3 verbatim … no behavioral changes."
**Why this is wrong:** Dual-shape acceptance is specified only for path *resolution* (ticket_id extraction). The verbatim-carried text contains DONE-shape-dependent behavior beyond resolution: companion brief lookup is "`brief.md` for DONE paths" (`skills\spec-reconcile\SKILL.md:37`) and the report write target is "`docs/specs/DONE/<TICKET-ID>/reconciliation.md`" only for the ticketless shape (`skills\spec-reconcile\SKILL.md:53`). Decision 6's new archive rule produces DONE artifacts with full names — a shape the carried text matches in neither branch. A `--report-only` run against a spec archived by spec-close itself silently misses the companion brief and has an undefined report path. Decision 7's "no behavioral changes" rule blocks the implementer from extending those conditionals.
**Suggested fix:** In Decision 7, carve out an explicit exception: the carried Phase 1 step 3 and Phase 3 DONE-shape branches are extended to both shapes, with the rule "companion filenames mirror the spec filename's shape."

### F-3: CLAUDE.md edit anchor `:25–31` excludes line 23, leaving "Four skills … the post-merge pair" stale
**Severity:** P2
**Pre-ship recommended:** yes
**Where:** spec.md:20 (Scope) and spec.md:118 (Cross-reference edits)
**Claim:** "`CLAUDE.md:25–31`: lifecycle becomes three numbered skills…"
**Why this is wrong:** `CLAUDE.md:23` reads "Four skills form the spec lifecycle. The authoring/impl pair runs in separate sessions…; the post-merge pair runs after code ships." It sits outside the cited `:25–31` range. An implementer editing exactly the anchored range leaves "Four skills" and "post-merge pair" contradicting the new three-item list — failing the spec's own checklist item "CLAUDE.md lifecycle reads as three steps" (spec.md:133).
**Suggested fix:** Extend the cross-reference edit to `CLAUDE.md:23`.

### F-4: Test-plan grep expectation contradicts its own command
**Severity:** P3
**Where:** spec.md:132 (Test plan, dangling-reference checklist item)
**Claim:** "`grep -ri "spec-reconcile\|spec-retire" CLAUDE.md README.md docs/customizing.md skills/ agents/` returns only historical mentions inside `docs/specs/`…"
**Why this is wrong:** `docs/specs/` is not among the grep's search paths, so the command can never return mentions inside it. Verified at HEAD: after the proposed deletions and CLAUDE.md edits, the only matches in the listed paths are inside the two deleted skill directories themselves — the correct expected result is empty output.
**Suggested fix:** Change the expectation to "returns no matches."

### F-5: Phase 2 parenthetical names `git grep`; the carried mechanism is `git log --grep`
**Severity:** P4
**Where:** spec.md:89 (Phase 2)
**Why this is wrong:** The verbatim source is `git log --all --oneline --grep="<TICKET-ID>"` (`skills\spec-reconcile\SKILL.md:28`). `git grep` is a different command.
**Suggested fix:** "(git log --grep → memory lookup → user prompt)".

### F-6: Ambiguous citation "spec-retire 2a/Phase 0 step 2a" for the tracking-status check
**Severity:** P4
**Where:** spec.md:69 (Phase 0 step 2)
**Why this is wrong:** Bare "2a" in spec-retire denotes Phase 2a (duplicate detection); the tracking check is Phase 0 step 2a (`skills\spec-retire\SKILL.md:13-15`).
**Suggested fix:** Cite "spec-retire Phase 0 step 2a" only.

## Summary
P0: 1 | P1: 1 | P2: 1 | P3: 1 | P4: 2

STATUS: RED P0=1 P1=1 P2=1 P3=1 P4=2
