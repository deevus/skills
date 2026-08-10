---
name: bench-supacode
description:
  Use when a bench workspace must be opened, arranged, verified, or operated in
  Supacode.
---

# Bench Supacode

Supacode mechanics for a bench. If `bench` has not already been loaded for this
request, load `bench` first and follow its generic workflow before doing these
UI steps.

## Principles

- Create the checkout with the repo's native VCS first. Do not use
  `supacode worktree-new`; it can copy VCS metadata such as `.jj`.
- Always pass explicit Supacode targets. Surface and tab commands default to the
  agent's own tab, not the bench.
- End with exactly two tabs: `Work` and `Diff`.
- Do not restructure a bench that is already in use. Closing the idle default
  tab is only part of setting up a new bench.

## Open the finished checkout

`supacode repo open <path>` is async and may print nothing. Poll until the path
appears:

```bash
supacode repo open <bench-path>
supacode worktree list
```

Derive the worktree id from `worktree list`; it is usually the percent-encoded
path.

Set appearance before focus:

```bash
supacode worktree appearance -w <WT> --title "<short title>" --color <colour>
```

Use the task record for a short title. Use the project's established colour
convention from its project topic; do not invent a generic project-specific
rule.

## Create tabs

Opening a worktree leaves an idle default shell tab. Create the real tabs with
initial commands, then close the idle default:

```bash
supacode tab new -w <WT> --title Work -i "<harness command>"
supacode tab new -w <WT> --title Diff -i "<comview watcher command>"
supacode tab list -w <WT>
supacode tab close -w <WT> -t <IDLE_DEFAULT_TAB>
supacode tab focus -w <WT> -t <WORK_TAB>
```

Identify the idle default by listing tabs/surfaces. The default shell is a bare
zsh; tabs created with `-i` run the harness or watcher.

## Harness launch constraint

Supacode has no reliable `surface send` / type-text command for launching the
harness after a shell exists. Start the harness via `-i` on `supacode tab new`.

Do not split the idle default shell for the harness; that leaves a two-pane work
tab and violates the bench layout.

## Target every command

Use explicit `-w`, `-t`, and `-s` where applicable:

```bash
supacode tab list -w <WT>
supacode surface list -w <WT> -t <TAB>
supacode surface focus -w <WT> -t <TAB> -s <SURFACE>
```

Bare `supacode surface list` proves nothing about the bench; it may show the
current agent tab.

## Verify before reporting success

Check both Supacode structure and process cwd:

```bash
supacode tab list -w <WT>
supacode surface list -w <WT> -t <WORK_TAB>
supacode surface list -w <WT> -t <DIFF_TAB>
lsof -a -d cwd -p <pid>
```

The harness and Comview watcher must both be rooted in `<bench-path>`. Focus
back to `Work` after verification.

## Hosts without Supacode

If `supacode` is not installed, return to `bench` and use the native-only path
or another UI skill selected by the environment.
