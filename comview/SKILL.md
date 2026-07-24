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
3. Read `.comview/comments.json` before changing comments.
4. Edit/write valid JSON, preserving existing comments.
5. If you edited reviewed files, verify comment line anchors still match.
6. Tell the user what comment file changes were made.
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

Treat comment-file writes as an offline operation. If comview is running, ask
the user to quit or save first, then reopen comview after the file edit. Editing
the file behind a live TUI can leave comview's in-memory comments stale and may
cause the TUI to report unsaved review state.

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

## Editing comments safely

- Always read the existing file first; missing file means
  `{ "version": 1, "comments": [] }`.
- Preserve top-level `source` metadata if present.
- If an existing file has `"comments": null`, treat it as no comments; write
  `"comments": []` when saving.
- Preserve existing comments unless the user asked to replace, delete, or clear
  them.
- Only write `.comview/comments.json` when comview is not actively reviewing
  that file, unless the user explicitly accepts the stale/dirty TUI risk.
- If comview is running, ask the user to quit or save first, then reopen it
  after the edit.
- If the user asks to clear comments, preserve `version` and top-level `source`,
  then write `"comments": []`.
- Write syntactically valid, indented JSON.
- Use `side: "RIGHT"` for added lines and context lines on the new side.
- Use `side: "LEFT"` for deleted lines on the old side.
- After writing comments, tell the user to reopen comview to load the new file.

## Maintaining comment anchors

After editing files that already have comview comments, verify affected comment
anchors before reporting back:

1. Re-read `.comview/comments.json`.
2. For each comment on an edited file, inspect the current target line.
3. If formatting or edits moved the relevant text, update the comment's `line`
   to the new 1-based line number.
4. Preserve the comment body, side, range, and metadata unless the user asked to
   change them.

## Common mistakes

- Running `comview`/`comview watch` directly and hanging the agent.
- Inventing `comview session ...` commands; they do not exist.
- Using default `jj diff` output; use `jj --no-pager diff --git` for comview.
- Claiming live navigation, focus, or session context support.
- Overwriting `.comview/comments.json` without preserving existing notes.
- Using `RIGHT` for deleted-only old-side lines or `LEFT` for new-side lines.
- Assuming comview live-reloads external comment-file edits.
