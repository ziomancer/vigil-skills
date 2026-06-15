# Brief: Compound Engineering vs. vigil-skills — use, adapt, or watch?

**Date:** 2026-06-14
**Author:** Devin (drafted with Claude)
**Subject:** EveryInc/compound-engineering-plugin (MIT) evaluated against the vigil-skills spec lifecycle
**Verdict:** **Adapt.** Lift four mechanisms, fill two gaps, watch the rest. Do not install the plugin.

---

## TL;DR

Your instinct is right: Compound Engineering (CE) is the same loop you already built — plan → execute → review → capture, with worktree isolation and institutional memory feeding the next cycle. It is convergent evolution, not a different idea. The difference is who it is built for. CE is the *generic* version for any team adopting the loop cold; vigil-skills is the *specific* version wired into Plane, the wiki's evidence-triple discipline, and CodeRabbit.

So neither is strictly "better." CE wins on **knowledge-capture lifecycle** (it captures at the moment context is freshest, distinguishes bugs from durable guidance, dedups by updating in place, and has a refresh/prune skill) and on **having a lightweight planning path** that doesn't require a full brief. vigil-skills wins on **integration depth and auditability** — the exact things CE has no concept of. Installing CE wholesale would regress the state.md evidence model that is the entire point of your wiki (the DYN-17 antidote).

Recommendation: stay on vigil-skills as the spine and port the genuinely better mechanisms across.

---

## What Compound Engineering actually is (verified)

CE is an MIT-licensed Claude Code plugin from Every Inc. (Kieran Klaassen's team), distributed via a plugin marketplace and a Bun/TypeScript converter CLI that re-targets it to Codex, Cursor, Copilot, Gemini, Windsurf, OpenCode, Qwen, and others. The repo's own component README cites **42+ skills and 50+ agents** (the interview transcript's "36 skills / 51 agents" and a web index's "37 / 51" are stale — counts drift per release; treat any specific number as version-dependent).

Its spine is a six-stage loop:

```
Brainstorm → Plan → Work → Review → Compound → Repeat
    ↑
  Ideate (optional)
```

The stated philosophy: *each unit of work should make the next one easier* — "80% planning and review, 20% execution." The load-bearing skills are `ce-plan` (guardrails, not code choreography), `ce-work` (execution against guardrails, worktree-isolated subagents, test gates), `ce-code-review` (persona-agent review), and `ce-compound` (writes a structured learning doc to `docs/solutions/` that future `ce-plan`/`ce-work` runs read back as institutional memory). The rest is a long tail of language-specific reviewers (Rails/DHH, TypeScript, Swift, Python) and integrations (Slack, Figma, Proof, Gemini imagegen, Xcode, demo reels) that are noise for a TypeScript/Python stack.

---

## The core finding: convergent evolution

Feature-for-feature, the two systems map cleanly onto each other. This is why it "feels like the same thing."

| Concern | vigil-skills | Compound Engineering | Edge |
|---|---|---|---|
| Plan philosophy | Spec captures Goal / Scope / Design / Done-when / Out-of-scope (WHAT) | `ce-plan` "guardrails over choreography" (WHAT, not HOW) | Tie — same principle |
| Parallel review | `spec-cycle` dispatches 3 lenses (correctness / edge-cases / conventions) in one message, P0/P1 gate, ≤4 rounds | `ce-code-review` + `ce-plan` doc-review persona agents, confidence-gated | Tie — vigil's gate is tighter; CE has more personas |
| Worktree isolation | `ship-spec` cuts a sibling worktree; primary tree untouched | `ce-work` per-subagent worktrees; conflicts surface explicitly | Tie |
| Test gate | `ship-spec` loop, fix smallest blocking failure, ≤5 iters, output captured for PR | `ce-work` continuous tests + integration-coverage check before "done" | CE — richer "done" definition |
| PR automation | `ship-spec` → `gh pr create` with file table + test plan | `ce-commit-push-pr` value-first description + operational-validation section | CE — operational/rollback section |
| Review triage | `review-pr` is **CodeRabbit-thread-aware** (per-thread SHA replies, auto-approval polling) | Generic persona review; no external-bot integration | **vigil** |
| Knowledge capture | `spec-close` harvests wiki decisions/comprehension + state.md evidence triple, post-merge | `ce-compound` writes `docs/solutions/` at moment of solving | CE — see below |
| Memory feeds planning | `spec-reviewer-conventions` reads wiki decisions/state | `ce-learnings-researcher` reads `docs/solutions/` during `ce-plan` | Tie |
| Task tracker | Plane (states.json, state flips, PR comment) | None | **vigil** |
| Evidence/audit | state.md evidence triple + pre-commit lint + skepticism rule | None | **vigil** |

The pattern: where the two overlap, they tie or vigil's version is *more disciplined*. CE pulls ahead specifically on the **capture lifecycle** and on **having an entry point lighter than a full brief+spec**.

---

## Where CE is genuinely better (and liftable)

These are real improvements, not just different. Ranked by value to your workflow.

**1. Capture happens when context is fresh, not at close time.** This is the single biggest gap. `spec-close` harvests learnings *post-merge* — potentially days after the problem was actually solved, when the reasoning has faded. `ce-compound` auto-invokes on phrases like "that worked" / "it's fixed" and captures immediately. You are leaving your highest-fidelity learnings on the floor by deferring all capture to close.

**2. Anti-pattern capture ("What Didn't Work").** `ce-compound`'s bug-track structure records symptoms, *what didn't work*, the fix, and prevention. Your `decisions/` + `comprehension/` entries capture the decision and the comprehension but not the dead ends — and the dead ends are the most expensive part of an investigation to re-derive. CE also splits **bug track vs knowledge track** (incident fix vs durable guidance) with different structures; your wiki only really has the knowledge-track shape.

**3. Overlap-scored update-in-place.** `ce-compound` scores a new learning against existing docs on five dimensions (problem, root cause, solution, files, prevention) and *updates the existing doc* on high overlap instead of creating a near-duplicate. `spec-close` has only a grep-based fast-path dup check. The update-in-place rule is the more principled defense against the doc-drift the two-axis trust model already worries about.

**4. A refresh/prune skill.** `ce-compound-refresh` decides whether to keep, update, replace, or archive stale learnings. The wiki has *no* equivalent — it relies on "never delete, mark superseded" plus manual hygiene. A refresh skill maps directly onto the wiki's freshness axis and would mechanize maintenance you currently do by hand.

**5. Stable unit IDs (U-IDs).** `ce-plan` gives each unit of work a never-renumbered ID that flows into `ce-work`'s tasks, commit messages, and PR text, surviving reordering and splits. Your specs have "Done when" criteria but no stable per-unit handle. U-IDs would make multi-unit specs traceable from spec line → commit → PR.

**6. A lightweight planning path.** `ce-plan`/`ce-work` accept a bare prompt and triage by complexity (trivial → straight to code; small/medium → task list; large → recommend full planning). vigil-skills has no quick-fix lane — everything requires brief → `spec-cycle` → `ship-spec`. This is the most-felt structural gap in day-to-day use.

**7. Two smaller, real ideas:** an **operational-validation section** in every PR (what to monitor, rollback triggers) — valuable for a security-first posture; and **idempotent re-execution** in `ce-work` (skip already-satisfied units when resuming) — `ship-spec` re-implements from spec with no such check.

---

## Where vigil-skills is better (do not regress)

Adopting CE wholesale would *cost* you the following, all of which CE has no concept of:

- **Plane integration** — states.json, automatic state flips to review, PR comments on tickets.
- **The evidence-triple model** — state.md flips requiring (Plane-ID, date, commit-hash) + a verification grep, enforced by a pre-commit hook. This is the codified DYN-17 antidote; `ce-compound` writes flat `docs/solutions/` files with no temporal anchor and no enforcement.
- **CodeRabbit-aware PR triage** — `review-pr`'s per-thread replies and auto-approval polling have no CE counterpart.
- **Spec-vs-shipped reconciliation** — `spec-close` diffs the spec against the merged code and writes an audit report. `ce-compound` captures learnings but never reconciles intent against outcome.
- **Skepticism discipline** — "don't treat user framing as truth; produce a load-bearing grep." This is wired into your reviewers and hooks; CE has nothing comparable and its `/lfg` "full autonomous" + auto-invoke ethos runs *counter* to a human-gated, security-first posture. (Note the interview's "never read the plan" habit is the precise opposite of your `spec-cycle` drift-check HARD STOP — a feature you should keep.)

---

## Recommendation

**Adapt, tiered.** Keep vigil-skills as the spine. Port mechanisms, not the plugin.

*Tier 1 — port into the wiki/spec flow (high value, low conflict):*
- Add an **early-capture** trigger so learnings are written at solve-time, not deferred entirely to `spec-close`. Fold the captured note into `spec-close`'s harvest so nothing double-writes.
- Add **"What Didn't Work" / anti-pattern** sections to `comprehension/` entries.
- Replace `spec-close`'s grep dup-check with **overlap-scored update-in-place** for decisions/comprehension.
- Build a **wiki-refresh skill** (the `ce-compound-refresh` analog) tied to the freshness axis.

*Tier 2 — fill the structural gaps:*
- Add **stable U-IDs** to the spec template and thread them through `ship-spec` commits/PRs.
- Add a **lightweight plan/quick-fix lane** for changes that don't merit a full brief+spec.
- Add an **operational-validation section** to `ship-spec` PR bodies and **idempotent re-execution** on resume.

*Tier 3 — watch, don't lift yet:*
- `ce-ideate` / `ce-brainstorm` upstream ideation — you author briefs deliberately; lower priority.
- A `ce-debug`-style structured root-cause workflow for the `ship-spec` test-gate halt case.
- The multi-harness converter CLI — notable only because your MCP server already serves OpenClaw/Calvin; revisit if cross-harness skill parity ever becomes a goal.

*Reject:* installing the plugin; the language-specific reviewers (Rails/DHH/Swift); and the Slack/Figma/Proof/imagegen/Xcode/demo-reel long tail.

---

## Decisions carried forward

1. **vigil-skills remains the spine; CE is a parts donor, not a replacement.** Convergent design means the loops are interchangeable in shape but not in integration — and the integration is the value.
2. **Do not install or depend on the plugin.** It would introduce a parallel `docs/solutions/` knowledge store with no evidence model, competing with the wiki and weakening the two-axis trust contract. MIT license means we may read and re-implement freely.
3. **The security-first, human-gated posture is non-negotiable.** Any lifted mechanism must preserve the drift-check HARD STOP and the state.md evidence enforcement; auto-invoke capture is acceptable, auto-*merge*/autonomous execution is not.
4. **Earliest-context capture is the most valuable single idea to adopt** and should be sequenced first.

## Done when

- This brief is reviewed and the Tier 1 lifts are each filed as VHS tickets in Plane with acceptance criteria.
- A spike has confirmed the early-capture trigger can coexist with `spec-close` harvest without double-writing wiki entries.
- The overlap-scoring dedup rule is specified against the existing `decisions/` + `comprehension/` schema (5-dimension score → update-vs-create threshold).
- A go/no-go is recorded for each Tier 2 item (U-IDs, quick-fix lane, operational-validation section, idempotency).
- Tier 3 items are logged as watch-items with a revisit trigger, not actioned.

## Out of scope

- Installing, vendoring, or running the compound-engineering plugin in any harness.
- Adopting CE's `docs/solutions/` directory structure (conflicts with the wiki as single knowledge layer).
- Language-specific reviewer agents and the Slack/Figma/Proof/imagegen/Xcode/demo-reel skills.
- The multi-harness converter CLI and any cross-tool (Codex/Cursor/OpenCode) skill-parity work.
- `ce-ideate`/`ce-brainstorm` upstream ideation (deferred to Tier 3 watch).
- Any change to the Plane/wiki evidence-triple model or pre-commit lint contract.

---

## Sources

- [EveryInc/compound-engineering-plugin (repo)](https://github.com/EveryInc/compound-engineering-plugin)
- [Plugin component README — full skill/agent list + MIT license](https://github.com/EveryInc/compound-engineering-plugin/blob/main/plugins/compound-engineering/README.md)
- [Marketplace README — workflow + philosophy](https://github.com/EveryInc/compound-engineering-plugin/blob/main/README.md)
- [ce-plan skill doc](https://github.com/EveryInc/compound-engineering-plugin/blob/main/docs/skills/ce-plan.md)
- [ce-work skill doc](https://github.com/EveryInc/compound-engineering-plugin/blob/main/docs/skills/ce-work.md)
- [ce-compound skill doc](https://github.com/EveryInc/compound-engineering-plugin/blob/main/docs/skills/ce-compound.md)
- [Compound engineering: how Every codes with agents](https://every.to/chain-of-thought/compound-engineering-how-every-codes-with-agents)
- vigil-skills repo: `skills/{spec-cycle,ship-spec,spec-close,review-pr}/SKILL.md`, `agents/spec-reviewer-*.md` (read 2026-06-14)
