---
name: comview
description:
  Use when the user has comview open, wants agent-side comview review support,
  or asks the agent to prepare, read, or manage comview review comments.
---

# Comview Review

Comview is an interactive terminal diff viewer managed by the human. Do not run
`comview` or `comview watch` yourself unless the user explicitly wants an
interactive terminal session.

Use normal shell commands to inspect the same diff source, and use
`.comview/comments.json` for persisted review notes. If the user wants coaching
on the TUI itself, use the `comview-guide` skill.

## Workflow

```text
1. Identify the diff source the user is viewing.
2. Inspect that source noninteractively (`git diff`, `git show`, `gh pr diff`, etc.).
3. Read `.comview/comments.json` when you need user review notes.
4. Treat `.comview/comments.json` as read-only.
5. If edits may affect existing comment anchors, tell the user what may need review.
```

## Inspecting the review

Run the diff-producing command directly instead of launching comview:

```bash
git diff
git diff --staged
git show HEAD
gh pr diff 123
```

In Jujutsu repositories, use unified git-format output and disable pagers:

```bash
jj --no-pager diff --git
jj --no-pager show --git @
```

There is no jj staging area, so do not translate `git diff --staged` literally.
If the user is using watch mode with a custom command, inspect that same
command.

## Watch-mode refresh

`comview watch` refreshes the displayed diff when the source command output
changes. It does not live-reload external edits to `.comview/comments.json`.

Do not edit `.comview/comments.json`. Let the human manage comments in comview.

## Comment file

Default path:

```text
.comview/comments.json
```

Basic schema:

```json
{
  "version": 1,
  "comments": [
    {
      "path": "main.go",
      "body": "Comment text",
      "line": 12,
      "side": "RIGHT"
    }
  ]
}
```

Top-level fields:

| Field      | Type   | Values/meaning                                      |
| ---------- | ------ | --------------------------------------------------- |
| `version`  | number | Use `1` when writing files                          |
| `source`   | object | Optional source metadata; preserve if already there |
| `comments` | array  | Comment objects; use `[]` for no comments           |

Comment fields:

| Field                             | Type   | Values/meaning                                            |
| --------------------------------- | ------ | --------------------------------------------------------- |
| `path`                            | string | Diff path, usually without `a/` or `b/`                   |
| `body`                            | string | Review note text                                          |
| `line`                            | number | 1-based target line number                                |
| `side`                            | string | `RIGHT` for new/context side, `LEFT` for deleted old side |
| `start_line`                      | number | Optional 1-based range start line                         |
| `start_side`                      | string | Optional range start side: `RIGHT` or `LEFT`              |
| `start_column`, `end_column`      | number | Optional 1-based same-line code-column range              |
| `commit_id`, `original_commit_id` | string | Optional commit anchors for commit/PR diffs               |
| `github_id`                       | number | Optional imported GitHub comment ID                       |
| `diff_hunk`                       | string | Optional imported GitHub diff hunk                        |

## Reading comments

- Read `.comview/comments.json` to understand the user's review notes.
- Missing file means there are no persisted comments.
- Treat `"comments": null` as no comments.
- Use `side: "RIGHT"` for added lines and context lines on the new side.
- Use `side: "LEFT"` for deleted lines on the old side.
- Do not write, clear, replace, delete, or re-anchor comments.

## Comment anchors after file edits

After editing files that already have comview comments:

1. Re-read `.comview/comments.json`.
2. For each comment on an edited file, inspect the current target line.
3. If formatting or edits moved the relevant text, tell the user which comment
   anchors may need attention in comview.
4. Do not update `.comview/comments.json` yourself.

## Common mistakes

- Running `comview`/`comview watch` directly and hanging the agent.
- Inventing `comview session ...` commands; they do not exist.
- Using default `jj diff` output; use `jj --no-pager diff --git` for comview.
- Claiming live navigation, focus, or session context support.
- Writing `.comview/comments.json`; treat it as read-only.
- Using `RIGHT` for deleted-only old-side lines or `LEFT` for new-side lines.
- Assuming comview live-reloads external comment-file edits.
- Announcing that you did not edit the comment file; only mention comment-file
  state when it matters.
