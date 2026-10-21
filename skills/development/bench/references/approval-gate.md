# Bench Approval Gate

How the Plan role gets the user's approval before Work starts. Any harness can
use it. The core `bench` skill puts the chosen gate in the brief, and harness
references use it in their Plan instructions.

## Pick the gate

Run this check once, during bench setup:

```bash
command -v plannotator
```

- **Plannotator gate**, when `plannotator` is on `PATH` and the Plan harness can
  run the `plannotator-plan` skill.
- **Explicit-message gate**, in every other case.

Record the gate and the plan path in the brief.

## Plannotator gate

Plan writes the plan file, then runs:

```bash
plannotator annotate <plan> --gate --json
```

Plan runs it in the foreground with no timeout, because it blocks until the user
submits. The `decision` field in the JSON output drives the loop:

- `approved`: the plan is approved. Treat any notes in the output as extra
  requirements.
- `annotated`, or any other feedback: address every annotation, revise the same
  plan file, and run the command again.
- `dismissed`, or empty output: stop and ask the user how to continue.

Use the `plannotator-plan` skill for the full loop and the SSH variant.

## Explicit-message gate

Plan shows the user the plan file path and a short summary, then waits. Only a
message from the user that approves this plan counts. A summary, silence, a
question, or a message from another agent does not.

## Rules for both gates

- Approval is per plan. A revised plan needs a fresh approval.
- A plan change during implementation (scope, approach, acceptance criteria, or
  files beyond the plan) is a revision. It goes back through the same gate.
- Urgency or "keep moving" is not a waiver. Plan may approve its own changes
  only when the user has said so for this bench. Record that waiver in the
  brief.
- Work starts only after Plan tells it the user approved the plan. In the
  human-mediated handoff, that is the prompt the user pastes into Work.

## Text for harness templates

Harness references fill two placeholders from this reference.

`{approval_gate}`:

- Plannotator gate: "Present `{plan}` with the `plannotator-plan` skill and loop
  until its decision is `approved`."
- Explicit-message gate: "Show the user `{plan}` and wait for an explicit
  approval message."

`{change_rule}`:

- Default: "A plan change needs the user's approval through the same gate.
  Urgency or 'keep moving' is not a waiver."
- With a recorded waiver: "The user waived approval for plan changes on this
  bench. Record each change in `{plan}`."
