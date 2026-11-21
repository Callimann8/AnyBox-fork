import struct
import tempfile
import unittest
from pathlib import Path

import helpers
import shader_scan


def container(parts):
    offsets, body = [], b""
    table = 32 + len(parts) * 4
    for fourcc, payload in parts:
        offsets.append(table + len(body))
        body += fourcc + struct.pack("<I", len(payload)) + payload
    size = table + len(body)
    return b"DXBC" + b"\0" * 16 + struct.pack("<HHII", 1, 0, size, len(parts)) + b"".join(struct.pack("<I", o) for o in offsets) + body


class ShaderScanTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)

    def tearDown(self):
        self.directory.cleanup()

    def write(self, name, data):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path

    def test_classifies_containers(self):
        self.assertEqual(shader_scan.kind(["ISG1", "DXIL", "HASH"]), "dxil")
        self.assertEqual(shader_scan.kind(["SHEX"]), "dxbc")
        self.assertEqual(shader_scan.kind(["SHDR", "DXIL"]), "mixed")
        self.assertEqual(shader_scan.kind(["RTS0"]), "rootsig")
        self.assertEqual(shader_scan.kind(["ABCD"]), "other")

    def test_finds_embedded_containers_and_skips_false_magic(self):
        dxil = container([(b"DXIL", b"\1" * 12), (b"XHW0", b"\2" * 4)])
        rootsig = container([(b"RTS0", b"\3" * 8)])
        path = self.write("pak/blob.bin", b"junk DXBC not a header" + dxil + b"\0" * 7 + rootsig + b"DXBC")
        found = shader_scan.scan_file(path)
        self.assertEqual([c["kind"] for c in found], ["dxil", "rootsig"])
        self.assertEqual(found[0]["parts"], ["DXIL", "XHW0"])
        self.assertEqual(found[0]["offset"], 22)

    def test_rejects_truncated_container(self):
        path = self.write("cut.cso", container([(b"DXIL", b"\1" * 12)])[:-4])
        self.assertEqual(shader_scan.scan_file(path), [])

    def test_rejects_part_inside_header(self):
        data = bytearray(container([(b"DXIL", b"\1" * 12)]))
        data[32:36] = b"\0\0\0\0"
        self.assertEqual(shader_scan.scan_file(self.write("bad.cso", bytes(data))), [])

    def test_summarizes_a_folder(self):
        self.write("a.cso", container([(b"SHEX", b"\1" * 4)]))
        self.write("sub/b.cso", container([(b"DXIL", b"\1" * 4), (b"XHW0", b"")]))
        self.write("empty.txt", b"")
        files = shader_scan.collect([self.root])
        results = {str(p): c for p in files if (c := shader_scan.scan_file(p))}
        self.assertEqual(shader_scan.summarize(results), {"files": 2, "containers": 2, "kinds": {"dxbc": 1, "dxil": 1}, "parts": {"DXIL": 1, "SHEX": 1, "XHW0": 1}})


if __name__ == "__main__":
    unittest.main()
