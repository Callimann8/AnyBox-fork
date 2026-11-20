import json
import unittest
from pathlib import Path

from helpers import TOOLS, temp_root, write

import debt_fold
import run_report_summary

DEBT = """# demo technical debt

### Silent stubs

- [Quiet](../../../core/libs/xdll/demo/Export.cpp) (demo) - returns S_OK without saving

### Functional

- [Queue](../../../core/libs/xdll/demo/Queue.cpp) (demo) - order unverified
  Closes when: measured on a console
"""

FRAGMENT = """# demo

## add Silent stubs

- [Louder](../../../core/libs/xdll/demo/Export.cpp) (demo) - ignores its flags

## change [Queue.cpp]

- [Queue](../../../core/libs/xdll/demo/Queue.cpp) (demo) - order measured, cancellation unverified

## add Unknown function info

- [Thing](../../../core/libs/xdll/demo/Inventory.cpp) (demo) - no parameters
"""


class DebtFoldTest(unittest.TestCase):
    def setUp(self):
        self.directory = temp_root()
        root = Path(self.directory.name)
        self.saved = (debt_fold.DEBT, debt_fold.INDEX, debt_fold.CHANGES, debt_fold.ROOT)
        debt_fold.ROOT = root
        debt_fold.DEBT = root / "debt"
        debt_fold.INDEX = root / "TechnicalDebt.md"
        debt_fold.CHANGES = root / "debt" / "changes"
        write(root, "debt/demo.md", DEBT)
        self.fragment = write(root, "debt/changes/feat-demo.md", FRAGMENT)

    def tearDown(self):
        debt_fold.DEBT, debt_fold.INDEX, debt_fold.CHANGES, debt_fold.ROOT = self.saved
        self.directory.cleanup()

    def test_add_change_remove(self):
        text = debt_fold.fold([self.fragment])["demo"]
        silent = text.index("### Silent stubs")
        self.assertLess(text.index("Quiet"), text.index("Louder"))
        self.assertGreater(text.index("Louder"), silent)
        self.assertLess(text.index("Louder"), text.index("### Functional"))
        self.assertIn("order measured, cancellation unverified", text)
        self.assertNotIn("Closes when: measured on a console", text)
        self.assertIn("### Unknown function info\n\n- [Thing]", text)
        removal = write(debt_fold.ROOT, "debt/changes/fix-demo.md", "# demo\n\n## remove [Export.cpp) (demo) - returns]\n")
        self.assertNotIn("Quiet", debt_fold.fold([removal])["demo"])

    def test_rejects_ambiguous_and_conflicting(self):
        ambiguous = write(debt_fold.ROOT, "debt/changes/a.md", "# demo\n\n## remove [(demo)]\n")
        with self.assertRaises(debt_fold.FoldError):
            debt_fold.fold([ambiguous])
        twice = write(debt_fold.ROOT, "debt/changes/b.md", "# demo\n\n## remove [Quiet]\n")
        again = write(debt_fold.ROOT, "debt/changes/c.md", "# demo\n\n## remove [Quiet]\n")
        with self.assertRaises(debt_fold.FoldError):
            debt_fold.fold([twice, again])

    def test_rejects_stray_text(self):
        bad = write(debt_fold.ROOT, "debt/changes/d.md", "# demo\n\nfree text\n")
        with self.assertRaises(debt_fold.FoldError):
            debt_fold.parse_fragment(bad)


class RunReportTest(unittest.TestCase):
    def test_fixtures_are_valid(self):
        fixtures = sorted((TOOLS.parent / "docs" / "run-report-fixtures").glob("*.json"))
        self.assertTrue(fixtures)
        for path in fixtures:
            report = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(run_report_summary.validate(report), [], path.name)
            self.assertIn(report["game"]["titleId"], run_report_summary.summary(report))

    def test_invalid_report(self):
        self.assertTrue(run_report_summary.validate({"format": "other"}))


if __name__ == "__main__":
    unittest.main()
