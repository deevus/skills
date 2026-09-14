---
name: bench-supacode
description:
  Use when a bench workspace must be opened, arranged, verified, or operated in
  Supacode.
---

# Bench Supacode

Supacode terminal mechanics for a bench. If `bench` has not already been loaded
for this request, load `bench` first and follow its generic workflow before
doing these UI steps.

## Principles

- Create the checkout with the repo's native VCS first. Do not use
  `supacode worktree-new`; it can copy VCS metadata such as `.jj`.
- Always pass explicit Supacode targets. Surface and tab commands default to the
  agent's own tab, not the bench.
- Reuse the sole default shell tab for the first harness tab. In the default
  workflow that tab is `Work`; in split mode it is usually `Plan`.
- Create additional first-class harness tabs only from the ordered harness tab
  specs supplied by `bench`.
- Create a companion tab only when `bench` provides both companion title and
  companion command.
- If the worktree already has unexpected tabs or surfaces, stop rather than
  restructure a bench that may be in use. The only exception is a stale tab
  restored from the saved Supacode layout for this exact path. The sidecar may
  close those tabs only after every restored tab proves to be a single idle
  shell in the bench, and it never writes `layouts.json`.
- Do not detect viewers, construct companion commands, or add review semantics
  in this skill.

## Open and arrange the finished checkout

Resolve `scripts/setup_bench.py` relative to this skill's directory. Call it
once after the checkout, environment, handoff brief, harness tab specs, and
optional companion input are ready.

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

python3 <bench-supacode-skill-dir>/scripts/setup_bench.py \
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

python3 <bench-supacode-skill-dir>/scripts/setup_bench.py \
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

The sidecar owns worktree polling, pre-existing-worktree refusal, optional
pinning, stale-layout tab cleanup, explicit Supacode targets, default-tab and
surface checks, `zmx` session discovery, harness launch, optional companion
creation, structural verification, and final Work focus. Do not reproduce those
mechanics in the calling shell.

A successful call prints one JSON object with these fields:

```json
{
  "worktree": "...",
  "work_tab": "...",
  "work_surface": "...",
  "work_session": "...",
  "work_shell_pid": 123,
  "harness_tabs": [
    {
      "role": "plan",
      "title": "Plan",
      "tab": "...",
      "surface": "...",
      "session": "...",
      "shell_pid": 122
    },
    {
      "role": "work",
      "title": "Work",
      "tab": "...",
      "surface": "...",
      "session": "...",
      "shell_pid": 123
    }
  ],
  "companion_tab": null,
  "companion_surface": null,
  "companion_session": null,
  "companion_shell_pid": null,
  "pinned": false,
  "closed_restored_tabs": []
}
```

The legacy `work_*` fields always describe the Work harness tab. The
`harness_tabs` array describes every first-class harness tab.
`closed_restored_tabs` lists any stale restored tab ids that setup closed; report
those ids in the bench result summary.

When a companion is requested, all `companion_*` fields must be non-null. When
no companion is requested, all `companion_*` fields must be null. A non-zero
exit means setup is incomplete. Report the error and inspect the existing state
instead of guessing or retrying mutations.

## Reused bench paths

Supacode saves a layout for each worktree path in
`~/.supacode/layouts.json`. The key is the absolute path with a trailing slash.
If a checkout is removed outside Supacode, or while Supacode is closed, that
entry can become an orphan. Reopening a bench at the same path can restore the
old tabs and add one fresh default tab.

The sidecar reads the saved layout before `supacode repo open`. It uses the
saved tab ids to identify restored tabs after the open. It then keeps the one
fresh default tab and closes only the restored tabs that prove safe: exactly one
surface, a matching `supa-<surface>` zmx session, one attached Supacode client,
a shell that starts and remains in the bench, and no child processes. Closing a
restored tab kills its zmx session, so these idle checks are mandatory. Any
failed check aborts setup before closing anything.

The sidecar never edits `layouts.json`. The `--layouts-file` flag exists only as
a test seam; normal callers should not pass it.

For teardown, remove or archive benches with
`supacode worktree delete -w <WT>` while the worktree is still open in Supacode.
That lets Supacode prune the layout entry. Removing the checkout by hand leaves
an orphan entry, which setup now tolerates. A teardown script is out of scope
here and is tracked as a follow-up issue after this lands.

## Target every command

Use explicit `-w`, `-t`, and `-s` where applicable:

```bash
supacode tab list -w <WT>
supacode surface list -w <WT> -t <TAB>
supacode surface focus -w <WT> -t <TAB> -s <SURFACE>
```

Bare `supacode surface list` proves nothing about the bench. It may show the
current agent tab.

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
or another UI skill selected by the environment.
