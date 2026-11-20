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

    def test_outputs_render(self):
        data = progress.snapshot(anybox_scan.scan(self.source), "0" * 40)
        self.assertIn("<svg", progress.progress_map(data))
        self.assertIn("Pending", progress.page(data))
        self.assertIn("60.0%", progress.badge("libraries", "60.0%", progress.DONE))


if __name__ == "__main__":
    unittest.main()
