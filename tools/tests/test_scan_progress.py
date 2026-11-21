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
        self.assertIn("| other | 0/1 (0.0%) | 1/1 (100.0%) | +100.0% |", report)
        self.assertIn("other: newly done Later", report)
        self.assertIn("No library changes.", progress.compare(head, head))

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
        self.assertIn("no library, 0/2", progress.progress_map(data))
        self.assertIn("--new-library absent --dll absent.dll", progress.page(data))
        self.assertIn("1 DLL with no library", progress.page(data))

    def test_outputs_render(self):
        data = progress.snapshot(anybox_scan.scan(self.source), "0" * 40)
        self.assertIn("<svg", progress.progress_map(data))
        self.assertIn("Pending", progress.page(data))
        self.assertIn("60.0%", progress.badge("libraries", "60.0%", progress.DONE))


if __name__ == "__main__":
    unittest.main()
