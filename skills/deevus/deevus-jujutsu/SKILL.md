---
name: deevus-jujutsu
description:
  Use when working in a Jujutsu repository with pushed bookmarks, open pull
  requests, rebases, or merge/rebase conflicts.
---

# Jujutsu Workflow

Workflow overlay for jj repositories: when this conflicts with generic jj
guidance, follow this skill.

## Core rule

Treat pushed bookmarks as append-only by default.

For any follow-up change on a branch, reviewed or not:

```bash
jj new -m "<message>"
# edit files
jj bookmark move <bookmark> --to @
jj git push --dry-run -b <bookmark>
# only if dry-run does NOT say "move sideways"
jj git push -b <bookmark>
```

Amend, squash, absorb, or rebase only when explicitly asked to rewrite history.
Extra commits cost nothing because the merge squashes them.

## The jj trap

When `@` is the bookmark commit, editing files amends that commit silently.
Amending is jj's default behaviour, so the next push is a sideways/force push
unless the remote already points at the rewritten commit.

The tell is dry-run output like:

```text
move sideways from X to Y
```

That is a force push. If a dry-run shows this and it was not explicitly
requested, do not run the real push. Recover before doing anything else:

```bash
jj undo
jj st
jj --no-pager bookmark list
```

Then recreate the follow-up as a child commit before dry-running the push again.

## Before pushing an open PR

Do not edit or rewrite the bookmarked commit. Start follow-up work from a child
commit before pushing:

```bash
jj new -m "<message>"
# edit files
jj bookmark move <bookmark> --to @
jj git push --dry-run -b <bookmark>
# only if dry-run does NOT say "move sideways"
jj git push -b <bookmark>
```

GitHub example for checking review state:

```bash
gh pr view <number> --json reviews
```

If the dry-run prints `move sideways from X to Y`, use the `jj undo` recovery
above instead of pushing.

Do not try to pass Git flags such as `--no-force` through `jj git push -o`.
`-o/--option` sends Git push options to the remote server; it does not make jj
fast-forward-only.

## Rebasing

Use native jj workspaces for rebasing jj-backed repos instead of git
checkout/rebase.

```bash
jj workspace add ../rebase-work
cd ../rebase-work
jj rebase -d <destination>
```

Do not switch into git checkout/rebase workflows for jj repositories unless the
user explicitly asks for that.

## Conflicts

Resolve merge/rebase conflicts with targeted conflict-region edits. Preserve
unrelated file content and surrounding history context.

Do not rewrite whole files to resolve conflicts.

## Common mistakes

- Following generic jj "commits are mutable" advice on a pushed bookmark.
- Editing the bookmark commit directly, then treating the push as routine.
- Skipping `jj git push --dry-run` before a real push.
- Missing `move sideways from X to Y` in dry-run output.
- Checking review state after pushing instead of before pushing.
- Using git checkout/rebase in a jj-backed repo.
- Replacing whole conflicted files instead of editing only conflict regions.
