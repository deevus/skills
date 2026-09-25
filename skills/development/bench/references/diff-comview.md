# Bench Diff Comview

Build the Comview companion for `bench`. This reference owns Comview range
recipes, watcher command construction, brief additions, and routing later agent
work to the `comview` skill.

Return a generic companion to the UI layer:

```text
companion title: Diff
companion command: <comview watcher command>
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

## Task bench ranges

For a Jujutsu task bench, show the branch contribution from the fork point:

```bash
comview watch -- jj --no-pager diff --git --from 'fork_point(trunk() | @)' --to @
```

For a Git task bench, calculate the merge base at launch time:

```bash
comview watch -- bash -lc 'base=$(git merge-base "$1" HEAD) || exit; git diff "$base" --' _ main
```

Substitute the configured Git base branch for the positional `main` argument.

## Review bench ranges

For a Jujutsu review bench, show the review head or local review merge against
the verified base:

```bash
comview watch -- jj --no-pager diff --git --from 'trunk()' --to @
```

For a Git review bench, use the remote PR base when available:

```bash
comview watch -- bash -lc 'base=$(git merge-base "$1" HEAD) || exit; git diff "$base" --' _ origin/main
```

Substitute the verified remote base for the positional `origin/main` argument.
Do not rebase or mutate the reviewed branch to make the range easier.

## Stack ranges

Choose the range that matches the user's requested stack scope:

- Whole stack in Jujutsu: use the task-bench fork-point range.
- Current Jujutsu layer only: use `@-` to `@` after verifying `@-` is the lower
  stack parent.
- Whole Git stack: use the merge-base task range.
- Current Git layer only: use the parent commit or explicit lower stack branch
  approved for the review.

Examples:

```bash
comview watch -- jj --no-pager diff --git --from @- --to @
comview watch -- git diff HEAD^ --
```

If the stack base is ambiguous, stop and ask `bench` to get a decision before
launching a companion.

## Path scope

Append path filters only after the range is correct:

```bash
comview watch -- jj --no-pager diff --git --from 'trunk()' --to @ -- src tests
comview watch -- bash -lc 'base=$(git merge-base "$1" HEAD) || exit; shift; git diff "$base" -- "$@"' _ origin/main src tests
```

Keep range arguments and path arguments separate. For Jujutsu, paths are argv
items after `--`. For Git, keep the shell snippet fixed: pass the base as `$1`,
then `shift` so paths flow through `"$@"` after Git's `--` path separator.

The companion command is a string for the UI layer. When that string contains
dynamic argv values such as branches, revsets, or paths, serialize the argv list
with each value shell-quoted as one argument, for example with Python's
`shlex.join(argv)`. Never concatenate untrusted text into the command string.

## Brief additions

Add these items to the handoff brief:

- Comview is open in the companion tab titled `Diff`.
- The exact `comview watch` command.
- The exact underlying Git or Jujutsu diff command without `comview watch --`.
- Agents must use the `comview` skill for later comment or review-note work.
- Agents cannot read the interactive TUI. They should inspect the underlying
  diff command noninteractively.
- `.comview/comments.json` is human-managed review state. Treat it as read-only.

## Verification

Before `bench` reports success:

1. Confirm `comview` exists on `PATH` if the resolver did not already fail.
2. Confirm the companion shell starts in the bench path.
3. Run the underlying diff command noninteractively if a smoke check is needed.
4. Leave the interactive watcher to the human terminal. Do not drive it from an
   agent session.
