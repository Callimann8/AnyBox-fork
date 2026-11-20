import json
import unittest
from pathlib import Path

from helpers import library, synthetic_pe, temp_root

import anybox_scan
import check_conventions
import import_audit
import stubgen


class AuditStubgenTest(unittest.TestCase):
    def setUp(self):
        self.directory = temp_root()
        self.root = Path(self.directory.name)
        library(self.root, "demo", ["demo.dll"], "ABX_API HRESULT Done();\nABX_API HRESULT Pending();\n",
                {"Export.cpp": "ABX_API HRESULT Done() { return S_OK; }\nABX_API HRESULT Pending() { AbxNotImplemented(__func__); }\n"},
                ["Tick=kernel32.GetTickCount64"])
        self.title = self.root / "package" / "title.exe"
        self.title.parent.mkdir()
        self.title.write_bytes(synthetic_pe([
            ("demo.dll", ["Done", "Pending", "Tick", "Missing", 5]),
            ("kernel32.dll", ["Sleep"]),
            ("mystery_x.dll", ["Thing"]),
            ("game.dll", ["Engine"]),
        ]))
        (self.root / "package" / "game.dll").write_bytes(synthetic_pe([]))

    def tearDown(self):
        self.directory.cleanup()

    def rows(self):
        libraries = anybox_scan.scan(anybox_scan.TreeSource(self.root))
        hosts = anybox_scan.host_patterns(anybox_scan.TreeSource(self.root))
        return import_audit.audit(import_audit.collect([self.root / "package"]), libraries, hosts)

    def test_audit_classifies_every_import(self):
        status = {(row["dll"], row["function"]): row["status"] for row in self.rows()}
        self.assertEqual(status[("demo.dll", "Done")], "implemented")
        self.assertEqual(status[("demo.dll", "Pending")], "stub")
        self.assertEqual(status[("demo.dll", "Tick")], "forwarded")
        self.assertEqual(status[("demo.dll", "Missing")], "absent")
        self.assertEqual(status[("demo.dll", "#5")], "absent")
        self.assertEqual(status[("kernel32.dll", "Sleep")], "host")
        self.assertEqual(status[("mystery_x.dll", "Thing")], "unrouted")
        self.assertEqual(status[("game.dll", "Engine")], "bundled")

    def test_stubgen_from_audit(self):
        audit = self.root / "audit.json"
        audit.write_text(json.dumps(self.rows()), encoding="utf-8")
        stubgen.from_audit(self.root, audit)
        demo = anybox_scan.scan_library(anybox_scan.TreeSource(self.root), "demo")
        self.assertIn("Missing", demo.stubs)
        self.assertEqual(check_conventions.run(self.root, commits=False), [])
        self.assertTrue((self.root / "docs/dev/debt/changes/stubgen-demo.md").exists())
        stubgen.add_stubs(self.root, "demo", ["Missing"])
        self.assertEqual(anybox_scan.scan_library(anybox_scan.TreeSource(self.root), "demo").stubs.count("Missing"), 1)

    def test_new_library(self):
        stubgen.new_library(self.root, "mystery_x", ["mystery_x.dll"])
        stubgen.add_stubs(self.root, "mystery_x", ["Thing"])
        libraries = anybox_scan.scan(anybox_scan.TreeSource(self.root))
        self.assertEqual(anybox_scan.route(libraries, "mystery_x.dll").stubs, ["Thing"])
        self.assertEqual(check_conventions.run(self.root, commits=False), [])


if __name__ == "__main__":
    unittest.main()
