---
name: bench
description: >
  Use when benching a ticket, issue, PR, or task into an isolated development
  workspace, including requests like "bench it", "set up a bench", or "bench PR
  #... for review".
---

# Bench

Create an isolated workspace for a task or review, start the chosen agent
harness, and keep a live diff watcher beside it.

## Route to the UI skill

Before doing UI setup, check the environment from the current shell:

```bash
printf 'HERDR_ENV=%s\n' "${HERDR_ENV:-}"
command -v supacode >/dev/null && echo supacode || echo no-supacode
```

- If `HERDR_ENV=1`, **REQUIRED SUB-SKILL:** use `bench-herdr` for terminal UI
  mechanics.
- Else if `supacode` exists, **REQUIRED SUB-SKILL:** use `bench-supacode` for
  Supacode mechanics.
- Else do the native VCS workspace steps only. If possible, use two ordinary
  terminal tabs/windows: work and `Diff`.

Read the relevant project topic or repo instructions for repo paths, workspace
naming, issue prefixes, colour conventions, and tracker specifics. Keep those
out of this generic workflow.

## Generic sequence

1. **Fetch first.** From the source repo, run `jj git fetch` for jj or
   `git fetch` for git before creating the bench. Report the resolved base
   revision.
2. **Use native VCS isolation.** Use `jj workspace add` for jj or `git worktree`
   / the repo's native workflow for git. Do not copy a checkout. Do not use UI
   worktree helpers that copy VCS metadata.
3. **Clear stale registrations.** For jj, check `jj --no-pager workspace list`;
   if the workspace directory was removed without `jj workspace forget`, forget
   the dangling workspace before recreating it.
4. **Verify metadata.** Confirm the new root has expected VCS metadata (`.jj`
   for jj workspaces, `.git` for git worktrees) and no stray copied metadata.
5. **Symlink local config.** Symlink, never copy, VCS-excluded local config from
   the source repo into the bench.
6. **Trust and install env.** If `mise.toml` exists in the new root, run
   `mise trust` there before terminals, agents, env installs, or diff watchers.
   Then run the repo's environment install.
7. **Write the handoff brief outside the workspace.** Use a temp/session scratch
   path, never the workspace root. Write from the ticket/PR/request only. Do not
   scout the codebase; the harness does that in the bench.
8. **Ask for the harness once.** Use a numbered list. Default/recommend Claude:
   `claude --permission-mode plan "Read <brief>, then plan before edits."`
   Alternative Pi: `pi @<brief> "Plan before edits."`
9. **Create two concerns.** Work tab/window runs the harness. `Diff` tab/window
   runs Comview. Never put Comview in a split in the work tab.
10. **Focus back to work.** After the watcher starts, return focus to the work
    harness.

## Diff watcher commands

For jj task benches, watch the branch diff from the fork point:

```bash
comview watch -- jj --no-pager diff --git --from 'fork_point(trunk() | @)' --to @
```

For git task benches, use merge-base rather than plain `main`:

```bash
comview watch -- bash -lc 'git diff "$(git merge-base main HEAD)"'
```

Use `fork_point` / `merge-base`; plain `trunk()` or `main` can show inverted
diffs after main moves.

## Review benches

For "bench PR ... for code review":

- Fetch first.
- Create the bench at the PR head.
- Confirm `trunk()` / `main` matches the remote base.
- If the PR is behind main, do not rebase or mutate someone else's branch. In
  jj, create a local review merge:

  ```bash
  jj new '<branch>@origin' 'trunk()' -m 'review bench: <ticket> PR head merged with current main'
  ```

- Re-run environment install after the merge.
- Verify the file count against the PR metadata.
- Do not push from a review bench.
- The brief carries PR description, verified file count, exact diff command, and
  review-only constraints. It does not pre-read the diff.

## Handoff brief contents

Include only information already in the request or tracker:

- Goal or review target.
- Acceptance criteria or review scope.
- Links and IDs.
- Resolved base revision.
- Exact diff watcher command.
- Known constraints and open questions.

A thin brief is correct when the ticket is thin. Put uncertainty in open
questions instead of scouting.

## Comview and agents

Agents cannot read the interactive Comview TUI. Inspect the same diff
noninteractively with the underlying VCS command. Treat `.comview/comments.json`
as read-only.
