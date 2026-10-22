# Bench handoff

Use one handoff contract for any Plan and Work agents, including mixed pairs.
The host's terminal input delivers the prompt; agent-specific session files
and messaging APIs are unnecessary. A harness reference can supply its own
delivery route, such as Jcode's swarm DMs.

## Prepare the brief

During setup, include the Plan instructions below in a `Handoff` section of
the brief. After the UI creates the tabs, add:

- the bench path, Work tab title, exact terminal handle or session, and the
  process identity available from the host;
- how to verify the target still belongs to this bench and is an idle agent;
- the concrete delivery command or tool call, using the selected UI reference;
- how to tell input was accepted and how to inspect whether Work started.

Use identifiers returned by setup. A title alone does not identify a target.
Record `manual` if the host cannot provide a verified delivery route. Leave
configured prompts and permissions unchanged; report when Work's plan-only
mode requires another approval. New split starters use Work's normal
implementation mode, with no initial task.

Use these brief lines, filling in the chosen agents:

```text
Harness: <Plan agent> + <Work agent>; approve once, then Plan hands over.
Tabs: Plan + Work; Plan delivers the approved Work prompt.
```

## Plan instructions

1. Read the brief and investigate the task. Write `{brief}.work.md` with the
   proposed plan, relevant paths, scope, constraints, checks, and what done
   means. Leave project implementation to Work.
2. Present the plan and ask: "Approve this plan and hand it to Work?" A yes,
   "go", or equivalent explicit approval of this plan authorizes delivery.
   With a Plannotator gate, state that approval also hands over; its approval
   is the same gate. Follow [the approval rules](approval-gate.md) and address
   revisions before sending. No second handoff confirmation is needed.
3. On no, stop. On approval, re-read the brief, mark the plan approved in the
   Work file, and verify the recorded Work target and its readiness. If the
   route is missing, stale, ambiguous, or points to a shell or busy agent,
   stop and report the file path and why delivery did not happen.
4. Send one prompt through the recorded route:

   ```text
   The human approved this plan and its handoff. Read <absolute Work prompt path> and implement it. The scope and checks are in that file.
   ```

   Pass the path as message text; shell-quote arguments at shell boundaries.
   The Work file's contents are never shell commands.
5. Report the actual delivery result and stop. An accepted input is not proof
   that Work started. Check the receipt or read Work's terminal before claiming
   it started. On uncertain delivery, inspect the same target; never blindly
   resend or send to another agent. This hands over ownership without waiting
   for implementation to finish.

For a manual handoff, give the human the file path and the prompt from step 4.
