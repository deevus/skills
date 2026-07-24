# Skills

This repository contains agent skills grouped by domain.

## Domains

### Comview

[Comview](https://github.com/rockorager/comview) is an interactive terminal diff
viewer for reviewing code and writing local review comments.

- `comview` — agent-side support for reading comview review comments and
  inspecting the same diff source.
- `comview-guide` — coaching a human through the comview TUI.

## Install with `npx skills add`

```bash
npx skills add deevus/skills
```

## Install with APM

```bash
apm install deevus/skills/comview deevus/skills/comview-guide
```

If APM cannot infer a target runtime, specify one:

```bash
apm install --target agent-skills deevus/skills/comview deevus/skills/comview-guide
```
