---
name: bench
description: >
  Use when benching a ticket, issue, PR, or task into an isolated development
  workspace, including requests like "bench it", "set up a bench", or "bench PR
  #... for review".
---

# Bench

Create an isolated workspace for a task or review. Resolve the agent harness and
optional diff companion, route terminal setup to the active UI, and verify that
the bench is ready before reporting success.

See [configuration](references/configuration.md) for the layered resolver
contract. The resolver is the source of truth for the harness argv and the diff
viewer choice.

## Responsibilities

`bench` owns:

- configuration resolution and any required user choices;
- native VCS workspace creation;
- local configuration links and environment setup;
- handoff brief creation;
- UI routing;
- diff integration routing; and
- final readiness checks.

`bench` does not build viewer commands or manage viewer review state. Use the
selected diff integration for the optional companion title, companion command,
and viewer-specific brief text.

## Resolve configuration

1. Pick a stable handoff brief path outside the workspace.
2. Write an initial brief from the request, ticket, or PR metadata only. Do not
   scout the codebase for the harness.
3. Run the resolver from the source repository:

   ```bash
   python3 skills/development/bench/scripts/resolve_bench_config.py \
     --repo-root /path/to/source-repo \
     --brief /tmp/bench-brief.md
   ```

4. If `harness.selection_required` is true, ask once with a numbered list:
   1. Claude, plan mode.
   2. Pi, plan before edits.

   Then rerun the resolver with `--harness-tool claude` or
   `--harness-tool pi`.
5. If `diff.selection_required` is true, ask once with a numbered list:
   1. Comview.
   2. Hunk.
   3. None.

   Then rerun the resolver with `--diff-tool comview`, `--diff-tool hunk`, or
   `--diff-tool none`.
6. Stop on resolver errors. Do not guess when configuration is malformed, an
   executable is missing, or a required choice is unresolved.

Pass the returned `harness.argv` to the UI adapter unchanged. It is an argv list,
not a shell command string.

## Create the native workspace

1. Read the relevant project topic or repo instructions for repo paths,
   workspace names, issue prefixes, colour conventions, and tracker specifics.
   Keep those project facts out of this generic skill.
2. Fetch first from the source repository. Use `jj git fetch` for Jujutsu or
   `git fetch` for Git. Report the resolved base revision.
3. Use native VCS isolation. Use `jj workspace add` for Jujutsu, or
   `git worktree` or the repo's native Git workflow for Git. Do not copy a
   checkout. Do not use UI helpers that copy VCS metadata.
4. For Jujutsu, check `jj --no-pager workspace list`. If a deleted directory
   left a stale workspace registration, forget it before recreating that name.
5. Verify the new root has the expected VCS metadata: `.jj` for Jujutsu
   workspaces or `.git` for Git worktrees. Fail closed on stray copied metadata.
6. Symlink, never copy, VCS-excluded local config from the source repository
   into the bench.
7. If `mise.toml` exists in the bench, run `mise trust` there before terminals,
   agents, environment installs, or companions.
8. Run the repo's environment install commands from the bench root.

If a fetch makes other Jujutsu workspaces stale, repair them separately with
`jj workspace update-stale` and re-verify any review bench diff before you
report success.

## Review benches

For "bench PR ... for code review":

1. Fetch first.
2. Create the bench at the PR head or the local review merge required by the
   repository workflow.
3. Confirm `trunk()` or the Git base branch matches the remote PR base.
4. If the PR is behind the base branch, do not rebase or mutate someone else's
   branch. In Jujutsu, create a local review merge instead.
5. Re-run environment install after the merge.
6. Verify the file count against PR metadata.
7. Do not push from a review bench.

Put review scope, constraints, the verified file count, and the resolved base in
the brief. Let the selected diff integration add its own range and interaction
instructions.

## Route the diff integration

Use the resolver's final `diff.tool` value:

- `comview`: use `bench-diff-comview` to produce the companion title, companion
  command, and brief additions.
- `hunk`: use `bench-diff-hunk` to produce the companion title, companion
  command, session verification, and brief additions.
- `none`: do not create a companion.

Pass the bench type and VCS facts to the diff integration: task, review, or
stack; Git or Jujutsu; base branch or revset; review head; and any path scope.
Do not duplicate its range recipes in this core skill.

## Finish the handoff brief

Keep the brief outside the workspace. Include only facts already known from the
request, tracker, PR metadata, resolver output, and selected diff integration:

- goal or review target;
- acceptance criteria or review scope;
- links and IDs;
- resolved base revision;
- selected harness argv in readable form;
- selected diff tool, or that no companion was requested;
- companion command and viewer-specific instructions, if a companion exists;
- known constraints and open questions.

A thin brief is correct when the ticket is thin. Put uncertainty in open
questions instead of scouting.

## Route to the terminal UI

Before doing UI setup, check the environment from the current shell:

```bash
printf 'HERDR_ENV=%s\n' "${HERDR_ENV:-}"
command -v supacode >/dev/null && echo supacode || echo no-supacode
```

- If `HERDR_ENV=1`, use `bench-herdr` for terminal mechanics.
- Else if `supacode` exists, use `bench-supacode` for Supacode mechanics.
- Else use native terminals when available.

Every UI path receives the same inputs: bench path, short title, harness argv,
and an optional companion title plus command. UI skills must not detect viewers,
construct viewer commands, or add review semantics.

## Native terminal fallback

When no UI skill is available, keep the same separation of concerns:

1. Start the harness in a work terminal rooted at the bench.
2. If a companion exists, start it in a separate terminal rooted at the bench.
3. Return focus to the work terminal when possible.
4. Verify the shell cwd for each terminal before reporting success.

If you cannot verify cwd or keep Work separate from the companion, report that
setup is incomplete.

## Final verification

Before reporting success, confirm:

- the workspace root and VCS metadata are correct;
- the environment setup completed;
- the handoff brief exists outside the workspace;
- the harness process started from the bench root;
- any companion process started from the bench root;
- the selected diff integration's verification passed;
- the UI is focused back on Work when a UI is available; and
- review benches have not pushed or mutated someone else's branch.

Fail closed on missing sessions, unexpected tabs, ambiguous cwd, unresolved
configuration, or unavailable executables.
