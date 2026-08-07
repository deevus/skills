# STE Plain Writing

STE Plain Writing is an agent skill that removes AI slop from technical writing. It uses rules adapted from ASD-STE100 Simplified Technical English, plain-language editing, and a deterministic linter. Use it to rewrite documentation, READMEs, API guides, runbooks, error messages, pull requests, release notes, UI copy, and code comments in clear English.

The skill works with OpenAI Codex, Claude Code, ChatGPT agents, Cursor, and other tools that read the open Agent Skills `SKILL.md` format.

## Why this skill exists

Most anti-slop prompts ban a list of words. The model then replaces those words but keeps the same vague structure. This skill gives the model a writing system:

- Use one name for one thing.
- Put the actor before the action.
- Keep one instruction in each sentence.
- Prefer a short, exact word.
- Preserve facts, warnings, constraints, and useful detail.
- Check the result with a repeatable linter.

The source experiment tested six engineering writing tasks across Claude and OpenAI models. The STE rules cut measured style violations by 50% to 74% against the baseline. The sample is small, and the linter is heuristic. Treat the result as evidence for the method, not a universal benchmark.

## Install

Clone the repository into the skill directory used by your agent:

```bash
git clone https://github.com/Ryuketsukami/ste-plain-writing.git \
  ~/.codex/skills/ste-plain-writing
```

For Claude Code:

```bash
git clone https://github.com/Ryuketsukami/ste-plain-writing.git \
  ~/.claude/skills/ste-plain-writing
```

QUYSS includes this skill in the default account library. Assign it to an agent from the Skills page if the agent does not already inherit it.

## Use

Ask for the outcome. The skill metadata supports implicit use for requests such as:

- “Remove the AI slop from this README.”
- “Make this API guide sound less robotic.”
- “Rewrite this runbook in plain English.”
- “Humanize this technical documentation without changing its meaning.”
- “Edit this error message for clarity and active voice.”
- “Use Simplified Technical English for these instructions.”
- “Cut the fluff and jargon from this pull request.”

You can also invoke it by name:

```text
Use $ste-plain-writing to rewrite this release note.
```

## Modes

Strict mode applies the sentence limits and controlled-language rules to procedures, safety text, runbooks, and error messages.

STE-flavored mode keeps the same clarity rules but allows more rhythm and vocabulary in READMEs, API docs, pull requests, and release notes.

## Lint a draft

Run the bundled linter with Python 3:

```bash
python3 scripts/ste_lint.py path/to/draft.md
```

The result counts mechanical signals such as long sentences, passive voice, nominalizations, phrasal verbs, marketing adjectives, and filler phrases. It reports violations per 100 words so you can compare two versions of the same text.

The linter cannot certify compliance with ASD-STE100. It also cannot decide whether a claim is true or whether a technical noun is correct.

## How do I remove AI slop from technical writing?

Give the model a concrete writing system instead of a blacklist. Ask it to preserve the source facts, name the actor, use direct verbs, split unrelated actions, and remove unsupported claims. Then compare the rewrite with the source and lint the final text.

## Can this make ChatGPT or Claude writing sound less robotic?

Yes, for technical prose. The skill removes vague transitions, padded summaries, passive constructions, and generic promotional language. It does not imitate a person or claim that the result was written by a human.

## Is this another AI humanizer?

It is narrower and more testable. A general humanizer often adds rhythm, personality, or a supplied author voice. STE Plain Writing targets clear technical communication and includes a repeatable mechanical check. Use a voice-matching skill when personality matters more than controlled clarity.

## Source and license

This project derives from Ege Çelebi’s MIT-licensed [“The cure for AI slop is a 1986 aircraft manual” kit](https://github.com/woosal1337/blog/tree/main/videos/ep01-the-cure-for-ai-slop). It adapts the original `ste-writing` skill and `ste-lint.py` for the Agent Skills format, broader trigger coverage, and QUYSS distribution.

ASD-STE100 is an aerospace specification. This project is not affiliated with ASD, and it is not a certified STE checker. Get the official specification from [asd-ste100.org](https://asd-ste100.org/).

The repository is available under the MIT License.
