---
name: comview-guide
description:
  Use when the user wants to learn comview, needs help navigating the comview
  TUI, or asks how to review diffs, add comments, search, watch changes, or use
  keybindings in comview.
---

# Comview Guide

Use this skill to coach a human through comview. Keep guidance task-focused:
give only the next few keys or commands the user needs, not the whole keymap
unless they ask for it.

If the agent needs to inspect or edit comview review comments itself, use the
`comview` skill.

## Launching comview

Prefer watch mode for review sessions, even when the source command is not
expected to change. Watch mode refreshes diff output as the command output
changes.

Git examples:

```bash
comview watch                         # watches `git diff`
comview watch --staged                # watches `git diff --staged`
comview watch -- git show HEAD
comview watch -- gh pr diff 123
```

Jujutsu examples:

```bash
comview watch -- jj --no-pager diff --git
comview watch -- jj --no-pager diff --git -r 'trunk()..@'
comview watch -- jj --no-pager show --git @
```

Use `--git` so jj emits unified diff output, and `--no-pager` so it does not
open an interactive pager. Jujutsu has no staging area, so `--staged` is a git
workflow only.

Do not pipe into watch mode. `comview watch` ignores stdin and reruns the
command after `--`; use pipes only for one-shot viewing.

For one-shot viewing only, piping still works:

```bash
git diff | comview
git show | comview
gh pr diff 123 | comview
jj --no-pager diff --git | comview
jj --no-pager diff --git -r 'trunk()..@' | comview
```

## Teaching flow

1. Ask what the user is trying to do: browse, review, comment, search, or save.
2. Give 3-5 relevant commands maximum.
3. Wait for what they see next.
4. Add more keys only when needed.

## Core navigation

| Key                 | Action                 |
| ------------------- | ---------------------- |
| `j`/`k`, arrows     | Move                   |
| `h`/`l`             | Move horizontally      |
| `gg` / `G`          | Top / bottom           |
| `Ctrl-d` / `Ctrl-u` | Half-page down / up    |
| `J` / `K`           | Next / previous commit |
| `]c` / `[c`         | Next / previous change |
| `<space>e`          | Find file in diff      |
| `?`                 | Show help              |
| `:q` / `:q!`        | Quit / force quit      |

## Comments and review notes

| Key         | Action                         |
| ----------- | ------------------------------ |
| `i` or `I`  | Add or edit a comment          |
| `Ctrl-s`    | Submit the active comment box  |
| `]n` / `[n` | Next / previous note           |
| `x` / `dd`  | Delete note under cursor       |
| `:w`        | Save comments                  |
| `:q`        | Quit if comments are saved     |
| `:q!`       | Quit and discard unsaved state |

Comments are stored in `.comview/comments.json`. Comview loads that file at
startup; if an agent edits it externally, quit and reopen comview to see those
changes.

## Search, selection, and copy

| Key     | Action                         |
| ------- | ------------------------------ |
| `/`     | Search                         |
| `n`/`N` | Next / previous search result  |
| `v`     | Visual selection               |
| `V`     | Visual-line selection          |
| `y`     | Copy selection                 |
| `o`     | Open cursor location in editor |

## Layout and appearance

| Key | Action                   |
| --- | ------------------------ |
| `s` | Toggle side-by-side view |
| `t` | Choose theme             |
| `?` | Show help                |

## Common coaching patterns

- For normal git working-tree review: ask the user to run `comview watch`.
- For staged git changes: ask the user to run `comview watch --staged`.
- For git commit or PR diffs: use `comview watch -- <diff-producing command>`.
- For jj working-copy review: ask the user to run
  `comview watch -- jj --no-pager diff --git`.
- For a jj branch/stack review, use
  `comview watch -- jj --no-pager diff --git -r 'trunk()..@'`.
- For jj commit diffs: use `comview watch -- jj --no-pager show --git @`.
- To add a note: move the cursor to the exact diff line to anchor the comment,
  press `i`, type the note, press `Ctrl-s`, then `:w`.
- To find the next changed area: press `]c`; use `[c` to go backward.
- To jump between notes: press `]n` or `[n`.
- To avoid overwhelming the user, teach one mini-workflow at a time.
