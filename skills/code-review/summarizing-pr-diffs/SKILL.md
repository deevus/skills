---
name: summarizing-pr-diffs
description: >
  Use when summarizing a pull request, merge request, patch, diff, or PR body;
  when checking whether a PR body matches its diff; or when turning a change into
  plain-language pseudocode.
---

# Summarizing PR Diffs

## Overview

Turn a PR body and diff into the useful story: why the change exists, what
shape it took, what the diff proves, and where the body is stale. Deslop the
explanation. Keep causal facts and remove PR-tour padding.

Use this with `ste-plain-writing` for the final prose when the user wants a
polished summary.

## Workflow

1. Save the PR metadata/body and diff to separate files.
2. Read the PR body for intent: problem, claims, tests, sequencing, and caveats.
3. Read the diff as source of truth: changed files, actual behavior, omitted
   changes, and unchanged contracts.
4. Reconcile the two. If the body is stale, stacked, incomplete, or overclaims,
   say so briefly.
5. Summarize the change by cause and effect, not by hunk order.
6. Add pseudocode when it clarifies the behavior or decision rule.

## Output Contract

Use this shape unless the user asks for another one:

````markdown
PR #123 — Title. State, author, branch direction, size, and sequencing.

## What it does

**The problem.** Why this change exists.

**The fix.** The central behavior, rule, or shape.

- Consequential detail.
- Consequential detail.
- Tests, unchanged contracts, deployment order, or operational effect.

## Body vs diff

Only include this section when they diverge. Name the stale count, omitted file,
omitted rule, stacked-base noise, or unsupported claim.

## As pseudocode

```text
# decision rule or before/after behavior
```
````

Keep prose concise. Most summaries should be 300-700 words plus pseudocode
under 50 lines.

## What to Preserve

- The problem the PR solves.
- Operational consequences: metrics, alerts, deploy order, migrations,
  ownership, scheduling, security, data contracts.
- Boundary choices: injected dependency vs import, config vs code, table vs
  value, old path vs canonical path.
- Tests and explicit unchanged behavior.
- Risks or manual follow-up when the PR body states them or the diff proves them.

## What to Cut

- File-by-file tours that repeat hunk order.
- Generic claims such as “improves reliability” without the mechanism.
- PR-template boilerplate.
- AI-ish framing: “this PR introduces,” “comprehensive,” “robust,” “seamless.”
- Review verdicts, acceptance reports, and implementation-plan language unless
  the user asked for a review.

## Pseudocode Rules

Use pseudocode for the load-bearing behavior, not the file structure.

For code changes, prefer before/after when behavior changed:

```text
# before
worker_reports_metric_after_finish()
# timeout kills worker before this runs

# after
dispatcher_receives_result_or_exception()
outcome = classify(result)
emit_count(catalog, outcome, count)
return timeout_count + error_count  # unchanged caller contract
```

For docs or policy changes, write decision functions:

```text
function choose_rollout(change):
    if change.touches_payments or change.touches_auth:
        return manual_approval_then_gradual_rollout
    if change.is_config_only and change.has_fast_rollback:
        return automatic_rollout
```

Name injected dependencies and side effects. Do not invent branches that the
body or diff does not support.

## Common Mistakes

| Mistake | Fix |
| --- | --- |
| Trusting the PR body counts | Verify file list and size against the diff. |
| Summarizing every file | Group by behavior, boundary, or operational effect. |
| Hiding stale-body findings | Add a short “Body vs diff” section. |
| Turning docs into no pseudocode | Docs often encode decision rules. Write those rules. |
| Writing a code review | Summarize unless the user explicitly asks for findings. |
| Letting STE remove caveats | Plain prose must preserve limits, tests, and unchanged contracts. |

## Quick Checklist

- [ ] Body and diff read from files.
- [ ] Diff used as source of truth.
- [ ] Problem and fix stated causally.
- [ ] Consequential details kept; hunk tour cut.
- [ ] Body/diff mismatch called out or omitted because none exists.
- [ ] Pseudocode included when it clarifies behavior.
