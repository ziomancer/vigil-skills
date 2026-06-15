# VHS-18 — Cross-harness: harness-agnostic authoring guidelines + lint

**Spec for:** docs/specs/TODO/VHS-18.brief.md · **Plane:** VHS-18 (child of VHS-16, depends on VHS-17)
**Ships:** one guidelines doc, one stdlib lint, its tests + fixtures, one README pointer.
**Status:** spec authoring (spec-cycle), round 2

## Goal

Turn the VHS-17 portability contract into day-to-day authoring discipline plus an automated guard, so skills stay portable **by construction** rather than by after-the-fact audit. Two deliverables: a **guidelines doc** (what to write / what to avoid) and a **stdlib-only lint** (`lint.py`) that mechanically flags the violations the contract defines — harness-specific tool calls used as operative instructions, and malformed/absent `requires:` capability declarations. The lint ships **warn-only** first, with a documented path to a blocking gate, and runs clean (zero errors) against the four shipped skills.

## Precondition & sequencing (load-bearing)

VHS-18 depends on **VHS-17**, whose work is in **PR #17 (branch `feat/vhs-17-portability-contract`), currently open, not merged to `main`.** This matters because `/ship-spec` cuts its worktree from the default branch (`main`), and on `main` **none** of VHS-18's anchors exist yet: `docs/portability-contract.md` is absent, `README.md` has no "Cross-harness portability" section, and `skills/spec-cycle/SKILL.md` has no `requires:` block. All three live only on the VHS-17 branch (commit on `feat/vhs-17-portability-contract`).

**Therefore the worktree base for VHS-18 implementation must contain the VHS-17 commit** so the contract, the README section, and spec-cycle's `requires:` block are present. Note that `/ship-spec` **always** bases its worktree on `origin/<default-branch>` (`skills/ship-spec/SKILL.md` Phase 1 hardcodes `git worktree add … origin/<default-branch>`; it has no base-branch override). So the ship-spec-executable path is: **merge VHS-17 (#17) to `main` first, then run `/ship-spec` for VHS-18** (it will then cut from `main` with the artifacts present). The alternative — a **manual, out-of-band** worktree cut from `feat/vhs-17-portability-contract` (stacked PR) — is available to a maintainer but is *not* something `/ship-spec` itself performs; if used, the implementer creates the worktree by hand and runs the implementation + test steps there. This is the concrete form of the brief's loop note ("gate VHS-18's spec-cycle on VHS-17 being green first"): green is sufficient to *author* this spec; *implementing* it requires the VHS-17 artifacts on the worktree base, which today means VHS-17 merged (or a manual stacked worktree). A follow-up to teach ship-spec a `--base`/stacked-branch option is noted as a spike finding, not built here.

Note on the README anchor: VHS-17's *spec text* said to add pointers to `CLAUDE.md`, but its *shipped PR* put them in a new `README.md` "Cross-harness portability" section instead — because `CLAUDE.md` is gitignored (`.gitignore:7`; carries user-specific paths). VHS-18 inherits that corrected target (D5). To keep this spec's tests independent of merge timing, the valid-`requires:` test path uses a dedicated fixture rather than spec-cycle's annotation (see Design / tests).

## Scope

**New files**
- `lint.py` — repo-root, stdlib-only portability lint (mirrors `sync.py` as a top-level dev script). Importable API + CLI.
- `docs/authoring-portable-skills.md` — the guidelines doc.
- `tests/test_lint.py` — stdlib `unittest`: known-bad fixture fires; good fixture validates; four shipped skills clean.
- `tests/fixtures/` — fixtures (see Design): `bad-skill/`, `good-skill/`, and malformed-input fixtures.

**Edited files**
- `README.md` — add a pointer to `docs/authoring-portable-skills.md` in the "Cross-harness portability" section VHS-17's branch introduced (create the section if, at implementation time, it is somehow absent — see D5).

**Left alone**
- `sync.py` — the lint is a separate concern; `sync.py` stays a pure file-mirror (CLAUDE.md convention). `lint.py` is not synced to `~/.claude/` (only `skills/`/`agents/` mirror).
- The four shipped skills — they already satisfy the error-level rules (VHS-17 §4 analysis). The three without a `requires:` block get a warn-level advisory only (D4), not an edit.
- `CLAUDE.md` — gitignored (D5); not editable in a PR.

## Decisions

### D1 — Hook point: a standalone stdlib `lint.py` at repo root (not a sync.py subcommand, not new CI)
The brief is explicit that **no CI path exists** (no `.github/workflows/`, `sync.py` has no test/lint hook, only CodeRabbit). Among the brief's candidate hook points this spec chooses a **standalone `lint.py`** (`python lint.py [paths…]`):
- **Mirrors the repo's shape** — `sync.py` is already a top-level, stdlib-only script; `lint.py` is its sibling. No new infrastructure.
- **Separation of concerns over a `sync.py` subcommand** — folding validation into the file-mirror violates "sync.py mirrors only." Rejected.
- **No new CI in v1** — `.github/workflows/` is net-new infra the repo has avoided; deferred to the promotion path.
- **Optional pre-commit hook is the promotion vehicle**, documented (not shipped): a hook calling `python lint.py --strict`, mirroring the wiki's `install-hooks` precedent in *shape* only (stdlib Python, not the wiki's Node toolchain).

### D2 — Two severity levels: ERROR (blocking-eligible) and WARN (advisory)
- **ERROR** — load-bearing violations: (a) a case-1 operative bare harness-tool call (contract §4); (b) a malformed `requires:` block (contract §3 violations: nested mapping incl. inline `{…}`, unknown key, out-of-vocabulary token, quoted scalar, trailing empty element, value with a stray `:`, tab-indented child).
- **WARN** — advisories that don't block: a **missing** `requires:` block (incl. a frontmatter-less or empty `SKILL.md`).
"Runs clean" = **zero ERRORs**. WARNs may be present.

### D3 — Advisory-then-blocking: warn-only default; `--strict` is the promotion switch
`python lint.py` (default) **always exits 0** — prints findings but never fails. `python lint.py --strict` exits non-zero iff **any ERROR** is present (WARNs never affect the exit code). For observability, both modes print a summary line to **stderr**: `lint: <E> error(s), <W> warning(s)` — so an ERROR in default mode has a greppable signal even though exit is 0. The guidelines doc instructs automation to use `--strict` (whose exit code is the contract). Promotion to a hard gate = installing the pre-commit hook to call `--strict`, once the missing-`requires:` backlog is cleared (D4).

### D4 — Missing-`requires:` advisories are tracked, not a blocking backlog
Three shipped skills (`ship-spec`, `spec-close`, `review-pr`) lack a `requires:` block (VHS-17 annotated only `spec-cycle`). Under D2 these are WARNs, not ERRORs, so the lint "runs clean" (zero ERRORs) against all four. Annotating the remaining three is follow-up work (VHS-17 fenced annotation to one skill); it is recorded as the tracked promotion-path backlog item in the guidelines doc (not a silent backlog). The done-when "violation backlog is zero or fully ticketed" is satisfied: zero ERRORs; missing-`requires:` is the documented, tracked promotion gate.

### D5 — Guidelines doc is linked from README.md, not CLAUDE.md (CLAUDE.md is gitignored)
`CLAUDE.md` is gitignored (`.gitignore:7`; user-specific absolute paths) — a committed link there can't ship in a PR. VHS-17 hit this same collision: although VHS-17's *spec text* named CLAUDE.md, its *shipped PR* added the pointer to a new `README.md` "Cross-harness portability" section instead. VHS-18 follows that corrected, tracked target: the guidelines link goes in the **same README section**. To stay idempotent and avoid a duplicate heading, the implementation does a deterministic check — grep `README.md` for an existing `## Cross-harness portability` heading: **if present** (the expected case once VHS-17 is on the worktree base), append the guidelines bullet inside it; **only if grep finds none** (an unexpected base) create the section with both the contract and guidelines pointers. This satisfies the brief's intent ("discoverable next to the contract reference") in a shippable way. Maintainers who keep a local `CLAUDE.md` may mirror the pointers there.

### D6 — Harness-tool detection keys on `mcp__*` tokens; three detection gaps are documented v1 limitations
The unambiguous, low-false-positive harness-specific signal is an `mcp__<server>__<tool>` identifier (and backticked tool-call spans). Bare Claude-Code tool names (`Read`, `Edit`, `Bash`) are ordinary words; flagging them would be noisy and is unnecessary (the contract classifies them as case-3 notes content). So v1 ERROR detection keys on `mcp__\w+` tokens. Three gaps are **explicitly documented** (in `lint.py` and the guidelines doc) as v1 limitations the qualitative CodeRabbit review backstops — the lint complements, does not replace, that review:
1. **Bare-name detection deferred** — non-`mcp__` tool names are not flagged.
2. **Operative-imperative-under-a-notes-heading** — contract §4 says an operative imperative under a "Tool-use notes" heading is still case 1, but the v1 lint applies the heading presumption as a flat case-3 exemption and does **not** detect a laundered operative call there. Documented, not silently missed (so the lint does not over-claim §4 enforcement).
3. **Case-2 window adjacency** — the case-2 exemption is window-scoped to ±1 non-blank line; an operative bare `mcp__*` call placed directly adjacent to an *unrelated* tagged sentence could be wrongly exempted. The ±1 window is the deliberate tradeoff that eliminates false-positives on tags wrapping onto the line above/below the token.

This keeps the lint deterministic and false-positive-free against the shipped skills, complementing CodeRabbit's qualitative pass.

## Design

### `lint.py` — robust reader, rules, structure

Stdlib-only. Public API (imported by the test): `lint_path(path) -> list[Finding]` for one `SKILL.md`; `lint_paths(paths) -> list[Finding]` aggregating (`lint_paths([])` returns `[]` — pure aggregation, **no** implicit globbing). `Finding = (severity, rule, file, line, message)`. CLI `python lint.py [paths…] [--strict]`: with no paths, the **CLI layer** (`main()`) globs `skills/*/SKILL.md` relative to the repo root (`Path(__file__).resolve().parent`) — the same single-level glob the test uses, matching the repo's flat one-dir-per-skill layout (a nested `skills/a/b/SKILL.md` is not a supported layout in v1); prints findings grouped by file; prints the stderr summary (D3); if `main()` resolves an empty path set it prints a notice (linted nothing). `lint_path` is **total** — it never raises on any file content; unreadable/empty/malformed files yield deterministic findings.

**Frontmatter reader (shared by R1/R2).** Read bytes, strip a leading UTF-8 BOM, decode UTF-8, split with `str.splitlines()` (handles LF/CRLF/CR uniformly). The frontmatter block is delimited by an opening `---` as the **first non-empty line** and the next `---`. If there is no opening `---`, or no closing `---`, treat the file as **having no frontmatter**: emit `missing-requires` WARN and run R2 over the whole file; never raise. An empty (0-byte) file → `missing-requires` WARN, no body to scan.

**Rule R1 — capability declaration (`requires:`)** (contract §3). Within the frontmatter:
- No `requires:` key → **WARN** `missing-requires` (D4).
- `requires:` with an **inline value** on the same line: `[]` or `{}` → present-but-empty (clean, no keys); an inline mapping `{…}` with content → **ERROR** `requires-malformed` (nested mapping per §3); any other inline scalar → **ERROR** `requires-malformed`.
- `requires:` as a block key: collect the contiguous **more-indented** child lines, where "more-indented" = leading-whitespace prefix strictly longer than the `requires:` line's; blank lines and comment-only lines (empty after the comment strip) interleaved in the block are **skipped** — not terminators, not violations. A **tab** anywhere in a child line's leading whitespace → **ERROR** `requires-malformed` (YAML forbids tab indentation; the lint additionally rejects it for determinism — a v1 lint choice slightly stricter than contract §3's written letter, noted in D6/guidelines). For each child line apply the §3 lexical rules: strip a whitespace-preceded `#` comment; split on the first `:` (a `:` inside a flow-sequence value is not a separator → out-of-vocabulary → ERROR); validate keys ∈ `{shell, filesystem, network, subagents, services}` (unknown → ERROR `requires-unknown-key`); `shell`/`network`/`subagents` are booleans; `filesystem` is a flow sequence ⊆ `{read, write}` (**no `?` permitted** — `[read?]` is out-of-vocabulary → ERROR); `services` is a flow sequence of `{issue-tracker, shared-memory, code-review-bot, vcs-host}` each with an optional single trailing `?`. Bracket-strip, comma-split, per-element trim, discard empty elements; quoted scalars, trailing empty elements (`[read, write,]`), nested mappings, out-of-vocabulary tokens → ERROR `requires-malformed` (sub-reason in the message).

**Rule R2 — intent-over-implementation** (contract §4). Walk the body, tracking (a) the current Markdown heading — **normalized** by stripping a leading `#{1,6}` and surrounding whitespace before matching — and (b) whether the line is inside a fenced code block. Fence detection: a fence line is one whose **leading-whitespace-stripped** content begins with a run of ≥3 backticks (```` ``` ````) **or** ≥3 tildes (`~~~`); any info string (e.g. ` ```bash `) is part of the opening fence. The stripping matters because the shipped skills nest indented fences inside lists (e.g. 6/8/10-space indents). v1 toggles a single in-code boolean on each fence line (open/close symmetric; no CommonMark close-must-match enforcement — adequate because the shipped skills are well-balanced). For each `mcp__\w+` token (or backticked tool-call span):
- **case 2 (allowed)** — a **window** consisting of the token's physical line plus the immediately preceding and following non-blank lines contains an "or the equivalent" phrase (the contract §4 tag; the example marker `e.g.`/`for example` is *not required* — keying on the tag matches §4's actual definition). Case-2 satisfaction is window-scoped: every `mcp__*` token on a line whose window has the tag is exempt (covers multiple tokens sharing one tagged sentence, and tags that wrap onto the line above or below the token).
- **case 3 (allowed)** — the occurrence is inside a fenced code block, **or** under a normalized heading matching `^(tool-use (notes|rules)|tools available)$` (case-insensitive). (v1 limitation per D6: an operative imperative laundered under such a heading is not separately detected.)
- **otherwise → ERROR** `operative-tool-call`.

The vocabulary and case rules are sourced from `docs/portability-contract.md` §3/§4; `lint.py` hardcodes the v1 schema and notes that a future contract-vocabulary revision updates the lint in lockstep.

### `docs/authoring-portable-skills.md` — guidelines

Restates the contract as authoring discipline: **lead with intent**; **declare capabilities** (always add a `requires:` block — §3 schema + copyable example); **never name a harness's tools as the operative instruction** — use the "(e.g. `<tool>` in Claude Code, or the equivalent in your host)" form, and keep bare tool inventories in a non-operative "Tool-use notes" section; **don't assume one harness's affordances**. Sections: "Running the lint" (`python lint.py`, `--strict`, the stderr summary), the warn-only→blocking **promotion path** (clear the missing-`requires:` backlog by annotating the remaining three skills → install the pre-commit hook calling `--strict`), and the **documented v1 limitations** (D6: `mcp__*`-only detection; operative-under-notes not caught — both backstopped by CodeRabbit). Cross-links `docs/portability-contract.md`.

### `tests/` — fixtures + test

Fixtures under `tests/fixtures/`:
- `bad-skill/SKILL.md` — frontmatter with `name`/`description`, **no `requires:`** (→ WARN `missing-requires`), and a body line ``First, call `mcp__plane__retrieve_work_item` to fetch the ticket.`` outside any example/notes construct (→ ERROR `operative-tool-call`).
- `good-skill/SKILL.md` — a well-formed `requires:` block (exercises R1's accept path **independently of spec-cycle's annotation / merge order**) and a body whose only `mcp__*` mention is a case-2 tagged example (zero ERRORs).
- Malformed-input fixtures (each asserting a deterministic finding, **no exception**): `empty.md` (0-byte), `no-frontmatter.md`, `unterminated-frontmatter.md`, `crlf-skill/SKILL.md` (CRLF endings), `bom-skill/SKILL.md` (UTF-8 BOM), `inline-requires-mapping.md` (`requires: {shell: true}` → ERROR), `tab-indent.md` (tab-indented child → ERROR), `notes-bare-name/SKILL.md` (a bare `mcp__*` inventory bullet under `## Tool-use notes` with **no** case-2 markers → zero ERRORs, proving case-3 heading normalization works), `split-marker/SKILL.md` (case-2 tag on the line after the token → zero ERRORs, proving the window), `indented-fence/SKILL.md` (an `mcp__*` example inside a 6-space-indented fenced block → zero ERRORs, proving leading-whitespace-tolerant fence detection), `comment-in-requires.md` (a comment-only line interleaved in a valid `requires:` block → zero ERRORs, proving comment/blank lines are skipped).

`tests/test_lint.py` — stdlib `unittest`, with `REPO_ROOT = Path(__file__).resolve().parents[1]` inserted on `sys.path` so `import lint` and all fixture/skill paths resolve from `__file__`, never cwd. Cases:
1. **Negative:** `lint_path(bad-skill)` yields ≥1 ERROR `operative-tool-call` **and** a WARN `missing-requires`.
2. **Positive (fixture):** `lint_path(good-skill)` yields zero ERRORs and no `missing-requires` (exercises the valid-`requires:` path deterministically).
3. **Shipped skills clean:** glob `skills/*/SKILL.md` from `REPO_ROOT`; **assert exactly 4 skills were found**, with a failure message naming the cause ("expected the 4 currently-shipped skills; found N — if you added a skill, bump this count after confirming it lints clean"). This is a deliberate inventory tripwire (not a clean-run check) — it fixes the round-1 vacuous-pass hole and will intentionally fail when skill #5 lands. Then assert each yields zero ERRORs.
4. **Robustness:** each malformed-input fixture yields its expected deterministic finding and raises no exception; `notes-bare-name`, `split-marker`, `indented-fence`, and `comment-in-requires` yield zero ERRORs.

Run as `python tests/test_lint.py` (a `unittest.main()` guard makes it directly runnable). Each test method carries a `# Regression for VHS-18:` comment naming the rule it guards.

## Test plan

- Add `tests/test_lint.py` (the repo's first test suite) with the four case groups above.
- The captured output shows the lint **firing** on the bad fixture and **running clean** on the good fixture + the four shipped skills (brief done-when), plus the robustness fixtures passing.
- Regression markers tie each method to the rule/edge it guards.

## Test command

```bash
python tests/test_lint.py
```

(Stdlib `unittest`; the test file inserts `REPO_ROOT` on `sys.path` and calls `unittest.main()`. Pin the interpreter to the project's `python` if multiple are on PATH. ship-spec runs this for its Phase 3 gate — all tests passing is the pass condition; the captured output is the brief's "both demonstrated in test output" artifact. Reminder per Precondition: run `/ship-spec` only after VHS-17 (#17) is merged to `main` (ship-spec always bases its worktree on `origin/<default-branch>`); otherwise a maintainer hand-cuts the worktree from `feat/vhs-17-portability-contract` out-of-band. Either way the contract + README section + spec-cycle `requires:` block must be present on the worktree base.)

## Done when

1. `docs/authoring-portable-skills.md` is merged and linked from `README.md` in the "Cross-harness portability" section (the shippable substitute for the gitignored CLAUDE.md — D5; the section is present on the stacked VHS-17 branch, or created by this spec if absent). — brief "Done when" #1
2. `lint.py` runs against all four current skills with a zero-**ERROR** backlog; the missing-`requires:` WARNs are recorded as the tracked promotion-path backlog item in the guidelines doc (not a silent backlog). — brief #2
3. The hook point is a concrete stdlib-only `lint.py`, invokable as `python lint.py` / `--strict`; it ships warn-only (default exit 0, stderr summary) with the promotion path to blocking and an optional pre-commit hook documented. — brief #3
4. The known-bad fixture (operative `mcp__*` call + missing `requires:`) makes the lint fire, and the good fixture + four shipped skills make it pass (zero ERRORs) — both demonstrated in the captured test output. — brief #4

## Out of scope

- The conversion engine / per-harness adapter (VHS-19 / VHS-20).
- Defining the portability rules themselves (VHS-17 — this spec only enforces them).
- The behavioral conformance suite (VHS-21).
- Annotating the three un-annotated skills with `requires:` blocks (tracked follow-up; D4) and broader bare-tool-name detection / operative-under-notes detection (deferred v1 limitations; D6).
- Shipping a pre-commit hook installer or a CI workflow (promotion path documented, not built — D1/D3).
- Any change to the Plane/wiki evidence-triple model.

## Deferred (P2+)

- (round 1, correctness F-7) Done-when #2 no longer depends on an external follow-up ticket existing — the backlog item is documented in the guidelines doc's promotion path instead.

## Post-green polish

- (round 4, edge-cases F-1, P4) Fixed a stale count in D6: heading + lead-in said "two detection gaps" but the list enumerates three (bare-name, operative-under-notes, case-2 window adjacency) — corrected to "three." Editorial only; no behavior or decision change.

