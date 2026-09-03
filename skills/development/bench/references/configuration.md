# Bench configuration

`bench` resolves harness and diff-viewer choices from layered TOML files plus
explicit request flags. The resolver is the source of truth for final harness
argv; UI skills must pass the returned argv without rebuilding it.

## Resolver command

```bash
python3 skills/development/bench/scripts/resolve_bench_config.py \
  --repo-root /path/to/source-repo \
  --brief /tmp/bench-brief.md
```

After a user choice, run the same command again with `--harness-tool` and/or
`--diff-tool`.

## Precedence

Configuration is read from lowest to highest precedence:

1. `$XDG_CONFIG_HOME/bench/config.toml`, or `~/.config/bench/config.toml` when
   `XDG_CONFIG_HOME` is unset.
2. `<source-repo>/.bench/config.toml`.
3. Explicit resolver flags for the current request.

Missing files are ignored. Repository values override user values, and explicit
flags override both.

## Schema

```toml
[harness]
tool = "claude" # ask | claude | pi
permission_mode = "plan"
prompt = "Read {brief}, then plan before edits."
# command = ["custom-agent", "--instructions", "{brief}"]

[diff]
tool = "auto" # auto | comview | hunk | none
```

Defaults:

- Missing `[harness]` behaves as `tool = "ask"`.
- Missing `harness.prompt` behaves as
  `"Read {brief}, then plan before edits."`.
- Missing `[diff]` behaves as `tool = "auto"`.

## Harness rules

- `harness.tool` and `harness.command` are mutually exclusive in the same
  configuration layer.
- `harness.command` must be a non-empty argv array of non-empty strings. It is
  never treated as a shell command.
- A higher-precedence `harness.tool` clears an inherited custom command.
- A higher-precedence `harness.command` clears inherited `tool` and
  `permission_mode`.
- `prompt` layers independently and is appended as the final argv item for
  configured harnesses.
- Only `{brief}` may be interpolated, and only in command arguments and prompt.
- Claude supports `acceptEdits`, `auto`, `bypassPermissions`, `manual`,
  `dontAsk`, and `plan`; omission defaults to `plan`.
- Pi rejects `permission_mode`; use `harness.command` for custom Pi flags.
- Configured preset and custom harness executables must exist on `PATH`.

Rendered presets:

```text
claude --permission-mode <mode> <prompt>
pi @<brief> <prompt>
```

Custom commands substitute `{brief}` in argv elements, then append the rendered
prompt as one final argv item.

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

```json
{
  "harness": {
    "tool": "claude",
    "argv": ["claude", "--permission-mode", "plan", "..."],
    "available": ["claude", "pi"],
    "selection_required": false
  },
  "diff": {
    "tool": null,
    "available": ["comview", "hunk"],
    "selection_required": true
  }
}
```

For `harness.tool = "ask"`, `harness.tool` is `null`, `argv` is empty, and
`selection_required` is `true`. For `harness.command`, `harness.tool` is
`"custom"` and `argv` contains the rendered command plus prompt.

## Security boundary

The resolver returns argv lists, not shell strings. Callers must execute or pass
these arguments as argv and must not concatenate them into a shell-evaluated
command. Only the literal `{brief}` placeholder is supported so configuration
cannot expand arbitrary environment variables or command substitutions.

## Errors

Resolution fails instead of guessing when configuration is malformed or
conflicting, including:

- unknown top-level, `[harness]`, or `[diff]` keys;
- empty strings or empty command arrays;
- unsupported tools or Claude permission modes;
- `harness.tool` combined with `harness.command` in one layer;
- `permission_mode` with Pi, Ask, or a custom command;
- unsupported placeholders such as `{ticket}`;
- missing executables for configured harnesses or explicit diff viewers.
