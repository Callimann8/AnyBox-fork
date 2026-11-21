import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import anybox_scan

ROOT = anybox_scan.ROOT
NAME = re.compile(r"[A-Za-z_]\w*")


def library_dir(root, name):
    return root / anybox_scan.XDLL / name


def new_library(root, name, dlls):
    if not re.fullmatch(r"[a-z0-9_]+", name):
        raise SystemExit("library names are lowercase letters, digits and underscores")
    base = library_dir(root, name)
    if base.exists():
        raise SystemExit(f"{base.relative_to(root)} already exists")
    (base / "include").mkdir(parents=True)
    (base / "Imports.txt").write_text("".join(f"{dll.lower()}\n" for dll in dlls), encoding="utf-8")
    (base / "CMakeLists.txt").write_text(f"anybox_add_xdll({name} SOURCES Inventory.cpp)\n", encoding="utf-8")
    (base / f"{name}.hpp").write_text(f'#pragma once\n\n#include "xdll/{name}/include/Exports.hpp"\n', encoding="utf-8")
    (base / "include" / "Exports.hpp").write_text('#pragma once\n\n#include "AbxApi.hpp"\n\n#include <windows.h>\n', encoding="utf-8")
    (base / "Inventory.cpp").write_text(f'#include "xdll/{name}/{name}.hpp"\n', encoding="utf-8")
    debt = root / "docs" / "dev" / "debt" / f"{name}.md"
    debt.parent.mkdir(parents=True, exist_ok=True)
    if not debt.exists():
        debt.write_text(f"# {name} technical debt\n\nServes {', '.join(dlls)}.\n", encoding="utf-8")
    print(f"created {base.relative_to(root).as_posix()}; reconfigure CMake to build ab_{name}.dll")


def add_stubs(root, name, functions):
    base = library_dir(root, name)
    if not base.exists():
        raise SystemExit(f"no library {name}; create it with --new-library {name} --dll <name>.dll")
    library = anybox_scan.scan_library(anybox_scan.TreeSource(root), name)
    known = set(library.definitions) | set(library.forwarded)
    wanted = []
    for function in functions:
        if function.startswith("#"):
            print(f"skipped ordinal import {function} of {name}: pin it as '<Name> @{function[1:]}' in core/libs/xdll/{name}/Ordinals.txt", file=sys.stderr)
        elif not NAME.fullmatch(function):
            print(f"skipped {function!r}: not a C identifier", file=sys.stderr)
        elif function not in known and function not in wanted:
            wanted.append(function)
    if not wanted:
        print(f"{name}: nothing to add")
        return []
    header = base / "include" / "Exports.hpp"
    inventory = base / "Inventory.cpp"
    if not inventory.exists():
        inventory.write_text(f'#include "xdll/{name}/{name}.hpp"\n', encoding="utf-8")
        cmake = base / "CMakeLists.txt"
        text = cmake.read_text(encoding="utf-8")
        if "Inventory.cpp" not in text:
            text = text.replace(f"anybox_add_xdll({name}", f"anybox_add_xdll({name} SOURCES Inventory.cpp", 1) if "SOURCES" not in text \
                else text.replace("SOURCES", "SOURCES Inventory.cpp", 1)
            cmake.write_text(text, encoding="utf-8")
    header_text = header.read_text(encoding="utf-8").rstrip("\n") + "\n\n"
    header_text += "".join(f"ABX_API HRESULT {function}();\n" for function in wanted)
    header.write_text(header_text, encoding="utf-8")
    inventory_text = inventory.read_text(encoding="utf-8").rstrip("\n") + "\n\n"
    inventory_text += "".join(f"ABX_API HRESULT {function}() {{ AbxNotImplemented(__func__); }}\n" for function in wanted)
    inventory.write_text(inventory_text, encoding="utf-8")
    fragment = root / "docs" / "dev" / "debt" / "changes" / f"stubgen-{name}.md"
    entry = f"- [{name}](../../../{anybox_scan.XDLL}/{name}/Inventory.cpp) ({name}) - declared without parameters, signatures unknown: {', '.join(wanted)}\n"
    fragment.parent.mkdir(parents=True, exist_ok=True)
    existing = fragment.read_text(encoding="utf-8") if fragment.exists() else f"# {name}\n\n## add Unknown function info\n\n"
    fragment.write_text(existing + entry, encoding="utf-8")
    print(f"{name}: added {len(wanted)} stubs ({', '.join(wanted)})")
    return wanted


def from_audit(root, path):
    rows = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(rows, dict):
        rows = rows.get("rows", [])
    absent = defaultdict(list)
    unrouted = defaultdict(set)
    for row in rows:
        if row.get("status") == "absent":
            absent[row["library"]].append(row["function"])
        elif row.get("status") == "unrouted":
            unrouted[row["dll"].lower()].add(row["function"])
    for name, functions in sorted(absent.items()):
        add_stubs(root, name, functions)
    for dll, functions in sorted(unrouted.items()):
        stem = re.sub(r"[^a-z0-9_]", "_", dll.rsplit(".", 1)[0])
        print(f"unrouted: {dll} ({len(functions)} functions); start a library with: python tools/stubgen.py --new-library {stem} --dll {dll}")


def main():
    parser = argparse.ArgumentParser(description="Add AbxNotImplemented stubs for imports AnyBox does not declare yet.")
    parser.add_argument("--library", help="library directory name under core/libs/xdll")
    parser.add_argument("--names", nargs="+", default=[], help="function names to stub")
    parser.add_argument("--from-audit", type=Path, help="JSON written by tools/import_audit.py --json, or needs.json from tools/needs.py")
    parser.add_argument("--new-library", metavar="NAME", help="create a library skeleton")
    parser.add_argument("--dll", action="append", default=[], help="DLL name the new library serves; repeatable")
    parser.add_argument("--root", type=Path, default=ROOT, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.new_library:
        if not args.dll:
            parser.error("--new-library needs at least one --dll")
        new_library(args.root, args.new_library, args.dll)
        if args.names:
            add_stubs(args.root, args.new_library, args.names)
    elif args.from_audit:
        from_audit(args.root, args.from_audit)
    elif args.library and args.names:
        add_stubs(args.root, args.library, args.names)
    else:
        parser.error("use --library with --names, --from-audit, or --new-library")


if __name__ == "__main__":
    main()
