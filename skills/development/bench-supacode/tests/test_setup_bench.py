from __future__ import annotations

import importlib.util
import json
import pathlib
import sys
import unittest
from collections import defaultdict, deque
from collections.abc import Sequence
from unittest import mock

SCRIPT = pathlib.Path(__file__).parents[1] / "scripts" / "setup_bench.py"
SPEC = importlib.util.spec_from_file_location("setup_bench", SCRIPT)
assert SPEC and SPEC.loader
SETUP_BENCH = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = SETUP_BENCH
SPEC.loader.exec_module(SETUP_BENCH)

BENCH_PATH = "/tmp/example bench"
WORKTREE = "%2Ftmp%2Fexample%20bench%2F"
WORK_TAB = "AAAAAAAA-AAAA-AAAA-AAAA-AAAAAAAAAAAA"
WORK_SURFACE = "BBBBBBBB-BBBB-BBBB-BBBB-BBBBBBBBBBBB"
WORK_SESSION = "supa-bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
WORK_ROOT_PID = 1234
WORK_SHELL_PID = 1235
DIFF_TAB = "CCCCCCCC-CCCC-CCCC-CCCC-CCCCCCCCCCCC"
DIFF_SESSION = "supa-cccccccc-cccc-cccc-cccc-cccccccccccc"
DIFF_ROOT_PID = 5678
DIFF_SHELL_PID = 5679
HARNESS = ("claude", "--permission-mode", "plan", "Read /tmp/brief.md")
DIFF_COMMAND = "comview watch -- git diff main...HEAD"


class FakeRunner:
    def __init__(self) -> None:
        self.commands: list[tuple[str, ...]] = []
        self.responses: dict[tuple[str, ...], deque[str]] = defaultdict(deque)

    def add(self, command: Sequence[str], *outputs: str) -> None:
        self.responses[tuple(command)].extend(outputs)

    def __call__(self, command: Sequence[str]) -> str:
        key = tuple(command)
        self.commands.append(key)
        if not self.responses[key]:
            raise AssertionError(f"Unexpected command: {key!r}")
        return self.responses[key].popleft()

    def assert_consumed(self) -> None:
        remaining = {
            command: list(outputs)
            for command, outputs in self.responses.items()
            if outputs
        }
        if remaining:
            raise AssertionError(f"Unused command responses: {remaining!r}")


def request():
    return SETUP_BENCH.BenchRequest(
        path=BENCH_PATH,
        title="Example task",
        color="blue",
        diff_command=DIFF_COMMAND,
        harness=HARNESS,
    )


def happy_runner() -> FakeRunner:
    runner = FakeRunner()
    runner.add(("supacode", "worktree", "list"), "", f"{WORKTREE}\n")
    runner.add(("supacode", "repo", "open", BENCH_PATH), "")
    runner.add(
        (
            "supacode",
            "worktree",
            "appearance",
            "-w",
            WORKTREE,
            "--title",
            "Example task",
            "--color",
            "blue",
        ),
        "",
    )
    runner.add(("supacode", "worktree", "focus", "-w", WORKTREE), "")
    runner.add(
        ("supacode", "tab", "list", "-w", WORKTREE),
        f"{WORK_TAB}\n",
        f"{WORK_TAB}\n{DIFF_TAB}\n",
    )
    runner.add(
        ("supacode", "surface", "list", "-w", WORKTREE, "-t", WORK_TAB),
        f"{WORK_SURFACE}\n",
        f"{WORK_SURFACE}\n",
    )
    runner.add(("zmx", "list", "--short"), f"other\n{WORK_SESSION}\n")
    runner.add(
        ("supacode", "tab", "rename", "-w", WORKTREE, "-t", WORK_TAB, "--title", "Work"),
        "",
    )
    runner.add(("zmx", "run", WORK_SESSION, "-d", *HARNESS), "command sent!\n")
    runner.add(
        (
            "supacode",
            "tab",
            "new",
            "-w",
            WORKTREE,
            "--title",
            "Diff",
            "-i",
            DIFF_COMMAND,
        ),
        f"{DIFF_TAB}\n",
    )
    runner.add(
        ("supacode", "surface", "list", "-w", WORKTREE, "-t", DIFF_TAB),
        f"{DIFF_TAB}\n",
    )
    runner.add(
        ("zmx", "list"),
        (
            f"name={WORK_SESSION}\tpid={WORK_ROOT_PID}\tclients=1"
            f"\tstart_dir={BENCH_PATH}\n"
            f"name={DIFF_SESSION}\tpid={DIFF_ROOT_PID}\tclients=1"
            f"\tstart_dir={BENCH_PATH}\n"
        ),
    )
    runner.add(("pgrep", "-P", str(WORK_ROOT_PID)), f"{WORK_SHELL_PID}\n")
    runner.add(
        ("lsof", "-a", "-d", "cwd", "-p", str(WORK_SHELL_PID), "-Fn"),
        f"p{WORK_SHELL_PID}\nfcwd\nn{BENCH_PATH}\n",
    )
    runner.add(("pgrep", "-P", str(DIFF_ROOT_PID)), f"{DIFF_SHELL_PID}\n")
    runner.add(
        ("lsof", "-a", "-d", "cwd", "-p", str(DIFF_SHELL_PID), "-Fn"),
        f"p{DIFF_SHELL_PID}\nfcwd\nn{BENCH_PATH}\n",
    )
    runner.add(("supacode", "tab", "focus", "-w", WORKTREE, "-t", WORK_TAB), "")
    return runner


class SetupBenchTests(unittest.TestCase):
    def test_happy_path_reuses_default_tab_and_returns_resource_ids(self) -> None:
        runner = happy_runner()

        result = SETUP_BENCH.setup_bench(request(), run=runner)

        self.assertEqual(
            result.as_dict(),
            {
                "worktree": WORKTREE,
                "work_tab": WORK_TAB,
                "work_surface": WORK_SURFACE,
                "work_session": WORK_SESSION,
                "work_shell_pid": WORK_SHELL_PID,
                "diff_tab": DIFF_TAB,
                "diff_surface": DIFF_TAB,
                "diff_session": DIFF_SESSION,
                "diff_shell_pid": DIFF_SHELL_PID,
            },
        )
        self.assertIn(("zmx", "run", WORK_SESSION, "-d", *HARNESS), runner.commands)
        self.assertEqual(
            runner.commands[-1],
            ("supacode", "tab", "focus", "-w", WORKTREE, "-t", WORK_TAB),
        )
        runner.assert_consumed()

    def test_expands_home_before_opening_repo(self) -> None:
        runner = happy_runner()
        home_request = SETUP_BENCH.BenchRequest(
            path="~/example bench",
            title="Example task",
            color="blue",
            diff_command=DIFF_COMMAND,
            harness=HARNESS,
        )

        with mock.patch.dict("os.environ", {"HOME": "/tmp"}):
            SETUP_BENCH.setup_bench(home_request, run=runner)

        self.assertIn(("supacode", "repo", "open", BENCH_PATH), runner.commands)
        runner.assert_consumed()

    def test_refuses_preexisting_worktree_before_opening_repo(self) -> None:
        runner = FakeRunner()
        runner.add(("supacode", "worktree", "list"), f"{WORKTREE}\n")

        with self.assertRaisesRegex(SETUP_BENCH.SetupError, "already registered"):
            SETUP_BENCH.setup_bench(request(), run=runner)

        self.assertNotIn(("supacode", "repo", "open", BENCH_PATH), runner.commands)

    def test_reports_timeout_when_opened_worktree_never_appears(self) -> None:
        runner = FakeRunner()
        runner.add(("supacode", "worktree", "list"), "", "")
        runner.add(("supacode", "repo", "open", BENCH_PATH), "")

        with self.assertRaisesRegex(SETUP_BENCH.SetupError, "did not appear"):
            SETUP_BENCH.setup_bench(request(), run=runner, timeout=0)

    def test_refuses_unexpected_initial_tab_count_before_renaming(self) -> None:
        runner = happy_runner()
        runner.responses[("supacode", "tab", "list", "-w", WORKTREE)][0] = (
            f"{WORK_TAB}\n{DIFF_TAB}\n"
        )

        with self.assertRaisesRegex(SETUP_BENCH.SetupError, "exactly one default tab"):
            SETUP_BENCH.setup_bench(request(), run=runner)

        self.assertFalse(any(command[:3] == ("supacode", "tab", "rename") for command in runner.commands))

    def test_refuses_unexpected_initial_surface_layout(self) -> None:
        runner = happy_runner()
        runner.responses[
            ("supacode", "surface", "list", "-w", WORKTREE, "-t", WORK_TAB)
        ][0] = f"{WORK_SURFACE}\n{DIFF_TAB}\n"

        with self.assertRaisesRegex(SETUP_BENCH.SetupError, "exactly one default surface"):
            SETUP_BENCH.setup_bench(request(), run=runner)

    def test_refuses_a_nondefault_surface_id(self) -> None:
        runner = happy_runner()
        runner.responses[
            ("supacode", "surface", "list", "-w", WORKTREE, "-t", WORK_TAB)
        ][0] = f"{WORK_TAB}\n"

        with self.assertRaisesRegex(SETUP_BENCH.SetupError, "distinct id"):
            SETUP_BENCH.setup_bench(request(), run=runner)

    def test_refuses_missing_zmx_session_before_renaming(self) -> None:
        runner = happy_runner()
        runner.responses[("zmx", "list", "--short")][0] = "other\n"

        with self.assertRaisesRegex(SETUP_BENCH.SetupError, "zmx session"):
            SETUP_BENCH.setup_bench(request(), run=runner)

        self.assertFalse(any(command[:3] == ("supacode", "tab", "rename") for command in runner.commands))

    def test_rejects_an_invalid_final_tab_layout(self) -> None:
        runner = happy_runner()
        runner.responses[("supacode", "tab", "list", "-w", WORKTREE)][1] = f"{WORK_TAB}\n"

        with self.assertRaisesRegex(SETUP_BENCH.SetupError, "final tabs"):
            SETUP_BENCH.setup_bench(request(), run=runner)

        self.assertNotEqual(
            runner.commands[-1],
            ("supacode", "tab", "focus", "-w", WORKTREE, "-t", WORK_TAB),
        )


    def test_rejects_a_backing_session_outside_the_bench_path(self) -> None:
        runner = happy_runner()
        runner.responses[("zmx", "list")][0] = (
            f"name={WORK_SESSION}\tpid={WORK_ROOT_PID}\tstart_dir=/tmp/wrong\n"
            f"name={DIFF_SESSION}\tpid={DIFF_ROOT_PID}\tstart_dir={BENCH_PATH}\n"
        )

        with self.assertRaisesRegex(SETUP_BENCH.SetupError, "starts outside"):
            SETUP_BENCH.setup_bench(request(), run=runner)


    def test_rejects_a_shell_process_outside_the_bench_path(self) -> None:
        runner = happy_runner()
        runner.responses[
            ("lsof", "-a", "-d", "cwd", "-p", str(WORK_SHELL_PID), "-Fn")
        ][0] = f"p{WORK_SHELL_PID}\nfcwd\nn/tmp/wrong\n"

        with self.assertRaisesRegex(SETUP_BENCH.SetupError, "shell starts outside"):
            SETUP_BENCH.setup_bench(request(), run=runner)

    def test_cli_parses_harness_as_argv_remainder(self) -> None:
        parsed = SETUP_BENCH.parse_args(
            [
                "--path",
                BENCH_PATH,
                "--title",
                "Example task",
                "--color",
                "blue",
                "--diff-command",
                DIFF_COMMAND,
                "--",
                *HARNESS,
            ]
        )

        self.assertEqual(parsed.harness, HARNESS)

    def test_main_prints_json_result(self) -> None:
        runner = happy_runner()

        output = SETUP_BENCH.execute(
            [
                "--path",
                BENCH_PATH,
                "--title",
                "Example task",
                "--color",
                "blue",
                "--diff-command",
                DIFF_COMMAND,
                "--",
                *HARNESS,
            ],
            run=runner,
        )

        self.assertEqual(json.loads(output)["work_session"], WORK_SESSION)

        runner.assert_consumed()


if __name__ == "__main__":
    unittest.main()
