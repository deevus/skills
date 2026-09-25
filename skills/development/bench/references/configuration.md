# Bench configuration

`bench` resolves harness and diff-viewer choices from layered TOML files plus
explicit request flags. The resolver is the source of truth for final harness
argv values and diff viewer choice. UI references must pass returned argv arrays
without rebuilding them.

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

## First-run setup

When neither configuration file exists, `bench` resolves installed tools and
then initializes one configuration file before creating the workspace. The setup
asks whether to create a Global file for future repositories or a Local file for
the current repository:

- Global: `$XDG_CONFIG_HOME/bench/config.toml`, falling back to
  `~/.config/bench/config.toml`.
- Local: `<source-repo>/.bench/config.toml`.

Starter configurations intentionally use one Work tab. The same harness plans
before editing and then performs the work. Split Plan/Work tabs are supported,
but they are advanced configuration rather than the onboarding default.

Harness discovery for `tool = "ask"` uses this matrix:

| Installed Claude/Pi presets | Result                                                             |
| --------------------------- | ------------------------------------------------------------------ |
| none                        | Unresolved; bench reports installation or custom-command guidance. |
| one                         | The sole preset is selected automatically.                         |
| both                        | The user selects Claude starter or Pi starter.                     |

Resolver errors, malformed TOML, and unresolved selections never write
configuration. Explicit configured tools still require their executable on
`PATH`. Custom commands are not auto-detected.

## Starter configurations

Use the Claude starter when Claude is the preferred single Work harness:

```toml
[harness]
tool = "claude"
permission_mode = "plan"
prompt = "Read {brief}, then plan before edits."

[diff]
tool = "auto"
```

Use the Pi starter when Pi is the preferred single Work harness:

```toml
[harness]
tool = "pi"
prompt = "Read {brief}, then plan before edits."

[diff]
tool = "auto"
```

The copy-ready examples use `diff.tool = "auto"` so installing or removing
Comview or Hunk changes the companion automatically. First-run initialization
materializes the final resolved Diff value instead: `comview`, `hunk`, or
`none`.

## Schema

The legacy `[harness]` table remains valid. It means the Work harness.

```toml
[harness]
tool = "claude" # ask | claude | pi
permission_mode = "plan"
prompt = "Read {brief}, then plan before edits."
# command = ["custom-agent", "--instructions", "{brief}"]

[diff]
tool = "auto" # auto | comview | hunk | none
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

Defaults:

- Missing `[harness]` and missing `[[harnesses]] role = "work"` behaves as Work
  `tool = "ask"`: auto-select the sole installed preset, ask when both Claude
  and Pi are installed, and remain unresolved when neither is installed.
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
combined with `tool`, `command`, `prompt`, `permission_mode`, or `title`.
Disabling Work is an error unless an explicit Work override is supplied for the
current run.

## Harness rules

- `tool` and `command` are mutually exclusive in the same harness table.
- `command` must be a non-empty argv array of non-empty strings. It is never
  treated as a shell command.
- A higher-precedence `tool` clears inherited `command` and `permission_mode`.
- A higher-precedence `command` clears inherited `tool` and `permission_mode`.
- In legacy `[harness]`, `prompt` layers independently and defaults when
  omitted.
- In `[[harnesses]]`, each role entry resets that role's prompt. Provide
  `prompt` to append one, or omit it to append no prompt.
- Only `{brief}` may be interpolated, and only in command arguments and prompt.
- Claude supports `acceptEdits`, `auto`, `bypassPermissions`, `manual`,
  `dontAsk`, and `plan`; omission defaults to `plan`.
- Pi rejects `permission_mode`; use `command` for custom Pi flags.
- Configured preset and custom harness executables must exist on `PATH`.

Rendered presets with a prompt:

```text
claude --permission-mode <mode> <prompt>
pi @<brief> <prompt>
```

Rendered presets without a prompt:

```text
claude --permission-mode <mode>
pi
```

Custom commands substitute `{brief}` in argv elements. The resolver appends the
rendered prompt as the final argv item only when that harness role has a prompt.

## Request flags

- `--harness-tool claude|pi|ask` selects or overrides Work for this request.
- `--plan-harness-tool claude|pi|ask` selects or overrides Plan for this
  request.
- `--diff-tool auto|comview|hunk|none` selects or overrides the diff viewer for
  this request.

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

## JSON output

The resolver keeps the legacy `harness` object. It is the resolved Work harness.
It also returns `harnesses`, the ordered list of first-class harness tabs.

```json
{
  "harness": {
    "role": "work",
    "title": "Work",
    "tool": "pi",
    "argv": ["pi", "@/tmp/bench-brief.md", "Read ..."],
    "available": ["claude", "pi"],
    "selection_required": false
  },
  "harnesses": [
    {
      "role": "plan",
      "title": "Plan",
      "tool": "claude",
      "argv": ["claude", "--permission-mode", "plan", "Read ..."],
      "available": ["claude", "pi"],
      "selection_required": false
    },
    {
      "role": "work",
      "title": "Work",
      "tool": "custom",
      "argv": ["pi", "--model", "openai-codex/gpt-5.6-astra"],
      "available": ["claude", "pi"],
      "selection_required": false
    }
  ],
  "diff": {
    "tool": null,
    "available": ["comview", "hunk"],
    "selection_required": true
  }
}
```

For unresolved `tool = "ask"`, `tool` is `null`, `argv` is empty, and
`selection_required` is `true`. If exactly one supported preset is installed,
`tool = "ask"` resolves to that preset with `selection_required = false`. For
`command`, `tool` is `"custom"` and `argv` contains the rendered command plus a
prompt only when one is configured.

## Advanced split-harness handoff

The first split-harness workflow is human-mediated. Plan starts with its
configured prompt. Work can start with no prompt as an empty interactive agent.
The Plan prompt should tell the Plan agent to write the plan, stop for approval,
and then produce the exact prompt that the human should paste into Work.

## Security boundary

The resolver returns argv lists, not shell strings. Callers must execute or pass
these arguments as argv and must not concatenate them into a shell-evaluated
command. Only the literal `{brief}` placeholder is supported so configuration
cannot expand arbitrary environment variables or command substitutions.

## Errors

Resolution fails instead of guessing when configuration is malformed or
conflicting, including:

- unknown top-level, `[harness]`, `[[harnesses]]`, or `[diff]` keys;
- unknown harness roles;
- duplicate harness roles in one layer;
- `[harness]` plus `[[harnesses]] role = "work"` in one layer;
- empty strings or empty command arrays;
- empty `title` values;
- `enabled = false` combined with other harness fields;
- Work disabled without an explicit Work override;
- unsupported tools or Claude permission modes;
- `tool` combined with `command` in one harness table;
- `permission_mode` with Pi, Ask, or a custom command;
- unsupported placeholders such as `{ticket}`;
- missing executables for configured harnesses or explicit diff viewers.
