# Bench Orca

Orca terminal mechanics for a bench. Use this reference only after the core
`bench` workflow has created the native workspace and selected Orca routing.

This reference applies when `ORCA_TERMINAL_HANDLE` is set. Run the executable in
`ORCA_CLI_COMMAND` when it is set; otherwise run `orca`.

## Inputs

`bench` provides:

- bench path;
- short workspace title;
- ordered harness tab specs;
- optional companion title plus companion command.

Each harness tab spec contains:

- `role`: `plan` or `work`;
- `title`: the tab title; and
- `argv`: the harness argv array.

Exactly one Work harness tab is required. A Plan harness tab is optional. The
companion pair is optional. If one of companion title or command is missing,
stop and return to `bench` for corrected inputs.

Do not detect viewers, construct companion commands, or add review semantics in
this reference. Treat the companion as a generic terminal command.

## Principles

- Create the checkout with the repo's native VCS first. Do not use
  `orca worktree create`; it makes its own checkout and does not forward harness
  argv.
- Pass `--worktree path:<bench-path>` to every worktree and terminal command.
  Without it, Orca targets the agent's own worktree, not the bench.
- Orca types `--command` into the tab's login shell. Build each harness command
  at this boundary as `cd <shell-quoted-bench-path> && <shell-quoted argv>`.
  Shell-quote every argv element. For a companion, append the companion command
  after `&&` exactly as `bench` supplied it.

## Sequence

1. Run `orca status --json`. Stop if the runtime is not reachable.
2. Run `orca worktree show --worktree path:<bench-path> --json`. Orca lists the
   Git worktrees of a registered repo, including worktrees it did not create. If
   the call fails and `orca repo list --json` does not include the source
   repository, run `orca repo add --path <source-repo> --json` once and retry.
   If it still fails, for example for a Jujutsu workspace that Orca does not
   list, use [Benches Orca does not list](#benches-orca-does-not-list).
3. Run `orca terminal list --worktree path:<bench-path> --json`. A fresh
   checkout has no terminals. If `totalCount` is not 0, stop and return to
   `bench` with the observed state. Do not restructure a bench that may be in
   use.
4. Label the worktree:

   ```bash
   orca worktree set --worktree path:<bench-path> \
     --display-name "<short title>" --json
   ```

5. Create harness tabs in the order supplied by `bench`:

   ```bash
   orca terminal create --worktree path:<bench-path> --title "<title>" \
     --command "<cd-and-argv command>" --json
   ```

   Record each `result.terminal.handle`.

6. If a companion was provided, create one more tab the same way. Title it
   exactly with the companion title.
7. For each harness handle, wait for the agent TUI:

   ```bash
   orca terminal wait --terminal <handle> --for tui-idle \
     --timeout-ms 60000 --json
   ```

   Require `wait.satisfied: true`. If it is false, rerun once with a larger
   timeout. If it is still false, stop: setup is incomplete. For a custom
   harness that is not an agent TUI, read the tab with `orca terminal read`
   instead and confirm it started without a shell error.

8. Focus Work: `orca terminal switch --terminal <work-handle> --json`.

The default layout is Work plus optional companion. A split-harness layout is
Plan, Work, and optional companion. The core `bench` skill picks the handoff
mode. Orca never signals Work: leave `orca terminal send` and
`orca orchestration` out of the handoff.

## Benches Orca does not list

Orca lists only Git worktrees, so a Jujutsu workspace returns
`selector_not_found` from `orca worktree show`. Host the bench tabs in the
current Orca worktree instead, and keep the `cd <bench>` prefix so each command
still runs in the bench:

1. Skip steps 3 and 4. The current worktree already has your own terminal, and
   its display name belongs to that worktree.
2. Create each tab without `--worktree`, so Orca uses the current worktree:

   ```bash
   orca terminal create --title "<title>" \
     --command "cd <shell-quoted-bench-path> && <shell-quoted argv>" --json
   ```

   Prefix each title with the short bench title, for example `ACCEPT-3 · Plan`,
   so the bench tabs stand apart from other tabs.

3. Continue at step 7.

On this path, `worktreePath` is the current worktree, not the bench. Check the
bench tabs by their recorded handles and titles, and take cwd evidence from the
`cd <bench>` prefix plus a clean start in `orca terminal read`. Other terminals
in the current worktree are expected; leave them alone.

## Readiness and safety checks

Before reporting success:

- confirm `orca terminal list --worktree path:<bench-path> --json` shows only
  the harness tabs and optional companion, with the expected titles (for a bench
  Orca does not list, find the recorded handles in `orca terminal list --json`
  instead);
- confirm each terminal's `worktreePath` is the bench path, except on the
  unlisted-bench path above;
- confirm each harness wait was satisfied, or each custom harness read showed a
  clean start;
- if a companion exists, read its tab and confirm the command started;
- confirm Work, Plan, and companion use separate tabs, not split panes;
- confirm focus returned to Work; and
- fail closed on missing tabs, unexpected existing terminals in a listed bench
  worktree, or a half-specified companion.

Orca does not report shell pids. Report cwd evidence as the `worktreePath` match
plus the `cd <bench>` prefix on each command, not as an `lsof` check.

## Hosts outside Orca

If `ORCA_TERMINAL_HANDLE` is not set, return to `bench` and use the UI path
selected by the environment.
