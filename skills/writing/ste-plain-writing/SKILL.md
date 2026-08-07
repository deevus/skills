---
name: ste-plain-writing
description: Write, edit, audit, or rewrite human-facing technical prose with ASD-STE100-inspired plain-language rules and a deterministic anti-slop linter. Use for documentation, READMEs, API docs, tutorials, runbooks, error messages, changelogs, release notes, PR descriptions, issue text, UI copy, or code comments when asked to remove AI slop or AI tells, humanize AI-generated text, make writing sound less robotic, reduce jargon or fluff, improve clarity and concision, use plain English, active voice, short sentences, controlled language, Simplified Technical English, or a consistent technical style. Do not apply to code or identifiers.
---

# STE plain writing

Rewrite technical prose with rules adapted from ASD-STE100 Simplified Technical English. Preserve the facts, intent, useful detail, formatting, and established author voice.

## Choose a mode

- Use **strict** mode for procedures, safety text, error messages, runbooks, and instructions.
- Use **STE-flavored** mode for READMEs, API docs, PR text, release notes, and other general technical prose.
- Use strict mode when the user does not specify a mode and the text tells a reader what to do.
- Use STE-flavored mode for all other requests.

Do not use this skill for code, identifiers, command syntax, creative writing, or marketing copy that depends on a distinct voice.

## Apply the workflow

1. Read the full source before editing.
2. Identify facts, requirements, warnings, commands, links, and structural elements that must remain.
3. Rewrite the text with the selected mode.
4. Compare the rewrite with the source. Restore any lost meaning or necessary detail.
5. Run the bundled linter when the text is available as a file.
6. Fix meaningful violations. Treat the linter as a diagnostic tool, not a certification system.
7. Return only the requested deliverable unless the user asks for an audit or explanation.

## Use plain words

- Use one name for one thing.
- Use a short common word when it keeps the exact meaning.
- Prefer `start` to `commence`, `use` to `utilize`, `help` to `facilitate`, and `show` to `demonstrate`.
- Give each word one meaning within the document.
- Use American spelling unless the source or user requires another variety.
- Remove empty intensifiers and promotional claims such as `seamless`, `robust`, `powerful`, `cutting-edge`, and `world-class`.
- Keep necessary technical terms. Define an unfamiliar term at its first use.

## Make actors and actions clear

- Use active voice when the actor is known.
- Use a verb for an action. Write `analyze the log`, not `perform an analysis of the log`.
- Prefer a simple tense to an `-ing` main verb.
- Remove stacked auxiliaries and modal hedges.
- State who or what performs each action.
- Preserve passive voice when the actor is unknown, irrelevant, or intentionally withheld.

## Control sentences and structure

- Put one instruction in each sentence.
- In strict mode, keep instructions at 20 words or fewer and descriptions at 25 words or fewer.
- In STE-flavored mode, prefer short sentences but vary length when it improves flow.
- Put a condition before the action it controls.
- Use a numbered vertical list for a sequence.
- Keep one topic in each paragraph and no more than six sentences.
- Replace semicolons with periods or another clear construction.
- Expand contractions in strict mode. Preserve them in STE-flavored mode when they match the author voice.
- Remove fake transitions, padded summaries, vague attributions, and repeated conclusions.

## Preserve substance

- Do not invent evidence, examples, measurements, quotes, or sources.
- Do not remove caveats, limitations, warnings, or exceptions to make the text shorter.
- Do not flatten a known author voice into generic corporate prose.
- Do not add personality when neutral technical prose is correct.
- Do not claim that text is human-written or undetectable.

## Run the linter

From the skill directory, run:

```bash
python3 scripts/ste_lint.py path/to/draft.md
```

The score reports heuristic violations per 100 words. Compare versions by score delta. Inspect each finding before editing because code samples and deliberate style choices can create false positives.

## Check the final text

- Does each sentence add information or direct an action?
- Does every pronoun have a clear referent?
- Did the rewrite preserve all facts and constraints?
- Can a shorter common word keep the same meaning?
- Can the known actor replace passive voice?
- Does each list contain a real set or sequence?
- Did any AI-shaped filler, forced rule of three, vague authority, or empty closer remain?
- In strict mode, did any sentence exceed its length limit?

This skill improves the form of technical prose. It cannot make weak ideas true or unsupported claims credible.
