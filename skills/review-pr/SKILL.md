---
name: review-pr
description: Triage and fix CodeRabbit review comments on a PR. Verifies findings against current code, fixes real issues, pushes, and resolves threads for auto-approve.
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

## Step 2: Fetch CodeRabbit review comments

```bash
# Get all reviews — find the latest coderabbit-ai[bot] review
gh api repos/{owner}/{repo}/pulls/<N>/reviews \
  --jq '[.[] | select(.user.login == "coderabbit-ai[bot]")] | sort_by(.submitted_at) | last | {id, state, submitted_at}'

# Get inline comments from CodeRabbit
gh api repos/{owner}/{repo}/pulls/<N>/comments \
  --jq '[.[] | select(.user.login == "coderabbit-ai[bot]")]'
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
2. After all fixes are applied, run the project's test suite:
   - Check `package.json` for a `test` script and run it
   - If there are multiple test configs (e.g., library + plugin), run all of them
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

## Step 6: Resolve threads, verify, and report

After pushing (or if all findings were skips/duplicates with nothing to push):

### 6a. Always post resolve command

```bash
gh pr comment <N> --body "@coderabbitai resolve"
```

This tells CodeRabbit to resolve all its open review threads.

### 6b. Verify threads are actually resolved

Do NOT assume the resolve worked. Check thread state:

```bash
gh api graphql -f query='query {
  repository(owner:"<OWNER>", name:"<REPO>") {
    pullRequest(number:<N>) {
      reviewThreads(first:50) {
        nodes {
          isResolved
          comments(first:1) {
            nodes { author { login } }
          }
        }
      }
    }
  }
}' --jq '[.data.repository.pullRequest.reviewThreads.nodes[] | select(.comments.nodes[0].author.login == "coderabbitai[bot]") | .isResolved] | if all then "all_resolved" else "unresolved_threads" end'
```

- If `all_resolved`: proceed to report.
- If `unresolved_threads` or empty output: warn the user that threads may still be open and need manual resolution. Do NOT report success.

### 6c. Verify CodeRabbit is not blocking merge

```bash
gh api repos/<OWNER>/<REPO>/pulls/<N>/reviews \
  --jq '[.[] | select(.user.login == "coderabbitai[bot]")] | sort_by(.submitted_at) | last | .state'
```

- If `APPROVED`: CodeRabbit has lifted the reviewer block.
- If `CHANGES_REQUESTED`: CodeRabbit is still blocking — threads may not have resolved yet. Report this and do NOT claim the PR is ready.

### Report to user

Summarize the round:

```
Review round complete for PR #<N>:
- Fixed: X findings (list them)
- Skipped: Y findings (list with reasons)
- Duplicates: Z
- Status: pushed <commit>, threads resolved, CodeRabbit approved
```

## Edge cases

- **No new comments**: report "Nothing to review" and exit
- **All findings are skips/duplicates**: resolve threads without pushing
- **CodeRabbit review pending**: "Review in progress — wait and retry"
- **CI failing from unrelated issue**: warn user but still process review findings (the review may contain the fix)
- **Branch protection blocks push**: report the error, don't retry
