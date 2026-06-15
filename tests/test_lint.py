#!/usr/bin/env python3
"""Tests for lint.py (VHS-18 portability lint).

Stdlib unittest. Run directly: `python tests/test_lint.py`.
Resolves the repo root and all paths from __file__ (never cwd) so it works
regardless of the working directory ship-spec runs it from.
"""

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import lint  # noqa: E402

FIX = Path(__file__).resolve().parent / "fixtures"


def errors(findings):
    return [f for f in findings if f[0] == lint.ERROR]


def warns(findings):
    return [f for f in findings if f[0] == lint.WARN]


def rule_names(findings):
    return {f[1] for f in findings}


class TestLint(unittest.TestCase):
    def test_bad_skill_fires(self):
        # Regression for VHS-18: operative mcp__ call (ERROR) + missing requires (WARN)
        f = lint.lint_path(FIX / "bad-skill" / "SKILL.md")
        self.assertIn("operative-tool-call", {x[1] for x in errors(f)},
                      f"expected an operative-tool-call ERROR, got {f}")
        self.assertIn("missing-requires", {x[1] for x in warns(f)},
                      f"expected a missing-requires WARN, got {f}")

    def test_good_skill_clean(self):
        # Regression for VHS-18: valid requires: block + tagged example -> no ERROR, no missing-requires
        f = lint.lint_path(FIX / "good-skill" / "SKILL.md")
        self.assertEqual(errors(f), [], f"good-skill should have zero ERRORs, got {errors(f)}")
        self.assertNotIn("missing-requires", rule_names(f))

    def test_shipped_skills_clean(self):
        # Regression for VHS-18: lint runs clean (zero ERRORs) against the shipped skills.
        skills = sorted((REPO_ROOT / "skills").glob("*/SKILL.md"))
        self.assertEqual(
            len(skills), 4,
            f"expected the 4 currently-shipped skills; found {len(skills)} — "
            f"if you added a skill, bump this count after confirming it lints clean "
            f"(deliberate inventory tripwire, not a clean-run check)",
        )
        for s in skills:
            errs = errors(lint.lint_path(s))
            self.assertEqual(errs, [], f"unexpected ERROR(s) in {s}: {errs}")

    def test_robustness_error_fixtures(self):
        # Regression for VHS-18: malformed requires -> deterministic ERROR, no exception
        for name in ("inline-requires-mapping.md", "tab-indent.md"):
            errs = errors(lint.lint_path(FIX / name))
            self.assertTrue(errs, f"{name} should produce an ERROR")

    def test_robustness_no_error_fixtures(self):
        # Regression for VHS-18: degenerate inputs never raise and never ERROR
        no_error_rel = (
            "empty.md", "no-frontmatter.md", "unterminated-frontmatter.md",
            "notes-bare-name/SKILL.md", "split-marker/SKILL.md",
            "indented-fence/SKILL.md", "comment-in-requires.md",
            "crlf-skill/SKILL.md", "bom-skill/SKILL.md",
        )
        for rel in no_error_rel:
            f = lint.lint_path(FIX / rel)
            self.assertEqual(errors(f), [], f"{rel} should have zero ERRORs, got {errors(f)}")

    def test_lint_paths_empty(self):
        # Regression for VHS-18: lint_paths([]) is pure aggregation -> []
        self.assertEqual(lint.lint_paths([]), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
