---
name: bench
description: >
  Use when benching a ticket, issue, PR, or task into an isolated development
  workspace, including requests like "bench it", "set up a bench", or "bench PR
  #... for review".
---

# Bench

Create an isolated workspace for a task or review. Resolve agent harness tabs
and an optional diff companion, route terminal setup to the active UI, and
verify that the bench is ready before reporting success.

See [configuration](references/configuration.md) for the layered resolver
contract. The resolver is the source of truth for harness argv arrays and the
diff viewer choice.

## Responsibilities

`bench` owns:

- configuration resolution and any required user choices;
- native VCS workspace creation;
- local configuration links and environment setup;
- handoff brief creation;
- UI routing;
- diff integration routing; and
- final readiness checks.

`bench` does not build viewer commands or manage viewer review state. Read only
the selected diff reference for the optional companion title, companion command,
and viewer-specific brief text.

## Resolve configuration

1. Pick a stable handoff brief path outside the workspace.
2. Write an initial brief from the request, ticket, or PR metadata only. Do not
   scout the codebase for the harness.
3. Before the first resolver run, check whether the user config and repository
   config already exist. User config is `$XDG_CONFIG_HOME/bench/config.toml`, or
   `~/.config/bench/config.toml` when `XDG_CONFIG_HOME` is unset. Repository
   config is `<source-repo>/.bench/config.toml`.
4. Resolve `scripts/resolve_bench_config.py` relative to the loaded `bench`
   skill directory. Run that installed resolver while passing the source
   repository with `--repo-root`:

   ```bash
   python3 <bench-skill-dir>/scripts/resolve_bench_config.py \
     --repo-root /path/to/source-repo \
     --brief /tmp/bench-brief.md
   ```

5. Inspect `harnesses` in the resolver output. It is ordered by first-class UI
   tab role: optional Plan first, then Work.
6. If any Plan or Work harness has `selection_required` true, use its
   `available` list as the only supported choices:
   - If `available` is empty, stop. Report that no supported harness executable
     was found and tell the user to install Claude or Pi, or configure a custom
     argv command with [configuration](references/configuration.md).
   - If `available` has one item, stop and report an internal resolver error;
     the resolver should have selected the only installed preset.
   - If `available` has both `claude` and `pi`, ask once with a numbered list
     generated in that order. For the no-config first-run branch, label them as
     starter presets: `Claude starter — one Work tab in plan mode` and
     `Pi starter — one Work tab prompted to plan before edits`. Both starter
     presets use one Work tab for planning and implementation; do not suggest a
     separate Plan role during onboarding.

   Rerun with `--plan-harness-tool <tool>` for Plan or `--harness-tool <tool>`
   for Work. Include any earlier explicit selections on every rerun, so later
   Work or Diff choices do not drop Plan or Work choices.

7. If `diff.selection_required` is true, ask once with a numbered list generated
   from `diff.available`, followed by `None`. Then rerun the resolver with
   `--diff-tool comview`, `--diff-tool hunk`, or `--diff-tool none`. Include all
   earlier explicit Plan and Work selections on this rerun.
8. Stop on resolver errors. Do not guess when configuration is malformed, an
   executable is missing, or a required choice is unresolved.
9. If neither config file existed before the first resolver run and the final
   resolver output has no `selection_required: true` value, initialize
   configuration before workspace creation. Say: "You need to set up a bench
   configuration. Would you like it to be global or local?"

   1. Global — create `$XDG_CONFIG_HOME/bench/config.toml`, falling back to
      `~/.config/bench/config.toml`, for future repositories.
   2. Local — create `<source-repo>/.bench/config.toml` for this repository
      only.

   The selected scope is consent to create that file; do not ask a separate
   Save-versus-Use-once question. Recheck the selected path immediately before
   writing. If it now exists, stop and ask the user to reconcile it rather than
   overwriting it.

10. Write a starter config for the resolved Work harness and final Diff tool.
    For Claude, write:

    ```toml
    [harness]
    tool = "claude"
    permission_mode = "plan"
    prompt = "Read {brief}, then plan before edits."

    [diff]
    tool = "<resolved-diff-tool>"
    ```

    For Pi, write:

    ```toml
    [harness]
    tool = "pi"
    prompt = "Read {brief}, then plan before edits."

    [diff]
    tool = "<resolved-diff-tool>"
    ```

    `<resolved-diff-tool>` is `comview`, `hunk`, or `none`. If Work resolved to
    `custom` or a split Plan/Work configuration somehow exists, do not invent a
    starter config; report the resolved configuration and continue without
    writing.

Pass each returned harness tab's `argv` to the UI adapter unchanged. Each value
is an argv list, not a shell command string. Keep the legacy `harness` object as
the resolved Work harness for callers that have not moved to `harnesses`.

## Split-harness handoff

When the resolver returns both Plan and Work harnesses, the bench uses a
human-mediated handoff in version 1:

1. Start Plan with its configured prompt.
2. Start Work with its resolved argv. Work may have no prompt and can start as
   an empty interactive agent.
3. The Plan prompt should tell the Plan agent to write the plan, stop for
   approval, and produce the exact prompt the human should paste into Work.
4. Do not make bench or the UI adapter signal Work directly.

## Create the native workspace

1. Read the relevant project topic or repo instructions for repo paths,
   workspace names, issue prefixes, colour conventions, and tracker specifics.
   Keep those project facts out of this generic skill.
2. Fetch first from the source repository. Use `jj git fetch` for Jujutsu or
   `git fetch` for Git. Report the resolved base revision.
3. Use native VCS isolation. Use `jj workspace add` for Jujutsu, or
   `git worktree` or the repo's native Git workflow for Git. Do not copy a
   checkout. Do not use UI helpers that copy VCS metadata.
4. For Jujutsu, check `jj --no-pager workspace list`. If a deleted directory
   left a stale workspace registration, forget it before recreating that name.
5. Verify the new root has the expected VCS metadata: `.jj` for Jujutsu
   workspaces or `.git` for Git worktrees. Fail closed on stray copied metadata.
6. Symlink, never copy, VCS-excluded local config from the source repository
   into the bench.
7. If `mise.toml` exists in the bench, run `mise trust` there before terminals,
   agents, environment installs, or companions.
8. Run the repo's environment install commands from the bench root.

If a fetch makes other Jujutsu workspaces stale, repair them separately with
`jj workspace update-stale` and re-verify any review bench diff before you
report success.

## Review benches

For "bench PR ... for code review":

1. Fetch first.
2. Create the bench at the PR head or the local review merge required by the
   repository workflow.
3. Confirm `trunk()` or the Git base branch matches the remote PR base.
4. If the PR is behind the base branch, do not rebase or mutate someone else's
   branch. In Jujutsu, create a local review merge instead.
5. Re-run environment install after the merge.
6. Verify the file count against PR metadata.
7. Do not push from a review bench.

Put review scope, constraints, the verified file count, and the resolved base in
the brief. Let the selected diff reference add its own range and interaction
instructions.

## Route the diff integration

Use the resolver's final `diff.tool` value:

- `comview`: read [Bench Diff Comview](references/diff-comview.md) to produce
  the companion title, companion command, and brief additions.
- `hunk`: read [Bench Diff Hunk](references/diff-hunk.md) to produce the
  companion title, companion command, session verification, and brief additions.
- `none`: do not create a companion and do not read a diff integration
  reference.

Pass the bench type and VCS facts to the diff reference: task, review, or stack;
Git or Jujutsu; base branch or revset; review head; and any path scope. Do not
duplicate its range recipes in this core skill.

## Finish the handoff brief

Keep the brief outside the workspace. Include only facts already known from the
request, tracker, PR metadata, resolver output, and selected diff integration:

- goal or review target;
- acceptance criteria or review scope;
- links and IDs;
- resolved base revision;
- selected harness tabs, roles, titles, and argv values in readable form;
- selected diff tool, or that no companion was requested;
- companion command and viewer-specific instructions, if a companion exists;
- for split harnesses, the Plan-to-Work paste handoff instruction; and
- known constraints and open questions.

A thin brief is correct when the ticket is thin. Put uncertainty in open
questions instead of scouting.

## Route to the terminal UI

Before doing UI setup, check the environment from the current shell:

```bash
printf 'HERDR_ENV=%s\n' "${HERDR_ENV:-}"
command -v supacode >/dev/null && echo supacode || echo no-supacode
```

- If `HERDR_ENV=1`, read [Bench Herdr](references/ui-herdr.md) for terminal
  mechanics.
- Else if `supacode` exists, read [Bench Supacode](references/ui-supacode.md)
  for Supacode mechanics.
- Else use native terminals when available and do not read a UI reference.

Every UI path receives the same inputs: bench path, short title, ordered harness
tab specs, and an optional companion title plus command. UI references must not
detect viewers, construct viewer commands, or add review semantics.

## Native terminal fallback

When no UI skill is available, keep the same separation of concerns:

1. If your host can open native terminal tabs, start each harness tab in order,
   rooted at the bench. If a companion exists, start it in a separate terminal
   rooted at the bench. Return focus to Work when possible and verify each shell
   cwd before reporting success.
2. If your host cannot open native terminal tabs, print paste-ready commands for
   the human. Print one command per ordered tab:

   ```text
   <Title>: cd <shell-quoted-bench-path> && <shell-quoted argv or companion command>
   ```

   Shell-quote the bench path and every harness argv element. Keep argv arrays
   unchanged until this display boundary. For a companion, append the companion
   command after `&&` exactly as produced by the selected diff reference.

   Example:

   ```text
   Work: cd '/path/to/bench' && claude --permission-mode plan 'Read /tmp/brief.md, then plan before edits.'
   ```

3. After printing commands, ask with a numbered list:
   1. I started the commands in separate terminals.
   2. I need help starting them.

   On option 1, accept the human confirmation as native launch verification and
   complete the bench. On option 2, keep the workspace and brief, report that
   setup is awaiting terminal launch, and repeat the commands.

If native terminal state cannot be machine-verified, do not claim it was
machine-verified; say that launch was confirmed by the human.

## Final verification

Before reporting success, confirm:

- the workspace root and VCS metadata are correct;
- the environment setup completed;
- the handoff brief exists outside the workspace;
- for Herdr and Supacode, each harness process started from the bench root;
- for manual native launch, the human confirmed starting each printed command,
  and every printed command began with `cd <bench>`;
- for Herdr and Supacode, any companion process started from the bench root;
- for manual native launch with a companion, the human confirmed starting the
  printed companion command;
- the selected diff integration's verification passed when a companion exists;
- the UI is focused back on Work when a UI is available; and
- review benches have not pushed or mutated someone else's branch.

In the final report, distinguish diff states:

- If `diff.tool == "none"` and `diff.available == []`, say: "No diff viewer is
  installed; Comview and Hunk are optional."
- If `diff.tool == "none"` and `diff.available` is not empty, say that no
  companion was requested.
- If a viewer is selected, report its name and companion command.

Fail closed on missing sessions, unexpected tabs, ambiguous cwd, unresolved
configuration, or unavailable executables.
