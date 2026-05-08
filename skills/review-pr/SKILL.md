---
name: review-pr
description: Triage and fix CodeRabbit review comments on a PR. Verifies findings against current code, fixes real issues, pushes, waits for CodeRabbit's incremental re-review, resolves threads, and polls for auto-approval.
user_invocable: true
---

# /review-pr — CodeRabbit review round handler

Process one round of CodeRabbit review findings on a GitHub PR. Triage by severity, fix real issues, push, resolve threads.

## Input parsing

Parse the argument into a PR number:

- `/review-pr 8` → PR #8
- `/review-pr https://github.com/.../pull/8` → extract #8 from URL
- `/review-pr` (no arg) → detect from current branch: `gh pr view --json number --jq .number`

## Step 1: Detect repo and check state

```bash
# Get owner/repo
gh repo view --json owner,name --jq '.owner.login + "/" + .name'

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
2. After all fixes are applied, run the project's test suite. Discover the test command using the same priority as `/ship-spec`:
   1. Read `<project_root>/CLAUDE.md` "Build & Run" section → form a combined command (build + test + lint)
   2. Fallback: check `package.json` for a `test` script, `Makefile`, `pyproject.toml`, or other standard runners
   3. If no test command found: warn but proceed — review-pr is fixing review comments, not authoring new features, so skipping tests is less critical than in ship-spec
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

**Note:** Pushing triggers CodeRabbit's auto-incremental review of the new commit. Step 6 waits for it before resolving threads.

## Step 6: Wait for re-review, resolve threads, poll for approval

`@coderabbitai resolve` **only marks conversation threads as resolved** — it does NOT change the GitHub review verdict. Auto-approval is a separate async action: CodeRabbit submits an `APPROVED` verdict only when `request_changes_workflow: true` AND all threads are resolved AND all pre-merge checks pass. The flow below respects this lifecycle.

### 6a. Wait for CodeRabbit's incremental review (only if fixes were pushed)

If no fixes were pushed (all skips/duplicates), skip to 6c.

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
- If any are categorized as `fix`: apply fixes, run tests, commit, push, then loop back to 6a
- **Cap at 3 fix-push-review cycles.** After 3 rounds, warn the user and proceed to 6c:
  ```text
  3 fix-push-review cycles completed. Remaining findings:
    - <list>
  Proceeding to resolve threads. Re-run /review-pr if needed.
  ```

If the incremental review has no new actionable findings (or only duplicates/already-fixed), proceed to 6c.

### 6c. Post resolve

```bash
gh pr comment <N> --body "@coderabbitai resolve"
```

This fires AFTER all incremental reviews have been triaged, so it resolves threads that have been genuinely addressed.

### 6d. Poll for thread resolution + approval

**Phase 1 — Wait for threads to resolve.**

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

Poll every 15 seconds, up to 2 minutes. Thread resolution is fast — CodeRabbit usually processes the resolve command within seconds.

If threads are NOT all resolved after timeout, warn and list the unresolved thread file paths. Do NOT report success.

**Phase 2 — Wait for review verdict to update.**

Once all threads are resolved, poll for the review verdict:

```bash
gh api repos/<OWNER>/<REPO>/pulls/<N>/reviews \
  --jq '[.[] | select(.user.login == "coderabbitai[bot]")] | sort_by(.submitted_at) | last | .state'
```

Poll every 20 seconds, up to 3 minutes. CodeRabbit's `request_changes_workflow` auto-approval fires after threads are resolved AND pre-merge checks pass.

Outcomes:
- `APPROVED`: success — CodeRabbit has lifted the reviewer block.
- `CHANGES_REQUESTED` after timeout: "All threads resolved but CodeRabbit has not approved. Pre-merge checks may be failing — check the CodeRabbit walkthrough comment for details."
- Skip Phase 2 entirely if Step 1b found `request_changes_workflow` is not enabled.

### 6e. Report

```text
Review round complete for PR #<N>:
- Fixed: X findings (list them)
- Skipped: Y findings (list with reasons)
- Duplicates: Z
- Incremental review rounds: M
- Thread status: all resolved / N unresolved (list files)
- CodeRabbit verdict: APPROVED / CHANGES_REQUESTED (pending)
```

## Edge cases

- **No new comments**: report "Nothing to review" and exit
- **All findings are skips/duplicates**: resolve threads without pushing (skip 6a/6b, go straight to 6c)
- **CodeRabbit review pending**: "Review in progress — wait and retry"
- **CI failing from unrelated issue**: warn user but still process review findings (the review may contain the fix)
- **Branch protection blocks push**: report the error, don't retry
- **Incremental review loop**: cap at 3 fix-push-review cycles to prevent infinite loops
- **CodeRabbit timeout/down**: if polls consistently timeout with no CodeRabbit activity, report and stop
- **Stale CHANGES_REQUESTED with no findings**: post resolve and wait for auto-approval — CodeRabbit may be blocking from a previous review round whose threads were never resolved
