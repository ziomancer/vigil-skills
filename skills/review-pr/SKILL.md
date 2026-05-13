---
name: review-pr
description: Triage and fix CodeRabbit review comments on a PR. Verifies findings against current code, fixes real issues, pushes, posts per-thread commit-hash replies, waits for CodeRabbit's incremental re-review, and polls for auto-approval.
user_invocable: true
---

# /review-pr — CodeRabbit review round handler

Process one round of CodeRabbit review findings on a GitHub PR. Triage by severity, fix real issues, push, resolve threads.

**Shell note:** All `gh api`, `git`, and `gh pr` commands use bash syntax (single quotes, `$()` expansion). Use the **Bash tool** for these commands, not PowerShell.

## Input parsing

Parse the argument into a PR number:

- `/review-pr 8` → PR #8
- `/review-pr https://github.com/.../pull/8` → extract #8 from URL
- `/review-pr` (no arg) → detect from current branch: `gh pr view --json number --jq .number`

## Step 1: Detect repo, resolve working directory, and check state

```bash
# Get owner/repo
gh repo view --json owner,name --jq '.owner.login + "/" + .name'

# Resolve the PR's head branch and find the right working directory
PR_BRANCH=$(gh pr view <N> --json headRefName --jq .headRefName)
# Exact-match the branch against worktree list (porcelain column: path + HEAD + branch)
WORKTREE_PATH=$(git worktree list --porcelain | awk -v b="$PR_BRANCH" '
  /^worktree /{ wt=$2 }
  /^branch /{ if ($2 == "refs/heads/" b) print wt }
')
```

If `WORKTREE_PATH` is non-empty, use it as the working directory for all subsequent steps (file reads, edits, git operations). If the branch is the current branch in the primary tree (`git branch --show-current` matches `$PR_BRANCH`), use the primary tree. If the branch isn't checked out anywhere, check it out before proceeding.

```bash
# Get the PR's diff scope (file list) — helps contextualize findings and triage outside-diff comments
gh pr diff <N> --name-only

# Check if CodeRabbit review is still pending
gh pr checks <N>
```

If CodeRabbit shows "Review in progress" or "pending", tell the user to wait and stop.

### 1b. Check CodeRabbit config

Read `.coderabbit.yaml` from the repo root. Confirm `reviews.request_changes_workflow: true`. This is what enables CodeRabbit to auto-approve after all threads are resolved and pre-merge checks pass.

If the file is missing or `request_changes_workflow` is not `true`, warn:
```text
⚠ request_changes_workflow is not enabled in .coderabbit.yaml.
CodeRabbit will not auto-approve after thread resolution.
Thread resolution will still work but the review verdict must be changed manually.
```

Proceed regardless — the skill still works for thread cleanup without auto-approval.

## Step 2: Fetch CodeRabbit review comments

```bash
# Get all reviews — find the latest coderabbitai[bot] review (body needed for infra-error check below)
gh api repos/{owner}/{repo}/pulls/<N>/reviews \
  --jq '[.[] | select(.user.login == "coderabbitai[bot]")] | sort_by(.submitted_at) | last | {id, state, submitted_at, body}'

# Get inline comments from CodeRabbit
gh api repos/{owner}/{repo}/pulls/<N>/comments \
  --jq '[.[] | select(.user.login == "coderabbitai[bot]")]'
```

If the latest review body contains infrastructure errors — look for `"Failed to clone"`, `"🔥 Problems"`, or `"Please run the @coderabbitai full review"` — then post `@coderabbitai full review` as a PR comment to re-trigger the review, report "CodeRabbit hit an infrastructure error — re-triggered full review", and stop.

If the latest review state is `APPROVED` and there are no unresolved comments, report "Nothing to review — PR is approved" and stop.

If there are no CodeRabbit reviews at all, report "No CodeRabbit reviews found" and stop.

## Step 3: Triage each finding

CodeRabbit tags findings with severity labels. Parse them from the comment body:

| Severity | Pattern in body | Default action |
|----------|----------------|----------------|
| Critical | `_🔴 Critical_` | **Always fix** |
| Major | `_🟠 Major_` | Fix unless already addressed in current code |
| Minor | `_🟡 Minor_` | Fix if trivial and correct; skip if over-engineering |
| Nitpick | `🧹 Nitpick` (appears in review body summary, not inline) | Skip unless trivially correct |

For EACH finding:

1. **Parse** the severity label and the file path + line number from the comment
2. **Read** the actual file at the referenced line using the Read tool
3. **Verify** whether the finding applies to the current code (it may already be fixed in a later commit)
4. **Categorize**:
   - `fix` — genuinely wrong code, security issue, real bug, applies to current code
   - `duplicate` — same finding repeated from a prior review round
   - `skip` — over-engineering suggestion, style preference, already fixed, or the reviewer misread the code
   - `already-fixed` — finding was valid but a subsequent commit already addressed it

Record the categorization and reason for each finding.

### Important triage rules

- **Outside-diff comments**: findings on code not changed by this PR. Fix only if genuinely wrong.
- **Duplicate comments**: CodeRabbit marks these in a "Duplicate comments" section in the review body. Always skip.
- **Nitpick sections**: CodeRabbit groups these in a "Nitpick comments" section in the review body. Default to skip.
- When in doubt about whether to fix, **read the code first** — never skip without verifying.

## Step 4: Fix and test

For all findings categorized as `fix`:

1. Apply the code fix using Edit tool
2. After all fixes are applied, run the project's test suite. Use the same test-command resolution as `/ship-spec` Phase 0 step 4: spec `## Test command` first, then `CLAUDE.md` "Build & Run" section. If no test command found: warn but proceed — review-pr is fixing review comments, not authoring new features, so skipping tests is less critical than in ship-spec
3. If tests fail, fix the test failure before continuing
4. If no findings were categorized as `fix`, skip this step entirely

## Step 5: Commit and push

Only if fixes were made:

1. Stage only the changed files by name (never use `git add -A` or `git add .`)
2. Write a descriptive commit message summarizing what was fixed and what was skipped:
   ```
   fix: <summary of fixes>

   Fixed: <list of what was fixed>
   Skipped: <list of what was skipped with brief reasons>

   Co-Authored-By: Claude <noreply@anthropic.com>
   ```
3. Push to the PR branch
4. Capture the resolving commit SHA and post per-thread replies:
   ```bash
   HEAD_SHORT_SHA=$(git rev-parse --short HEAD)
   ```
   For each fix-categorized finding from this round, post an inline reply on the originating review-comment thread (see Step 6c for the reply mechanism and error handling). Then continue to Step 6a.

**Note:** Pushing triggers CodeRabbit's auto-incremental review of the new commit. Step 6 waits for it before attempting thread resolution.

## Step 6: Wait for re-review, verify thread resolution, poll for approval

Per-thread `Resolved in <sha>` replies on fix-categorized finding threads are the primary closure mechanism. Threads for non-fix findings (skip/duplicate/already-fixed) are left open for CodeRabbit and the user to handle naturally. Auto-approval (`APPROVED` verdict) requires all threads resolved AND `request_changes_workflow: true` AND pre-merge checks passing. The skill never posts `@coderabbitai resolve` — if threads don't auto-resolve on hash reply, the report offers the manual command.

**Fast-path predicate (evaluated once, after Step 5):**

```
FAST_PATH = (round1_finding_count <= 2
             AND every round-1 finding is categorized as "fix"
             AND step 5 pushed successfully)
```

If `FAST_PATH` is true, skip Steps 6a and 6b entirely — proceed directly to Step 6d. Log: `Fast path triggered — skipping incremental review wait (≤2 fix-only findings)`. The rationale: on trivial PRs (1–2 fix-only findings), CodeRabbit's incremental review of the resulting small fix almost never surfaces new actionable findings. The 30s–5min wait in 6a has near-zero expected value. If CodeRabbit does post new findings, re-running `/review-pr` on the same PR picks them up naturally.

### 6a. Wait for CodeRabbit's incremental review (only if fixes were pushed)

If no fixes were pushed (all skips/duplicates/already-fixed), skip to 6d.

**If FAST_PATH is true**, set `REVIEW_SIGNAL=fast-path` and skip to 6d. (Per-thread replies were already posted in Step 5.)

**Otherwise, capture push time and check for pre-existing approval:**

```bash
HEAD_SHA=$(git rev-parse HEAD)
PUSH_TIME=$(gh api repos/<OWNER>/<REPO>/commits/$HEAD_SHA --jq '.commit.committer.date')

gh api repos/<OWNER>/<REPO>/pulls/<N>/reviews \
  --jq '[.[] | select(.user.login == "coderabbitai[bot]")] | sort_by(.submitted_at) | last | {state, submitted_at}'
```

`PUSH_TIME` is conversational state — the LLM captures its value from the Bash output and substitutes it literally into subsequent Bash commands. Individual Bash tool calls do not share shell variables.

If the latest verdict's `state` is `APPROVED` **and its `submitted_at` is after `PUSH_TIME`**, skip 6a/6b and go straight to 6e. Set `REVIEW_SIGNAL=pre-existing-approval`. (This skips 6d — the existing behavior, preserved from the current SKILL.md; `APPROVED` implies threads are resolved or will be imminently.) A pre-push `APPROVED` verdict must not short-circuit: the incoming incremental review may flip it back to `CHANGES_REQUESTED`.

**Otherwise, gate on CodeRabbit's CI check completing:**

```bash
gh pr checks <N> --json name,state \
  --jq '[.[] | select(.name | test("coderabbit"; "i")) | .state] | if length == 0 then "NONE" elif any(. == "PENDING") then "PENDING" elif all(. == "SUCCESS") then "SUCCESS" else "FAILURE" end'
```

The jq aggregation handles four cases: if no CodeRabbit-named checks exist, return `NONE` (triggers the "no check found" fallback); if any is `PENDING`, treat the overall state as `PENDING`; if all are `SUCCESS`, treat as `SUCCESS`; otherwise `FAILURE` (catches `FAILURE`, `CANCELLED`, `ERROR`, `STALE`, and any other non-standard GitHub check state — conservative and safe).

Poll by making **individual Bash tool calls** every 15 seconds (intervals are aspirational because the agent harness fires Bash tool calls back-to-back; `FIRST_POLL_TIME` is what bounds total polling, not the per-poll wait). Note the wall-clock time at first poll as `FIRST_POLL_TIME` — this is conversational state tracked by the LLM across tool calls, not a persistent shell variable (individual Bash calls do not share state). Reset `FIRST_POLL_TIME` at the start of each re-entry to 6a from 6b (timeouts are per-round, not cumulative). Outcomes:

- **CodeRabbit check returns `SUCCESS`:** set `REVIEW_SIGNAL=ci-check`. Fetch the latest CodeRabbit review to capture its `id` for Step 6b:
  ```bash
  gh api repos/<OWNER>/<REPO>/pulls/<N>/reviews \
    --jq '[.[] | select(.user.login == "coderabbitai[bot]")] | sort_by(.submitted_at) | last | .id'
  ```
  Proceed to 6b.

- **CodeRabbit check returns `FAILURE`:** set `REVIEW_SIGNAL=ci-check (FAILURE)`. CodeRabbit errored — no incremental findings expected. Proceed to 6d (skip 6b).

- **CodeRabbit check returns `NONE` (no check found):** Track how long since `FIRST_POLL_TIME`. Early `NONE` results are expected (push-to-check registration race). After 1 minute of continuous `NONE`, fall back to reviews-API poll for the remaining time (up to 5 minutes total from first poll). Set `REVIEW_SIGNAL=reviews-api-fallback`.

  Substitute the actual ISO8601 timestamp captured from `PUSH_TIME` (conversational state) in place of `<PUSH_TIME_ISO8601_LITERAL>` before invoking each Bash tool call — shell variables are not shared between individual calls.
  ```bash
  # Detection query (returns count):
  gh api repos/<OWNER>/<REPO>/pulls/<N>/reviews \
    --jq '[.[] | select(.user.login == "coderabbitai[bot]") | select(.submitted_at > "<PUSH_TIME_ISO8601_LITERAL>")] | length'

  # Once count > 0, capture the review ID:
  gh api repos/<OWNER>/<REPO>/pulls/<N>/reviews \
    --jq '[.[] | select(.user.login == "coderabbitai[bot]") | select(.submitted_at > "<PUSH_TIME_ISO8601_LITERAL>")] | last | .id'
  ```
  When a new review is detected, capture its `id` for Step 6b. If timeout with no new review, proceed to 6d — CodeRabbit may have decided the diff didn't warrant a re-review.

- **CodeRabbit check found but still `PENDING` after 5 minutes:** extend to 10 minutes total (preserved from current 6a behavior). During the extension, also check the reviews-API as a parallel signal — if a new review is detected via reviews-API while the check is still `PENDING`, use the review and proceed to 6b (set `REVIEW_SIGNAL=reviews-api-fallback`). If still pending after 10 minutes, set `REVIEW_SIGNAL=ci-check (timeout)`, warn-and-proceed to 6d.

**Re-entry from 6b (round 2+ guard):** When 6b loops back to 6a after a subsequent push, the CodeRabbit CI check from the prior round still shows `SUCCESS`. Before gating on `SUCCESS`, the skill must first observe the check transition to `PENDING` (indicating the new review run started). If the check does not transition away from `SUCCESS` within 1 minute, fall back to reviews-API poll (whose `submitted_at > PUSH_TIME` filter naturally handles staleness).

When a new review is detected (via either signal), capture its `id` for use in Step 6b.

### 6b. Triage new findings from incremental review

(Skipped entirely when FAST_PATH is true — proceed to 6d.)

Once the incremental review lands, fetch its inline comments **filtered to the new review's ID** (captured in 6a) to avoid re-triaging old comments from prior rounds:

```bash
gh api repos/<OWNER>/<REPO>/pulls/<N>/comments \
  --jq '[.[] | select(.user.login == "coderabbitai[bot]") | select(.pull_request_review_id == <REVIEW_ID>)]'
```

If the new review has NEW findings not present in the original review:

- Triage using Step 3 logic
- If any are categorized as `fix`: apply fixes, run tests, commit, push, capture `HEAD_SHORT_SHA=$(git rev-parse --short HEAD)`, post per-thread replies for this round's fix-categorized findings (same mechanism as Step 6c), then loop back to 6a
- **Cap at 3 fix-push-review cycles.** After 3 rounds, warn the user and proceed to 6d:
  ```text
  3 fix-push-review cycles completed. Remaining findings:
    - <list>
  Proceeding to check thread resolution status. Re-run /review-pr if needed.
  ```

If the incremental review has no new actionable findings (or only duplicates/already-fixed), proceed to 6d.

### 6c. Per-thread commit-hash replies (mechanism)

Step 6c is not a standalone post-loop step — per-thread replies are posted immediately after each push (Step 5 and each Step 6b fix-push cycle). This ensures each reply contains the correct SHA for the round that fixed the finding.

**Reply mechanism:**

For each fix-categorized finding from the current round, post an inline reply on the originating review-comment thread:

```bash
gh api -X POST \
  repos/<OWNER>/<REPO>/pulls/<N>/comments/<COMMENT_ID>/replies \
  -f body="Resolved in <HEAD_SHORT_SHA>"
```

Where `<COMMENT_ID>` is the review-comment ID from the finding's triage. For findings from Step 3 (initial triage), the comment ID comes from Step 2's inline-comment fetch. For findings from Step 6b (incremental review triage), the comment ID comes from the incremental review's comment fetch (filtered to the new review ID). Each round uses its own comment IDs.

**Guard for body-level findings:** If a fix-categorized finding has no associated comment ID (e.g., a review-body-level nitpick that was categorized as fix), skip the reply for that finding. Note the skip in the Step 6e report: `Reply skipped: finding has no inline comment ID (review-body-level)`.

**Error handling:** If a reply call fails (404 = comment deleted, 403 = permission issue, 422 = thread locked, 429 = rate limited), log the failure and continue. Do not abort the loop. On 429 with a `Retry-After` header, wait the indicated duration and retry once. Failed reply count is reported in Step 6e.

**If no findings were fix-categorized** (all non-fix, no push), no replies are posted.

### 6d. Poll for thread resolution + approval

**Short-circuit:** If no fix-categorized findings exist across ALL rounds of this run (not just the current round), skip Phase 1 entirely — no fix-threads to wait for. If prior rounds had fix-categorized findings, poll to observe their resolution status even if the current round had no fixes.

**Phase 1 — Observe thread resolution status.**

> Note: GitHub's GraphQL API returns `coderabbitai` for the bot login (no `[bot]` suffix). The REST API used elsewhere in this skill returns `coderabbitai[bot]`. The jq filter below runs against GraphQL data, so it uses the unsuffixed form.

```bash
gh api graphql -f query='query {
  repository(owner:"<OWNER>", name:"<REPO>") {
    pullRequest(number:<N>) {
      reviewThreads(first:100) {
        pageInfo { hasNextPage endCursor }
        nodes {
          isResolved
          path
          comments(first:1) {
            nodes { author { login } }
          }
        }
      }
    }
  }
}' --jq '.data.repository.pullRequest.reviewThreads | {hasNextPage: .pageInfo.hasNextPage, endCursor: .pageInfo.endCursor, threads: [.nodes[] | select(.comments.nodes[0].author.login == "coderabbitai")]}'
```

If `hasNextPage` is true, repeat with `reviewThreads(first:100, after:"<endCursor>")` and merge the `threads` arrays until `hasNextPage` is false. Then evaluate the merged set:

```bash
# On the merged threads array:
# all_resolved if every thread's .isResolved is true
# otherwise: unresolved_threads: <comma-separated .path values of unresolved threads>
```

Poll by making **individual Bash tool calls** (not a sleep loop — sleep loops are blocked in this environment). Make up to 8 polling attempts; the attempt count governs total polling, not wall-clock duration — intervals are aspirational because the agent harness fires Bash tool calls back-to-back. After each poll, observe how many CodeRabbit threads are resolved and how many are still unresolved. The skill does not attempt to correlate unresolved thread counts against finding counts — it simply observes and reports.

If after exhausting the polling attempts some threads are still unresolved, report the unresolved thread file paths and the manual resolve command:

```text
N CodeRabbit threads still unresolved after 2min:
  - <path1>
  - <path2>
To force-resolve all threads: gh pr comment <N> --body "@coderabbitai resolve"
```

Do not auto-fire the command.

**Phase 2 — Wait for review verdict to update.**

**Enter Phase 2 only if ALL CodeRabbit threads are resolved.** This means:
- If all threads resolved (all findings were fix-categorized and all fix-threads resolved) → enter Phase 2
- If any threads unresolved (non-fix threads open, or fix-threads stuck) → **skip Phase 2**; report that `CHANGES_REQUESTED` is expected while threads remain open
- If `request_changes_workflow` is not enabled (per Step 1b) → skip Phase 2 as before

Once entered, poll for the review verdict:

```bash
gh api repos/<OWNER>/<REPO>/pulls/<N>/reviews \
  --jq '[.[] | select(.user.login == "coderabbitai[bot]")] | sort_by(.submitted_at) | last | .state'
```

Poll by making **individual Bash tool calls**; make up to 9 polling attempts. The attempt count governs total polling, not wall-clock duration — intervals are aspirational because the agent harness fires Bash tool calls back-to-back. CodeRabbit's `request_changes_workflow` auto-approval fires after threads are resolved AND pre-merge checks pass.

Outcomes:
- `APPROVED`: success — CodeRabbit has lifted the reviewer block.
- `CHANGES_REQUESTED` after timeout: "All threads resolved but CodeRabbit has not approved. Pre-merge checks may be failing — check the CodeRabbit walkthrough comment for details."

### 6e. Report

```text
Review round complete for PR #<N>:
- Fixed: X findings in commit <short-sha> (list them)
  [If multi-round: "Round 1: A findings in <sha1>; Round 2: B findings in <sha2>"]
- Skipped: Y findings (list with reasons) — threads left open
- Already fixed: Z findings (list them) — threads left open
- Duplicates: W
- Incremental review rounds: M
- Reply failures: F (list comment IDs and error codes, if any)
- Reply skipped: G (body-level findings with no inline comment ID, if any)
- Thread status: X resolved via reply / Y left open (non-fix)
  [If fix-threads unresolved: "N fix-threads still unresolved — to force-resolve: gh pr comment <N> --body '@coderabbitai resolve'"]
- CodeRabbit verdict: APPROVED / CHANGES_REQUESTED (expected — N threads open) / not polled (request_changes_workflow disabled)
- Fast path: yes — re-run /review-pr if CodeRabbit posts new findings / no
- Review completion signal: ci-check / ci-check (FAILURE) / ci-check (timeout) / reviews-api-fallback / pre-existing-approval / fast-path
```

## Edge cases

- **No new comments**: report "Nothing to review" and exit
- **All findings are non-fix (skip/duplicate/already-fixed)**: no push, no replies, no resolution — report only, threads stay open
- **CodeRabbit review pending**: "Review in progress — wait and retry"
- **CI failing from unrelated issue**: warn user but still process review findings (the review may contain the fix)
- **Branch protection blocks push**: report the error, don't retry
- **Incremental review loop**: cap at 3 fix-push-review cycles to prevent infinite loops
- **CodeRabbit timeout/down**: if polls consistently timeout with no CodeRabbit activity, report and stop
- **Stale CHANGES_REQUESTED with no new findings**: no new findings → no triage → report "no findings but N prior-round threads still open" with manual resolve command (`gh pr comment <N> --body "@coderabbitai resolve"`)
- **Fix-threads don't auto-resolve on hash reply**: report unresolved threads + manual resolve command. No automated fallback
- **Reply API call fails (404/403/422)**: log failure, continue loop, report count in 6e
- **Reply API rate-limited (429)**: wait `Retry-After` duration, retry once. If still 429, log and continue
- **Mixed fix+non-fix findings, all fix-threads resolve**: skip Phase 2 (non-fix threads open → no APPROVED expected), report non-fix threads
- **All fix, no non-fix, threads resolve**: per-thread replies, poll, Phase 2 → APPROVED
- **Multi-round fix-push-review**: per-thread replies posted after each push with correct per-round SHA
- **Comment deleted between triage and reply**: 404 from reply API — logged, counted, non-fatal
- **Body-level nitpick categorized as fix**: reply skipped (no comment ID), noted in report
- **Incremental review creates new thread on same location**: round-N replies use round-N comment IDs from the incremental review fetch. If the new thread is on the same file:line as a prior round's "Resolved" reply, both coexist — cosmetically confusing but functionally correct
- **Rate limit on reply API (pathological 30+ findings)**: 429 retry handles transient limits; if persistent, cap at available budget and report
- **Fast path triggered, no incremental review observed**: expected behavior — the fast path intentionally skips 6a/6b. If CodeRabbit posts new findings after the run, re-run `/review-pr` to pick them up.
- **Fast path triggered but CodeRabbit posts new findings before 6d completes**: 6d's thread-resolution polling may observe unresolved threads from the new findings. The report will show them as unresolved with the manual resolve command. Re-run `/review-pr` to triage.
- **CodeRabbit check missing or stuck — fallback to reviews-API**: if `gh pr checks <N>` returns no CodeRabbit-named check within 1 minute of first poll, fall back to reviews-API poll. Report shows `Review completion signal: reviews-api-fallback`. Common causes: draft PR, paused review, CodeRabbit Checks integration disabled.
- **CodeRabbit check `FAILURE`**: CodeRabbit encountered an error and did not post findings. Proceed to 6d (skip 6b). Report shows `Review completion signal: ci-check (FAILURE)`.
- **CodeRabbit check stuck `PENDING` for 10 minutes**: the PENDING extension window expires. Set `REVIEW_SIGNAL=ci-check (timeout)`, warn, proceed to 6d. Report shows the timeout signal for observability.
- **Race between push and check registration**: the CodeRabbit check may not appear on the first 1–2 polls after push. The 1-minute compatibility window is measured from first poll, not first miss — early misses do not trigger fallback.
- **Reviews-API fallback hides CI-check regression**: if `reviews-api-fallback` appears consistently when `ci-check` is expected, the CI-check filter may be broken. Report makes this observable.
- **Stale CI check on round 2+ re-entry**: after 6b pushes and loops back to 6a, the round-1 CodeRabbit check still shows `SUCCESS`. The re-entry guard waits for `PENDING` before gating on the next `SUCCESS`. If the check never transitions (CodeRabbit skipped re-review), the 1-minute window expires and the skill falls back to reviews-API.
