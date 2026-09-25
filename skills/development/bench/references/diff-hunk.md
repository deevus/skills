# Bench Diff Hunk

Build the Hunk companion for `bench`. This reference owns Hunk range recipes,
`--watch` command construction, session verification, brief additions, and the
pointer to Hunk's bundled review skill.

Return a generic companion to the UI layer:

```text
companion title: Diff
companion command: <hunk watch command>
```

Do not open terminal tabs here. The selected UI route owns terminal creation
and focus.

## Inputs from bench

Get these facts from `bench` before constructing the command:

- bench path;
- VCS: Git or Jujutsu;
- bench type: task, review, or stack;
- base branch, remote base, or Jujutsu revset;
- review head or local review merge, when applicable; and
- optional path scope.

Stop if the base is unknown. Use the repository's actual base branch or revset
instead of assuming `main` or `trunk()` when the project says otherwise.

## Required review-skill pointer

Before finalizing the brief, resolve the Hunk review skill path from the local
installation:

```bash
hunk skill path hunk-review
```

Record the exact returned path in the brief. Later agents should use that
`hunk-review` skill and `hunk session *` commands to inspect or control the live
session. They must not run interactive Hunk commands in an agent terminal.

## Task bench ranges

For a Jujutsu task bench, show the branch contribution from the fork point:

```bash
hunk diff 'fork_point(trunk() | @)..@' --watch
```

For a Git task bench, calculate the merge base at launch time:

```bash
bash -lc 'base=$(git merge-base "$1" HEAD) || exit; hunk diff "$base" --watch' _ main
```

Substitute the configured Git base branch for the positional `main` argument.

## Review bench ranges

For a Jujutsu review bench, show the review head or local review merge against
the verified base:

```bash
hunk diff 'trunk()..@' --watch
```

For a Git review bench, use the remote PR base when available:

```bash
bash -lc 'base=$(git merge-base "$1" HEAD) || exit; hunk diff "$base" --watch' _ origin/main
```

Substitute the verified remote base for the positional `origin/main` argument.
Do not rebase or mutate the reviewed branch to make the range easier.

## Stack ranges

Choose the range that matches the user's requested stack scope:

- Whole stack in Jujutsu: use the task-bench fork-point range.
- Current Jujutsu layer only: use `@-..@` after verifying `@-` is the lower
  stack parent.
- Whole Git stack: use the merge-base task range.
- Current Git layer only: use `hunk show HEAD --watch` or an explicit lower
  stack branch approved for the review.

Examples:

```bash
hunk diff '@-..@' --watch
hunk show HEAD --watch
```

If the stack base is ambiguous, stop and ask `bench` to get a decision before
launching a companion.

## Path scope

Append path filters only after the range is correct:

```bash
hunk diff 'trunk()..@' --watch -- src tests
bash -lc 'base=$(git merge-base "$1" HEAD) || exit; shift; hunk diff "$base" --watch -- "$@"' _ origin/main src tests
```

Keep range arguments and path arguments separate. For Jujutsu, paths are argv
items after `--`. For Git, keep the shell snippet fixed: pass the base as `$1`,
then `shift` so paths flow through `"$@"` after Hunk's `--` path separator.

The companion command is a string for the UI layer. When that string contains
dynamic argv values such as branches, revsets, or paths, serialize the argv list
with each value shell-quoted as one argument, for example with Python's
`shlex.join(argv)`. Never concatenate untrusted text into the command string.

## Brief additions

Add these items to the handoff brief:

- Hunk is open in the companion tab titled `Diff`.
- The exact Hunk watch command.
- The exact `hunk session get --repo <bench-path> --json` verification command.
- The exact path returned by `hunk skill path hunk-review`.
- Agents must use the returned `hunk-review` skill for live-session review work.
- Agents should inspect the session with `hunk session *`; the TUI is for the
  human terminal.

## Verification

Before `bench` reports success:

1. Confirm `hunk` exists on `PATH` if the resolver did not already fail.
2. Confirm the companion shell starts in the bench path.
3. Verify the live session:

   ```bash
   hunk session get --repo <bench-path> --json
   ```

4. Confirm the returned session is associated with the bench path.
5. Leave the interactive watcher to the human terminal. Do not drive it from an
   agent session.
