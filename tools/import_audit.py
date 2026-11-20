import argparse
import json
import struct
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import anybox_scan

CLASSES = ("implemented", "forwarded", "stub", "absent", "bundled", "host", "unrouted")
ORDINAL_FLAG = 1 << 63


class AuditError(Exception):
    pass


class Pe:
    def __init__(self, path):
        self.path = path
        self.data = path.read_bytes()
        if self.data[:2] != b"MZ":
            raise AuditError(f"{path}: not a PE file")
        pe = self.u32(0x3C)
        if self.data[pe:pe + 4] != b"PE\0\0":
            raise AuditError(f"{path}: no PE signature")
        sections = self.u16(pe + 6)
        optional_size = self.u16(pe + 20)
        optional = pe + 24
        if self.u16(optional) != 0x20B:
            raise AuditError(f"{path}: not PE32+")
        self.machine = self.u16(pe + 4)
        self.subsystem = self.u16(optional + 68)
        self.headers = self.u32(optional + 60)
        count = self.u32(optional + 108)
        self.directories = [(self.u32(optional + 112 + i * 8), self.u32(optional + 116 + i * 8)) for i in range(min(count, 16))]
        table = optional + optional_size
        self.sections = []
        for i in range(sections):
            base = table + i * 40
            virtual_size, rva, raw_size, raw = struct.unpack_from("<IIII", self.data, base + 8)
            self.sections.append((rva, max(virtual_size, raw_size), raw, raw_size))

    def u16(self, offset):
        return struct.unpack_from("<H", self.data, offset)[0]

    def u32(self, offset):
        return struct.unpack_from("<I", self.data, offset)[0]

    def u64(self, offset):
        return struct.unpack_from("<Q", self.data, offset)[0]

    def offset(self, rva):
        if rva < self.headers:
            return rva
        for start, size, raw, raw_size in self.sections:
            if start <= rva < start + size and rva - start < raw_size:
                return raw + rva - start
        raise AuditError(f"{self.path}: RVA 0x{rva:x} is not backed by file data")

    def string(self, rva):
        start = self.offset(rva)
        end = self.data.index(b"\0", start)
        return self.data[start:end].decode("ascii", errors="replace")

    def thunks(self, rva):
        functions = []
        offset = self.offset(rva)
        while True:
            thunk = self.u64(offset)
            offset += 8
            if thunk == 0:
                return functions
            functions.append(f"#{thunk & 0xFFFF}" if thunk & ORDINAL_FLAG else self.string((thunk & 0x7FFFFFFF) + 2))

    def imports(self):
        modules = []
        if len(self.directories) > 1 and self.directories[1][0]:
            offset = self.offset(self.directories[1][0])
            while True:
                lookup, _, _, name, iat = struct.unpack_from("<IIIII", self.data, offset)
                if not (lookup or name or iat):
                    break
                modules.append((self.string(name), False, self.thunks(lookup or iat)))
                offset += 20
        if len(self.directories) > 13 and self.directories[13][0]:
            offset = self.offset(self.directories[13][0])
            while True:
                fields = struct.unpack_from("<IIIIIIII", self.data, offset)
                if not fields[1]:
                    break
                modules.append((self.string(fields[1]), True, self.thunks(fields[4])))
                offset += 32
        return modules


def collect(paths):
    files = []
    for path in paths:
        if path.is_dir():
            files += sorted(p for p in path.rglob("*") if p.suffix.lower() in (".exe", ".dll") and p.is_file())
        else:
            files.append(path)
    return files


def audit(files, libraries, hosts):
    bundled = {path.name.lower() for path in files}
    rows = []
    for path in files:
        try:
            pe = Pe(path)
        except AuditError as error:
            rows.append({"file": str(path), "error": str(error)})
            continue
        for dll, delayed, functions in pe.imports():
            lower = dll.lower()
            library = None if lower in bundled else anybox_scan.route(libraries, lower)
            for function in functions:
                if lower in bundled:
                    status = "bundled"
                elif library is not None:
                    status = library.status(function)
                elif any(anybox_scan.match_pattern(pattern, lower) for pattern in hosts):
                    status = "host"
                else:
                    status = "unrouted"
                rows.append({"file": path.name, "dll": dll, "delayLoaded": delayed, "function": function,
                             "library": library.name if library else None, "status": status})
    return rows


def main():
    parser = argparse.ArgumentParser(description="List a GDK title's imports and what AnyBox does with each one.")
    parser.add_argument("paths", nargs="+", type=Path, help="executables, DLLs or package folders (decrypted)")
    parser.add_argument("--json", type=Path, help="write the rows as JSON (input for tools/stubgen.py --from-audit)")
    parser.add_argument("--strict-stubs", action="store_true", help="fail when a stub is imported")
    parser.add_argument("--all", action="store_true", help="also print implemented, forwarded, bundled and host rows")
    args = parser.parse_args()

    libraries = anybox_scan.scan()
    rows = audit(collect(args.paths), libraries, anybox_scan.host_patterns())
    errors = [row for row in rows if "error" in row]
    rows = [row for row in rows if "error" not in row]
    for row in errors:
        print(f"error: {row['error']}")
    shown = {"stub", "absent", "unrouted"} if not args.all else set(CLASSES)
    for row in rows:
        if row["status"] in shown:
            print(f"{row['status']:<11} {row['file']}: {row['dll']}!{row['function']}{' (delay)' if row['delayLoaded'] else ''}")
    counts = Counter(row["status"] for row in rows)
    print("summary: " + ", ".join(f"{name} {counts.get(name, 0)}" for name in CLASSES))
    if args.json:
        args.json.write_text(json.dumps(rows, indent=1) + "\n", encoding="utf-8")
    failing = counts.get("absent", 0) + counts.get("unrouted", 0) + (counts.get("stub", 0) if args.strict_stubs else 0)
    return 1 if failing or errors else 0


if __name__ == "__main__":
    sys.exit(main())
