import unittest

from helpers import library, temp_root

import anybox_scan
import progress

HEADER = """
ABX_API HRESULT Done(int value);
ABX_API HRESULT Pending();
ABX_API void Braces();
"""

SOURCE = """#include "x.hpp"
ABX_API HRESULT Done(int value) { return value ? S_OK : E_FAIL; }
ABX_API HRESULT Pending() { AbxNotImplemented(__func__); }
ABX_API void Braces() {
    const char* text = "AbxNotImplemented( } {";
}
"""


class ScanTest(unittest.TestCase):
    def setUp(self):
        self.directory = temp_root()
        library(self.directory.name, "demo", ["demo.dll", "demo_*.dll"], HEADER, {"Export.cpp": SOURCE}, ["Tick=kernel32.GetTickCount64"])
        library(self.directory.name, "other", ["other.dll"], "ABX_API HRESULT Later();\n", {"Export.cpp": "ABX_API HRESULT Later() { AbxNotImplemented(__func__); }\n"})
        self.source = anybox_scan.TreeSource(self.directory.name)

    def tearDown(self):
        self.directory.cleanup()

    def test_classifies_functions(self):
        demo = anybox_scan.scan_library(self.source, "demo")
        self.assertEqual(demo.implemented, ["Braces", "Done"])
        self.assertEqual(demo.stubs, ["Pending"])
        self.assertEqual(demo.forwarded, {"Tick": "kernel32.GetTickCount64"})
        self.assertEqual(demo.declared, 4)
        self.assertEqual(demo.status("Pending"), "stub")
        self.assertEqual(demo.status("Missing"), "absent")

    def test_routes_by_pattern(self):
        libraries = anybox_scan.scan(self.source)
        self.assertEqual(anybox_scan.route(libraries, "DEMO_XS.dll").name, "demo")
        self.assertIsNone(anybox_scan.route(libraries, "nothing.dll"))

    def test_snapshot_and_compare(self):
        base = progress.snapshot(anybox_scan.scan(self.source))
        self.assertEqual(base["totals"]["declared"], 5)
        self.assertEqual(base["totals"]["percent"], 60.0)
        library(self.directory.name, "other", ["other.dll"], "ABX_API HRESULT Later();\n", {"Export.cpp": "ABX_API HRESULT Later() { return S_OK; }\n"})
        head = progress.snapshot(anybox_scan.scan(self.source))
        report = progress.compare(base, head)
        self.assertTrue(report.startswith("📈 **Libraries**: 80% (+20%, +1 implemented function)"), report)
        self.assertIn("| other | `Later` |", report)
        self.assertIn("| other | 0/1 (0%) | 1/1 (100%) | +100.00% |", report)
        self.assertEqual(progress.compare(head, head), "")

    def test_compare_lists_regressions_and_new_stubs(self):
        base = progress.snapshot(anybox_scan.scan(self.source))
        library(self.directory.name, "other", ["other.dll"], "ABX_API HRESULT Later();\nABX_API HRESULT Newer();\n",
                {"Export.cpp": "ABX_API HRESULT Later() { AbxNotImplemented(__func__); }\nABX_API HRESULT Newer() { AbxNotImplemented(__func__); }\n"})
        library(self.directory.name, "demo", ["demo.dll", "demo_*.dll"], HEADER, {"Export.cpp": SOURCE.replace("return value ? S_OK : E_FAIL;", "AbxNotImplemented(__func__);")}, ["Tick=kernel32.GetTickCount64"])
        report = progress.compare(base, progress.snapshot(anybox_scan.scan(self.source)))
        self.assertTrue(report.startswith("📉 **Libraries**: 33.33% (-26.6667%, -1 no longer done, +1 declared function)"), report)
        self.assertIn("⚠️ **1 function no longer done**: `demo!Done`", report)
        self.assertIn("🆕 1 declared as stubs", report)
        self.assertIn("| other | `Newer` |", report)

    def test_root_counts_another_checkout(self):
        import contextlib, io, json, sys
        output = io.StringIO()
        arguments = sys.argv
        sys.argv = ["progress.py", "--root", self.directory.name, "--json"]
        try:
            with contextlib.redirect_stdout(output):
                progress.main()
        finally:
            sys.argv = arguments
        data = json.loads(output.getvalue())
        self.assertEqual((data["totals"]["declared"], data["totals"]["implemented"], data["totals"]["forwarded"]), (5, 2, 1))

    def test_known_functions_and_unserved_dlls(self):
        known = {"demo_xs.dll": {"Done", "Pending", "NotYet"}, "absent.dll": {"A", "B"}, "kernel32.dll": {"Sleep"}}
        data = progress.snapshot(anybox_scan.scan(self.source), None, known, {"absent.dll": {"T1", "T2"}}, ["kernel32.dll"])
        demo = next(row for row in data["libraries"] if row["name"] == "demo")
        other = next(row for row in data["libraries"] if row["name"] == "other")
        self.assertEqual((demo["missing"], demo["known"], demo["missingNames"], demo["surfaceKnown"]), (1, 5, ["NotYet"], True))
        self.assertEqual((other["missing"], other["surfaceKnown"]), (0, False))
        self.assertEqual(data["unserved"], [{"dll": "absent.dll", "missing": 2, "titles": 2, "missingNames": ["A", "B"]}])
        self.assertEqual((data["totals"]["missing"], data["totals"]["known"], data["totals"]["unservedDlls"]), (3, 8, 1))
        self.assertEqual(data["totals"]["knownPercent"], 37.5)
        drawn = progress.progress_map(data)
        self.assertIn("absent.dll: no AnyBox library, 2 known functions, needed by 2 titles", drawn)
        self.assertIn('stroke-dasharray="5 3"', drawn)
        self.assertIn("other*", drawn)
        self.assertEqual(drawn.count(f'fill="{progress.MISSING}"'), 1 + 3)
        self.assertIn("--new-library absent --dll absent.dll", progress.page(data))
        self.assertIn("1 DLL with no library", progress.page(data))

    def test_treemap_layout(self):
        boxes = progress.squarify([6, 3, 1], 0, 0, 100, 50)
        self.assertAlmostEqual(sum(w * h for _, _, w, h in boxes), 5000)
        for (x, y, w, h), size in zip(boxes, [6, 3, 1]):
            self.assertAlmostEqual(w * h, 500 * size)
            self.assertTrue(0 <= x and x + w <= 100.001 and 0 <= y and y + h <= 50.001)
        cells = progress.grid_cells(7, 0, 0, 70, 20)
        self.assertEqual(len(cells), 7)
        self.assertAlmostEqual(sum(w * h for _, _, w, h in cells), 1400)

    def test_outputs_render(self):
        data = progress.snapshot(anybox_scan.scan(self.source), "0" * 40)
        self.assertIn("<svg", progress.progress_map(data))
        self.assertIn("Pending", progress.page(data))
        self.assertIn("60.0%", progress.badge("libraries", "60.0%", progress.DONE))


if __name__ == "__main__":
    unittest.main()
