# Skills

This repository contains agent skills grouped by namespace.

## Namespaces

### Comview

[Comview](https://github.com/rockorager/comview) is an interactive terminal diff
viewer for reviewing code and writing local review comments.

- `comview` — agent-side support for reading comview review comments and
  inspecting the same diff source.
- `comview-guide` — coaching a human through the comview TUI.

### Deevus

Deevus skills encode my personal workflows. They are useful to copy or adapt,
but they are not intended as general-purpose defaults for everyone.

- `deevus-jujutsu` — my Jujutsu workflow overlay.

## Install with `npx skills add`

```bash
npx skills@latest add deevus/skills
```

## Install with APM

```bash
apm install deevus/skills/skills/comview/comview deevus/skills/skills/comview/comview-guide deevus/skills/skills/deevus/deevus-jujutsu
```

If APM cannot infer a target runtime, specify one:

```bash
apm install --target agent-skills deevus/skills/skills/comview/comview deevus/skills/skills/comview/comview-guide deevus/skills/skills/deevus/deevus-jujutsu
```
