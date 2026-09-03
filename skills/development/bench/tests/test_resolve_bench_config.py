from __future__ import annotations

import importlib.util
import json
import os
import pathlib
import sys
import tempfile
import textwrap
import unittest
from unittest import mock

SCRIPT = pathlib.Path(__file__).parents[1] / "scripts" / "resolve_bench_config.py"
SPEC = importlib.util.spec_from_file_location("resolve_bench_config", SCRIPT)
assert SPEC and SPEC.loader
RESOLVER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = RESOLVER
SPEC.loader.exec_module(RESOLVER)


class ResolveBenchConfigTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)
        self.home = self.root / "home"
        self.xdg = self.root / "xdg"
        self.repo = self.root / "repo"
        self.brief = self.root / "brief.md"
        self.home.mkdir()
        self.xdg.mkdir()
        self.repo.mkdir()
        self.brief.write_text("brief", encoding="utf-8")
        self.executables: set[str] = set()
        self.env = {
            "HOME": str(self.home),
            "XDG_CONFIG_HOME": str(self.xdg),
        }

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def write_user(self, body: str, *, xdg: bool = True) -> pathlib.Path:
        base = self.xdg if xdg else self.home / ".config"
        path = base / "bench" / "config.toml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(textwrap.dedent(body).strip() + "\n", encoding="utf-8")
        return path

    def write_repo(self, body: str) -> pathlib.Path:
        path = self.repo / ".bench" / "config.toml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(textwrap.dedent(body).strip() + "\n", encoding="utf-8")
        return path

    def resolve(self, *extra_args: str, env: dict[str, str] | None = None) -> dict[str, object]:
        def fake_which(name: str) -> str | None:
            if name in self.executables:
                return f"/mock/bin/{name}"
            return None

        with mock.patch.dict(os.environ, self.env if env is None else env, clear=True):
            with mock.patch.object(RESOLVER.shutil, "which", side_effect=fake_which):
                output = RESOLVER.execute(
                    [
                        "--repo-root",
                        str(self.repo),
                        "--brief",
                        str(self.brief),
                        *extra_args,
                    ]
                )
        return json.loads(output)

    def assert_config_error(self, message: str, *extra_args: str) -> None:
        with self.assertRaisesRegex(RESOLVER.ConfigError, message):
            self.resolve(*extra_args)

    def test_missing_files_default_to_ask_harness_and_auto_none_diff(self) -> None:
        result = self.resolve()

        self.assertEqual(
            result,
            {
                "harness": {
                    "tool": None,
                    "argv": [],
                    "available": [],
                    "selection_required": True,
                },
                "diff": {
                    "tool": "none",
                    "available": [],
                    "selection_required": False,
                },
            },
        )

    def test_reads_xdg_config_before_home_config_when_xdg_is_set(self) -> None:
        self.executables.add("claude")
        self.write_user(
            """
            [harness]
            tool = "claude"
            prompt = "XDG {brief}"
            """,
            xdg=True,
        )
        self.write_user(
            """
            [harness]
            tool = "pi"
            """,
            xdg=False,
        )

        result = self.resolve()

        self.assertEqual(result["harness"]["tool"], "claude")
        self.assertEqual(result["harness"]["argv"], ["claude", "--permission-mode", "plan", f"XDG {self.brief}"])

    def test_falls_back_to_home_config_when_xdg_is_unset(self) -> None:
        self.executables.add("pi")
        self.write_user(
            """
            [harness]
            tool = "pi"
            prompt = "Home {brief}"
            """,
            xdg=False,
        )

        result = self.resolve(env={"HOME": str(self.home)})

        self.assertEqual(result["harness"]["tool"], "pi")
        self.assertEqual(result["harness"]["argv"], ["pi", f"@{self.brief}", f"Home {self.brief}"])

    def test_repository_config_overrides_user_config_but_keeps_independent_prompt(self) -> None:
        self.executables.update({"claude", "hunk"})
        self.write_user(
            """
            [harness]
            tool = "claude"
            prompt = "User {brief}"

            [diff]
            tool = "comview"
            """
        )
        self.write_repo(
            """
            [harness]
            permission_mode = "auto"

            [diff]
            tool = "hunk"
            """
        )

        result = self.resolve()

        self.assertEqual(result["harness"]["argv"], ["claude", "--permission-mode", "auto", f"User {self.brief}"])
        self.assertEqual(result["diff"]["tool"], "hunk")

    def test_explicit_overrides_win_over_repository_config(self) -> None:
        self.executables.update({"claude", "comview"})
        self.write_repo(
            """
            [harness]
            tool = "pi"

            [diff]
            tool = "hunk"
            """
        )

        result = self.resolve("--harness-tool", "claude", "--diff-tool", "comview")

        self.assertEqual(result["harness"]["tool"], "claude")
        self.assertEqual(result["diff"]["tool"], "comview")

    def test_higher_precedence_tool_clears_inherited_custom_command(self) -> None:
        self.executables.add("claude")
        self.write_user(
            """
            [harness]
            command = ["custom-agent", "--brief", "{brief}"]
            """
        )
        self.write_repo(
            """
            [harness]
            tool = "claude"
            permission_mode = "manual"
            """
        )

        result = self.resolve()

        self.assertEqual(result["harness"]["tool"], "claude")
        self.assertEqual(result["harness"]["argv"], ["claude", "--permission-mode", "manual", f"Read {self.brief}, then plan before edits."])

    def test_higher_precedence_command_clears_tool_and_permission_mode(self) -> None:
        self.executables.add("custom-agent")
        self.write_user(
            """
            [harness]
            tool = "claude"
            permission_mode = "bypassPermissions"
            """
        )
        self.write_repo(
            """
            [harness]
            command = ["custom-agent", "--instructions", "{brief}"]
            """
        )

        result = self.resolve()

        self.assertEqual(result["harness"]["tool"], "custom")
        self.assertEqual(result["harness"]["argv"], ["custom-agent", "--instructions", str(self.brief), f"Read {self.brief}, then plan before edits."])

    def test_claude_defaults_permission_mode_to_plan(self) -> None:
        self.executables.add("claude")
        self.write_repo(
            """
            [harness]
            tool = "claude"
            """
        )

        result = self.resolve()

        self.assertEqual(result["harness"]["argv"], ["claude", "--permission-mode", "plan", f"Read {self.brief}, then plan before edits."])

    def test_claude_supports_every_documented_permission_mode(self) -> None:
        self.executables.add("claude")
        for mode in ["acceptEdits", "auto", "bypassPermissions", "manual", "dontAsk", "plan"]:
            with self.subTest(mode=mode):
                self.write_repo(
                    f"""
                    [harness]
                    tool = "claude"
                    permission_mode = "{mode}"
                    """
                )

                result = self.resolve()

                self.assertEqual(result["harness"]["argv"][2], mode)

    def test_pi_rejects_permission_mode(self) -> None:
        self.executables.add("pi")
        self.write_repo(
            """
            [harness]
            tool = "pi"
            permission_mode = "plan"
            """
        )

        self.assert_config_error("permission_mode.*pi")

    def test_custom_argv_is_preserved_and_prompt_is_appended(self) -> None:
        self.executables.add("custom-agent")
        self.write_repo(
            """
            [harness]
            command = ["custom-agent", "--flag", "value with spaces", "{brief}"]
            prompt = "Continue from {brief}"
            """
        )

        result = self.resolve()

        self.assertEqual(
            result["harness"]["argv"],
            ["custom-agent", "--flag", "value with spaces", str(self.brief), f"Continue from {self.brief}"],
        )

    def test_unknown_placeholders_are_rejected(self) -> None:
        self.executables.add("custom-agent")
        self.write_repo(
            """
            [harness]
            command = ["custom-agent", "{ticket}"]
            """
        )

        self.assert_config_error("Unsupported placeholder")

    def test_empty_values_are_rejected(self) -> None:
        self.write_repo(
            """
            [harness]
            prompt = ""
            """
        )

        self.assert_config_error("non-empty")

    def test_unknown_keys_are_rejected(self) -> None:
        self.write_repo(
            """
            [harness]
            tool = "claude"
            extra = true
            """
        )

        self.assert_config_error("Unknown key")

    def test_missing_harness_executable_fails(self) -> None:
        self.write_repo(
            """
            [harness]
            tool = "claude"
            """
        )

        self.assert_config_error("Executable not found")

    def test_conflicting_tool_and_command_fail(self) -> None:
        self.write_repo(
            """
            [harness]
            tool = "claude"
            command = ["custom-agent"]
            """
        )

        self.assert_config_error("mutually exclusive")

    def test_diff_explicit_none_never_requires_selection(self) -> None:
        self.write_repo(
            """
            [diff]
            tool = "none"
            """
        )

        result = self.resolve()

        self.assertEqual(result["diff"], {"tool": "none", "available": [], "selection_required": False})

    def test_diff_explicit_comview_and_hunk_require_installed_executables(self) -> None:
        for tool in ["comview", "hunk"]:
            with self.subTest(tool=tool):
                self.write_repo(
                    f"""
                    [diff]
                    tool = "{tool}"
                    """
                )
                self.assert_config_error("Executable not found")
                self.executables.add(tool)
                result = self.resolve()
                self.assertEqual(result["diff"]["tool"], tool)
                self.executables.remove(tool)

    def test_diff_auto_selects_none_when_zero_viewers_are_installed(self) -> None:
        self.write_repo(
            """
            [diff]
            tool = "auto"
            """
        )

        result = self.resolve()

        self.assertEqual(result["diff"], {"tool": "none", "available": [], "selection_required": False})

    def test_diff_auto_selects_the_only_installed_viewer(self) -> None:
        for tool in ["comview", "hunk"]:
            with self.subTest(tool=tool):
                self.executables = {tool}
                result = self.resolve("--diff-tool", "auto")
                self.assertEqual(result["diff"], {"tool": tool, "available": [tool], "selection_required": False})

    def test_diff_auto_with_two_viewers_requires_selection(self) -> None:
        self.executables.update({"comview", "hunk"})

        result = self.resolve("--diff-tool", "auto")

        self.assertEqual(
            result["diff"],
            {"tool": None, "available": ["comview", "hunk"], "selection_required": True},
        )


if __name__ == "__main__":
    unittest.main()
