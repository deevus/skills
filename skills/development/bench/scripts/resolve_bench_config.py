#!/usr/bin/env python3
from __future__ import annotations

import argparse
import dataclasses
import json
import os
import pathlib
import shutil
import string
import sys
import tomllib
from collections.abc import Callable, Sequence
from typing import Any

DEFAULT_PROMPT = "Read {brief}, then plan before edits."
CLAUDE_PERMISSION_MODES = frozenset(
    {"acceptEdits", "auto", "bypassPermissions", "manual", "dontAsk", "plan"}
)
HARNESS_TOOLS = frozenset({"ask", "claude", "pi"})
HARNESS_ROLES = frozenset({"plan", "work"})
ROLE_ORDER = ("plan", "work")
ROLE_TITLES = {"plan": "Plan", "work": "Work"}
DIFF_TOOLS = frozenset({"auto", "comview", "hunk", "none"})
HARNESS_KEYS = frozenset({"tool", "permission_mode", "prompt", "command"})
ROLE_HARNESS_KEYS = HARNESS_KEYS | frozenset({"role", "title", "enabled"})
DIFF_KEYS = frozenset({"tool"})
TOP_LEVEL_KEYS = frozenset({"harness", "harnesses", "diff"})


class ConfigError(ValueError):
    """Raised when bench configuration is malformed or cannot be resolved."""


@dataclasses.dataclass
class HarnessConfig:
    tool: str | None = None
    permission_mode: str | None = None
    prompt: str | None = None
    command: tuple[str, ...] | None = None
    title: str | None = None
    use_default_prompt: bool = True


@dataclasses.dataclass
class DiffConfig:
    tool: str | None = None


@dataclasses.dataclass
class BenchConfig:
    harnesses: dict[str, HarnessConfig] = dataclasses.field(default_factory=dict)
    disabled_roles: set[str] = dataclasses.field(default_factory=set)
    diff: DiffConfig = dataclasses.field(default_factory=DiffConfig)


def user_config_path() -> pathlib.Path:
    xdg_config_home = os.environ.get("XDG_CONFIG_HOME")
    if xdg_config_home:
        return pathlib.Path(xdg_config_home).expanduser() / "bench" / "config.toml"
    return pathlib.Path.home() / ".config" / "bench" / "config.toml"


def repo_config_path(repo_root: pathlib.Path) -> pathlib.Path:
    return repo_root.expanduser() / ".bench" / "config.toml"


def load_config_file(path: pathlib.Path) -> dict[str, Any]:
    try:
        with path.open("rb") as handle:
            data = tomllib.load(handle)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"Invalid TOML in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigError(f"Configuration in {path} must be a TOML table")
    return data


def config_paths(repo_root: pathlib.Path) -> list[pathlib.Path]:
    return [user_config_path(), repo_config_path(repo_root)]


def merge_config_file(config: BenchConfig, path: pathlib.Path) -> None:
    if not path.exists():
        return
    data = load_config_file(path)
    merge_layer(config, data, source=str(path))


def merge_layer(config: BenchConfig, data: dict[str, Any], *, source: str) -> None:
    unknown_top_level = set(data) - TOP_LEVEL_KEYS
    if unknown_top_level:
        raise ConfigError(
            f"Unknown key in {source}: {format_key_list(unknown_top_level)}"
        )

    harness = data.get("harness")
    if harness is not None and not isinstance(harness, dict):
        raise ConfigError(f"[harness] in {source} must be a table")

    harness_entries = parse_role_harness_entries(data.get("harnesses"), source=source)
    if harness is not None and any(role == "work" for role, _entry in harness_entries):
        raise ConfigError(
            f"{source} cannot both define [harness] and [[harnesses]] role = \"work\""
        )

    if harness is not None:
        merge_legacy_work_harness(config, harness, source=source)

    for role, entry in harness_entries:
        merge_role_harness(config, role, entry, source=source)

    diff = data.get("diff")
    if diff is not None:
        if not isinstance(diff, dict):
            raise ConfigError(f"[diff] in {source} must be a table")
        merge_diff_layer(config.diff, diff, source=source)


def parse_role_harness_entries(
    value: Any, *, source: str
) -> list[tuple[str, dict[str, Any]]]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ConfigError(f"[[harnesses]] in {source} must be an array of tables")

    entries: list[tuple[str, dict[str, Any]]] = []
    seen: set[str] = set()
    for index, entry in enumerate(value):
        if not isinstance(entry, dict):
            raise ConfigError(f"[[harnesses]] entry {index} in {source} must be a table")
        unknown_keys = set(entry) - ROLE_HARNESS_KEYS
        if unknown_keys:
            raise ConfigError(
                f"Unknown key in [[harnesses]] in {source}: {format_key_list(unknown_keys)}"
            )
        role = require_non_empty_string(entry.get("role"), "harnesses.role", source)
        if role not in HARNESS_ROLES:
            raise ConfigError(f"Unsupported harness role in {source}: {role}")
        if role in seen:
            raise ConfigError(f"Duplicate harness role in {source}: {role}")
        seen.add(role)
        entries.append((role, entry))
    return entries


def merge_legacy_work_harness(
    config: BenchConfig, data: dict[str, Any], *, source: str
) -> None:
    work = config.harnesses.setdefault("work", HarnessConfig())
    work.use_default_prompt = True
    config.disabled_roles.discard("work")
    merge_harness_layer(work, data, source=source)


def merge_role_harness(
    config: BenchConfig, role: str, data: dict[str, Any], *, source: str
) -> None:
    if "enabled" in data:
        enabled = data["enabled"]
        if not isinstance(enabled, bool):
            raise ConfigError(f"harnesses.enabled in {source} must be a boolean")
        if enabled is False:
            extra_keys = set(data) - {"role", "enabled"}
            if extra_keys:
                raise ConfigError(
                    "enabled = false cannot be combined with other harness fields"
                )
            config.harnesses.pop(role, None)
            config.disabled_roles.add(role)
            return

    harness = config.harnesses.setdefault(role, HarnessConfig(use_default_prompt=False))
    harness.use_default_prompt = False
    harness.prompt = None
    config.disabled_roles.discard(role)

    if "title" in data:
        harness.title = require_non_empty_string(data["title"], "harnesses.title", source)

    harness_data = {key: value for key, value in data.items() if key in HARNESS_KEYS}
    merge_harness_layer(harness, harness_data, source=source)


def merge_harness_layer(
    config: HarnessConfig, data: dict[str, Any], *, source: str
) -> None:
    unknown_keys = set(data) - HARNESS_KEYS
    if unknown_keys:
        raise ConfigError(f"Unknown key in [harness] in {source}: {format_key_list(unknown_keys)}")
    if "tool" in data and "command" in data:
        raise ConfigError("harness.tool and harness.command are mutually exclusive")

    if "tool" in data:
        tool = require_non_empty_string(data["tool"], "harness.tool", source)
        if tool not in HARNESS_TOOLS:
            raise ConfigError(f"Unsupported harness.tool in {source}: {tool}")
        config.tool = tool
        config.command = None
        config.permission_mode = None

    if "command" in data:
        command = require_command(data["command"], source)
        config.command = command
        config.tool = None
        config.permission_mode = None

    if "permission_mode" in data:
        config.permission_mode = require_non_empty_string(
            data["permission_mode"], "harness.permission_mode", source
        )

    if "prompt" in data:
        config.prompt = require_non_empty_string(data["prompt"], "harness.prompt", source)


def merge_diff_layer(config: DiffConfig, data: dict[str, Any], *, source: str) -> None:
    unknown_keys = set(data) - DIFF_KEYS
    if unknown_keys:
        raise ConfigError(f"Unknown key in [diff] in {source}: {format_key_list(unknown_keys)}")
    if "tool" in data:
        tool = require_non_empty_string(data["tool"], "diff.tool", source)
        if tool not in DIFF_TOOLS:
            raise ConfigError(f"Unsupported diff.tool in {source}: {tool}")
        config.tool = tool


def require_non_empty_string(value: Any, key: str, source: str) -> str:
    if not isinstance(value, str) or value == "":
        raise ConfigError(f"{key} in {source} must be a non-empty string")
    return value


def require_command(value: Any, source: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise ConfigError(f"harness.command in {source} must be a non-empty argv array")
    command: list[str] = []
    for item in value:
        if not isinstance(item, str) or item == "":
            raise ConfigError(
                f"harness.command in {source} must contain only non-empty strings"
            )
        command.append(item)
    return tuple(command)


def format_key_list(keys: set[str]) -> str:
    return ", ".join(sorted(keys))


def available_tools(names: Sequence[str], which: Callable[[str], str | None]) -> list[str]:
    return [name for name in names if which(name)]


def render_template(value: str, *, brief: pathlib.Path) -> str:
    formatter = string.Formatter()
    try:
        parsed = list(formatter.parse(value))
    except ValueError as exc:
        raise ConfigError(f"Invalid placeholder syntax: {exc}") from exc
    for _literal_text, field_name, format_spec, conversion in parsed:
        if field_name is None:
            continue
        if field_name != "brief" or format_spec or conversion:
            raise ConfigError(
                f"Unsupported placeholder {{{field_name}}}; only {{brief}} is supported"
            )
    try:
        return value.format(brief=str(brief))
    except ValueError as exc:
        raise ConfigError(f"Invalid placeholder syntax: {exc}") from exc


def require_executable(name: str, which: Callable[[str], str | None]) -> None:
    if not which(name):
        raise ConfigError(f"Executable not found: {name}")


def render_prompt(config: HarnessConfig, *, brief: pathlib.Path) -> str | None:
    if config.prompt is not None:
        return render_template(config.prompt, brief=brief)
    if config.use_default_prompt:
        return render_template(DEFAULT_PROMPT, brief=brief)
    return None


def with_role(result: dict[str, Any], *, role: str, title: str) -> dict[str, Any]:
    return {"role": role, "title": title, **result}


def resolve_harness(
    config: HarnessConfig,
    *,
    brief: pathlib.Path,
    which: Callable[[str], str | None],
    role: str,
    title: str,
) -> dict[str, Any]:
    prompt = render_prompt(config, brief=brief)
    available = available_tools(["claude", "pi"], which)

    if config.command is not None:
        if config.permission_mode is not None:
            raise ConfigError("harness.permission_mode cannot be used with harness.command")
        argv = [render_template(arg, brief=brief) for arg in config.command]
        require_executable(argv[0], which)
        if prompt is not None:
            argv.append(prompt)
        return with_role(
            {
                "tool": "custom",
                "argv": argv,
                "available": available,
                "selection_required": False,
            },
            role=role,
            title=title,
        )

    tool = config.tool or "ask"
    if tool == "ask":
        if config.permission_mode is not None:
            raise ConfigError("harness.permission_mode cannot be used when harness.tool is ask")
        return with_role(
            {
                "tool": None,
                "argv": [],
                "available": available,
                "selection_required": True,
            },
            role=role,
            title=title,
        )

    if tool == "claude":
        permission_mode = config.permission_mode or "plan"
        if permission_mode not in CLAUDE_PERMISSION_MODES:
            raise ConfigError(f"Unsupported Claude permission_mode: {permission_mode}")
        require_executable("claude", which)
        argv = ["claude", "--permission-mode", permission_mode]
        if prompt is not None:
            argv.append(prompt)
        return with_role(
            {
                "tool": "claude",
                "argv": argv,
                "available": available,
                "selection_required": False,
            },
            role=role,
            title=title,
        )

    if tool == "pi":
        if config.permission_mode is not None:
            raise ConfigError("harness.permission_mode is not supported for pi")
        require_executable("pi", which)
        argv = ["pi"]
        if prompt is not None:
            argv.extend([f"@{brief}", prompt])
        return with_role(
            {
                "tool": "pi",
                "argv": argv,
                "available": available,
                "selection_required": False,
            },
            role=role,
            title=title,
        )

    raise ConfigError(f"Unsupported harness.tool: {tool}")


def resolve_diff(
    config: DiffConfig, *, which: Callable[[str], str | None]
) -> dict[str, Any]:
    available = available_tools(["comview", "hunk"], which)
    tool = config.tool or "auto"

    if tool == "auto":
        if len(available) == 0:
            resolved_tool = "none"
            selection_required = False
        elif len(available) == 1:
            resolved_tool = available[0]
            selection_required = False
        else:
            resolved_tool = None
            selection_required = True
        return {
            "tool": resolved_tool,
            "available": available,
            "selection_required": selection_required,
        }

    if tool == "none":
        return {"tool": "none", "available": available, "selection_required": False}

    if tool in {"comview", "hunk"}:
        require_executable(tool, which)
        return {"tool": tool, "available": available, "selection_required": False}

    raise ConfigError(f"Unsupported diff.tool: {tool}")


def apply_harness_tool_override(
    config: BenchConfig, *, role: str, tool: str, source: str
) -> None:
    if tool not in HARNESS_TOOLS:
        raise ConfigError(f"Unsupported {source}: {tool}")
    if role in config.disabled_roles or role not in config.harnesses:
        config.harnesses[role] = HarnessConfig(use_default_prompt=True)
    harness = config.harnesses[role]
    harness.tool = tool
    harness.command = None
    harness.permission_mode = None
    config.disabled_roles.discard(role)


def resolved_harnesses(
    config: BenchConfig, *, brief: pathlib.Path, which: Callable[[str], str | None]
) -> list[dict[str, Any]]:
    resolved: list[dict[str, Any]] = []
    for role in ROLE_ORDER:
        harness = config.harnesses.get(role)
        if harness is None:
            continue
        resolved.append(
            resolve_harness(
                harness,
                brief=brief,
                which=which,
                role=role,
                title=harness.title or ROLE_TITLES[role],
            )
        )
    return resolved


def resolve_config(
    *,
    repo_root: pathlib.Path,
    brief: pathlib.Path,
    harness_tool: str | None = None,
    plan_harness_tool: str | None = None,
    diff_tool: str | None = None,
    which: Callable[[str], str | None] | None = None,
) -> dict[str, Any]:
    which = shutil.which if which is None else which
    config = BenchConfig()
    for path in config_paths(repo_root):
        merge_config_file(config, path)

    if plan_harness_tool is not None:
        apply_harness_tool_override(
            config, role="plan", tool=plan_harness_tool, source="--plan-harness-tool"
        )

    if harness_tool is not None:
        apply_harness_tool_override(
            config, role="work", tool=harness_tool, source="--harness-tool"
        )

    if "work" in config.disabled_roles and "work" not in config.harnesses:
        raise ConfigError("work harness is disabled and no explicit Work override was provided")
    if "work" not in config.harnesses:
        config.harnesses["work"] = HarnessConfig(use_default_prompt=True)

    if diff_tool is not None:
        if diff_tool not in DIFF_TOOLS:
            raise ConfigError(f"Unsupported --diff-tool: {diff_tool}")
        config.diff.tool = diff_tool

    harnesses = resolved_harnesses(config, brief=brief, which=which)
    work = next(item for item in harnesses if item["role"] == "work")
    return {
        "harness": work,
        "harnesses": harnesses,
        "diff": resolve_diff(config.diff, which=which),
    }


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Resolve layered bench harness and diff configuration as JSON."
    )
    parser.add_argument(
        "--repo-root",
        default=".",
        help="source repository root containing optional .bench/config.toml",
    )
    parser.add_argument("--brief", required=True, help="handoff brief path")
    parser.add_argument(
        "--harness-tool",
        choices=sorted(HARNESS_TOOLS),
        help="explicit Work harness selection for this request",
    )
    parser.add_argument(
        "--plan-harness-tool",
        choices=sorted(HARNESS_TOOLS),
        help="explicit Plan harness selection for this request",
    )
    parser.add_argument(
        "--diff-tool",
        choices=sorted(DIFF_TOOLS),
        help="explicit diff viewer selection for this request",
    )
    return parser.parse_args(argv)


def execute(argv: Sequence[str]) -> str:
    args = parse_args(argv)
    resolved = resolve_config(
        repo_root=pathlib.Path(args.repo_root),
        brief=pathlib.Path(args.brief),
        harness_tool=args.harness_tool,
        plan_harness_tool=args.plan_harness_tool,
        diff_tool=args.diff_tool,
    )
    return json.dumps(resolved, indent=2, sort_keys=True) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    try:
        sys.stdout.write(execute(sys.argv[1:] if argv is None else argv))
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
