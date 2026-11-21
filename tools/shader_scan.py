import argparse
import json
import mmap
import struct
import sys
from collections import Counter
from pathlib import Path

MAGIC = b"DXBC"
HEADER = 32
MAX_PARTS = 64
CODE_PARTS = {"DXIL": "dxil", "SHEX": "dxbc", "SHDR": "dxbc"}


def container_at(data, offset):
    if offset + HEADER > len(data):
        return None
    major, minor, size, count = struct.unpack_from("<HHII", data, offset + 20)
    if (major, minor) != (1, 0) or size < HEADER or offset + size > len(data) or not 0 < count <= MAX_PARTS or HEADER + count * 4 > size:
        return None
    parts = []
    for index in range(count):
        part = struct.unpack_from("<I", data, offset + HEADER + index * 4)[0]
        if part + 8 > size:
            return None
        fourcc = bytes(data[offset + part:offset + part + 4])
        length = struct.unpack_from("<I", data, offset + part + 4)[0]
        if part + 8 + length > size or not all(0x20 <= c < 0x7F for c in fourcc):
            return None
        parts.append(fourcc.decode("ascii"))
    return size, parts


def kind(parts):
    kinds = {CODE_PARTS[part] for part in parts if part in CODE_PARTS}
    if len(kinds) == 1:
        return kinds.pop()
    if kinds:
        return "mixed"
    return "rootsig" if "RTS0" in parts else "other"


def scan_file(path):
    containers = []
    if path.stat().st_size < HEADER:
        return containers
    with path.open("rb") as file, mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_READ) as data:
        offset = data.find(MAGIC)
        while offset != -1:
            found = container_at(data, offset)
            if found:
                containers.append({"offset": offset, "size": found[0], "kind": kind(found[1]), "parts": found[1]})
                offset = data.find(MAGIC, offset + found[0])
            else:
                offset = data.find(MAGIC, offset + 1)
    return containers


def collect(paths):
    files = []
    for path in paths:
        files += sorted(p for p in path.rglob("*") if p.is_file()) if path.is_dir() else [path]
    return files


def summarize(results):
    kinds, parts = Counter(), Counter()
    for containers in results.values():
        for container in containers:
            kinds[container["kind"]] += 1
            parts.update(container["parts"])
    return {"files": sum(1 for c in results.values() if c), "containers": sum(kinds.values()), "kinds": dict(sorted(kinds.items())), "parts": dict(sorted(parts.items()))}


def main():
    parser = argparse.ArgumentParser(description="Count the DXBC shader containers in a GDK title and the parts each one holds (DXIL, DXBC bytecode, root signature or unknown).")
    parser.add_argument("paths", nargs="+", type=Path, help="files or package folders (decrypted)")
    parser.add_argument("--json", type=Path, help="write the summary and per-file containers as JSON: names, offsets and part tags only")
    args = parser.parse_args()

    results = {}
    for path in collect(args.paths):
        try:
            containers = scan_file(path)
        except OSError as error:
            print(f"{path}: {error}", file=sys.stderr)
            continue
        if containers:
            results[str(path)] = containers
            print(f"{path}: {', '.join(f'{n} {k}' for k, n in sorted(Counter(c['kind'] for c in containers).items()))}")

    summary = summarize(results)
    print(f"{summary['containers']} containers in {summary['files']} files; kinds: {summary['kinds']}; parts: {summary['parts']}")
    if args.json:
        args.json.write_text(json.dumps({"summary": summary, "files": results}, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
