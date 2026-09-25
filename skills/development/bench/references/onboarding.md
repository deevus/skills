# Bench onboarding

First-run onboarding is for a teammate with no user or repository bench config.
It creates one starter config before bench creates the workspace.

## First-run setup

When neither configuration file exists, `bench` resolves installed tools and
then initializes one configuration file. Ask whether to create a Global file or
a Local file:

- Global: `$XDG_CONFIG_HOME/bench/config.toml`, falling back to
  `~/.config/bench/config.toml`.
- Local: `<source-repo>/.bench/config.toml`.

After choosing Global or Local, ask which workflow shape to initialize:

1. Simple starter — one Work tab. Recommended.
2. Advanced split — Plan tab plus Work tab.

The simple starter uses one Work tab. The same harness plans before editing and
then performs the work. The advanced split starts a Plan harness and a separate
Work harness. It is available for users who want to try separate planning and
implementation agents.

Harness discovery for `tool = "ask"` uses this matrix:

| Installed Claude/Codex/Pi presets | Result                                                             |
| --------------------------------- | ------------------------------------------------------------------ |
| none                              | Unresolved; bench reports installation or custom-command guidance. |
| one                               | The sole preset is selected automatically.                         |
| multiple                          | The user selects Claude, Codex, or Pi starter.                     |

Resolver errors, malformed TOML, and unresolved selections never write
configuration. Explicit configured tools still require their executable on
`PATH`. Custom commands are not auto-detected.

## Simple starter configurations

Use the Claude starter when Claude is the preferred single Work harness. Pin the
model to the current state-of-the-art minus one model. At the moment, use Opus
5.5 rather than Fable so the starter does not burn through limits.

```toml
[harness]
command = ["claude", "--model", "claude-opus-5-5", "--permission-mode", "plan"]
prompt = "Read {brief}, then plan before edits."

[diff]
tool = "auto"
```

Use the Codex starter when Codex is the preferred single Work harness. Codex
model selection depends on the local Codex CLI setup, so this starter uses the
user's Codex defaults.

```toml
[harness]
tool = "codex"
prompt = "Read {brief}, then plan before edits."

[diff]
tool = "auto"
```

If a team has a standard Codex model, replace `tool = "codex"` with a command
that names that model, for example:

```toml
[harness]
command = ["codex", "--model", "<team-codex-model>"]
prompt = "Read {brief}, then plan before edits."
```

Replace `<team-codex-model>` before use.

Use the Pi starter when Pi is the preferred single Work harness. Pi model
selection depends on the local Pi environment, so this starter uses the user's
Pi defaults.

```toml
[harness]
tool = "pi"
prompt = "Read {brief}, then plan before edits."

[diff]
tool = "auto"
```

If a team has a standard Pi model, replace `tool = "pi"` with a command that
names that model, for example:

```toml
[harness]
command = ["pi", "--model", "<team-pi-model>"]
prompt = "Read {brief}, then plan before edits."
```

Replace `<team-pi-model>` before use.

The copy-ready examples use `diff.tool = "auto"` so installing or removing
Comview or Hunk changes the companion automatically. First-run initialization
materializes the final resolved Diff value instead: `comview`, `hunk`, or
`none`.

## Advanced split configuration

Use the advanced split when the user wants separate Plan and Work tabs. Ask for
the Plan harness and the Work harness from the installed presets. If only one
preset is installed, tell the user only one harness is available and use it for
both tabs unless they cancel.

The Plan harness gets a prompt. It must read the brief, write a plan, stop for
approval, and write the final Work prompt to a file. The human can then provide
that file to the Work tab after approving the plan. The Work harness starts
without a prompt.

Use this Plan prompt:

```text
Read {brief}, then write a plan before edits. When the plan is ready, stop and wait for approval. Write the final Work prompt to a file next to the brief so the human can provide it to the Work agent after approving the plan.
```

A split config with Claude for Plan and Pi for Work looks like this:

```toml
[[harnesses]]
role = "plan"
title = "Plan"
command = ["claude", "--model", "claude-opus-5-5", "--permission-mode", "plan"]
prompt = "Read {brief}, then write a plan before edits. When the plan is ready, stop and wait for approval. Write the final Work prompt to a file next to the brief so the human can provide it to the Work agent after approving the plan."

[[harnesses]]
role = "work"
title = "Work"
tool = "pi"

[diff]
tool = "auto"
```

For other harness choices, use the selected harness's simple starter command or
tool. Keep the Plan prompt. Omit the Work prompt so Work starts empty.

## Diff companion recommendation

When no diff viewer is installed, recommend installing Hunk from
<https://www.hunk.dev/>. The quick install command is:

```bash
curl -fsSL https://hunk.dev/install.sh | sh
```

Comview is an available alternative at <https://github.com/rockorager/comview>.
Keep starter configs on `diff.tool = "auto"` so bench can use either viewer
after installation.

## First-run files to write

When first-run initialization writes the Claude starter, materialize the final
Diff choice:

```toml
[harness]
command = ["claude", "--model", "claude-opus-5-5", "--permission-mode", "plan"]
prompt = "Read {brief}, then plan before edits."

[diff]
tool = "<resolved-diff-tool>"
```

When first-run initialization writes the Codex starter, use the local Codex
defaults unless the user or repository gives a standard Codex model command:

```toml
[harness]
tool = "codex"
prompt = "Read {brief}, then plan before edits."

[diff]
tool = "<resolved-diff-tool>"
```

When first-run initialization writes the Pi starter, use the local Pi defaults
unless the user or repository gives a standard Pi model command:

```toml
[harness]
tool = "pi"
prompt = "Read {brief}, then plan before edits."

[diff]
tool = "<resolved-diff-tool>"
```

For advanced split first-run initialization, materialize the final Diff choice
in the split config:

```toml
[diff]
tool = "<resolved-diff-tool>"
```

`<resolved-diff-tool>` is `comview`, `hunk`, or `none`. If Work resolved to
`custom` or a split Plan/Work configuration already exists before onboarding, do
not invent a starter config. Report the resolved configuration and continue
without writing.
