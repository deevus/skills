from __future__ import annotations

import importlib.util
import pathlib
import unittest

SCRIPT = pathlib.Path(__file__).parents[1] / "scripts" / "ste_lint.py"
SPEC = importlib.util.spec_from_file_location("ste_lint", SCRIPT)
assert SPEC and SPEC.loader
STE_LINT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(STE_LINT)


class LintTests(unittest.TestCase):
    def test_clean_plain_text_has_no_violations(self) -> None:
        result = STE_LINT.lint(
            "The parser reads the file. It reports each invalid field."
        )

        self.assertEqual(result["total"], 0)
        self.assertEqual(result["words"], 10)

    def test_ai_slop_patterns_are_reported(self) -> None:
        result = STE_LINT.lint(
            "It is important to note that our seamless platform is being used "
            "to leverage a variety of powerful tools; furthermore, this "
            "revolutionary approach is designed to facilitate robust outcomes."
        )
        violations = result["violations"]

        self.assertGreater(violations["marketing_adjective"], 0)
        self.assertGreater(violations["banned_word"], 0)
        self.assertGreater(violations["semicolon"], 0)
        self.assertGreater(violations["passive_voice"], 0)
        self.assertGreater(result["total_per100w"], 0)

    def test_code_blocks_do_not_affect_the_score(self) -> None:
        result = STE_LINT.lint(
            "Run this command.\n\n```python\n"
            "perform_an_analysis = 'seamless; robust'\n"
            "```\n"
        )

        self.assertEqual(result["total"], 0)


if __name__ == "__main__":
    unittest.main()
