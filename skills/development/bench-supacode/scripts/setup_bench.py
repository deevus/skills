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
from typing import Protocol
from urllib.parse import quote


class SetupError(RuntimeError):
    """A safe bench setup could not be completed."""


class Runner(Protocol):
    def __call__(self, command: Sequence[str]) -> str: ...


@dataclass(frozen=True)
class BenchRequest:
    path: str
    title: str
    color: str
    harness: tuple[str, ...]
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
    companion_tab: str | None
    companion_surface: str | None
    companion_session: str | None
    companion_shell_pid: int | None
    pinned: bool

    def as_dict(self) -> dict[str, str | int | bool | None]:
        return {
            "worktree": self.worktree,
            "work_tab": self.work_tab,
            "work_surface": self.work_surface,
            "work_session": self.work_session,
            "work_shell_pid": self.work_shell_pid,
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
        start_dir = details["start_dir"]
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
    if not request.harness:
        raise SetupError("Harness command is required")

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

    work_tab = exactly_one(
        output_lines(run(("supacode", "tab", "list", "-w", worktree))),
        "default tab",
    )
    work_surface = exactly_one(
        output_lines(
            run(
                (
                    "supacode",
                    "surface",
                    "list",
                    "-w",
                    worktree,
                    "-t",
                    work_tab,
                )
            )
        ),
        "default surface",
    )
    if work_surface == work_tab:
        raise SetupError("Expected the default surface to have a distinct id")

    work_session = f"supa-{work_surface.lower()}"
    sessions = output_lines(run(("zmx", "list", "--short")))
    if work_session not in sessions:
        raise SetupError(f"Expected zmx session was not found: {work_session}")

    run(
        (
            "supacode",
            "tab",
            "rename",
            "-w",
            worktree,
            "-t",
            work_tab,
            "--title",
            "Work",
        )
    )
    run(("zmx", "run", work_session, "-d", *request.harness))

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
    expected_tabs = {work_tab} if companion_tab is None else {work_tab, companion_tab}
    if len(final_tabs) != len(expected_tabs) or set(final_tabs) != expected_tabs:
        raise SetupError(f"Unexpected final tabs: {final_tabs!r}")

    final_work_surface = exactly_one(
        output_lines(
            run(
                (
                    "supacode",
                    "surface",
                    "list",
                    "-w",
                    worktree,
                    "-t",
                    work_tab,
                )
            )
        ),
        "final Work surface",
    )
    if final_work_surface != work_surface:
        raise SetupError("Work surface changed during setup")

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
    work_shell_pid = require_session_shell(
        sessions, work_session, bench_path, run=run
    )
    if companion_session is not None:
        companion_shell_pid = require_session_shell(
            sessions, companion_session, bench_path, run=run
        )

    run(("supacode", "tab", "focus", "-w", worktree, "-t", work_tab))
    return BenchResult(
        worktree=worktree,
        work_tab=work_tab,
        work_surface=work_surface,
        work_session=work_session,
        work_shell_pid=work_shell_pid,
        companion_tab=companion_tab,
        companion_surface=companion_surface,
        companion_session=companion_session,
        companion_shell_pid=companion_shell_pid,
        pinned=request.pin,
    )


def parse_args(arguments: Sequence[str]) -> BenchRequest:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--color", required=True)
    parser.add_argument("--companion-title")
    parser.add_argument("--companion-command")
    parser.add_argument("--pin", action="store_true")
    parser.add_argument("harness", nargs=argparse.REMAINDER)
    parsed = parser.parse_args(list(arguments))
    if (parsed.companion_title is None) != (parsed.companion_command is None):
        parser.error("--companion-title and --companion-command must be specified together")
    harness = tuple(parsed.harness)
    if harness[:1] == ("--",):
        harness = harness[1:]
    if not harness:
        parser.error("a harness command is required after --")
    return BenchRequest(
        path=parsed.path,
        title=parsed.title,
        color=parsed.color,
        harness=harness,
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
