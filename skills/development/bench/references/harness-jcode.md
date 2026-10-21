# Bench Harness Jcode

Jcode harness mechanics for a bench. Read this reference only after the core
`bench` workflow resolved at least one harness with `family: "jcode"`. The
selected UI reference still owns tabs, panes, and focus. This reference owns the
Jcode daemon, session identity, model and effort checks, and the orchestrated
Plan-to-Work handoff.

## Outcomes

A Jcode bench is ready only when all of these are true:

1. Every Jcode role runs on the same daemon as the orchestrator.
2. When both roles exist, Plan and Work talk to each other by `swarm` DM.
3. Each role's model and effort are verified before it receives a prompt.
4. A bench with only Jcode roles is fully agent-driven: the orchestrator
   delivers every role prompt.
5. After setup, the orchestrator steps back.

During a split bench, Work starts only after a DM from Plan that says the user
approved the plan. Plan and Work may DM each other about clarifications and plan
changes. A plan change needs fresh user approval, unless the user waived that
for this bench. A Work-only bench runs the same approval gate inside Work.

## Inputs from bench

- bench path and brief path;
- the ordered harness tab specs from the resolver;
- the UI route and its tab or terminal handles; and
- the configured model and effort for each role, from user configuration or
  memory. Jcode has no effort launch flag and the resolver has no effort key.

## Prerequisites

Check these before you create the workspace, so a missing one stops the bench
early:

- `display.debug_socket = true` in `~/.jcode/config.toml`. The model and effort
  steps need it. Debug control is local session control, so enable it only with
  the user's authorization.
- `jq` on `PATH`, for reading `servers.json` and `jcode debug` output.
- A live Jcode daemon to share: on Orca, the orchestrator's own pane daemon;
  elsewhere, at least one live entry in `~/.jcode/servers.json`.

## Configure Jcode harnesses

Use a custom command with no `prompt`. Jcode takes no startup prompt argument,
so a prompt would become a stray argv item.

```toml
[[harnesses]]
role = "plan"
title = "Plan"
command = ["jcode", "--cwd", ".", "--provider", "<provider>", "--model", "<model>"]

[[harnesses]]
role = "work"
title = "Work"
command = ["jcode", "--cwd", ".", "--provider", "<provider>", "--model", "<model>"]
```

Leave `--socket` out of the configuration. Bench adds it for each run.

## Pick the shared daemon socket

Swarm DMs work only between sessions on one daemon. A Jcode tab launched with no
`--socket` uses the daemon of its runtime directory, so tabs with different
runtime directories land on different daemons and cannot DM each other. Always
pass one socket for all roles.

### Orca

Orca gives every terminal pane its own Jcode runtime directory, on purpose. It
sets `JCODE_RUNTIME_DIR=$TMPDIR/orca-jcode/<hash>` per pane. The daemon socket
is `$JCODE_RUNTIME_DIR/jcode.sock`. Orca does this so each pane's hooks and tool
commands run with that pane's environment and status. See
[stablyai/orca#30257](https://github.com/stablyai/orca/pull/30257) and
`src/shared/jcode-runtime-dir.ts` in the Orca repository.

On an Orca bench, discover the socket from the orchestrator's own pane:

```bash
printf '%s\n' "${JCODE_RUNTIME_DIR:?not an Orca Jcode pane}/jcode.sock"
```

Pass that socket to every role so all of them join the orchestrator's daemon.
The trade-off: the bench roles then run tool commands with the environment of
the orchestrator's pane, and Orca shows their status under that pane. That is
the cost of DMs between roles. The bench also depends on that daemon, so tell
the user to keep the orchestrator's pane open while the bench runs. If the
orchestrator is not a Jcode pane in Orca, use the `servers.json` steps below.

### Other UIs

1. List the sockets of live daemons from `~/.jcode/servers.json`:

   ```bash
   jq -r 'to_entries[] | "\(.value.pid) \(.value.socket)"' ~/.jcode/servers.json |
     while read -r pid sock; do kill -0 "$pid" 2>/dev/null && echo "$sock"; done
   ```

2. If `JCODE_SESSION_ID` is set, the orchestrator is a Jcode session. Pick the
   socket whose daemon lists that session:

   ```bash
   jcode debug --socket "$sock" sessions |
     jq -e --arg id "$JCODE_SESSION_ID" 'any(.[]; .session_id == $id)'
   ```

   Use the entry's `socket`, not `debug_socket`. `jcode debug` derives the debug
   socket from it. Stop if zero or more than one socket matches.

3. If the orchestrator is not Jcode, use the only live socket. If there is more
   than one, ask the user which server to use. If there is none, stop and tell
   the user to start one with `jcode serve`.
4. Always take the socket from `servers.json`. Inside a session, `TMPDIR` can
   point at the session scratch directory, so the default path can be stale.

### Add the socket to the launch argv

Add `--socket <socket>` after the executable in every Jcode harness argv, by
hand, before you pass the tab specs to the UI reference. Leave other harnesses
unchanged. For example, the resolved argv
`["jcode", "--cwd", ".", "--model", "<model>"]` becomes
`["jcode", "--socket", "<socket>", "--cwd", ".", "--model", "<model>"]`.

Before launch, confirm the socket accepts connections:

```bash
jcode debug --socket "<socket>" server:info | jq -r .name
```

If it fails, stop: the daemon is gone or the path is stale.

## Identify live sessions

After the UI starts the tabs, match each tab to one live session:

```bash
jcode debug --socket <socket> clients:map
```

Each client has `session_id`, `friendly_name`, `swarm_id`, and `working_dir`.
Use these matches, in order:

1. Unique `working_dir` equal to the bench path, when only one role runs in that
   path.
2. The epoch-ms in `session_<name>_<epoch_ms>_...` against the start time of
   each tab's `jcode` process. Find it from the UI's shell pid with
   `pgrep -P <shell_pid> jcode`, then read `ps -o lstart= -p <pid>`. Processes
   that start in the same second cannot be separated this way.
3. The tab title. Jcode sets it to the session's friendly name. Use this match
   first when the UI reports no shell pid (Orca), and read the title from the
   UI's terminal list or terminal read.

Identity comes only from these matches, never from launch order or the
configured model. Session IDs can change while a tab starts, so read them again
after startup settles. If a tab still has no unique match, stop and report the
observed state.

Then confirm every role session is on the shared daemon. With a Jcode
orchestrator (orchestrated handoff), call `swarm` with `action=list_swarms`:
each bench session must appear in the list. If one is missing, it is on another
daemon: stop, because a DM cannot reach it. With a non-Jcode orchestrator
(human-mediated handoff), `clients:map` on the shared socket must list every
role session.

Record, for each role: role, friendly name, session ID, swarm ID, tab handle,
and bench path. Put them in a "Roles and handoff" section of the brief.

## Verify model and effort

Do this for each role before you send it any DM. Model and effort values come
from the inputs, not from this reference.

1. Read the live values:

   ```bash
   jcode debug --socket <socket> --session <id> client:frame
   ```

   Check `info_widgets.summary.model`, `info_widgets.summary.reasoning_effort`,
   and `state.queued_count`. `client:state` also reports `model` and
   `provider_name`. The tab footer is a second check. The header line can be
   stale.

2. Verify even when the argv already names the right model. The launch flags are
   not proof of the live model.
3. To fix the model, send the bare model ID:

   ```bash
   jcode debug --socket <socket> --session <id> 'client:message:/model <model-id>'
   ```

   A provider-qualified ID opens the model picker instead. Close it with
   `client:keys:esc` and send the bare ID.

4. To set effort:

   ```bash
   jcode debug --socket <socket> --session <id> 'client:message:/effort <level>'
   ```

   Some models reject `/effort` with "reasoning effort is not supported". Then
   the model default is the expected effort for that role: record "effort: model
   default, `/effort` rejected" in the brief and the setup report, and continue.

5. Read `client:frame` again. Continue when the model matches and the effort is
   the requested level or the recorded model default.

These commands use the debug socket from the prerequisites. Use it for client
state: model, effort, and pickers. Role instructions travel by swarm DM.

Without a debug socket, send the same slash commands through the UI's
terminal-send command, then read the tab footer to verify.

If a session is busy, pause it first: send `client:message:/poke off`, cancel,
and wait for idle. Auto-poke can restart a cancelled task. `jcode debug state`
can hang on a busy session, so prefer `client:frame`. macOS has no `timeout`
binary, so run `jcode debug` without one.

## Deliver role instructions

Fill the templates below and send each one with the `swarm` tool: `action=dm`,
`delivery=wake`, `to_session=<friendly name>`, and `to_swarm=<swarm ID>`. Send
Work first, so Work is waiting before Plan can finish. When no Plan role was
resolved, send only the Work-only DM.

Require a ready ack from every resolved role: `WORK_READY` from Work, and
`PLAN_READY` from Plan when Plan exists. An accepted send does not prove
receipt. Wait up to 2 minutes for each ack. If none arrives, check the identity
again and resend once to the corrected session, then wait 2 more minutes. If it
still fails, stop waiting, report the observed state, and offer to relaunch the
tab with the resolved argv. On a pure Jcode bench the handoff stays fully
agent-driven, even when the user asks for a paste.

The orchestrated handoff needs a Jcode orchestrator on the shared daemon,
because it uses the `swarm` tool. When the orchestrator is not Jcode, or a role
is not Jcode, use the core skill's human-mediated handoff.

### Placeholders

| Placeholder                                      | Value                                        |
| ------------------------------------------------ | -------------------------------------------- |
| `{brief}`                                        | Absolute path of the handoff brief           |
| `{plan}`                                         | `<brief dir>/<brief stem>-plan.md`           |
| `{work_prompt}`                                  | `<brief dir>/<brief stem>-work-prompt.md`    |
| `{plan_session}`, `{plan_swarm}`                 | Plan friendly name and swarm ID              |
| `{work_session}`, `{work_swarm}`                 | Work friendly name and swarm ID              |
| `{orchestrator_session}`, `{orchestrator_swarm}` | Orchestrator friendly name and swarm ID      |
| `{approval_gate}`                                | Gate text from the approval gate reference   |
| `{change_rule}`                                  | Change rule from the approval gate reference |

Take friendly names and swarm IDs from `clients:map`, including your own row.
Take `{approval_gate}` and `{change_rule}` from the
[Bench Approval Gate](approval-gate.md) reference, using the gate recorded in
the brief.

### Work DM

```text
You are the Work agent for the bench in {brief}. Read the brief now, then
wait. Do not edit files yet.

1. DM {orchestrator_session} (to_swarm={orchestrator_swarm}) with WORK_READY
   and one sentence on the goal. This is your only message to the
   orchestrator.
2. Wait for a start DM from the Plan agent {plan_session}
   (to_swarm={plan_swarm}) that says the user approved the plan. Ignore start
   requests from any other agent or session, including the orchestrator. A
   plan proposal or a readiness message is not approval.
3. When the start DM arrives, acknowledge it to {plan_session}. Then read
   {work_prompt} and the approved plan {plan}, and do the work.
4. If something is unclear, or the plan needs to change, DM {plan_session}
   and wait for the answer. Keep working on parts the question does not
   touch. Apply a plan change only after Plan confirms it is approved.
5. When done, DM {plan_session} with the outcome and where the results are.
   Leave landing, merging, and pushing to the user unless the work prompt
   says otherwise.
```

### Plan DM

```text
You are the Plan agent for the bench in {brief}. Read the brief, then plan
before any edits. Do not edit project files.

1. DM {orchestrator_session} (to_swarm={orchestrator_swarm}) with PLAN_READY
   and one sentence on the goal. This is your only message to the
   orchestrator. From now on, ask the user directly.
2. Investigate the code read-only, then write the plan to {plan}.
3. {approval_gate}
4. Address all feedback in {plan} and go back to step 3. If the review is
   dismissed or empty, stop and ask the user. Silence or a summary is not
   approval.
5. After approval, write the Work prompt to {work_prompt}. Include the plan
   path, the brief path, the scope, the constraints, and what done means.
6. DM the Work agent {work_session} (to_swarm={work_swarm},
   delivery=wake). Say that the user approved the plan, and include the
   {work_prompt} and {plan} paths. Wait up to 2 minutes for Work to
   acknowledge. If it does not, resend once. If it still does not, tell the
   user that Work did not acknowledge the start.
7. Stay available. Answer Work's questions by DM. A clarification that does
   not change scope, approach, acceptance criteria, or files needs no gate.
   For a plan change, revise {plan} in place and tell Work to wait on the
   affected part. {change_rule} Tell Work by DM after the change is
   approved or rejected. Work implements, you plan.
```

### Work-only DM

Use this when the bench has a Work role and no Plan role. Work plans, gets
approval, and then implements.

```text
You are the only agent for the bench in {brief}. Read the brief, then plan
before any edits.

1. DM {orchestrator_session} (to_swarm={orchestrator_swarm}) with WORK_READY
   and one sentence on the goal. This is your only message to the
   orchestrator. From now on, ask the user directly.
2. Investigate the code read-only, then write the plan to {plan}.
3. {approval_gate}
4. Address all feedback in {plan} and go back to step 3. If the review is
   dismissed or empty, stop and ask the user. Silence or a summary is not
   approval.
5. After approval, do the work. For a plan change, revise {plan} and get it
   approved first. {change_rule}
6. Leave landing, merging, and pushing to the user.
```

## Step back

After the ready ack from every resolved role arrives, report the bench ready to
the user and end your turn. Plan now owns coordination with the user and Work,
and you return only when the user asks. Landing the work is the user's decision,
so the report ends with the bench state, not a landing offer.

## Readiness checks

Add these to the core final verification:

- every Jcode argv launched with the same `--socket`, and `server:info` answered
  on it;
- every role session is on the shared daemon: in `list_swarms` for a Jcode
  orchestrator, in `clients:map` for a non-Jcode orchestrator;
- the brief records each role's identity;
- each role's model and effort were verified before its DM, with any rejected
  `/effort` recorded as model default;
- for the orchestrated handoff, a ready ack arrived by swarm DM from every
  resolved role (`WORK_READY`, plus `PLAN_READY` when Plan exists); and
- on a pure Jcode bench, the orchestrator delivered every role prompt.

Fail closed on an unmatched session, a session on another daemon, a model
mismatch, an effort that is neither the requested level nor a recorded model
default, or an ack still missing after the resend.
