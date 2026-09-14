#!/usr/bin/env python3
"""Open and arrange a new Supacode bench."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.parse import quote


class SetupError(RuntimeError):
    """A safe bench setup could not be completed."""


class Runner(Protocol):
    def __call__(self, command: Sequence[str]) -> str: ...


HARNESS_ROLES = frozenset({"plan", "work"})


@dataclass(frozen=True)
class HarnessTab:
    role: str
    title: str
    argv: tuple[str, ...]


@dataclass(frozen=True)
class HarnessTabResult:
    role: str
    title: str
    tab: str
    surface: str
    session: str
    shell_pid: int

    def as_dict(self) -> dict[str, str | int]:
        return {
            "role": self.role,
            "title": self.title,
            "tab": self.tab,
            "surface": self.surface,
            "session": self.session,
            "shell_pid": self.shell_pid,
        }


@dataclass(frozen=True)
class BenchRequest:
    path: str
    title: str
    color: str
    harness_tabs: tuple[HarnessTab, ...]
    companion_title: str | None = None
    companion_command: str | None = None
    pin: bool = False


@dataclass(frozen=True)
class BenchResult:
    worktree: str
    work_tab: str
    work_surface: str
    work_session: str
    work_shell_pid: int
    harness_tabs: tuple[HarnessTabResult, ...]
    companion_tab: str | None
    companion_surface: str | None
    companion_session: str | None
    companion_shell_pid: int | None
    pinned: bool

    def as_dict(self) -> dict[str, str | int | bool | None | list[dict[str, str | int]]]:
        return {
            "worktree": self.worktree,
            "work_tab": self.work_tab,
            "work_surface": self.work_surface,
            "work_session": self.work_session,
            "work_shell_pid": self.work_shell_pid,
            "harness_tabs": [tab.as_dict() for tab in self.harness_tabs],
            "companion_tab": self.companion_tab,
            "companion_surface": self.companion_surface,
            "companion_session": self.companion_session,
            "companion_shell_pid": self.companion_shell_pid,
            "pinned": self.pinned,
        }


def run_command(command: Sequence[str]) -> str:
    """Run one external command and return stdout."""
    try:
        completed = subprocess.run(
            list(command),
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as error:
        detail = (error.stderr or error.stdout or "").strip()
        suffix = f": {detail}" if detail else ""
        raise SetupError(f"Command failed: {' '.join(command)}{suffix}") from error
    return completed.stdout


def normalized_path(path: str) -> str:
    """Expand a local path without resolving path symlinks such as /tmp."""
    return os.path.abspath(os.path.expanduser(path)).rstrip(os.sep) or os.sep


def worktree_id(path: str) -> str:
    """Return Supacode's percent-encoded id for a local worktree path."""
    normalized = normalized_path(path).rstrip(os.sep) + os.sep
    return quote(normalized, safe="")


def output_lines(output: str) -> list[str]:
    return [line.strip() for line in output.splitlines() if line.strip()]


def exactly_one(values: Sequence[str], description: str) -> str:
    if len(values) != 1:
        raise SetupError(f"Expected exactly one {description}; found {len(values)}")
    return values[0]


def parse_zmx_sessions(output: str) -> dict[str, dict[str, str]]:
    sessions: dict[str, dict[str, str]] = {}
    for line in output.splitlines():
        fields: dict[str, str] = {}
        normalized = line.strip().removeprefix("→").strip()
        for item in normalized.split("\t"):
            if "=" in item:
                key, value = item.split("=", 1)
                fields[key] = value
        if name := fields.get("name"):
            sessions[name] = fields
    return sessions


def require_session_shell(
    sessions: dict[str, dict[str, str]],
    name: str,
    bench_path: str,
    *,
    run: Runner,
) -> int:
    details = sessions.get(name)
    if details is None:
        raise SetupError(f"Expected zmx session details were not found: {name}")
    try:
        root_pid = int(details["pid"])
        start_dir = details.get("start_dir") or details["cwd"]
    except (KeyError, ValueError) as error:
        raise SetupError(f"Incomplete zmx session details for {name}") from error
    if os.path.realpath(start_dir) != os.path.realpath(bench_path):
        raise SetupError(f"zmx session {name} starts outside the bench: {start_dir}")

    shell_pid_text = exactly_one(
        output_lines(run(("pgrep", "-P", str(root_pid)))),
        f"shell process for {name}",
    )
    try:
        shell_pid = int(shell_pid_text)
    except ValueError as error:
        raise SetupError(f"Invalid shell pid for {name}: {shell_pid_text}") from error

    lsof_output = output_lines(
        run(("lsof", "-a", "-d", "cwd", "-p", str(shell_pid), "-Fn"))
    )
    shell_cwd = exactly_one(
        [line[1:] for line in lsof_output if line.startswith("n")],
        f"shell cwd for {name}",
    )
    if os.path.realpath(shell_cwd) != os.path.realpath(bench_path):
        raise SetupError(f"zmx session {name} shell starts outside the bench: {shell_cwd}")
    return shell_pid


def wait_for_worktree(
    expected: str,
    *,
    run: Runner,
    sleep: Callable[[float], None],
    monotonic: Callable[[], float],
    timeout: float,
    poll_interval: float,
) -> None:
    deadline = monotonic() + timeout
    while True:
        if expected in output_lines(run(("supacode", "worktree", "list"))):
            return
        if monotonic() >= deadline:
            raise SetupError(f"Supacode worktree did not appear: {expected}")
        sleep(poll_interval)


def validate_harness_tabs(harness_tabs: Sequence[HarnessTab]) -> tuple[HarnessTab, ...]:
    if not harness_tabs:
        raise SetupError("At least one harness tab is required")
    plan_count = 0
    work_count = 0
    validated: list[HarnessTab] = []
    for tab in harness_tabs:
        if tab.role not in HARNESS_ROLES:
            raise SetupError(f"Unsupported harness tab role: {tab.role}")
        if tab.title == "":
            raise SetupError(f"Harness tab title is required for role {tab.role}")
        if not tab.argv:
            raise SetupError(f"Harness command is required for role {tab.role}")
        if tab.role == "plan":
            plan_count += 1

        if tab.role == "work":
            work_count += 1
        validated.append(tab)
    if plan_count > 1:
        raise SetupError(f"Expected at most one plan harness tab; found {plan_count}")

    if work_count != 1:
        raise SetupError(f"Expected exactly one work harness tab; found {work_count}")
    return tuple(validated)


def require_short_session(name: str, *, run: Runner) -> None:
    sessions = output_lines(run(("zmx", "list", "--short")))
    if name not in sessions:
        raise SetupError(f"Expected zmx session was not found: {name}")


def setup_bench(
    request: BenchRequest,
    *,
    run: Runner = run_command,
    sleep: Callable[[float], None] = time.sleep,
    monotonic: Callable[[], float] = time.monotonic,
    timeout: float = 180.0,
    poll_interval: float = 0.25,
) -> BenchResult:
    """Create the Supacode layout for a new bench."""
    if (request.companion_title is None) != (request.companion_command is None):
        raise SetupError("companion title and command must be specified together")
    harness_tabs = validate_harness_tabs(request.harness_tabs)

    bench_path = normalized_path(request.path)
    worktree = worktree_id(bench_path)
    existing = output_lines(run(("supacode", "worktree", "list")))
    if worktree in existing:
        raise SetupError(f"Bench worktree is already registered: {worktree}")

    run(("supacode", "repo", "open", bench_path))
    wait_for_worktree(
        worktree,
        run=run,
        sleep=sleep,
        monotonic=monotonic,
        timeout=timeout,
        poll_interval=poll_interval,
    )

    run(
        (
            "supacode",
            "worktree",
            "appearance",
            "-w",
            worktree,
            "--title",
            request.title,
            "--color",
            request.color,
        )
    )
    if request.pin:
        run(
            (
                "supacode",
                "worktree",
                "pin",
                "-w",
                worktree,
                "--background",
            )
        )
    run(("supacode", "worktree", "focus", "-w", worktree))

    default_tab = exactly_one(
        output_lines(run(("supacode", "tab", "list", "-w", worktree))),
        "default tab",
    )
    default_surface = exactly_one(
        output_lines(
            run(
                (
                    "supacode",
                    "surface",
                    "list",
                    "-w",
                    worktree,
                    "-t",
                    default_tab,
                )
            )
        ),
        "default surface",
    )
    if default_surface == default_tab:
        raise SetupError("Expected the default surface to have a distinct id")

    harness_results: list[HarnessTabResult] = []
    first = harness_tabs[0]
    first_session = f"supa-{default_surface.lower()}"
    require_short_session(first_session, run=run)
    run(
        (
            "supacode",
            "tab",
            "rename",
            "-w",
            worktree,
            "-t",
            default_tab,
            "--title",
            first.title,
        )
    )
    run(("zmx", "run", first_session, "-d", *first.argv))
    harness_results.append(
        HarnessTabResult(
            role=first.role,
            title=first.title,
            tab=default_tab,
            surface=default_surface,
            session=first_session,
            shell_pid=0,
        )
    )

    for tab in harness_tabs[1:]:
        tab_id = exactly_one(
            output_lines(
                run(("supacode", "tab", "new", "-w", worktree, "--title", tab.title))
            ),
            f"{tab.role} tab id",
        )
        surface = exactly_one(
            output_lines(
                run(("supacode", "surface", "list", "-w", worktree, "-t", tab_id))
            ),
            f"{tab.role} surface",
        )
        session = f"supa-{surface.lower()}"
        require_short_session(session, run=run)
        run(("zmx", "run", session, "-d", *tab.argv))
        harness_results.append(
            HarnessTabResult(
                role=tab.role,
                title=tab.title,
                tab=tab_id,
                surface=surface,
                session=session,
                shell_pid=0,
            )
        )

    companion_tab: str | None = None
    companion_surface: str | None = None
    companion_session: str | None = None
    companion_shell_pid: int | None = None
    if request.companion_title is not None and request.companion_command is not None:
        companion_tab = exactly_one(
            output_lines(
                run(
                    (
                        "supacode",
                        "tab",
                        "new",
                        "-w",
                        worktree,
                        "--title",
                        request.companion_title,
                        "-i",
                        request.companion_command,
                    )
                )
            ),
            "companion tab id",
        )

    final_tabs = output_lines(run(("supacode", "tab", "list", "-w", worktree)))
    expected_tabs = {tab.tab for tab in harness_results}
    if companion_tab is not None:
        expected_tabs.add(companion_tab)
    if len(final_tabs) != len(expected_tabs) or set(final_tabs) != expected_tabs:
        raise SetupError(f"Unexpected final tabs: {final_tabs!r}")

    for index, result in enumerate(harness_results):
        final_surface = exactly_one(
            output_lines(
                run(
                    (
                        "supacode",
                        "surface",
                        "list",
                        "-w",
                        worktree,
                        "-t",
                        result.tab,
                    )
                )
            ),
            f"final {result.title} surface",
        )
        if final_surface != result.surface:
            raise SetupError(f"{result.title} surface changed during setup")
        harness_results[index] = result

    if companion_tab is not None:
        companion_surface = exactly_one(
            output_lines(
                run(
                    (
                        "supacode",
                        "surface",
                        "list",
                        "-w",
                        worktree,
                        "-t",
                        companion_tab,
                    )
                )
            ),
            "final companion surface",
        )
        if companion_surface != companion_tab:
            raise SetupError("Companion surface id does not match its tab id")
        companion_session = f"supa-{companion_surface.lower()}"

    sessions = parse_zmx_sessions(run(("zmx", "list")))
    harness_results_with_pids: list[HarnessTabResult] = []
    for result in harness_results:
        shell_pid = require_session_shell(sessions, result.session, bench_path, run=run)
        harness_results_with_pids.append(
            HarnessTabResult(
                role=result.role,
                title=result.title,
                tab=result.tab,
                surface=result.surface,
                session=result.session,
                shell_pid=shell_pid,
            )
        )
    if companion_session is not None:
        companion_shell_pid = require_session_shell(
            sessions, companion_session, bench_path, run=run
        )

    work_result = next(result for result in harness_results_with_pids if result.role == "work")
    run(("supacode", "tab", "focus", "-w", worktree, "-t", work_result.tab))
    return BenchResult(
        worktree=worktree,
        work_tab=work_result.tab,
        work_surface=work_result.surface,
        work_session=work_result.session,
        work_shell_pid=work_result.shell_pid,
        harness_tabs=tuple(harness_results_with_pids),
        companion_tab=companion_tab,
        companion_surface=companion_surface,
        companion_session=companion_session,
        companion_shell_pid=companion_shell_pid,
        pinned=request.pin,
    )


def require_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or value == "":
        raise ValueError(f"{field} must be a non-empty string")
    return value


def parse_harness_tabs_json(value: str) -> tuple[HarnessTab, ...]:
    raw = json.loads(value)
    if not isinstance(raw, list):
        raise ValueError("harness tabs must be a JSON array")
    tabs: list[HarnessTab] = []
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError(f"harness tab {index} must be an object")
        role = require_string(item.get("role"), f"harness tab {index} role")
        title = require_string(item.get("title"), f"harness tab {index} title")
        argv = item.get("argv")
        if not isinstance(argv, list) or not argv:
            raise ValueError(f"harness tab {index} argv must be a non-empty array")
        if not all(isinstance(arg, str) and arg for arg in argv):
            raise ValueError(f"harness tab {index} argv must contain non-empty strings")
        tabs.append(HarnessTab(role=role, title=title, argv=tuple(argv)))
    validate_harness_tabs(tabs)
    return tuple(tabs)


def parse_args(arguments: Sequence[str]) -> BenchRequest:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--color", required=True)
    parser.add_argument("--companion-title")
    parser.add_argument("--companion-command")
    parser.add_argument("--harness-tabs-json")
    parser.add_argument("--pin", action="store_true")
    parser.add_argument("harness", nargs=argparse.REMAINDER)
    parsed = parser.parse_args(list(arguments))
    if (parsed.companion_title is None) != (parsed.companion_command is None):
        parser.error("--companion-title and --companion-command must be specified together")
    harness = tuple(parsed.harness)
    if harness[:1] == ("--",):
        harness = harness[1:]
    if parsed.harness_tabs_json is not None and harness:
        parser.error("--harness-tabs-json cannot be combined with a harness command")
    if parsed.harness_tabs_json is not None:
        try:
            harness_tabs = parse_harness_tabs_json(parsed.harness_tabs_json)
        except (json.JSONDecodeError, ValueError, SetupError) as error:
            parser.error(str(error))
    else:
        if not harness:
            parser.error("a harness command is required after --")
        harness_tabs = (HarnessTab(role="work", title="Work", argv=harness),)
    return BenchRequest(
        path=parsed.path,
        title=parsed.title,
        color=parsed.color,
        harness_tabs=harness_tabs,
        companion_title=parsed.companion_title,
        companion_command=parsed.companion_command,
        pin=parsed.pin,
    )


def execute(arguments: Sequence[str], *, run: Runner = run_command) -> str:
    result = setup_bench(parse_args(arguments), run=run)
    return json.dumps(result.as_dict(), sort_keys=True)


def main(arguments: Sequence[str] | None = None) -> int:
    try:
        print(execute(sys.argv[1:] if arguments is None else arguments))
    except SetupError as error:
        print(f"setup_bench: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
