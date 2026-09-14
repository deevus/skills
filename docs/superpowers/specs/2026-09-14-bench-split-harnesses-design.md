# Bench split harnesses design

## Purpose

Bench currently starts one first-class agent harness in a `Work` tab. It can also start one optional diff companion in a `Diff` tab. This keeps the common workflow simple, but it cannot model a split workflow where one harness plans and another harness implements.

This design adds first-class plan and work harness roles. The default workflow stays `Work` plus optional `Diff`. A split workflow becomes `Plan`, `Work`, and optional `Diff` when a plan harness is configured.

## Goals

- Preserve all existing bench configs and resolver output used by current callers.
- Support two known harness roles: `plan` and `work`.
- Make `plan` opt-in and keep `work` as the logical default.
- Keep Comview and Hunk as generic diff companions.
- Keep final UI focus on `Work`.
- Fail closed when required harness tabs cannot be resolved, started, or verified.

## Non-goals

- Do not support arbitrary harness roles yet.
- Do not let UI adapters detect diff viewers or build diff commands.
- Do not replace the existing `[harness]` table in the first change.
- Do not add shell-string command evaluation. Harness commands remain argv arrays.

## Configuration interface

Bench keeps the existing `[harness]` table. It remains valid and means the `work` harness.

```toml
[harness]
tool = "pi"
prompt = "Read {brief}, then plan before edits."
```

Bench also adds a preferred role-keyed form for first-class harness tabs.

```toml
[[harnesses]]
role = "plan"
title = "Plan"
tool = "claude"
permission_mode = "plan"
prompt = "Read {brief}, write a plan, then stop for approval."

[[harnesses]]
role = "work"
title = "Work"
command = ["pi", "--model", "openai-codex/gpt-5.6-astra"]
# No prompt means the Work tab starts as an empty interactive agent.
```

The resolver supports only these roles:

- `plan`
- `work`

The `title` field is optional. It must be a non-empty string when present. The default title for `plan` is `Plan`. The default title for `work` is `Work`.

If no `plan` harness is present, bench creates the existing layout: `Work` plus optional `Diff`. If a `plan` harness is present, bench creates `Plan`, `Work`, and optional `Diff`.

The `work` role is always required after resolution. If no work harness is configured, it falls back to the existing Work harness default and selection behavior.

A config layer must not define both `[harness]` and `[[harnesses]]` with `role = "work"`. That is ambiguous, so the resolver must report an error.

### Prompt semantics

Prompt defaults depend on the config form.

- In legacy `[harness]`, an omitted `prompt` keeps the current default prompt.
- In `[[harnesses]]`, an omitted `prompt` means no initial prompt for that role.
- In `[[harnesses]]`, a provided `prompt` must be a non-empty string.
- If no `work` role exists, Work falls back to the existing default prompt and selection behavior.

When a role uses `command`, the resolver appends the rendered prompt only when that role has a prompt. When a role has no prompt, the resolver returns the command argv unchanged.

This lets split benches start Work as an empty interactive agent while Plan receives the real brief-driven prompt.

## Layering and merge behavior

The resolver normalizes each config layer into a role-keyed harness map before it merges layers.

```text
{
  "plan": HarnessConfig | absent,
  "work": HarnessConfig | absent
}
```

Precedence stays unchanged:

1. user config: `$XDG_CONFIG_HOME/bench/config.toml`, or `~/.config/bench/config.toml`
2. repo config: `<repo>/.bench/config.toml`
3. explicit resolver flags

Harnesses merge by role. Within one role, fields layer like the current `[harness]` fields:

- a higher-precedence `tool` clears inherited `command` and `permission_mode`
- a higher-precedence `command` clears inherited `tool` and `permission_mode`
- a provided `prompt` layers independently
- `title` layers independently
- in `[[harnesses]]`, an omitted `prompt` removes any inherited prompt for that role

This means repo config can add or override only the Plan harness without redefining Work. It can also override the Work harness without affecting Plan.

A higher-precedence layer can remove an inherited role with `enabled = false`.

```toml
[[harnesses]]
role = "plan"
enabled = false
```

Rules for `enabled = false`:

- It removes that role from the final harness map.
- It must not be combined with `tool`, `command`, `prompt`, `permission_mode`, or `title`.
- It is invalid for `role = "work"` unless an explicit Work override flag supplies Work for the current run.

## Resolver output

The resolver returns a new `harnesses` array. It also keeps the existing `harness` object during migration.

```json
{
  "harness": {
    "tool": "pi",
    "argv": ["pi", "@/tmp/brief.md", "Read ..."],
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
    "tool": "comview",
    "available": ["comview", "hunk"],
    "selection_required": false
  }
}
```

The legacy `harness` object is the resolved Work harness. Existing callers can keep using it until they move to `harnesses`.

The `harnesses` array is ordered by role semantics:

1. `plan`, when present
2. `work`

Any unresolved required selection blocks setup. If `plan.selection_required` is true, bench asks which tool to use for Plan. If `work.selection_required` is true, bench asks which tool to use for Work.

The existing `--harness-tool` flag applies to Work. The resolver adds `--plan-harness-tool` for Plan. Existing diff flags and output stay unchanged.

## UI adapter contract

Long term, bench passes UI adapters an ordered list of harness tab specs instead of one harness argv.

```text
[
  { role: "plan", title: "Plan", argv: [...] },
  { role: "work", title: "Work", argv: [...] }
]
```

The diff integration still contributes an optional companion tab.

```text
{ title: "Diff", command: "comview watch ..." }
```

UI adapters create these layouts:

- default: `Work`, optional `Diff`
- split: `Plan`, `Work`, optional `Diff`

Each harness tab is first-class. The adapter must verify:

- the tab shell starts in the bench root
- the harness process starts from the bench root
- the tab title matches the resolved title
- every required harness tab exists

Setup fails if any required harness tab fails. Final focus must return to `Work`, not `Plan`.

The companion remains generic. UI adapters must not detect Comview or Hunk, build diff commands, or add review semantics.

## Version 1 handoff

The first split-harness workflow is human-mediated.

Bench starts all first-class tabs during setup:

- `Plan` starts with its configured prompt.
- `Work` can start with no prompt, as an empty interactive agent.
- `Diff` starts when a diff companion is selected.

The Plan prompt tells the Plan agent to write the plan and stop for approval. After approval, the Plan agent must produce the exact prompt that the human should paste into Work. Bench does not signal Work directly in version 1.

A later version can add a machine-mediated handoff. For example, Plan could write a known plan artifact or ready marker, and Work could start after that marker exists. That behavior is out of scope for the first implementation.

## Validation

The resolver reports an error for:

- unknown harness roles
- duplicate roles within the same layer
- `[harness]` plus `[[harnesses]] role = "work"` in the same layer
- `enabled = false` combined with other harness fields
- `role = "work", enabled = false` without an explicit Work override for the current run
- `permission_mode` on a non-Claude harness
- empty `title` values
- empty strings or empty `command` arrays
- unsupported placeholders other than `{brief}`
- a provided `prompt` that is not a non-empty string
- missing executables for configured harnesses

## Migration plan

1. Add resolver support and tests for `[[harnesses]]`.
2. Keep existing `[harness]` support and legacy resolver output.
3. Update bench docs to prefer `[[harnesses]]` for split workflows.
4. Update `bench-supacode` to accept a harness-tab list while preserving single-harness mode.
5. Update `bench-herdr` to accept the same harness-tab list.
6. Add example configs for default `Work` plus `Diff`, and for `Plan`, `Work`, and Comview `Diff`.

## Example target config

This config starts Claude Fable as the Plan harness, Pi with Codex Astra as the Work harness, and Comview as the diff companion.

```toml
[[harnesses]]
role = "plan"
command = [
  "claude",
  "--permission-mode",
  "plan",
  "--allow-dangerously-skip-permissions",
  "--model",
  "claude-fable-5-1",
]
prompt = "Read {brief}, write a plan, then stop for approval."

[[harnesses]]
role = "work"
command = ["pi", "--model", "openai-codex/gpt-5.6-astra"]
# No prompt: Plan will produce the exact prompt to paste into this tab.

[diff]
tool = "comview"
```

## Self-review notes

- No arbitrary roles are included in this design.
- The existing `[harness]` interface stays valid.
- The diff integration remains separate from UI mechanics.
- The Work tab remains the final focus target.
- The resolver keeps an explicit migration path for current callers.
