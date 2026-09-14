from __future__ import annotations

import importlib.util
import json
import os
import pathlib
import sys
import tempfile
import unittest
from collections import defaultdict, deque
from collections.abc import Sequence
from unittest import mock
from urllib.parse import quote

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
COMPANION_COMMAND = "companion-tool --mode observe --label opaque-pass-through"
PLAN_TAB = WORK_TAB
PLAN_SURFACE = WORK_SURFACE
PLAN_SESSION = WORK_SESSION
WORK2_TAB = "DDDDDDDD-DDDD-DDDD-DDDD-DDDDDDDDDDDD"
WORK2_SURFACE = "EEEEEEEE-EEEE-EEEE-EEEE-EEEEEEEEEEEE"
WORK2_SESSION = "supa-eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee"
WORK2_ROOT_PID = 9012
WORK2_SHELL_PID = 9013
PLAN_HARNESS = ("claude", "--permission-mode", "plan", "Plan")
WORK_HARNESS = ("pi", "--model", "openai-codex/gpt-5.6-astra")
OLD_TAB = "11111111-1111-1111-1111-111111111111"
OLD_SURFACE = "22222222-2222-2222-2222-222222222222"
OLD_SESSION = "supa-22222222-2222-2222-2222-222222222222"
OLD_ROOT_PID = 2234
OLD_SHELL_PID = 2235
OLD2_TAB = "33333333-3333-3333-3333-333333333333"
OLD2_SURFACE = "44444444-4444-4444-4444-444444444444"
OLD2_SESSION = "supa-44444444-4444-4444-4444-444444444444"
OLD2_ROOT_PID = 4434
OLD2_SHELL_PID = 4435
LAYOUTS_KEY = BENCH_PATH + "/"


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


def harness_tab(role: str, title: str, argv: tuple[str, ...]):
    return SETUP_BENCH.HarnessTab(role=role, title=title, argv=argv)


def request(
    *,
    companion_title: str | None = None,
    companion_command: str | None = None,
    pin: bool = False,
    harness_tabs: tuple[object, ...] | None = None,
    layouts_file: str | None = None,
):
    return SETUP_BENCH.BenchRequest(
        path=BENCH_PATH,
        title="Example task",
        color="blue",
        companion_title=companion_title,
        companion_command=companion_command,
        harness_tabs=harness_tabs or (harness_tab("work", "Work", HARNESS),),
        pin=pin,
        layouts_file=layouts_file,
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
    harness_tabs: tuple[object, ...] | None = None,
) -> FakeRunner:
    harness_tabs = harness_tabs or (harness_tab("work", "Work", HARNESS),)
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
    created_tabs = [WORK_TAB]
    if len(harness_tabs) > 1:
        created_tabs.append(WORK2_TAB)
    if has_companion:
        created_tabs.append(COMPANION_TAB)
    final_tabs = "".join(f"{tab}\n" for tab in created_tabs)
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
    first = harness_tabs[0]
    runner.add(
        ("supacode", "tab", "rename", "-w", WORKTREE, "-t", WORK_TAB, "--title", first.title),
        "",
    )
    runner.add(("zmx", "run", WORK_SESSION, "-d", *first.argv), "command sent!\n")
    if len(harness_tabs) > 1:
        second = harness_tabs[1]
        runner.add(
            (
                "supacode",
                "tab",
                "new",
                "-w",
                WORKTREE,
                "--title",
                second.title,
            ),
            f"{WORK2_TAB}\n",
        )
        runner.add(
            ("supacode", "surface", "list", "-w", WORKTREE, "-t", WORK2_TAB),
            f"{WORK2_SURFACE}\n",
            f"{WORK2_SURFACE}\n",
        )
        runner.add(("zmx", "list", "--short"), f"other\n{WORK_SESSION}\n{WORK2_SESSION}\n")
        runner.add(("zmx", "run", WORK2_SESSION, "-d", *second.argv), "command sent!\n")
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
    if len(harness_tabs) > 1:
        zmx_details += (
            f"name={WORK2_SESSION}\tpid={WORK2_ROOT_PID}\tclients=1"
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
    if len(harness_tabs) > 1:
        runner.add(("pgrep", "-P", str(WORK2_ROOT_PID)), f"{WORK2_SHELL_PID}\n")
        runner.add(
            ("lsof", "-a", "-d", "cwd", "-p", str(WORK2_SHELL_PID), "-Fn"),
            f"p{WORK2_SHELL_PID}\nfcwd\nn{BENCH_PATH}\n",
        )
    if has_companion:
        runner.add(("pgrep", "-P", str(COMPANION_ROOT_PID)), f"{COMPANION_SHELL_PID}\n")
        runner.add(
            ("lsof", "-a", "-d", "cwd", "-p", str(COMPANION_SHELL_PID), "-Fn"),
            f"p{COMPANION_SHELL_PID}\nfcwd\nn{BENCH_PATH}\n",
        )
    work_tab = next(tab for tab in harness_tabs if tab.role == "work")
    work_tab_id = WORK_TAB if work_tab is harness_tabs[0] else WORK2_TAB
    runner.add(("supacode", "tab", "focus", "-w", WORKTREE, "-t", work_tab_id), "")
    return runner


def layout_entry(*tabs: tuple[str, str | None]) -> dict[str, object]:
    return {"tabs": [{"id": tab, "surfaceID": surface} for tab, surface in tabs]}


def write_layouts(home: str, value: dict[str, object] | str) -> str:
    layouts_dir = pathlib.Path(home) / ".supacode"
    layouts_dir.mkdir(parents=True, exist_ok=True)
    layouts_file = layouts_dir / "layouts.json"
    if isinstance(value, str):
        layouts_file.write_text(value)
    else:
        layouts_file.write_text(json.dumps(value))
    return str(layouts_file)


def ps_output(*pairs: tuple[int, int]) -> str:
    return "".join(f"{pid} {ppid}\n" for pid, ppid in pairs)


def restored_runner(
    runner: FakeRunner,
    restored: tuple[tuple[str, str, str, int, int], ...],
    *,
    fresh_first: bool = False,
) -> FakeRunner:
    tab_list = runner.responses[("supacode", "tab", "list", "-w", WORKTREE)]
    restored_tabs = [tab for tab, _surface, _session, _root_pid, _shell_pid in restored]
    initial_tabs = [WORK_TAB, *restored_tabs] if fresh_first else [*restored_tabs, WORK_TAB]
    tab_list[0] = "".join(f"{tab}\n" for tab in initial_tabs)
    tab_list.insert(1, f"{WORK_TAB}\n")

    restored_details = ""
    for tab, surface, session, root_pid, shell_pid in restored:
        runner.add(("supacode", "surface", "list", "-w", WORKTREE, "-t", tab), f"{surface}\n")
        runner.add(("pgrep", "-P", str(root_pid)), f"{shell_pid}\n")
        runner.add(
            ("lsof", "-a", "-d", "cwd", "-p", str(shell_pid), "-Fn"),
            f"p{shell_pid}\nfcwd\nn{BENCH_PATH}\n",
        )
        runner.add(("supacode", "tab", "close", "-w", WORKTREE, "-t", tab), "")
        restored_details += (
            f"name={session}\tpid={root_pid}\tclients=1"
            f"\tstart_dir={BENCH_PATH}\n"
        )
    runner.responses[("zmx", "list")].appendleft(restored_details)
    runner.add(("ps", "-axo", "pid=,ppid="), ps_output())
    return runner


class SetupBenchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.home_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.home_dir.cleanup)
        self.home_patch = mock.patch.dict(os.environ, {"HOME": self.home_dir.name})
        self.home_patch.start()
        self.addCleanup(self.home_patch.stop)

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
                "harness_tabs": [
                    {
                        "role": "work",
                        "title": "Work",
                        "tab": WORK_TAB,
                        "surface": WORK_SURFACE,
                        "session": WORK_SESSION,
                        "shell_pid": WORK_SHELL_PID,
                    }
                ],
                "companion_tab": None,
                "companion_surface": None,
                "companion_session": None,
                "companion_shell_pid": None,
                "pinned": False,
                "closed_restored_tabs": [],
            },
        )
        self.assertIn(("zmx", "run", WORK_SESSION, "-d", *HARNESS), runner.commands)
        self.assertFalse(any(command[:3] == ("supacode", "tab", "new") for command in runner.commands))
        self.assertEqual(
            runner.commands[-1],
            ("supacode", "tab", "focus", "-w", WORKTREE, "-t", WORK_TAB),
        )
        runner.assert_consumed()

    def test_split_harness_reuses_default_tab_for_plan_and_focuses_work(self) -> None:
        harness_tabs = (
            harness_tab("plan", "Plan", PLAN_HARNESS),
            harness_tab("work", "Work", WORK_HARNESS),
        )
        runner = happy_runner(harness_tabs=harness_tabs)

        result = SETUP_BENCH.setup_bench(request(harness_tabs=harness_tabs), run=runner)

        self.assertEqual(result.work_tab, WORK2_TAB)
        self.assertEqual(result.work_session, WORK2_SESSION)
        self.assertIn(
            ("supacode", "tab", "rename", "-w", WORKTREE, "-t", PLAN_TAB, "--title", "Plan"),
            runner.commands,
        )
        self.assertIn(("zmx", "run", PLAN_SESSION, "-d", *PLAN_HARNESS), runner.commands)
        self.assertIn(
            ("supacode", "tab", "new", "-w", WORKTREE, "--title", "Work"),
            runner.commands,
        )
        self.assertIn(("zmx", "run", WORK2_SESSION, "-d", *WORK_HARNESS), runner.commands)
        self.assertEqual(
            result.as_dict()["harness_tabs"],
            [
                {
                    "role": "plan",
                    "title": "Plan",
                    "tab": PLAN_TAB,
                    "surface": PLAN_SURFACE,
                    "session": PLAN_SESSION,
                    "shell_pid": WORK_SHELL_PID,
                },
                {
                    "role": "work",
                    "title": "Work",
                    "tab": WORK2_TAB,
                    "surface": WORK2_SURFACE,
                    "session": WORK2_SESSION,
                    "shell_pid": WORK2_SHELL_PID,
                },
            ],
        )
        self.assertEqual(
            runner.commands[-1],
            ("supacode", "tab", "focus", "-w", WORKTREE, "-t", WORK2_TAB),
        )
        runner.assert_consumed()

    def test_split_harness_still_supports_a_companion_tab(self) -> None:
        harness_tabs = (
            harness_tab("plan", "Plan", PLAN_HARNESS),
            harness_tab("work", "Work", WORK_HARNESS),
        )
        runner = happy_runner(
            companion_title=COMPANION_TITLE,
            companion_command=COMPANION_COMMAND,
            harness_tabs=harness_tabs,
        )

        result = SETUP_BENCH.setup_bench(
            request(
                companion_title=COMPANION_TITLE,
                companion_command=COMPANION_COMMAND,
                harness_tabs=harness_tabs,
            ),
            run=runner,
        )

        self.assertEqual(result.work_tab, WORK2_TAB)
        self.assertEqual(result.companion_tab, COMPANION_TAB)
        self.assertEqual(result.companion_session, COMPANION_SESSION)
        self.assertEqual(
            runner.commands[-1],
            ("supacode", "tab", "focus", "-w", WORKTREE, "-t", WORK2_TAB),
        )
        runner.assert_consumed()

    def test_named_companion_creates_second_tab_and_returns_resource_ids(self) -> None:
        runner = happy_runner(
            companion_title=COMPANION_TITLE,
            companion_command=COMPANION_COMMAND,
        )

        result = SETUP_BENCH.setup_bench(companion_request(), run=runner)

        self.assertEqual(result.work_tab, WORK_TAB)
        self.assertEqual(result.companion_tab, COMPANION_TAB)
        self.assertEqual(result.companion_surface, COMPANION_TAB)
        self.assertEqual(result.companion_session, COMPANION_SESSION)
        self.assertEqual(result.companion_shell_pid, COMPANION_SHELL_PID)
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
            harness_tabs=(harness_tab("work", "Work", HARNESS),),
            layouts_file=str(pathlib.Path(self.home_dir.name) / ".supacode" / "layouts.json"),
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

    def test_refuses_request_without_work_harness_before_opening_repo(self) -> None:
        runner = FakeRunner()

        with self.assertRaisesRegex(SETUP_BENCH.SetupError, "work"):
            SETUP_BENCH.setup_bench(
                request(harness_tabs=(harness_tab("plan", "Plan", PLAN_HARNESS),)),
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


    def test_closes_idle_restored_tabs_and_reports_them(self) -> None:
        write_layouts(
            self.home_dir.name,
            {LAYOUTS_KEY: layout_entry((OLD_TAB, OLD_SURFACE), (OLD2_TAB, OLD2_SURFACE))},
        )
        restored = (
            (OLD_TAB, OLD_SURFACE, OLD_SESSION, OLD_ROOT_PID, OLD_SHELL_PID),
            (OLD2_TAB, OLD2_SURFACE, OLD2_SESSION, OLD2_ROOT_PID, OLD2_SHELL_PID),
        )
        runner = restored_runner(happy_runner(), restored)

        result = SETUP_BENCH.setup_bench(request(), run=runner)

        self.assertEqual(result.closed_restored_tabs, (OLD_TAB, OLD2_TAB))
        close_commands = [
            ("supacode", "tab", "close", "-w", WORKTREE, "-t", OLD_TAB),
            ("supacode", "tab", "close", "-w", WORKTREE, "-t", OLD2_TAB),
        ]
        restored_lsof_and_ps = [
            ("lsof", "-a", "-d", "cwd", "-p", str(OLD_SHELL_PID), "-Fn"),
            ("lsof", "-a", "-d", "cwd", "-p", str(OLD2_SHELL_PID), "-Fn"),
            ("ps", "-axo", "pid=,ppid="),
        ]
        self.assertLess(
            max(runner.commands.index(command) for command in restored_lsof_and_ps),
            min(runner.commands.index(command) for command in close_commands),
        )
        self.assertLess(
            max(runner.commands.index(command) for command in close_commands),
            runner.commands.index(
                ("supacode", "tab", "rename", "-w", WORKTREE, "-t", WORK_TAB, "--title", "Work")
            ),
        )
        runner.assert_consumed()

    def test_identifies_fresh_tab_by_id_not_position(self) -> None:
        write_layouts(self.home_dir.name, {LAYOUTS_KEY: layout_entry((OLD_TAB, OLD_SURFACE))})
        runner = restored_runner(
            happy_runner(),
            ((OLD_TAB, OLD_SURFACE, OLD_SESSION, OLD_ROOT_PID, OLD_SHELL_PID),),
            fresh_first=True,
        )

        result = SETUP_BENCH.setup_bench(request(), run=runner)

        self.assertEqual(result.work_tab, WORK_TAB)
        self.assertEqual(result.closed_restored_tabs, (OLD_TAB,))
        runner.assert_consumed()

    def test_saved_layout_present_but_nothing_restored_uses_default_path(self) -> None:
        write_layouts(self.home_dir.name, {LAYOUTS_KEY: layout_entry((OLD_TAB, OLD_SURFACE))})
        runner = happy_runner()

        result = SETUP_BENCH.setup_bench(request(), run=runner)

        self.assertEqual(result.closed_restored_tabs, ())
        self.assertFalse(any(command[:3] == ("supacode", "tab", "close") for command in runner.commands))
        runner.assert_consumed()

    def test_ignores_saved_layouts_for_other_paths(self) -> None:
        write_layouts(self.home_dir.name, {"/tmp/other bench/": layout_entry((OLD_TAB, OLD_SURFACE))})
        runner = happy_runner()

        result = SETUP_BENCH.setup_bench(request(), run=runner)

        self.assertEqual(result.closed_restored_tabs, ())
        self.assertFalse(any(command[:3] == ("supacode", "tab", "close") for command in runner.commands))
        runner.assert_consumed()

    def test_undecodable_layouts_file_is_treated_as_no_saved_layout(self) -> None:
        write_layouts(self.home_dir.name, "not json")
        runner = happy_runner()

        result = SETUP_BENCH.setup_bench(request(), run=runner)

        self.assertEqual(result.closed_restored_tabs, ())
        runner.assert_consumed()

    def test_reads_saved_layout_before_opening_repo(self) -> None:
        write_layouts(self.home_dir.name, {LAYOUTS_KEY: layout_entry((OLD_TAB, OLD_SURFACE))})
        runner = restored_runner(
            happy_runner(),
            ((OLD_TAB, OLD_SURFACE, OLD_SESSION, OLD_ROOT_PID, OLD_SHELL_PID),),
        )

        def run(command: Sequence[str]) -> str:
            if tuple(command) == ("supacode", "repo", "open", BENCH_PATH):
                write_layouts(self.home_dir.name, {})
            return runner(command)

        result = SETUP_BENCH.setup_bench(request(), run=run)

        self.assertEqual(result.closed_restored_tabs, (OLD_TAB,))
        runner.assert_consumed()

    def test_refuses_saved_layout_when_fresh_tab_count_is_not_one(self) -> None:
        cases = {
            "zero fresh": f"{OLD_TAB}\n",
            "two fresh": f"{OLD_TAB}\n{WORK_TAB}\n{WORK2_TAB}\n",
        }
        for name, tabs in cases.items():
            with self.subTest(name=name):
                write_layouts(self.home_dir.name, {LAYOUTS_KEY: layout_entry((OLD_TAB, OLD_SURFACE))})
                runner = happy_runner()
                runner.responses[("supacode", "tab", "list", "-w", WORKTREE)][0] = tabs

                with self.assertRaisesRegex(SETUP_BENCH.SetupError, "fresh default tab"):
                    SETUP_BENCH.setup_bench(request(), run=runner)

                self.assertFalse(any(command[:3] == ("supacode", "tab", "close") for command in runner.commands))
                self.assertFalse(any(command[:3] == ("supacode", "tab", "rename") for command in runner.commands))

    def test_refuses_restored_tab_with_two_surfaces(self) -> None:
        write_layouts(self.home_dir.name, {LAYOUTS_KEY: layout_entry((OLD_TAB, OLD_SURFACE))})
        runner = restored_runner(
            happy_runner(),
            ((OLD_TAB, OLD_SURFACE, OLD_SESSION, OLD_ROOT_PID, OLD_SHELL_PID),),
        )
        runner.responses[("supacode", "surface", "list", "-w", WORKTREE, "-t", OLD_TAB)][0] = (
            f"{OLD_SURFACE}\n{OLD2_SURFACE}\n"
        )

        with self.assertRaisesRegex(SETUP_BENCH.SetupError, "surface in restored tab"):
            SETUP_BENCH.setup_bench(request(), run=runner)

        self.assertFalse(any(command[:3] == ("supacode", "tab", "close") for command in runner.commands))

    def test_refuses_restored_tab_whose_shell_cwd_left_bench(self) -> None:
        write_layouts(self.home_dir.name, {LAYOUTS_KEY: layout_entry((OLD_TAB, OLD_SURFACE))})
        runner = restored_runner(
            happy_runner(),
            ((OLD_TAB, OLD_SURFACE, OLD_SESSION, OLD_ROOT_PID, OLD_SHELL_PID),),
        )
        runner.responses[("lsof", "-a", "-d", "cwd", "-p", str(OLD_SHELL_PID), "-Fn")][0] = (
            f"p{OLD_SHELL_PID}\nfcwd\nn/tmp/wrong\n"
        )

        with self.assertRaisesRegex(SETUP_BENCH.SetupError, "shell starts outside"):
            SETUP_BENCH.setup_bench(request(), run=runner)

        self.assertFalse(any(command[:3] == ("supacode", "tab", "close") for command in runner.commands))

    def test_refuses_restored_tab_with_busy_shell(self) -> None:
        write_layouts(self.home_dir.name, {LAYOUTS_KEY: layout_entry((OLD_TAB, OLD_SURFACE))})
        runner = restored_runner(
            happy_runner(),
            ((OLD_TAB, OLD_SURFACE, OLD_SESSION, OLD_ROOT_PID, OLD_SHELL_PID),),
        )
        runner.responses[("ps", "-axo", "pid=,ppid=")][0] = ps_output((9999, OLD_SHELL_PID))

        with self.assertRaisesRegex(SETUP_BENCH.SetupError, "shell is busy"):
            SETUP_BENCH.setup_bench(request(), run=runner)

        self.assertFalse(any(command[:3] == ("supacode", "tab", "close") for command in runner.commands))

    def test_refuses_restored_tab_with_multiple_clients(self) -> None:
        write_layouts(self.home_dir.name, {LAYOUTS_KEY: layout_entry((OLD_TAB, OLD_SURFACE))})
        runner = restored_runner(
            happy_runner(),
            ((OLD_TAB, OLD_SURFACE, OLD_SESSION, OLD_ROOT_PID, OLD_SHELL_PID),),
        )
        runner.responses[("zmx", "list")][0] = (
            f"name={OLD_SESSION}\tpid={OLD_ROOT_PID}\tclients=2\tstart_dir={BENCH_PATH}\n"
        )

        with self.assertRaisesRegex(SETUP_BENCH.SetupError, "clients attached"):
            SETUP_BENCH.setup_bench(request(), run=runner)

        self.assertFalse(any(command[:3] == ("supacode", "tab", "close") for command in runner.commands))

    def test_checks_every_restored_tab_before_closing_any(self) -> None:
        write_layouts(
            self.home_dir.name,
            {LAYOUTS_KEY: layout_entry((OLD_TAB, OLD_SURFACE), (OLD2_TAB, OLD2_SURFACE))},
        )
        runner = restored_runner(
            happy_runner(),
            (
                (OLD_TAB, OLD_SURFACE, OLD_SESSION, OLD_ROOT_PID, OLD_SHELL_PID),
                (OLD2_TAB, OLD2_SURFACE, OLD2_SESSION, OLD2_ROOT_PID, OLD2_SHELL_PID),
            ),
        )
        runner.responses[("supacode", "surface", "list", "-w", WORKTREE, "-t", OLD2_TAB)][0] = (
            f"{OLD2_SURFACE}\n{WORK_SURFACE}\n"
        )

        with self.assertRaisesRegex(SETUP_BENCH.SetupError, "surface in restored tab"):
            SETUP_BENCH.setup_bench(request(), run=runner)

        self.assertFalse(any(command[:3] == ("supacode", "tab", "close") for command in runner.commands))

    def test_refuses_when_restored_tabs_remain_after_close(self) -> None:
        write_layouts(self.home_dir.name, {LAYOUTS_KEY: layout_entry((OLD_TAB, OLD_SURFACE))})
        runner = restored_runner(
            happy_runner(),
            ((OLD_TAB, OLD_SURFACE, OLD_SESSION, OLD_ROOT_PID, OLD_SHELL_PID),),
        )
        runner.responses[("supacode", "tab", "list", "-w", WORKTREE)][1] = f"{WORK_TAB}\n{OLD_TAB}\n"

        with self.assertRaisesRegex(SETUP_BENCH.SetupError, "Unexpected tabs after closing"):
            SETUP_BENCH.setup_bench(request(), run=runner)

        self.assertIn(("supacode", "tab", "close", "-w", WORKTREE, "-t", OLD_TAB), runner.commands)
        self.assertFalse(any(command[:3] == ("supacode", "tab", "rename") for command in runner.commands))

    def test_load_saved_layout_skips_invalid_tabs_and_handles_empty_inputs(self) -> None:
        layouts_file = write_layouts(
            self.home_dir.name,
            {
                LAYOUTS_KEY: {
                    "tabs": [
                        {"id": OLD_TAB, "surfaceID": OLD_SURFACE},
                        {"id": None, "surfaceID": OLD2_SURFACE},
                        "not a dict",
                        {"surfaceID": WORK_SURFACE},
                        {"id": OLD2_TAB},
                    ]
                },
                "/tmp/empty/": {"tabs": [{"id": None}]},
                "/tmp/non-list/": {"tabs": "not a list"},
                "/tmp/not-dict/": [OLD_TAB],
            },
        )

        saved = SETUP_BENCH.load_saved_layout(BENCH_PATH, layouts_file)

        self.assertEqual(saved.tab_ids, frozenset({OLD_TAB, OLD2_TAB}))
        self.assertIsNone(SETUP_BENCH.load_saved_layout("/tmp/empty", layouts_file))
        self.assertIsNone(SETUP_BENCH.load_saved_layout("/tmp/non-list", layouts_file))
        self.assertIsNone(SETUP_BENCH.load_saved_layout("/tmp/not-dict", layouts_file))
        self.assertIsNone(SETUP_BENCH.load_saved_layout("/tmp/missing", layouts_file))
        self.assertIsNone(SETUP_BENCH.load_saved_layout(BENCH_PATH, "/tmp/no-such-layouts.json"))

    def test_layouts_key_round_trips_to_worktree_id(self) -> None:
        self.assertEqual(SETUP_BENCH.layouts_key(BENCH_PATH), LAYOUTS_KEY)
        self.assertEqual(quote(SETUP_BENCH.layouts_key(BENCH_PATH), safe=""), WORKTREE)
        self.assertEqual(SETUP_BENCH.worktree_id(BENCH_PATH), WORKTREE)

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

    def test_rejects_missing_later_harness_zmx_session(self) -> None:
        harness_tabs = (
            harness_tab("plan", "Plan", PLAN_HARNESS),
            harness_tab("work", "Work", WORK_HARNESS),
        )
        runner = happy_runner(harness_tabs=harness_tabs)
        runner.responses[("zmx", "list", "--short")][1] = f"other\n{WORK_SESSION}\n"

        with self.assertRaisesRegex(SETUP_BENCH.SetupError, "zmx session"):
            SETUP_BENCH.setup_bench(request(harness_tabs=harness_tabs), run=runner)

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

    def test_rejects_duplicate_plan_harness_tabs_before_opening_repo(self) -> None:
        runner = FakeRunner()
        harness_tabs = (
            harness_tab("plan", "Plan", PLAN_HARNESS),
            harness_tab("plan", "Plan again", PLAN_HARNESS),
            harness_tab("work", "Work", WORK_HARNESS),
        )

        with self.assertRaisesRegex(SETUP_BENCH.SetupError, "at most one plan"):
            SETUP_BENCH.setup_bench(request(harness_tabs=harness_tabs), run=runner)

        self.assertEqual(runner.commands, [])


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

    def test_accepts_zmx_cwd_session_details(self) -> None:
        runner = happy_runner()
        runner.responses[("zmx", "list")][0] = (
            f"name={WORK_SESSION}\tpid={WORK_ROOT_PID}\tclients=1"
            f"\tcreated=1789348149\tcwd={BENCH_PATH}\tcmd=/usr/bin/zsh\n"
        )

        result = SETUP_BENCH.setup_bench(request(), run=runner)

        self.assertEqual(result.work_shell_pid, WORK_SHELL_PID)
        runner.assert_consumed()


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
            harness_tabs=(
                SETUP_BENCH.HarnessTabResult(
                    role="work",
                    title="Work",
                    tab=WORK_TAB,
                    surface=WORK_SURFACE,
                    session=WORK_SESSION,
                    shell_pid=WORK_SHELL_PID,
                ),
            ),
            companion_tab=None,
            companion_surface=None,
            companion_session=None,
            companion_shell_pid=None,
            pinned=False,
            closed_restored_tabs=(),
        )

        self.assertIsNone(result.as_dict()["companion_tab"])
        self.assertIsNone(result.as_dict()["companion_shell_pid"])

        self.assertEqual(result.as_dict()["closed_restored_tabs"], [])

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
        self.assertEqual(parsed.harness_tabs, (harness_tab("work", "Work", HARNESS),))
        self.assertTrue(parsed.pin)


    def test_cli_parses_layouts_file(self) -> None:
        parsed = SETUP_BENCH.parse_args(
            [
                "--path",
                BENCH_PATH,
                "--title",
                "Example task",
                "--color",
                "blue",
                "--layouts-file",
                "/tmp/layouts.json",
                "--",
                *HARNESS,
            ]
        )

        self.assertEqual(parsed.layouts_file, "/tmp/layouts.json")

    def test_cli_parses_harness_tabs_json(self) -> None:
        parsed = SETUP_BENCH.parse_args(
            [
                "--path",
                BENCH_PATH,
                "--title",
                "Example task",
                "--color",
                "blue",
                "--harness-tabs-json",
                json.dumps(
                    [
                        {"role": "plan", "title": "Plan", "argv": list(PLAN_HARNESS)},
                        {"role": "work", "title": "Work", "argv": list(WORK_HARNESS)},
                    ]
                ),
            ]
        )

        self.assertEqual(
            parsed.harness_tabs,
            (
                harness_tab("plan", "Plan", PLAN_HARNESS),
                harness_tab("work", "Work", WORK_HARNESS),
            ),
        )

    def test_cli_rejects_harness_tabs_json_with_duplicate_plan_roles(self) -> None:
        with self.assertRaises(SystemExit):
            SETUP_BENCH.parse_args(
                [
                    "--path",
                    BENCH_PATH,
                    "--title",
                    "Example task",
                    "--color",
                    "blue",
                    "--harness-tabs-json",
                    json.dumps(
                        [
                            {"role": "plan", "title": "Plan", "argv": list(PLAN_HARNESS)},
                            {"role": "plan", "title": "Plan again", "argv": list(PLAN_HARNESS)},
                            {"role": "work", "title": "Work", "argv": list(WORK_HARNESS)},
                        ]
                    ),
                ]
            )


    def test_cli_rejects_harness_tabs_json_without_work_role(self) -> None:
        with self.assertRaises(SystemExit):
            SETUP_BENCH.parse_args(
                [
                    "--path",
                    BENCH_PATH,
                    "--title",
                    "Example task",
                    "--color",
                    "blue",
                    "--harness-tabs-json",
                    json.dumps([{"role": "plan", "title": "Plan", "argv": list(PLAN_HARNESS)}]),
                ]
            )

    def test_cli_rejects_harness_tabs_json_with_argv_remainder(self) -> None:
        with self.assertRaises(SystemExit):
            SETUP_BENCH.parse_args(
                [
                    "--path",
                    BENCH_PATH,
                    "--title",
                    "Example task",
                    "--color",
                    "blue",
                    "--harness-tabs-json",
                    json.dumps([{"role": "work", "title": "Work", "argv": list(WORK_HARNESS)}]),
                    "--",
                    *HARNESS,
                ]
            )

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

        self.assertEqual(json.loads(output)["closed_restored_tabs"], [])
        runner.assert_consumed()


if __name__ == "__main__":
    unittest.main()
