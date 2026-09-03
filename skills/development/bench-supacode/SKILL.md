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
- Reuse the sole default shell tab as `Work` when setting up a new bench. If the
  worktree already has unexpected tabs or surfaces, stop rather than restructure
  a bench that may be in use.

## Open the finished checkout

Capture the existing worktree ids before opening the checkout. Keep the
captured value in the same shell call as the remaining setup commands.

`supacode repo open <path>` is async and may print nothing. Poll until the new
path appears:

```bash
EXISTING_WORKTREES=$(supacode worktree list)
supacode repo open <bench-path>
supacode worktree list
```

Derive `WT` from the new `worktree list`; it is usually the percent-encoded
path. Abort before changing appearance or tabs if that id existed before the
open:

```bash
if printf '%s\n' "$EXISTING_WORKTREES" | grep -Fx "$WT" >/dev/null; then
  printf 'Bench worktree already existed; refusing to restructure %s\n' "$WT" >&2
  exit 1
fi

supacode worktree appearance -w "$WT" --title "<short title>" --color <colour>
```

Use the task record for a short title. Use the project's established colour
convention from its project topic; do not invent a generic project-specific
rule.

## Reuse the default tab and create Diff

Opening a worktree leaves one default shell tab with one surface. Require that
one-tab, one-surface structure before continuing. Reuse the default as `Work`
and create only `Diff`.

Run the related commands in one shell call so the captured ids remain
available:

```bash
set -euo pipefail

WORK_TAB=$(supacode tab list -w "$WT")
TAB_COUNT=$(printf '%s\n' "$WORK_TAB" |
  awk 'NF { count++ } END { print count + 0 }')
if [ "$TAB_COUNT" -ne 1 ]; then
  printf 'Expected one default tab; refusing to restructure %s\n' "$WT" >&2
  exit 1
fi

WORK_SURFACE=$(supacode surface list -w "$WT" -t "$WORK_TAB")
SURFACE_COUNT=$(printf '%s\n' "$WORK_SURFACE" |
  awk 'NF { count++ } END { print count + 0 }')
if [ "$SURFACE_COUNT" -ne 1 ]; then
  printf 'Expected one Work surface; refusing to restructure %s\n' "$WT" >&2
  exit 1
fi

if [ "$WORK_SURFACE" = "$WORK_TAB" ]; then
  printf 'Expected the default tab surface to have a distinct id\n' >&2
  exit 1
fi

WORK_SESSION="supa-$(printf '%s' "$WORK_SURFACE" | tr '[:upper:]' '[:lower:]')"
zmx list --short | grep -Fx "$WORK_SESSION" >/dev/null

supacode tab rename -w "$WT" -t "$WORK_TAB" --title Work
zmx run "$WORK_SESSION" -d <harness command and arguments>
DIFF_TAB=$(supacode tab new -w "$WT" --title Diff \
  -i "<comview watcher command>")
supacode tab focus -w "$WT" -t "$WORK_TAB"
```

The `zmx` session name comes from the surface id, not the tab id. Supacode names
each backing session `supa-<lowercase surface UUID>`. The checks abort before
renaming if the layout is unexpected or the exact session is absent. Pass the
harness command and its arguments directly after `-d`; do not quote the whole
command as one argument.

`zmx run -d` launches the harness in the existing shell without waiting for it
to exit. Do not split the default shell for the harness; the finished `Work` tab
must contain one surface.

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
