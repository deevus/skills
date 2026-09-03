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
COMPANION_TITLE = "Review"
COMPANION_TAB = "CCCCCCCC-CCCC-CCCC-CCCC-CCCCCCCCCCCC"
COMPANION_SESSION = "supa-cccccccc-cccc-cccc-cccc-cccccccccccc"
COMPANION_ROOT_PID = 5678
COMPANION_SHELL_PID = 5679
HARNESS = ("claude", "--permission-mode", "plan", "Read /tmp/brief.md")
COMPANION_COMMAND = "watch-review -- git diff main...HEAD"


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


def request(
    *,
    companion_title: str | None = None,
    companion_command: str | None = None,
    pin: bool = False,
):
    return SETUP_BENCH.BenchRequest(
        path=BENCH_PATH,
        title="Example task",
        color="blue",
        companion_title=companion_title,
        companion_command=companion_command,
        harness=HARNESS,
        pin=pin,
    )


def companion_request(*, pin: bool = False):
    return request(
        companion_title=COMPANION_TITLE,
        companion_command=COMPANION_COMMAND,
        pin=pin,
    )


def happy_runner(
    *,
    companion_title: str | None = None,
    companion_command: str | None = None,
    pin: bool = False,
) -> FakeRunner:
    has_companion = companion_title is not None and companion_command is not None
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
    if pin:
        runner.add(
            ("supacode", "worktree", "pin", "-w", WORKTREE, "--background"),
            "",
        )
    runner.add(("supacode", "worktree", "focus", "-w", WORKTREE), "")
    final_tabs = f"{WORK_TAB}\n{COMPANION_TAB}\n" if has_companion else f"{WORK_TAB}\n"
    runner.add(
        ("supacode", "tab", "list", "-w", WORKTREE),
        f"{WORK_TAB}\n",
        final_tabs,
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
    if has_companion:
        runner.add(
            (
                "supacode",
                "tab",
                "new",
                "-w",
                WORKTREE,
                "--title",
                companion_title,
                "-i",
                companion_command,
            ),
            f"{COMPANION_TAB}\n",
        )
        runner.add(
            ("supacode", "surface", "list", "-w", WORKTREE, "-t", COMPANION_TAB),
            f"{COMPANION_TAB}\n",
        )
    zmx_details = (
        f"name={WORK_SESSION}\tpid={WORK_ROOT_PID}\tclients=1"
        f"\tstart_dir={BENCH_PATH}\n"
    )
    if has_companion:
        zmx_details += (
            f"name={COMPANION_SESSION}\tpid={COMPANION_ROOT_PID}\tclients=1"
            f"\tstart_dir={BENCH_PATH}\n"
        )
    runner.add(("zmx", "list"), zmx_details)
    runner.add(("pgrep", "-P", str(WORK_ROOT_PID)), f"{WORK_SHELL_PID}\n")
    runner.add(
        ("lsof", "-a", "-d", "cwd", "-p", str(WORK_SHELL_PID), "-Fn"),
        f"p{WORK_SHELL_PID}\nfcwd\nn{BENCH_PATH}\n",
    )
    if has_companion:
        runner.add(("pgrep", "-P", str(COMPANION_ROOT_PID)), f"{COMPANION_SHELL_PID}\n")
        runner.add(
            ("lsof", "-a", "-d", "cwd", "-p", str(COMPANION_SHELL_PID), "-Fn"),
            f"p{COMPANION_SHELL_PID}\nfcwd\nn{BENCH_PATH}\n",
        )
    runner.add(("supacode", "tab", "focus", "-w", WORKTREE, "-t", WORK_TAB), "")
    return runner


class SetupBenchTests(unittest.TestCase):
    def test_work_only_reuses_default_tab_and_returns_nullable_companion_fields(self) -> None:
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
                "companion_tab": None,
                "companion_surface": None,
                "companion_session": None,
                "companion_shell_pid": None,
                "pinned": False,
            },
        )
        self.assertIn(("zmx", "run", WORK_SESSION, "-d", *HARNESS), runner.commands)
        self.assertFalse(any(command[:3] == ("supacode", "tab", "new") for command in runner.commands))
        self.assertEqual(
            runner.commands[-1],
            ("supacode", "tab", "focus", "-w", WORKTREE, "-t", WORK_TAB),
        )
        runner.assert_consumed()

    def test_named_companion_creates_second_tab_and_returns_resource_ids(self) -> None:
        runner = happy_runner(
            companion_title=COMPANION_TITLE,
            companion_command=COMPANION_COMMAND,
        )

        result = SETUP_BENCH.setup_bench(companion_request(), run=runner)

        self.assertEqual(
            result.as_dict(),
            {
                "worktree": WORKTREE,
                "work_tab": WORK_TAB,
                "work_surface": WORK_SURFACE,
                "work_session": WORK_SESSION,
                "work_shell_pid": WORK_SHELL_PID,
                "companion_tab": COMPANION_TAB,
                "companion_surface": COMPANION_TAB,
                "companion_session": COMPANION_SESSION,
                "companion_shell_pid": COMPANION_SHELL_PID,
                "pinned": False,
            },
        )
        self.assertIn(
            (
                "supacode",
                "tab",
                "new",
                "-w",
                WORKTREE,
                "--title",
                COMPANION_TITLE,
                "-i",
                COMPANION_COMMAND,
            ),
            runner.commands,
        )
        self.assertEqual(
            runner.commands[-1],
            ("supacode", "tab", "focus", "-w", WORKTREE, "-t", WORK_TAB),
        )
        runner.assert_consumed()

    def test_pin_flag_silently_pins_before_focusing_worktree(self) -> None:
        runner = happy_runner(pin=True)
        pin_command = (
            "supacode",
            "worktree",
            "pin",
            "-w",
            WORKTREE,
            "--background",
        )

        result = SETUP_BENCH.setup_bench(request(pin=True), run=runner)

        self.assertTrue(result.pinned)
        self.assertIn(pin_command, runner.commands)
        self.assertLess(
            runner.commands.index(pin_command),
            runner.commands.index(
                ("supacode", "worktree", "focus", "-w", WORKTREE)
            ),
        )
        runner.assert_consumed()

    def test_expands_home_before_opening_repo(self) -> None:
        runner = happy_runner()
        home_request = SETUP_BENCH.BenchRequest(
            path="~/example bench",
            title="Example task",
            color="blue",
            companion_title=None,
            companion_command=None,
            harness=HARNESS,
        )

        with mock.patch.dict("os.environ", {"HOME": "/tmp"}):
            SETUP_BENCH.setup_bench(home_request, run=runner)

        self.assertIn(("supacode", "repo", "open", BENCH_PATH), runner.commands)
        runner.assert_consumed()

    def test_refuses_half_specified_companion_before_opening_repo(self) -> None:
        runner = FakeRunner()

        with self.assertRaisesRegex(SETUP_BENCH.SetupError, "companion"):
            SETUP_BENCH.setup_bench(
                request(companion_title=COMPANION_TITLE, companion_command=None),
                run=runner,
            )

        self.assertEqual(runner.commands, [])

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
            f"{WORK_TAB}\n{COMPANION_TAB}\n"
        )

        with self.assertRaisesRegex(SETUP_BENCH.SetupError, "exactly one default tab"):
            SETUP_BENCH.setup_bench(request(), run=runner)

        self.assertFalse(any(command[:3] == ("supacode", "tab", "rename") for command in runner.commands))

    def test_refuses_unexpected_initial_surface_layout(self) -> None:
        runner = happy_runner()
        runner.responses[
            ("supacode", "surface", "list", "-w", WORKTREE, "-t", WORK_TAB)
        ][0] = f"{WORK_SURFACE}\n{COMPANION_TAB}\n"

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

    def test_rejects_an_invalid_work_only_final_tab_layout(self) -> None:
        runner = happy_runner()
        runner.responses[("supacode", "tab", "list", "-w", WORKTREE)][1] = (
            f"{WORK_TAB}\n{COMPANION_TAB}\n"
        )

        with self.assertRaisesRegex(SETUP_BENCH.SetupError, "final tabs"):
            SETUP_BENCH.setup_bench(request(), run=runner)

        self.assertNotEqual(
            runner.commands[-1],
            ("supacode", "tab", "focus", "-w", WORKTREE, "-t", WORK_TAB),
        )

    def test_rejects_an_invalid_companion_final_tab_layout(self) -> None:
        runner = happy_runner(
            companion_title=COMPANION_TITLE,
            companion_command=COMPANION_COMMAND,
        )
        runner.responses[("supacode", "tab", "list", "-w", WORKTREE)][1] = f"{WORK_TAB}\n"

        with self.assertRaisesRegex(SETUP_BENCH.SetupError, "final tabs"):
            SETUP_BENCH.setup_bench(companion_request(), run=runner)

        self.assertNotEqual(
            runner.commands[-1],
            ("supacode", "tab", "focus", "-w", WORKTREE, "-t", WORK_TAB),
        )

    def test_rejects_a_companion_surface_mismatch(self) -> None:
        runner = happy_runner(
            companion_title=COMPANION_TITLE,
            companion_command=COMPANION_COMMAND,
        )
        runner.responses[
            ("supacode", "surface", "list", "-w", WORKTREE, "-t", COMPANION_TAB)
        ][0] = f"{WORK_SURFACE}\n"

        with self.assertRaisesRegex(SETUP_BENCH.SetupError, "Companion surface"):
            SETUP_BENCH.setup_bench(companion_request(), run=runner)

    def test_rejects_a_backing_session_outside_the_bench_path(self) -> None:
        runner = happy_runner()
        runner.responses[("zmx", "list")][0] = (
            f"name={WORK_SESSION}\tpid={WORK_ROOT_PID}\tstart_dir=/tmp/wrong\n"
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

    def test_bench_result_as_dict_preserves_nullable_companion_fields(self) -> None:
        result = SETUP_BENCH.BenchResult(
            worktree=WORKTREE,
            work_tab=WORK_TAB,
            work_surface=WORK_SURFACE,
            work_session=WORK_SESSION,
            work_shell_pid=WORK_SHELL_PID,
            companion_tab=None,
            companion_surface=None,
            companion_session=None,
            companion_shell_pid=None,
            pinned=False,
        )

        self.assertIsNone(result.as_dict()["companion_tab"])
        self.assertIsNone(result.as_dict()["companion_shell_pid"])

    def test_cli_parses_companion_flags_and_harness_as_argv_remainder(self) -> None:
        parsed = SETUP_BENCH.parse_args(
            [
                "--path",
                BENCH_PATH,
                "--title",
                "Example task",
                "--color",
                "blue",
                "--companion-title",
                COMPANION_TITLE,
                "--companion-command",
                COMPANION_COMMAND,
                "--pin",
                "--",
                *HARNESS,
            ]
        )

        self.assertEqual(parsed.companion_title, COMPANION_TITLE)
        self.assertEqual(parsed.companion_command, COMPANION_COMMAND)
        self.assertEqual(parsed.harness, HARNESS)
        self.assertTrue(parsed.pin)

    def test_cli_rejects_half_specified_companion_flags(self) -> None:
        with self.assertRaises(SystemExit):
            SETUP_BENCH.parse_args(
                [
                    "--path",
                    BENCH_PATH,
                    "--title",
                    "Example task",
                    "--color",
                    "blue",
                    "--companion-title",
                    COMPANION_TITLE,
                    "--",
                    *HARNESS,
                ]
            )

    def test_main_prints_json_result(self) -> None:
        runner = happy_runner(
            companion_title=COMPANION_TITLE,
            companion_command=COMPANION_COMMAND,
        )

        output = SETUP_BENCH.execute(
            [
                "--path",
                BENCH_PATH,
                "--title",
                "Example task",
                "--color",
                "blue",
                "--companion-title",
                COMPANION_TITLE,
                "--companion-command",
                COMPANION_COMMAND,
                "--",
                *HARNESS,
            ],
            run=runner,
        )

        self.assertEqual(json.loads(output)["work_session"], WORK_SESSION)
        self.assertEqual(json.loads(output)["companion_session"], COMPANION_SESSION)
        runner.assert_consumed()


if __name__ == "__main__":
    unittest.main()
