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
# Check if the branch is checked out in a worktree
git worktree list  # look for $PR_BRANCH in the output
```

If the PR branch is checked out in a worktree, use that worktree as the working directory for all subsequent steps (file reads, edits, git operations). If the branch is the current branch in the primary tree, use the primary tree. If the branch isn't checked out anywhere, check it out before proceeding.

```bash
# Get the PR's diff scope — helps contextualize findings and triage outside-diff comments
gh pr diff <N> --stat

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

### 6a. Wait for CodeRabbit's incremental review (only if fixes were pushed)

If no fixes were pushed (all skips/duplicates/already-fixed), skip to 6d.

**Before entering the wait loop, check the current verdict:**

```bash
gh api repos/<OWNER>/<REPO>/pulls/<N>/reviews \
  --jq '[.[] | select(.user.login == "coderabbitai[bot]")] | sort_by(.submitted_at) | last | .state'
```

If the latest verdict is `APPROVED` **and its `submitted_at` is after `PUSH_TIME`**, skip 6a/6b and go straight to 6e — CodeRabbit has already reviewed the new commit and approved it. A pre-push `APPROVED` verdict must not short-circuit: the incoming incremental review may flip it back to `CHANGES_REQUESTED`.

**Otherwise**, after pushing, CodeRabbit auto-triggers an incremental review of the new commit. Wait for it to land before resolving anything — otherwise the resolve may race with new findings from the re-review.

```bash
# Fetch the HEAD commit's author date from GitHub (always UTC — avoids local-timezone mismatch on Windows)
HEAD_SHA=$(git rev-parse HEAD)
PUSH_TIME=$(gh api repos/<OWNER>/<REPO>/commits/$HEAD_SHA --jq '.commit.author.date')

# Poll: is there a CodeRabbit review submitted after our push?
gh api repos/<OWNER>/<REPO>/pulls/<N>/reviews \
  --jq '[.[] | select(.user.login == "coderabbitai[bot]") | select(.submitted_at > "'"$PUSH_TIME"'")] | length'
```

Poll by making **individual Bash tool calls** (not a single blocking loop) so the conversation stays responsive — the user can interject, correct, or cancel between checks. Check every 30 seconds, up to 5 minutes (10 attempts). If at timeout `gh pr checks <N>` still shows CodeRabbit "in_progress", extend the wait to 10 minutes total. If no CodeRabbit check is running at all, proceed — CodeRabbit may have decided the diff didn't warrant a re-review.

When a new review is detected, capture its `id` for use in Step 6b.

### 6b. Triage new findings from incremental review

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
}' --jq '.data.repository.pullRequest.reviewThreads | {hasNextPage: .pageInfo.hasNextPage, threads: [.nodes[] | select(.comments.nodes[0].author.login == "coderabbitai[bot]")]}'
```

If `hasNextPage` is true, repeat with `reviewThreads(first:100, after:"<endCursor>")` and merge the `threads` arrays until `hasNextPage` is false. Then evaluate the merged set:

```bash
# On the merged threads array:
# all_resolved if every thread's .isResolved is true
# otherwise: unresolved_threads: <comma-separated .path values of unresolved threads>
```

Poll by making **individual Bash tool calls** (not a sleep loop — sleep loops are blocked in this environment). Check every 15 seconds, up to 2 minutes. After each poll, observe how many CodeRabbit threads are resolved and how many are still unresolved. The skill does not attempt to correlate unresolved thread counts against finding counts — it simply observes and reports.

If after the 2-minute polling window some threads are still unresolved, report the unresolved thread file paths and the manual resolve command:

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

Poll by making **individual Bash tool calls** every 20 seconds, up to 3 minutes. CodeRabbit's `request_changes_workflow` auto-approval fires after threads are resolved AND pre-merge checks pass.

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
