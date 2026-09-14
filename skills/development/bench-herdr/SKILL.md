---
name: bench-herdr
description:
  Use when a bench workspace must be opened, arranged, verified, or operated
  inside Herdr.
---

# Bench Herdr

Herdr terminal mechanics for a bench. If `bench` has not already been loaded for
this request, load `bench` first and follow its generic workflow before doing
these UI steps.

This skill applies when `HERDR_ENV=1`.

## Inputs

`bench` provides:

- bench path;
- short workspace title;
- ordered harness tab specs;
- optional companion title plus companion command.

Each harness tab spec contains:

- `role`: `plan` or `work`;
- `title`: the tab title; and
- `argv`: the harness argv array.

Exactly one Work harness tab is required. A Plan harness tab is optional. The
companion pair is optional. If one of companion title or command is missing,
stop and return to `bench` for corrected inputs.

Do not detect viewers, construct companion commands, or add review semantics in
this skill. Treat the companion as a generic terminal command.

## Sequence

1. Create the native VCS checkout or workspace first, as directed by `bench`.
2. Confirm the bench path exists and has the expected VCS metadata.
3. Open or create a Herdr workspace rooted at the bench path.
4. Label the workspace with the short title from `bench`.
5. Create harness tabs in the order supplied by `bench`.
6. Reuse the initial tab for the first harness tab when Herdr exposes that
   control. Rename or label it with the harness tab title.
7. Start each harness argv from its own tab without wrapping the argv in a new
   shell string.
8. If no companion was provided, keep only the harness tabs and focus Work.
9. If a companion was provided, create a separate tab rooted at the same bench
   path. Title it exactly with the companion title.
10. Run the companion command in that companion tab.
11. Focus back to Work.

The default layout is Work plus optional companion. A split-harness layout is
Plan, Work, and optional companion. In version 1, Plan produces the exact prompt
that the human should paste into Work after plan approval; Herdr does not signal
Work directly.

Use project-specific title or color conventions only when `bench` passes them in
or the project topic requires them.

## Readiness and safety checks

Before reporting success:

- confirm each harness tab's shell starts in the bench path;
- confirm each harness process started from its own tab;
- if a companion exists, confirm its tab shell starts in the bench path;
- confirm Work, Plan, and companion use separate tabs, not split panes;
- confirm focus returned to Work; and
- fail closed on missing tabs, ambiguous cwd, unexpected existing sessions, or a
  half-specified companion.

If a Herdr workspace already has unexpected tabs or active work, do not
restructure it. Return to `bench` with the observed state.

## Hosts outside Herdr

If `HERDR_ENV` is not `1`, return to `bench` and use the UI path selected by the
environment.
