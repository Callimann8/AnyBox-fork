import json
import struct
import unittest
from pathlib import Path

from helpers import library, synthetic_pe, temp_root, write

import anybox_scan
import import_audit
import lib_inventory
import needs
import stubgen


def member(name, body):
    header = f"{name:<16}{0:<12}{0:<6}{0:<6}{0:<8}{len(body):<10}".encode("ascii") + b"`\n"
    return header + body + (b"\n" if len(body) % 2 else b"")


def short_import(symbol, dll, name_type=1, hint=0, extra=None):
    strings = symbol.encode() + b"\0" + dll.encode() + b"\0" + ((extra.encode() + b"\0") if extra else b"")
    return struct.pack("<HHHHIIHH", 0, 0xFFFF, 0, 0x8664, 0, len(strings), hint, name_type << 2) + strings


def import_library(entries):
    data = b"!<arch>\n" + member("/", b"\0\0\0\0")
    for entry in entries:
        data += member("x.dll/", short_import(*entry))
    return data


class InventoryTest(unittest.TestCase):
    def setUp(self):
        self.directory = temp_root()
        self.root = Path(self.directory.name)

    def tearDown(self):
        self.directory.cleanup()

    def test_short_import_library(self):
        path = self.root / "xgameruntime.lib"
        path.write_bytes(import_library([
            ("XGameRuntimeInitialize", "XGameRuntime.dll"),
            ("_XUserAddAsync", "XGameRuntime.dll", 2),
            ("_XUserGetId@8", "XGameRuntime.dll", 3),
            ("Renamed", "XGameRuntime.dll", 4, 0, "XRealName"),
            ("Ordinal", "Other.dll", 0, 42),
        ]))
        inventory = lib_inventory.collect([self.root])
        self.assertEqual(inventory["xgameruntime.dll"], ["XGameRuntimeInitialize", "XRealName", "XUserAddAsync", "XUserGetId"])
        self.assertEqual(inventory["other.dll"], ["Ordinal"])

    def test_skips_objects_with_import_signature(self):
        path = self.root / "static.lib"
        anonymous = struct.pack("<HHHHIIHH", 0, 0xFFFF, 1, 0x8664, 0, 4, 0, 0) + bytes(40)
        path.write_bytes(b"!<arch>\n" + member("/", bytes(4)) + member("a.obj/", anonymous))
        with self.assertRaises(lib_inventory.InventoryError):
            lib_inventory.read_import_library(path)
        path.write_bytes(import_library([("XGameRuntimeInitialize", "XGameRuntime.dll")]) + member("a.obj/", anonymous))
        self.assertEqual(lib_inventory.read_import_library(path), {"xgameruntime.dll": {"XGameRuntimeInitialize"}})

    def test_rename(self):
        inventory = {"a.thunks.dll": ["X", "Y"], "a.dll": ["Init", "X"]}
        self.assertEqual(lib_inventory.rename(inventory, {"a.thunks.dll": "a.dll"}), {"a.dll": ["Init", "X", "Y"]})

    def test_rejects_non_archive(self):
        path = self.root / "bad.lib"
        path.write_bytes(b"not an archive")
        with self.assertRaises(lib_inventory.InventoryError):
            lib_inventory.read_import_library(path)


class NeedsTest(unittest.TestCase):
    def setUp(self):
        self.directory = temp_root()
        self.root = Path(self.directory.name)
        library(self.root, "demo", ["demo.dll"], "ABX_API HRESULT Done();\nABX_API HRESULT Pending();\n",
                {"Export.cpp": "ABX_API HRESULT Done() { return S_OK; }\nABX_API HRESULT Pending() { AbxNotImplemented(__func__); }\n"})
        self.source = anybox_scan.TreeSource(self.root)

    def tearDown(self):
        self.directory.cleanup()

    def report(self, titles, inventories=()):
        return needs.build(titles, list(inventories), anybox_scan.scan(self.source), anybox_scan.host_patterns(self.source))

    def test_ranks_by_titles_and_status(self):
        titles = [
            {"titleId": "0000000A", "name": "A", "version": None, "imports": {"demo.dll": ["Done", "Pending", "Missing"], "kernel32.dll": ["Sleep"]}},
            {"titleId": "0000000B", "name": "B", "version": None, "imports": {"demo.dll": ["Pending"], "new.dll": ["Thing"]}},
        ]
        inventory = {"format": "anybox-inventory", "version": 1, "label": None, "dlls": {"demo.dll": ["Done", "Pending", "Missing", "Unused"]}}
        report = self.report(titles, [inventory])
        order = [(row["function"], row["status"], len(row["titles"])) for row in report["rows"]]
        self.assertEqual(order[0], ("Pending", "stub", 2))
        self.assertEqual(order[1:3], [("Thing", "unrouted", 1), ("Missing", "absent", 1)])
        self.assertIn(("Unused", "absent", 0), order)
        self.assertEqual(order[-1], ("Done", "implemented", 1))
        self.assertNotIn("Sleep", [row["function"] for row in report["rows"]])
        demo = next(entry for entry in report["dlls"] if entry["dll"] == "demo.dll")
        self.assertEqual((demo["known"], demo["needed"], demo["declared"], demo["done"], demo["neededDone"]), (4, 3, 2, 1, 1))
        title_a = next(title for title in report["titles"] if title["titleId"] == "0000000A")
        self.assertEqual((title_a["needed"], title_a["done"]), (3, 1))
        self.assertEqual(title_a["blockers"], ["demo.dll!Pending", "demo.dll!Missing"])
        self.assertIn("| `Pending` | demo.dll | demo | stub | 2 |", needs.markdown(report, 10))
        self.assertIn("What AnyBox still needs", needs.page(report))

    def test_stubgen_reads_needs_report(self):
        report = self.report([{"titleId": "0000000A", "name": None, "version": None, "imports": {"demo.dll": ["Missing"]}}])
        path = self.root / "needs.json"
        path.write_text(json.dumps(report), encoding="utf-8")
        stubgen.from_audit(self.root, path)
        self.assertIn("Missing", anybox_scan.scan_library(self.source, "demo").stubs)

    def test_audit_needs_record(self):
        package = self.root / "package"
        write(package, "MicrosoftGame.config",
              '<Game><Identity Name="X" Publisher="CN=X" Version="1.2.3.4"/><TitleId>00ab12cd</TitleId>'
              '<ShellVisuals DefaultDisplayName="Example"/></Game>')
        (package / "title.exe").write_bytes(synthetic_pe([("demo.dll", ["Done", "Missing"]), ("kernel32.dll", ["Sleep"])]))
        libraries = anybox_scan.scan(self.source)
        rows = import_audit.audit(import_audit.collect([package]), libraries, anybox_scan.host_patterns(self.source))
        record = import_audit.needs_record(rows, import_audit.title_metadata([package]))
        self.assertEqual(record["titleId"], "00AB12CD")
        self.assertEqual((record["name"], record["version"]), ("Example", "1.2.3.4"))
        self.assertEqual(record["imports"], {"demo.dll": ["Done", "Missing"]})


if __name__ == "__main__":
    unittest.main()
