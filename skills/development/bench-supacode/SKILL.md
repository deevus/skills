---
name: bench-supacode
description:
  Use when a bench workspace must be opened, arranged, verified, or operated in
  Supacode.
---

# Bench Supacode

Supacode terminal mechanics for a bench. If `bench` has not already been loaded
for this request, load `bench` first and follow its generic workflow before doing
these UI steps.

## Principles

- Create the checkout with the repo's native VCS first. Do not use
  `supacode worktree-new`; it can copy VCS metadata such as `.jj`.
- Always pass explicit Supacode targets. Surface and tab commands default to the
  agent's own tab, not the bench.
- Reuse the sole default shell tab as `Work` when setting up a new bench.
- Create a companion tab only when `bench` provides both companion title and
  companion command.
- If the worktree already has unexpected tabs or surfaces, stop rather than
  restructure a bench that may be in use.
- Do not detect viewers, construct companion commands, or add review semantics
  in this skill.

## Open and arrange the finished checkout

Resolve `scripts/setup_bench.py` relative to this skill's directory. Call it once
after the checkout, environment, handoff brief, harness argv, and optional
companion input are ready.

Build companion flags only when both companion values are present:

```bash
BENCH_PATH="<bench-path>" # --path, e.g. /Users/me/Projects/project-task-123
SHORT_TITLE="<short title>" # --title, e.g. "TASK-123 · parser fix"
COLOUR="<colour>" # --color, e.g. blue
PIN_ARGS=() # Optional --pin; use PIN_ARGS=(--pin) to pin the new worktree.
HARNESS=(claude --permission-mode plan "Read <brief>, then plan before edits.")

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
  "${COMPANION_ARGS[@]}" \
  "${PIN_ARGS[@]}" \
  -- "${HARNESS[@]}"
```

Use the selected harness argv after `--`. Pass the executable and arguments
separately. Do not wrap the whole harness in one quoted argument.

If there is no companion, omit `--companion-title` and `--companion-command`
entirely. Do not pass empty strings. The sidecar also rejects half-specified
pairs before mutating Supacode.

Use the task record for the short title and the project's established colour
convention from its project topic. Do not invent a generic project-specific
rule.

The sidecar owns worktree polling, pre-existing-worktree refusal, optional
pinning, explicit Supacode targets, default-tab and surface checks, `zmx`
session discovery, harness launch, optional companion creation, structural
verification, and final Work focus. Do not reproduce those mechanics in the
calling shell.

A successful call prints one JSON object with these fields:

```json
{
  "worktree": "...",
  "work_tab": "...",
  "work_surface": "...",
  "work_session": "...",
  "work_shell_pid": 123,
  "companion_tab": null,
  "companion_surface": null,
  "companion_session": null,
  "companion_shell_pid": null,
  "pinned": false
}
```

When a companion is requested, all `companion_*` fields must be non-null. When no
companion is requested, all `companion_*` fields must be null. A non-zero exit
means setup is incomplete. Report the error and inspect the existing state
instead of guessing or retrying mutations.

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
lsof -a -d cwd -p <work_shell_pid>
# Only when companion_shell_pid is not null:
lsof -a -d cwd -p <companion_shell_pid>
```

If a supplied command changes directory itself, inspect that child process before
reporting success. The sidecar leaves `Work` focused.

## Hosts without Supacode

If `supacode` is not installed, return to `bench` and use the native-only path or
another UI skill selected by the environment.
