import json
import re
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
XDLL = "core/libs/xdll"
NEEDS_DIR = ROOT / "docs" / "needs"
INVENTORY_DIR = ROOT / "docs" / "inventory"
STUB_CALL = re.compile(r"\bAbxNotImplemented\s*\(")
DEFINITION = re.compile(r"\bABX_API\s+[\w:<>*&\s]*?\b(\w+)\s*\(([^;{}]*)\)\s*(?:noexcept\s*)?\{")
DECLARATION = re.compile(r"\bABX_API\s+[\w:<>*&\s]*?\b(\w+)\s*\(([^;{}]*)\)\s*(?:noexcept\s*)?;")
FORWARD = re.compile(r"^\s*(\w+)\s*=\s*([\w.-]+)\.(#?\w+)\s*$")
TOKEN = re.compile(
    r'(?P<raw>R"(?P<delim>[^(\s]{0,16})\((?:.|\n)*?\)(?P=delim)")'
    r'|(?P<string>"(?:\\.|[^"\\\n])*")'
    r"|(?P<char>'(?:\\.|[^'\\\n])*')"
    r"|(?P<line>//[^\n]*)"
    r"|(?P<block>/\*(?:.|\n)*?\*/)"
)
SOURCE_SUFFIXES = (".cpp", ".cc", ".c", ".hpp", ".h", ".inl")


@dataclass
class Library:
    name: str
    dlls: list = field(default_factory=list)
    implemented: list = field(default_factory=list)
    stubs: list = field(default_factory=list)
    forwarded: dict = field(default_factory=dict)
    declarations: dict = field(default_factory=dict)
    definitions: dict = field(default_factory=dict)

    @property
    def declared(self):
        return len(self.implemented) + len(self.stubs) + len(self.forwarded)

    @property
    def done(self):
        return len(self.implemented) + len(self.forwarded)

    def status(self, name):
        if name in self.implemented:
            return "implemented"
        if name in self.forwarded:
            return "forwarded"
        if name in self.stubs:
            return "stub"
        return "absent"


def comments(text):
    for match in TOKEN.finditer(text):
        if match.group("line") is not None or match.group("block") is not None:
            yield match


def strip(text):
    def blank(match):
        if match.group("line") is not None or match.group("block") is not None:
            return re.sub(r"[^\n]", " ", match.group())
        if match.group("raw") is not None or match.group("string") is not None:
            return '""'
        return "' '"
    return TOKEN.sub(blank, text)


def body_end(text, start):
    depth = 0
    for index in range(start, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return index
    raise ValueError("unbalanced braces")


def line_of(text, offset):
    return text.count("\n", 0, offset) + 1


class TreeSource:
    def __init__(self, root=ROOT):
        self.root = Path(root)

    def files(self, prefix):
        base = self.root / prefix
        if not base.exists():
            return []
        return sorted(path.relative_to(self.root).as_posix() for path in base.rglob("*") if path.is_file())

    def read(self, path):
        return (self.root / path).read_text(encoding="utf-8", errors="replace")


def scan_library(source, name):
    library = Library(name)
    prefix = f"{XDLL}/{name}"
    for path in source.files(prefix):
        relative = path[len(prefix) + 1:]
        if relative.startswith("tests/"):
            continue
        if relative == "Imports.txt":
            library.dlls = [line.strip().lower() for line in source.read(path).splitlines() if line.strip()]
        elif relative == "Forwards.def":
            for line in source.read(path).splitlines():
                match = FORWARD.match(line)
                if match:
                    library.forwarded[match.group(1)] = f"{match.group(2)}.{match.group(3)}"
        elif path.endswith(SOURCE_SUFFIXES):
            text = strip(source.read(path))
            for match in DECLARATION.finditer(text):
                library.declarations.setdefault(match.group(1), []).append(f"{path}:{line_of(text, match.start())}")
            for match in DEFINITION.finditer(text):
                function = match.group(1)
                if function.endswith("_nid_no_patch"):
                    continue
                end = body_end(text, match.end() - 1)
                library.definitions.setdefault(function, []).append(f"{path}:{line_of(text, match.start())}")
                if STUB_CALL.search(text, match.end() - 1, end):
                    library.stubs.append(function)
                else:
                    library.implemented.append(function)
    library.implemented = sorted(set(library.implemented) - set(library.stubs))
    library.stubs = sorted(set(library.stubs))
    return library


def library_names(source):
    names = set()
    for path in source.files(XDLL):
        parts = path.split("/")
        if len(parts) >= 5:
            names.add(parts[3])
    return sorted(names)


def scan(source=None, only=None):
    source = source or TreeSource()
    names = library_names(source)
    if only:
        missing = sorted(set(only) - set(names))
        if missing:
            raise SystemExit(f"no library directory for: {', '.join(missing)}")
        names = [name for name in names if name in only]
    return [scan_library(source, name) for name in names]


def match_pattern(pattern, text):
    return re.fullmatch(re.escape(pattern).replace(r"\*", ".*"), text) is not None


def host_patterns(source=None):
    source = source or TreeSource()
    return [line.strip().lower() for line in source.read("core/relinker/HostDlls.txt").splitlines() if line.strip()]


def route(libraries, dll):
    lower = dll.lower()
    for library in libraries:
        if any(match_pattern(pattern, lower) for pattern in library.dlls):
            return library
    return None


def load_records(directory, kind):
    records = []
    for path in sorted(Path(directory).glob("*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        if record.get("format") != kind:
            raise SystemExit(f"{path}: format is not {kind}")
        records.append(record)
    return records


def known_functions(needs_dir=NEEDS_DIR, inventory_dir=INVENTORY_DIR):
    functions = {}
    titles = {}
    for inventory in load_records(inventory_dir, "anybox-inventory"):
        for dll, names in inventory["dlls"].items():
            functions.setdefault(dll.lower(), set()).update(names)
    for title in load_records(needs_dir, "anybox-needs"):
        label = title.get("titleId") or title.get("name") or "unknown"
        for dll, names in title["imports"].items():
            functions.setdefault(dll.lower(), set()).update(names)
            titles.setdefault(dll.lower(), set()).add(label)
    return functions, titles
