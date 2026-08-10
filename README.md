# Skills

This repository contains agent skills grouped by namespace.

## Namespaces

### Comview

[Comview](https://github.com/rockorager/comview) is an interactive terminal diff
viewer for reviewing code and writing local review comments.

- `comview` — agent-side support for reading comview review comments and
  inspecting the same diff source.
- `comview-guide` — coaching a human through the comview TUI.

### Code review

Code review skills help agents understand and explain diffs, PRs, and review
artifacts.

### Writing

Writing skills help agents edit technical prose, documentation, and human-facing
copy.

- `ste-plain-writing` is vendored from
  [Ryuketsukami/ste-plain-writing](https://github.com/Ryuketsukami/ste-plain-writing).

### Development

Development skills capture reusable coding workflows.

- `bench` — create isolated task or review benches with a harness and diff
  watcher.
- `bench-supacode` — Supacode UI mechanics for benches.
- `bench-herdr` — Herdr UI mechanics for benches.

### Deevus

Deevus skills encode my personal workflows. They are useful to copy or adapt,
but they are not intended as general-purpose defaults for everyone.

- `deevus-jujutsu` — my Jujutsu workflow overlay.

## Install with `npx skills add`

```bash
npx skills@latest add deevus/skills
```

## Install with APM

Install the whole repo with `npx skills add` when possible. For APM, install
only the skill paths you want:

```bash
apm install deevus/skills/skills/<namespace>/<skill>
```

If APM cannot infer a target runtime, specify one:

```bash
apm install --target agent-skills deevus/skills/skills/<namespace>/<skill>
```
