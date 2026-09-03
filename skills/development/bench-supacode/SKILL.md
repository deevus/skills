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

## Open and arrange the finished checkout

Resolve `scripts/setup_bench.py` relative to this skill's directory. Call it once
after the checkout, environment, handoff brief, harness command, and Diff
command are ready:

```bash
BENCH_PATH="<bench-path>" # --path, e.g. /Users/me/Projects/project-task-123
SHORT_TITLE="<short title>" # --title, e.g. "TASK-123 · parser fix"
COLOUR="<colour>" # --color, e.g. blue
DIFF_COMMAND="<watcher>" # --diff-command, e.g. comview watch -- git diff main...HEAD
HARNESS=(claude --permission-mode plan "Read <brief>, then plan before edits.") # after --

python3 <bench-supacode-skill-dir>/scripts/setup_bench.py \
  --path "$BENCH_PATH" \
  --title "$SHORT_TITLE" \
  --color "$COLOUR" \
  --diff-command "$DIFF_COMMAND" \
  -- "${HARNESS[@]}"
```

Use the selected harness command after `--`; the example shows the default from
`bench`. Pass its executable and arguments separately rather than wrapping the
whole command in one quoted argument.

Use the task record for the short title and the project's established colour
convention from its project topic. Do not invent a generic project-specific
rule.

The sidecar owns worktree polling, pre-existing-worktree refusal, explicit
Supacode targets, default-tab and surface checks, `zmx` session discovery,
harness launch, Diff creation, structural verification, and final Work focus.
Do not reproduce those mechanics in the calling shell.

A successful call prints one JSON object with `worktree`, `work_tab`,
`work_surface`, `work_session`, `work_shell_pid`, `diff_tab`, `diff_surface`,
`diff_session`, and `diff_shell_pid`. Preserve it for verification. A non-zero
exit means setup is incomplete; report the error and inspect the existing state
instead of guessing or retrying mutations.

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

The sidecar verifies Supacode structure plus each backing shell's cwd.
Independently confirm the returned shell pids still have the bench cwd:

```bash
lsof -a -d cwd -p <work_shell_pid>
lsof -a -d cwd -p <diff_shell_pid>
```

The harness and Comview watcher inherit that cwd. If either supplied command
changes directory itself, inspect that child process before reporting success.
The sidecar leaves `Work` focused.

## Hosts without Supacode

If `supacode` is not installed, return to `bench` and use the native-only path
or another UI skill selected by the environment.
