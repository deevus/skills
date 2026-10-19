# Bench Supacode

Supacode terminal mechanics for a bench. Use this reference only after the core
`bench` workflow has created the native workspace and selected Supacode routing.

## Principles

- Create the checkout with the repo's native VCS first. Do not use
  `supacode worktree-new`; it can copy VCS metadata such as `.jj`.
- Always pass explicit Supacode targets. Pane and tab commands default to the
  agent's own tab, not the bench.
- Reuse the sole default shell tab for the first harness tab. In the default
  workflow that tab is `Work`; in split mode it is usually `Plan`.
- Create additional first-class harness tabs only from the ordered harness tab
  specs supplied by `bench`.
- Create a companion tab only when `bench` provides both companion title and
  companion command.
- If the worktree already has unexpected tabs or panes, stop rather than
  restructure a bench that may be in use. The only exception is a stale tab
  restored from the saved Supacode layout for this exact path. The sidecar may
  close those tabs only after every restored tab proves to be a single idle
  shell in the bench, and it never writes Supacode's saved layouts.
- Do not detect viewers, construct companion commands, or add review semantics
  in this reference.

## Open and arrange the finished checkout

Resolve `scripts/setup_bench.py` relative to the loaded `bench` skill directory.
Call it once after the checkout, environment, handoff brief, harness tab specs,
and optional companion input are ready.

Use the multi-harness path when `bench` returns `harnesses`:

```bash
BENCH_PATH="<bench-path>" # --path, e.g. /Users/me/Projects/project-task-123
SHORT_TITLE="<short title>" # --title, e.g. "TASK-123 · parser fix"
COLOUR="<colour>" # --color, e.g. blue
PIN_ARGS=() # Optional --pin; use PIN_ARGS=(--pin) to pin the new worktree.

HARNESS_TABS_JSON='[
  {
    "role": "plan",
    "title": "Plan",
    "argv": ["claude", "--permission-mode", "plan", "Read <brief>"]
  },
  {
    "role": "work",
    "title": "Work",
    "argv": ["pi", "--model", "openai-codex/gpt-5.6-astra"]
  }
]'

COMPANION_ARGS=()
if [[ -n ${COMPANION_TITLE:-} || -n ${COMPANION_COMMAND:-} ]]; then
  if [[ -z ${COMPANION_TITLE:-} || -z ${COMPANION_COMMAND:-} ]]; then
    echo "companion title and command must be specified together" >&2
    exit 1
  fi
  COMPANION_ARGS=(
    --companion-title "$COMPANION_TITLE"
    --companion-command "$COMPANION_COMMAND"
  )
fi

python3 <bench-skill-dir>/scripts/setup_bench.py \
  --path "$BENCH_PATH" \
  --title "$SHORT_TITLE" \
  --color "$COLOUR" \
  --harness-tabs-json "$HARNESS_TABS_JSON" \
  "${COMPANION_ARGS[@]}" \
  "${PIN_ARGS[@]}"
```

Each harness tab object must contain:

- `role`: `plan` or `work`;
- `title`: non-empty tab title; and
- `argv`: non-empty argv array.

Exactly one Work harness tab is required. The sidecar creates harness tabs in
the supplied order and focuses Work at the end.

For compatibility, the sidecar still accepts the old single-harness form:

```bash
HARNESS=(claude --permission-mode plan "Read <brief>, then plan before edits.")

python3 <bench-skill-dir>/scripts/setup_bench.py \
  --path "$BENCH_PATH" \
  --title "$SHORT_TITLE" \
  --color "$COLOUR" \
  "${COMPANION_ARGS[@]}" \
  "${PIN_ARGS[@]}" \
  -- "${HARNESS[@]}"
```

Use the selected harness argv after `--`. Pass the executable and arguments
separately. Do not wrap the whole harness in one quoted argument. Do not combine
`--harness-tabs-json` with a harness argv remainder.

If there is no companion, omit `--companion-title` and `--companion-command`
entirely. Do not pass empty strings. The sidecar also rejects half-specified
pairs before mutating Supacode.

Use the task record for the short title and the project's established colour
convention from its project topic. Do not invent a generic project-specific
rule.

The sidecar owns worktree and default-tab polling, pre-existing-worktree
refusal, optional pinning, stale-layout tab cleanup, explicit Supacode targets,
default-tab and pane checks, `zmx` session discovery, harness launch, optional
companion creation, structural verification, and final Work focus. New tabs go
into the bench's single pane. Do not reproduce those mechanics in the calling
shell.

A successful call prints one JSON object. Use these fields:

- `harness_tabs[].shell_pid` and `companion_shell_pid`: verify each shell's cwd
  as described below. `companion_shell_pid` is null when there is no companion.
- `closed_restored_tabs`: report any stale restored tab ids that setup closed in
  the bench result summary.

A non-zero exit means setup is incomplete. Report the error and inspect the
existing state instead of guessing or retrying mutations.

## Reused bench paths

Supacode saves a layout for each worktree path in the UserDefaults domain
`app.supabit.supacode`, under the key `layoutsFile`. Inside it, each worktree is
keyed by its absolute path with a trailing slash. If a checkout is removed
outside Supacode, or while Supacode is closed, that entry can become an orphan.
Reopening a bench at the same path can restore the old tabs and add one fresh
default tab.

The sidecar reads the saved layout with `defaults export app.supabit.supacode -`
before `supacode repo open`. It uses the saved tab ids to identify restored tabs
after the open. It then keeps the one fresh default tab and closes only the
restored tabs that prove safe: a matching `supa-<content id>` zmx session, one
attached Supacode client, a shell that starts and remains in the bench, and no
child processes. Closing a restored tab kills its zmx session, so these idle
checks are mandatory. The content id equals the tab id for tabs Supacode
creates. A restored tab can carry a different content id, so the sidecar takes
it from the saved layout. Any failed check aborts setup before closing anything.

The sidecar never writes Supacode's saved layouts.

For teardown, remove or archive benches with `supacode worktree delete -w <WT>`
while the worktree is still open in Supacode. That lets Supacode prune the
layout entry. Removing the checkout by hand leaves an orphan entry, which setup
now tolerates. A teardown script is out of scope here and is tracked as a
follow-up issue after this lands.

## Target every command

Use explicit `-w`, `-t`, and `--pane` where applicable:

```bash
supacode tab list -w <WT>
supacode pane list -w <WT>
supacode tab new -w <WT> --pane <PANE> --title <T>
supacode tab focus -w <WT> -t <TAB>
```

`supacode surface` is deprecated. The sidecar does not use it. Bare
`supacode tab list` or `supacode pane list` without `-w` proves nothing about
the bench. It may show the current agent tab.

## Verify before reporting success

The sidecar verifies Supacode structure plus each backing shell's cwd.
Independently confirm the returned shell pids still have the bench cwd:

```bash
# For each entry in harness_tabs:
lsof -a -d cwd -p <harness_shell_pid>
# Only when companion_shell_pid is not null:
lsof -a -d cwd -p <companion_shell_pid>
```

If a supplied command changes directory itself, inspect that child process
before reporting success. The sidecar leaves `Work` focused.

## Hosts without Supacode

If `supacode` is not installed, return to `bench` and use the native-only path
or Herdr path selected by the environment.
