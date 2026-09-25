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

    def test_resolve_config_accepts_plan_harness_tool_compatibility_parameter(self) -> None:
        with mock.patch.dict(os.environ, self.env, clear=True):
            result = RESOLVER.resolve_config(
                repo_root=self.repo,
                brief=self.brief,
                plan_harness_tool=None,
                which=lambda _name: None,
            )

        self.assertEqual(result["harness"]["role"], "work")
        self.assertEqual(result["harnesses"], [result["harness"]])

    def test_missing_files_with_zero_harnesses_stay_unresolved_and_auto_none_diff(self) -> None:
        result = self.resolve()

        self.assertEqual(
            result,
            {
                "harness": {
                    "role": "work",
                    "title": "Work",
                    "tool": None,
                    "argv": [],
                    "available": [],
                    "selection_required": True,
                },
                "harnesses": [
                    {
                        "role": "work",
                        "title": "Work",
                        "tool": None,
                        "argv": [],
                        "available": [],
                        "selection_required": True,
                    }
                ],
                "diff": {
                    "tool": "none",
                    "available": [],
                    "selection_required": False,
                },
            },
        )

    def test_missing_files_auto_select_the_only_available_harness(self) -> None:
        cases = {
            "claude": [
                "claude",
                "--permission-mode",
                "plan",
                f"Read {self.brief}, then plan before edits.",
            ],
            "codex": [
                "codex",
                f"Read {self.brief}, then plan before edits.",
            ],
            "pi": [
                "pi",
                f"@{self.brief}",
                f"Read {self.brief}, then plan before edits.",
            ],
        }
        for tool, argv in cases.items():
            with self.subTest(tool=tool):
                self.executables = {tool}

                result = self.resolve()

                self.assertEqual(
                    result["harness"],
                    {
                        "role": "work",
                        "title": "Work",
                        "tool": tool,
                        "argv": argv,
                        "available": [tool],
                        "selection_required": False,
                    },
                )
                self.assertEqual(result["harnesses"], [result["harness"]])

    def test_missing_files_with_multiple_available_harnesses_require_selection(self) -> None:
        self.executables.update({"claude", "codex", "pi"})

        result = self.resolve()

        self.assertEqual(
            result["harness"],
            {
                "role": "work",
                "title": "Work",
                "tool": None,
                "argv": [],
                "available": ["claude", "codex", "pi"],
                "selection_required": True,
            },
        )
        self.assertEqual(result["harnesses"], [result["harness"]])

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
        self.assertEqual(result["harnesses"], [{**result["harness"], "role": "work", "title": "Work"}])

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

    def test_repository_tool_pi_clears_inherited_claude_permission_mode(self) -> None:
        self.executables.add("pi")
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
            tool = "pi"
            """
        )

        result = self.resolve()

        self.assertEqual(result["harness"]["tool"], "pi")
        self.assertEqual(result["harness"]["argv"], ["pi", f"@{self.brief}", f"Read {self.brief}, then plan before edits."])

    def test_explicit_harness_tool_pi_clears_inherited_permission_mode(self) -> None:
        self.executables.add("pi")
        self.write_repo(
            """
            [harness]
            tool = "claude"
            permission_mode = "auto"
            """
        )

        result = self.resolve("--harness-tool", "pi")

        self.assertEqual(result["harness"]["tool"], "pi")
        self.assertEqual(result["harness"]["argv"], ["pi", f"@{self.brief}", f"Read {self.brief}, then plan before edits."])

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

    def test_codex_renders_prompt_as_positional_argument(self) -> None:
        self.executables.add("codex")
        self.write_repo(
            """
            [harness]
            tool = "codex"
            """
        )

        result = self.resolve()

        self.assertEqual(
            result["harness"],
            {
                "role": "work",
                "title": "Work",
                "tool": "codex",
                "argv": ["codex", f"Read {self.brief}, then plan before edits."],
                "available": ["codex"],
                "selection_required": False,
            },
        )

    def test_role_keyed_codex_without_prompt_starts_without_brief_prompt(self) -> None:
        self.executables.add("codex")
        self.write_repo(
            """
            [[harnesses]]
            role = "work"
            tool = "codex"
            """
        )

        result = self.resolve()

        self.assertEqual(result["harness"]["argv"], ["codex"])

    def test_codex_rejects_permission_mode(self) -> None:
        self.executables.add("codex")
        self.write_repo(
            """
            [harness]
            tool = "codex"
            permission_mode = "plan"
            """
        )

        self.assert_config_error("permission_mode.*codex")

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

    def test_role_keyed_harnesses_resolve_plan_and_work(self) -> None:
        self.executables.update({"claude", "pi"})
        self.write_repo(
            """
            [[harnesses]]
            role = "plan"
            tool = "claude"
            permission_mode = "plan"
            prompt = "Plan from {brief}"

            [[harnesses]]
            role = "work"
            command = ["pi", "--model", "openai-codex/gpt-5.6-astra"]
            """
        )

        result = self.resolve()

        self.assertEqual([item["role"] for item in result["harnesses"]], ["plan", "work"])
        self.assertEqual(result["harnesses"][0]["argv"], ["claude", "--permission-mode", "plan", f"Plan from {self.brief}"])
        self.assertEqual(result["harnesses"][1]["tool"], "custom")
        self.assertEqual(result["harnesses"][1]["argv"], ["pi", "--model", "openai-codex/gpt-5.6-astra"])
        self.assertEqual(result["harness"], result["harnesses"][1])


    def test_role_keyed_ask_harnesses_auto_select_the_only_available_harness(self) -> None:
        self.executables.add("pi")
        self.write_repo(
            """
            [[harnesses]]
            role = "plan"
            tool = "ask"
            prompt = "Plan from {brief}"
            """
        )

        result = self.resolve()

        self.assertEqual([item["role"] for item in result["harnesses"]], ["plan", "work"])
        self.assertEqual(result["harnesses"][0]["tool"], "pi")
        self.assertEqual(result["harnesses"][0]["argv"], ["pi", f"@{self.brief}", f"Plan from {self.brief}"])
        self.assertEqual(result["harness"]["tool"], "pi")
        self.assertEqual(
            result["harness"]["argv"],
            ["pi", f"@{self.brief}", f"Read {self.brief}, then plan before edits."],
        )

    def test_omitted_prompt_in_role_entry_clears_inherited_prompt(self) -> None:
        self.executables.add("pi")
        self.write_user(
            """
            [[harnesses]]
            role = "work"
            command = ["pi"]
            prompt = "User prompt {brief}"
            """
        )
        self.write_repo(
            """
            [[harnesses]]
            role = "work"
            command = ["pi", "--model", "openai-codex/gpt-5.6-astra"]
            """
        )

        result = self.resolve()

        self.assertEqual(result["harness"]["argv"], ["pi", "--model", "openai-codex/gpt-5.6-astra"])

    def test_role_keyed_pi_without_prompt_starts_without_brief_prompt(self) -> None:
        self.executables.add("pi")
        self.write_repo(
            """
            [[harnesses]]
            role = "work"
            tool = "pi"
            """
        )

        result = self.resolve()

        self.assertEqual(result["harness"]["argv"], ["pi"])

    def test_plan_harness_can_be_disabled_by_higher_precedence_layer(self) -> None:
        self.executables.add("pi")
        self.write_user(
            """
            [[harnesses]]
            role = "plan"
            command = ["pi"]
            prompt = "Plan {brief}"
            """
        )
        self.write_repo(
            """
            [[harnesses]]
            role = "plan"
            enabled = false
            """
        )

        result = self.resolve("--harness-tool", "pi")

        self.assertEqual([item["role"] for item in result["harnesses"]], ["work"])

    def test_explicit_plan_harness_tool_opts_into_plan_role(self) -> None:
        self.executables.update({"claude", "pi"})
        result = self.resolve("--plan-harness-tool", "claude", "--harness-tool", "pi")

        self.assertEqual([item["role"] for item in result["harnesses"]], ["plan", "work"])
        self.assertEqual(result["harnesses"][0]["tool"], "claude")
        self.assertEqual(result["harnesses"][1]["tool"], "pi")

    def test_unknown_harness_role_is_rejected(self) -> None:
        self.write_repo(
            """
            [[harnesses]]
            role = "review"
            tool = "claude"
            """
        )

        self.assert_config_error("Unsupported harness role")

    def test_duplicate_harness_roles_in_one_layer_are_rejected(self) -> None:
        self.write_repo(
            """
            [[harnesses]]
            role = "plan"
            tool = "claude"

            [[harnesses]]
            role = "plan"
            tool = "pi"
            """
        )

        self.assert_config_error("Duplicate harness role")

    def test_legacy_harness_and_role_keyed_work_in_one_layer_are_rejected(self) -> None:
        self.write_repo(
            """
            [harness]
            tool = "claude"

            [[harnesses]]
            role = "work"
            tool = "pi"
            """
        )

        self.assert_config_error("cannot both define")

    def test_empty_harness_title_is_rejected(self) -> None:
        self.write_repo(
            """
            [[harnesses]]
            role = "work"
            title = ""
            tool = "pi"
            """
        )

        self.assert_config_error("title.*non-empty")

    def test_disabled_harness_cannot_include_other_fields(self) -> None:
        self.write_repo(
            """
            [[harnesses]]
            role = "plan"
            enabled = false
            prompt = "Plan {brief}"
            """
        )

        self.assert_config_error("enabled = false")

    def test_work_harness_cannot_be_disabled_without_explicit_override(self) -> None:
        self.write_repo(
            """
            [[harnesses]]
            role = "work"
            enabled = false
            """
        )

        self.assert_config_error("work.*disabled")

    def test_explicit_work_harness_tool_overrides_disabled_work_role(self) -> None:
        self.executables.add("pi")
        self.write_repo(
            """
            [[harnesses]]
            role = "work"
            enabled = false
            """
        )

        result = self.resolve("--harness-tool", "pi")

        self.assertEqual(result["harness"]["tool"], "pi")

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
