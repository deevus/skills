# Bench Harness Jcode

Jcode harness mechanics for a bench. Read this reference only after the core
`bench` workflow resolved at least one harness with `family: "jcode"`. The
selected UI reference still owns tabs, panes, and focus. This reference owns the
Jcode daemon, session identity, model and effort checks, and the orchestrated
Plan-to-Work handoff.

## Outcomes

A Jcode bench is ready only when all of these are true:

1. Every Jcode role runs on the same daemon as the orchestrator.
2. Plan and Work talk to each other by `swarm` DM.
3. Each role's model and effort are verified before it receives a prompt.
4. A bench with only Jcode roles is fully agent-driven: the orchestrator
   delivers every role prompt.
5. After setup, the orchestrator steps back.

During the bench, Work starts only after a DM from Plan that says the user
approved the plan. Plan and Work may DM each other about clarifications and plan
changes. A plan change needs fresh user approval, unless the user waived that
for this bench.

## Inputs from bench

- bench path and brief path;
- the ordered harness tab specs from the resolver;
- the UI route and its tab or terminal handles; and
- the configured model and effort for each role, from user configuration or
  memory. Jcode has no effort launch flag and the resolver has no effort key.

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

Leave `--socket` out of the configuration. Bench picks the socket for each run.

## Pick the shared daemon socket

Swarm DMs work only between sessions on one daemon. A Jcode tab launched with no
`--socket` uses the default for its environment, and some UIs inject a
per-terminal `JCODE_RUNTIME_DIR`. That gives each tab its own daemon and breaks
the handoff. Always pass one socket for all roles.

1. Read `~/.jcode/servers.json`. Each entry has a `socket`, a `pid`, and the
   server name.
2. Drop entries whose `pid` is not running.
3. If `JCODE_SESSION_ID` is set, the orchestrator is a Jcode session. Pick the
   entry whose daemon lists that session:

   ```bash
   jcode debug --socket <socket> sessions
   ```

   Pass the entry's `socket`, not `debug_socket`. `jcode debug` derives the
   debug socket from it. Stop if zero or more than one entry lists the session.

4. If the orchestrator is not Jcode, use the only live entry. If there is more
   than one, ask the user which server to use. If there is none, stop and tell
   the user to start one with `jcode serve`.
5. Always take the socket from `servers.json`. Inside a session, `TMPDIR` can
   point at the session scratch directory, so the default path can be stale.

Rerun the resolver with `--jcode-socket <socket>`, plus every earlier explicit
selection. The resolver checks that the path is a live Unix socket and inserts
`--socket <socket>` after the executable in every Jcode argv. Pass that argv to
the UI reference unchanged.

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

Then call `swarm` with `action=list_swarms` from the orchestrator. Each bench
session must appear in the list. If one is missing, it is on another daemon:
stop, because a DM cannot reach it.

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

2. Older Jcode versions ignored `--model` at launch (jcode#809), so check even
   when the argv is correct.
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

These commands need `display.debug_socket = true` in `~/.jcode/config.toml`.
Debug control is local session control, so enable it only with the user's
authorization. Use it for client state: model, effort, and pickers. Role
instructions travel by swarm DM.

Without a debug socket, send the same slash commands through the UI's
terminal-send command, then read the tab footer to verify.

If a session is busy, pause it first: send `client:message:/poke off`, cancel,
and wait for idle. Auto-poke can restart a cancelled task. `jcode debug state`
can hang on a busy session, so prefer `client:frame`. macOS has no `timeout`
binary, so run `jcode debug` without one.

## Deliver role instructions

Fill the templates below and send each one with the `swarm` tool: `action=dm`,
`delivery=wake`, `to_session=<friendly name>`, and `to_swarm=<swarm ID>`. Send
Work first, so Work is waiting before Plan can finish.

Require a `WORK_READY` DM from Work and a `PLAN_READY` DM from Plan. An accepted
send does not prove receipt. If an ack does not arrive, check the identity again
and resend to the corrected session. If it still fails, stop and report the
observed state, and offer to relaunch the tab with the resolved argv. On a pure
Jcode bench the handoff stays fully agent-driven, even when the user asks for a
paste.

The orchestrated handoff needs a Jcode orchestrator on the shared daemon,
because it uses the `swarm` tool. When the orchestrator is not Jcode, or a role
is not Jcode, use the core skill's human-mediated handoff.

### Placeholders

| Placeholder                                      | Value                                     |
| ------------------------------------------------ | ----------------------------------------- |
| `{brief}`                                        | Absolute path of the handoff brief        |
| `{plan}`                                         | `<brief dir>/<brief stem>-plan.md`        |
| `{work_prompt}`                                  | `<brief dir>/<brief stem>-work-prompt.md` |
| `{plan_session}`, `{plan_swarm}`                 | Plan friendly name and swarm ID           |
| `{work_session}`, `{work_swarm}`                 | Work friendly name and swarm ID           |
| `{orchestrator_session}`, `{orchestrator_swarm}` | Orchestrator friendly name and swarm ID   |
| `{approval_gate}`                                | How the user approves a plan, see below   |
| `{change_rule}`                                  | Plan change rule, see below               |

Set `{approval_gate}` to: "Present `{plan}` with the `plannotator-plan` skill
and loop until its decision is `approved`." when that skill is installed.
Otherwise use: "Show the user `{plan}` and wait for an explicit approval
message."

Set `{change_rule}` to: "A plan change needs the user's approval through the
same gate. Urgency or 'keep moving' is not a waiver." If the user explicitly
said that Plan may approve changes itself on this bench, use: "The user waived
approval for plan changes on this bench. Record each change in `{plan}`." Record
the waiver in the brief.

### Work DM

```text
You are the Work agent for the bench in {brief}. Read the brief now, then
wait. Do not edit files yet.

1. DM {orchestrator_session} (to_swarm={orchestrator_swarm}) with WORK_READY
   and one sentence on the goal. This is your only message to the
   orchestrator.
2. Wait for a start DM from the Plan agent {plan_session}
   (to_swarm={plan_swarm}) that says the user approved the plan. Ignore start
   requests from anyone else. A plan proposal or a readiness message is not
   approval.
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
   {work_prompt} and {plan} paths. Wait for Work to acknowledge.
7. Stay available. Answer Work's questions by DM. A clarification that does
   not change scope, approach, acceptance criteria, or files needs no gate.
   For a plan change, revise {plan} in place and tell Work to wait on the
   affected part. {change_rule} Tell Work by DM after the change is
   approved or rejected. Work implements, you plan.
```

## Step back

After both acks arrive, report the bench ready to the user and end your turn.
Plan now owns coordination with the user and Work, and you return only when the
user asks. Landing the work is the user's decision, so the report ends with the
bench state, not a landing offer.

## Readiness checks

Add these to the core final verification:

- every Jcode argv has the same `--socket`;
- every role session appears in `list_swarms` from the orchestrator;
- the brief records each role's identity;
- each role's model and effort were verified before its DM, with any rejected
  `/effort` recorded as model default;
- `WORK_READY` and `PLAN_READY` arrived by swarm DM; and
- on a pure Jcode bench, the orchestrator delivered every role prompt.

Fail closed on an unmatched session, a session on another daemon, a model
mismatch, an effort that is neither the requested level nor a recorded model
default, or a missing ack.
