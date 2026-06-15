# Cross-Harness Skill Parity — Spike Synthesis (VHS-16 / 17 / 18)

**Date:** 2026-06-14 · **Author:** Claude (autonomous `/loop`, 5-min heartbeat) · **Scope:** the VHS-16 epic's first two loopable children, taken from brief → `spec-cycle` → `ship-spec` end to end.

## TL;DR

Both shippable children of the cross-harness epic are **done and open as PRs**, fully reviewed and test-green:

| Ticket | Deliverable | PR | Spec rounds | Test gate |
|--------|-------------|----|-------------|-----------|
| **VHS-17** | `docs/portability-contract.md` (5-section contract) + `requires:` worked annotation on `spec-cycle` | [#17](https://github.com/ziomancer/vigil-skills/pull/17) — `+680`, 15 files, base `main`, MERGEABLE | green at **round 3** (5→3→0 blocking) | `sync.py --dry-run`: 1 action, no `sync.py` change |
| **VHS-18** | `lint.py` (stdlib portability lint) + `docs/authoring-portable-skills.md` + tests/fixtures | [#18](https://github.com/ziomancer/vigil-skills/pull/18) — `+1118`, 33 files, **stacked on #17**, MERGEABLE | green at **round 4** (7→1→2→0 blocking) | `python tests/test_lint.py`: **6/6 pass**; lint fires on bad fixture, clean on 4 shipped skills |

VHS-16 itself is an orientation epic — "done" when its children merge, which is now one human merge-and-retarget away. The spike also surfaced **four process findings** worth more than the code (below).

## What shipped

- **The contract (VHS-17)** makes "just works across harnesses" checkable: canonical source = Claude Code `SKILL.md`; a portable frontmatter subset with a Hermes mapping; a flat, stdlib-parseable `requires:` capability declaration; an operativeness-based intent-over-implementation rule; and a four-dimension behavioral-parity definition. Every downstream item (VHS-19–23) now has one artifact to target.
- **The enforcement (VHS-18)** turns the contract into a guard: `lint.py` validates `requires:` (R1, contract §3) and flags operative `mcp__*` tool calls (R2, contract §4), warn-only with a `--strict` promotion path. It runs **clean (0 ERRORs) against all four shipped skills** today; the 3 un-annotated skills emit a tracked `missing-requires` WARN, which is the documented promotion backlog.

Demonstrated end-state (from `VHS-18.test-output.txt`): the lint **fires** on a known-bad skill (`operative-tool-call` ERROR + `missing-requires` WARN, `--strict` exit 1) and runs **clean** on the shipped skills — exactly the brief's acceptance criterion.

## Process findings (the real spike value)

### 1. `CLAUDE.md` is gitignored — "reference from CLAUDE.md" specs can't ship that edit
Both briefs (and both specs, initially) said to link new docs "from `CLAUDE.md`." But `.gitignore:7` ignores `CLAUDE.md` (it holds user-specific absolute paths). A committed pointer there **cannot appear in a PR**. Both tickets pivoted the pointer to the tracked `README.md` "Cross-harness portability" section.
- **Sharper sub-finding:** this passed *all three* VHS-17 spec-cycle reviewers across 3 rounds. They verified `CLAUDE.md`'s *content* (the File-layout section exists) but never its *git tracking status*. The collision only surfaced at `ship-spec`, which operates on `origin/main` reality. **Recommendation:** teach `spec-reviewer-correctness` to check `git ls-files` / `git check-ignore` for any file a spec proposes to edit — "exists on disk" ≠ "shippable in a PR."

### 2. Cross-ticket dependencies collide with worktree-from-`main`
VHS-18 enforces a contract that lives only in VHS-17's **unmerged** branch. But `/ship-spec` Phase 1 hardcodes `git worktree add … origin/<default-branch>` — no base override. So a worktree cut for VHS-18 from `main` would lack the contract, the README anchor, and spec-cycle's `requires:` block, and the run would fail. This was caught by the VHS-18 reviewers (a P1) and resolved by **hand-cutting the worktree from the VHS-17 branch** (a stacked PR) — the documented out-of-band path. **Recommendation:** add a `--base <branch>` / stacked-PR option to `ship-spec` so cross-ticket dependency chains don't require a manual worktree. (Candidate follow-up ticket.)

### 3. The drift surfaced at `ship-spec`, not `spec-cycle` — and that's structurally expected
`spec-cycle` reviewers cold-read the local tree; they can't see what `origin/main` actually contains or what `git` ignores. Both #1 and #2 were *spec/reality* gaps invisible to a content-only review and only exposed when `ship-spec` materialized a worktree from the real remote base. The two-skill split (author vs. implement) is doing its job: the spec converges on *intent*, the implementation reconciles with *reality*. The fix isn't to merge the skills — it's to give the reviewers two cheap reality probes (git-tracking status; base-branch availability of cross-ticket deps).

### 4. The review loop earns its cost — it caught load-bearing bugs, not nits
Across 21 reviewer reports, the adversarial closure-manifest loop caught issues that would have shipped broken:
- **VHS-17:** the contract initially ignored that **Hermes already has a capability-declaration convention** (`metadata.hermes.requires_toolsets`) — without the reconciliation + mapping the reviewers forced in, VHS-20 would have inherited an unscoped translation problem. Also: the intent-rule had to be re-grounded on *operativeness* (not "names a neutral role") or VHS-18's lint would have fired on every shipped skill's "Tool-use notes" section.
- **VHS-18:** the lint's case-3 heading allowlist (`^Tool-use…`) **would not have matched the real `## Tool-use notes` ATX headings** (needs `#`-stripping) — a silent dead-code exemption; the frontmatter parser was undefined for CRLF/BOM/empty/unterminated inputs (Windows is the primary platform — CRLF would have mis-parsed every skill); and a round-3 edit left an **internal contradiction** (line 116 re-asserting a ship-spec capability the Precondition had just retracted, a P0) that a final round caught.

Convergence was monotonic once findings were addressed: VHS-17 5→3→0 blocking over 3 rounds; VHS-18 7→1→{1 P0}→0 over 4. No round-4 blank-slate rewrite was needed.

## On the `/loop` spike format itself

The 5-minute cron heartbeat worked as a **session-boundary crosser**: it paced `spec-cycle(17) → ship-spec(17) → spec-cycle(18) → ship-spec(18) → examine → synthesize` across separate turns, honoring `spec-cycle`'s HARD STOP (author and implement in different sessions, to avoid token-cap pressure) while still driving the whole chain autonomously. Each fire re-read state from disk (specs, reviews, task list) rather than trusting in-context memory — which is also what made the artifact examination rigorous. One manual interruption ("continue") was the only human touch needed mid-run.

Caveat: the loop never auto-merged a PR (correctly — merging is human-gated). That's why VHS-18 is *stacked* rather than built on a merged VHS-17, and why the done-criteria are "finished" (shipped + reviewed + green) rather than "merged."

## Recommended next actions (for the human)

1. **Merge order:** merge #17 → `main`, then re-target #18's base to `main` (GitHub keeps the diff clean since #18 was cut from #17's tip). Then run the manual load-check in VHS-17's spec (confirm `/spec-cycle` still loads with the `requires:` key).
2. **File two follow-ups** from findings #1 and #2: (a) `spec-reviewer-correctness` should verify git-tracking status of spec-edited files; (b) `ship-spec` should accept a `--base` for stacked/dependent specs.
3. **Lint promotion backlog:** annotate `ship-spec`, `spec-close`, `review-pr` with `requires:` blocks (clears the 3 `missing-requires` WARNs), then flip `lint.py` to a `--strict` pre-commit hook. This is VHS-18's documented promotion path.
4. **Optional cleanup:** VHS-17's spec text still says "CLAUDE.md" though its PR shipped README pointers — reconcile the spec wording at `spec-close` time so the archived record matches what shipped.
5. **Worktrees** `VHS-17-worktree` and `VHS-18-worktree` are kept alive for review fixes; remove after merge (`git worktree remove …`).

## Artifact index

- Specs: `docs/specs/TODO/VHS-17.spec.md`, `docs/specs/TODO/VHS-18.spec.md`
- Reviews: `docs/specs/TODO/VHS-17.reviews/round-{1..3}/` (9 files), `docs/specs/TODO/VHS-18.reviews/round-{1..4}/` (12 files)
- Test outputs: `docs/specs/TODO/VHS-17.test-output.txt`, `docs/specs/TODO/VHS-18.test-output.txt`
- Shipped deliverables (on the PR branches): `docs/portability-contract.md`, `lint.py`, `docs/authoring-portable-skills.md`, `tests/test_lint.py`, `tests/fixtures/**`
- PRs: #17 (VHS-17), #18 (VHS-18, stacked)
