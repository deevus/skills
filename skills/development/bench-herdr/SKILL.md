---
name: bench-herdr
description:
  Use when a bench workspace must be opened, arranged, verified, or operated
  inside Herdr.
---

# Bench Herdr

Herdr mechanics for a bench. If `bench` has not already been loaded for this
request, load `bench` first and follow its generic workflow before doing these
UI steps.

This applies when `HERDR_ENV=1`.

## Sequence

1. Create the native VCS checkout/workspace first, as directed by `bench`.
2. Open or create a Herdr workspace rooted at the bench directory.
3. Label the workspace from the ticket/task. Prefix with a short project or
   issue code when one is available from the project topic.
4. Keep the initial tab as the work shell. The harness runs there.
5. Create a second tab rooted at the same bench directory, titled exactly
   `Diff`.
6. Run the Comview watcher in `Diff`.
7. Focus back to the work shell.

## Diff tab

Use the watcher command from `bench`; it depends on VCS and whether this is a
task bench or review bench. For jj task benches the default is:

```bash
comview watch -- jj --no-pager diff --git --from 'fork_point(trunk() | @)' --to @
```

The watcher should show the branch contribution from the fork point, not only
uncommitted working-tree changes.

## Harness

Ask which harness to run if `bench` has not already asked. Default/recommend
Claude plan mode; Pi is the alternative.

The work tab must hold the harness. Comview belongs in the separate `Diff` tab,
not a split pane.

## Agents and Comview

Agents cannot read the interactive Comview TUI. Inspect the same diff
noninteractively with the underlying VCS command. Treat `.comview/comments.json`
as read-only.

## Hosts outside Herdr

If `HERDR_ENV` is not `1`, return to `bench` and use `bench-supacode` or the
native-only path selected by the environment.
