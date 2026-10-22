# Bench configuration

`bench` resolves harness and diff-viewer choices from layered TOML files plus
explicit request flags. The resolver is the source of truth for harness argv
values and diff viewer choice. A harness reference may add per-run launch
arguments to that argv before the UI launch. UI references must pass the argv
arrays they receive without rebuilding them.

## Resolver command

Resolve `scripts/resolve_bench_config.py` relative to the loaded `bench` skill
installation, not relative to the source repository. Pass the source repository
with `--repo-root`:

```bash
python3 <bench-skill-dir>/scripts/resolve_bench_config.py \
  --repo-root /path/to/source-repo \
  --brief /tmp/bench-brief.md
```

After a user choice, run the same command again with `--harness-tool`,
`--plan-harness-tool`, and/or `--diff-tool`. Include all earlier explicit
selections on every rerun, so a later Plan, Work, or Diff choice does not drop
an earlier choice.

## Precedence

Configuration is read from lowest to highest precedence:

1. `$XDG_CONFIG_HOME/bench/config.toml`, or `~/.config/bench/config.toml` when
   `XDG_CONFIG_HOME` is unset.
2. `<source-repo>/.bench/config.toml`.
3. Explicit resolver flags for the current request.

Missing files are ignored. Repository values override user values, and explicit
flags override both.

## Onboarding

For first-run Global/Local setup and starter Claude/Codex/Pi configs, read
[Bench onboarding](onboarding.md).

## Schema

The legacy `[harness]` table remains valid. It means the Work harness.

```toml
[harness]
tool = "claude" # ask | claude | codex | pi
permission_mode = "plan"
effort = "high" # optional reasoning effort, see Effort below
prompt = "Read {brief}, then plan before edits."
# command = ["custom-agent", "--instructions", "{brief}"]

[diff]
tool = "auto" # auto | comview | hunk | none

[ui]
pinned = false # pin the bench in ADEs that support it
```

Use `[[harnesses]]` only for advanced benches that need first-class harness tabs
by role.

### Advanced: split Plan and Work

```toml
[[harnesses]]
role = "plan" # plan | work
title = "Plan"
tool = "claude"
permission_mode = "plan"
prompt = "Read {brief}, write a plan, then stop."

[[harnesses]]
role = "work"
title = "Work"
command = ["pi", "--model", "openai-codex/gpt-5.6-astra"]
# No prompt: start Work as an empty interactive agent.

[diff]
tool = "comview"
```

Jcode harnesses use a custom command with no `prompt`. See
[Bench Harness Jcode](harness-jcode.md) for the command shape.

### Effort

`effort` sets the reasoning effort for that role. It is optional, and each
role can have its own, for example `effort = "high"` on Plan and
`effort = "medium"` on Work.

| Harness | Rendered at launch | Accepted levels |
| --- | --- | --- |
| `claude` | `--effort <level>` | low, medium, high, xhigh, max |
| `codex` | `-c model_reasoning_effort="<level>"` | minimal, low, medium, high, xhigh |
| `pi` | `--thinking <level>` | off, minimal, low, medium, high, xhigh, max |
| custom `command` | nothing; reported as `post_launch` | Jcode only; see below |

For presets the resolver checks the level and puts the flag in the argv. For a
custom command the resolver cannot know the flag, so it leaves the argv alone
and reports the level. A harness reference then applies it after launch. Only
Jcode has such a reference today, using `/effort <level>`: see
[Bench Harness Jcode](harness-jcode.md). For any other custom command, `effort`
is an error. Put that tool's own effort flag in `command` instead.

Defaults:

- Missing `[harness]` and missing `[[harnesses]] role = "work"` behaves as Work
  `tool = "ask"`: auto-select the sole installed preset, ask when multiple
  supported presets are installed, and remain unresolved when none is installed.
- Missing legacy `harness.prompt` behaves as
  `"Read {brief}, then plan before edits."`.
- Missing `prompt` in a `[[harnesses]]` entry means no initial prompt for that
  role.
- Missing `title` in a `[[harnesses]]` entry defaults to `Plan` for `plan` and
  `Work` for `work`.
- Missing `[diff]` behaves as `tool = "auto"`.

## Harness roles

Only two roles are supported:

- `plan`: optional. When present, bench creates a first-class Plan tab.
- `work`: required after resolution. If absent, it falls back to the existing
  Work default and selection behavior.

The resolved harness list is ordered as Plan, then Work. Final UI focus returns
to Work.

A config layer must not define both `[harness]` and `[[harnesses]]` with
`role = "work"`. That is ambiguous and resolves as an error.

A higher-precedence layer can remove an inherited role:

```toml
[[harnesses]]
role = "plan"
enabled = false
```

`enabled = false` removes that role from the final harness map. It cannot be
combined with `tool`, `command`, `prompt`, `permission_mode`, `effort`, or
`title`.
Disabling Work is an error unless an explicit Work override is supplied for the
current run.

## Harness rules

- `tool` and `command` are mutually exclusive in the same harness table.
- `command` must be a non-empty argv array of non-empty strings. It is never
  treated as a shell command.
- A higher-precedence `tool` clears inherited `command` and `permission_mode`.
- A higher-precedence `command` clears inherited `tool` and `permission_mode`.
- `effort` is a per-role intent. It layers on its own and survives a `tool` or
  `command` change in a higher layer or an explicit harness flag. A layer that
  omits `effort` keeps the inherited value.
- In legacy `[harness]`, `prompt` layers independently and defaults when
  omitted.
- In `[[harnesses]]`, each role entry resets that role's prompt. Provide
  `prompt` to append one, or omit it to append no prompt.
- Only `{brief}` may be interpolated, and only in command arguments and prompt.
- Claude supports `acceptEdits`, `auto`, `bypassPermissions`, `manual`,
  `dontAsk`, and `plan`; omission defaults to `plan`.
- Codex and Pi reject `permission_mode`; use `command` for custom flags.
- Configured preset and custom harness executables must exist on `PATH`.

Rendered presets with a prompt (each `[effort flag]` appears only when
`effort` is set):

```text
claude --permission-mode <mode> [--effort <level>] <prompt>
codex [-c model_reasoning_effort="<level>"] <prompt>
pi [--thinking <level>] @<brief> <prompt>
```

Rendered presets without a prompt:

```text
claude --permission-mode <mode> [--effort <level>]
codex [-c model_reasoning_effort="<level>"]
pi [--thinking <level>]
```

Custom commands substitute `{brief}` in argv elements. The resolver appends the
rendered prompt as the final argv item only when that harness role has a prompt.

## Request flags

- `--harness-tool claude|codex|pi|ask` selects or overrides Work for this
  request.
- `--plan-harness-tool claude|codex|pi|ask` selects or overrides Plan for this
  request.
- `--diff-tool auto|comview|hunk|none` selects or overrides the diff viewer for
  this request.
- `--effort <level>` and `--plan-effort <level>` set or override the effort for
  Work and Plan for this request. They need that role to exist, and the same
  per-harness checks apply.
- `--pinned` or `--no-pinned` overrides `ui.pinned` for this request.

The resolver knows no harness-specific launch flags. A harness reference that
needs per-run argv, such as the Jcode daemon socket, adds it to the resolved
argv itself before the UI launches the tab.

Explicit harness flags clear inherited `command` and `permission_mode` for their
role. If the role did not exist, the flag creates it with the default prompt
behavior.

## Diff rules

- `tool = "none"` disables the companion diff viewer.
- `tool = "comview"` requires `comview` on `PATH`.
- `tool = "hunk"` requires `hunk` on `PATH`.
- `tool = "auto"` selects the sole installed viewer, resolves to `none` when
  neither viewer is installed, and returns `selection_required` when both are
  installed.

The two-viewer `auto` case deliberately does not choose a winner. The core skill
must ask for Comview, Hunk, or None and rerun the resolver with `--diff-tool`.

## UI rules

`[ui]` holds settings for the bench workspace itself, not for a role. It layers
like `[diff]`: a higher layer overrides a lower one, and `--pinned` or
`--no-pinned` overrides both for one run.

- `pinned` (boolean, default `false`) asks the UI to pin the bench in its
  sidebar. The resolver does not know which UI will run, so it does not check
  support. Supacode and Orca pin. Herdr and native terminals report "pin not
  supported" and continue. A repo `.bench/config.toml` can pin every bench for
  one project.

## JSON output

The resolver keeps the legacy `harness` object. It is the resolved Work harness.
It also returns `harnesses`, the ordered list of first-class harness tabs.

Each harness has a `family` for routing harness references: the preset tool
name (`claude`, `codex`, or `pi`), the executable basename of a custom command
(`jcode` for both `jcode` and `/usr/local/bin/jcode`), or `null` while a
selection is required.

Each harness also has `effort`, the configured level or `null`, and
`effort_applied`:

- `"argv"`: the resolver rendered it into the launch command;
- `"post_launch"`: a Jcode custom command, so the Jcode harness reference applies
  it after launch;
- `null`: no effort is configured.

```json
{
  "harness": {
    "role": "work",
    "title": "Work",
    "family": "pi",
    "effort": null,
    "effort_applied": null,
    "tool": "pi",
    "argv": ["pi", "@/tmp/bench-brief.md", "Read ..."],
    "available": ["claude", "codex", "pi"],
    "selection_required": false
  },
  "harnesses": [
    {
      "role": "plan",
      "title": "Plan",
      "family": "claude",
      "effort": "high",
      "effort_applied": "argv",
      "tool": "claude",
      "argv": ["claude", "--permission-mode", "plan", "--effort", "high", "Read ..."],
      "available": ["claude", "codex", "pi"],
      "selection_required": false
    },
    {
      "role": "work",
      "title": "Work",
      "family": "pi",
      "effort": null,
      "effort_applied": null,
      "tool": "custom",
      "argv": ["pi", "--model", "openai-codex/gpt-5.6-astra"],
      "available": ["claude", "codex", "pi"],
      "selection_required": false
    }
  ],
  "diff": {
    "tool": null,
    "available": ["comview", "hunk"],
    "selection_required": true
  },
  "ui": {
    "pinned": false
  }
}
```

For unresolved `tool = "ask"`, `tool` is `null`, `argv` is empty, and
`selection_required` is `true`. If exactly one supported preset is installed,
`tool = "ask"` resolves to that preset with `selection_required = false`. For
`command`, `tool` is `"custom"` and `argv` contains the rendered command plus a
prompt only when one is configured.

## Advanced split-harness handoff

When Plan and Work both have `family: "claude"`, use the
[Claude-to-Claude handoff](onboarding.md#claude-to-claude-handoff) prompt and
brief wording. Plan writes the approved Work prompt to `{brief}.work.md`, asks
the human, and sends it only on yes to exactly one verified Work session.
Existing configs need their Plan prompt updated to opt in; the resolver does
not rewrite configured prompts or permission modes.

Other split-harness workflows are human-mediated. Plan starts with its
configured prompt. Work can start with no prompt as an empty interactive agent.
The Plan prompt tells the Plan agent to write the plan, stop for approval, and
then produce the exact prompt that the human should paste into Work.

A harness reference can replace that with an orchestrated handoff. Jcode
benches do: see [Bench Harness Jcode](harness-jcode.md).

## Security boundary

The resolver returns argv lists, not shell strings. Callers must execute or pass
these arguments as argv and must not concatenate them into a shell-evaluated
command. Only the literal `{brief}` placeholder is supported so configuration
cannot expand arbitrary environment variables or command substitutions.

## Errors

Resolution fails instead of guessing when configuration is malformed or
conflicting, including:

- unknown top-level, `[harness]`, `[[harnesses]]`, `[diff]`, or `[ui]` keys;
- `[ui]` that is not a table, or a `pinned` value that is not a boolean;
- unknown harness roles;
- duplicate harness roles in one layer;
- `[harness]` plus `[[harnesses]] role = "work"` in one layer;
- empty strings or empty command arrays;
- empty `title` values;
- `enabled = false` combined with other harness fields;
- Work disabled without an explicit Work override;
- unsupported tools or Claude permission modes;
- `tool` combined with `command` in one harness table;
- `permission_mode` with Codex, Pi, Ask, or a custom command;
- an `effort` level the preset does not accept, `effort` on a custom command
  with no harness reference that applies it (anything but Jcode), or `--effort`
  or `--plan-effort` for a role that is not configured;
- unsupported placeholders such as `{ticket}`;
- missing executables for configured harnesses or explicit diff viewers.
