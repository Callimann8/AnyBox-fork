import argparse
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import anybox_scan
import debt_fold

ROOT = anybox_scan.ROOT
COMMIT = re.compile(r"^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\([\w./-]+\))?!?: \S.*$")
ALLOWED_COMMENT_LINE = re.compile(r"^\s*(#\s*endif\b|}\s*(//|/\*)\s*namespace\b)")
LICENCE = re.compile(r"Copyright|SPDX-License-Identifier")
TEXT_SUFFIXES = {".cpp", ".hpp", ".h", ".c", ".inl", ".py", ".md", ".txt", ".json", ".yml", ".yaml", ".cmake", ".def", ".html", ".mjs", ".css", ".toml"}
SKIP_DIRS = {".git", "build", "build-relinker", "3rdparty", "__pycache__", "node_modules"}


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")


def project_files(root=ROOT):
    listed = git("ls-files", "--cached", "--others", "--exclude-standard") if root == ROOT else None
    if listed is not None and listed.returncode == 0 and listed.stdout.strip():
        return sorted(root / line for line in listed.stdout.splitlines() if (root / line).is_file())
    files = []
    for path in root.rglob("*"):
        if path.is_file() and not (set(path.relative_to(root).parts) & SKIP_DIRS):
            files.append(path)
    return sorted(files)


def check_comments(path, text):
    errors = []
    lines = text.splitlines()
    for match in anybox_scan.comments(text):
        line = anybox_scan.line_of(text, match.start())
        if ALLOWED_COMMENT_LINE.match(lines[line - 1]):
            continue
        if match.start() == len(text) - len(text.lstrip()) and LICENCE.search(match.group()):
            continue
        errors.append(f"{path}:{line}: comment in code; record known gaps in docs/dev/debt instead")
    return errors


def check_text(path):
    try:
        return path.read_bytes().decode("utf-8"), []
    except UnicodeDecodeError as error:
        return None, [f"{path}: not UTF-8 ({error.reason} at byte {error.start})"]


def check_libraries(root=ROOT):
    errors = []
    source = anybox_scan.TreeSource(root)
    claimed = {}
    for name in anybox_scan.library_names(source):
        library = anybox_scan.scan_library(source, name)
        base = f"{anybox_scan.XDLL}/{name}"
        if not (root / base / "Imports.txt").exists() or not library.dlls:
            errors.append(f"{base}: Imports.txt is missing or empty; list the DLL names this library serves")
        if not (root / base / f"{name}.hpp").exists():
            errors.append(f"{base}: {name}.hpp is missing; it must include every header that declares an export")
        if not re.fullmatch(r"[a-z0-9_]+", name):
            errors.append(f"{base}: library directory names are lowercase letters, digits and underscores")
        for pattern in library.dlls:
            if pattern in claimed and claimed[pattern] != name:
                errors.append(f"{base}/Imports.txt: {pattern} is already served by {claimed[pattern]}")
            claimed[pattern] = name
        for function, places in sorted(library.definitions.items()):
            if len(places) > 1:
                errors.append(f"{places[1]}: {function} is defined {len(places)} times")
            declarations = library.declarations.get(function, [])
            in_headers = [place for place in declarations if place.split(":")[0].endswith((".hpp", ".h"))]
            in_sources = [place for place in declarations if place not in in_headers]
            if len(in_headers) != 1:
                errors.append(f"{places[0]}: {function} needs exactly one declaration in a header under {base}/include, found {len(in_headers)}")
            for place in in_sources:
                errors.append(f"{place}: {function} is declared in a source file; declare it once in a header")
            if function in library.forwarded:
                errors.append(f"{places[0]}: {function} is both defined and forwarded in Forwards.def")
        for function, places in sorted(library.declarations.items()):
            if function not in library.definitions:
                errors.append(f"{places[0]}: {function} is declared but never defined")
    return errors


def check_commits(base):
    if base is None:
        for candidate in ("upstream/main", "origin/main", "main"):
            if git("rev-parse", "--verify", "--quiet", candidate).returncode == 0:
                base = candidate
                break
    if base is None:
        return []
    log = git("log", "--format=%H %s", f"{base}..HEAD")
    if log.returncode != 0:
        return [f"cannot list commits since {base}: {log.stderr.strip()}"]
    errors = []
    for line in log.stdout.splitlines():
        commit, _, subject = line.partition(" ")
        if subject.startswith("Merge "):
            continue
        if not COMMIT.match(subject):
            errors.append(f"commit {commit[:10]}: subject {subject!r} is not a Conventional Commit (type(scope): summary)")
    return errors


def run(root=ROOT, base=None, commits=True):
    errors = []
    for path in project_files(root):
        relative = path.relative_to(root).as_posix()
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        text, problems = check_text(path)
        errors += problems
        if text is not None and relative.startswith("core/") and path.suffix in anybox_scan.SOURCE_SUFFIXES:
            errors += check_comments(relative, text)
    errors += check_libraries(root)
    if root == ROOT:
        try:
            debt_fold.fold(debt_fold.fragments())
        except debt_fold.FoldError as error:
            errors.append(f"debt fragment: {error}")
        if commits:
            errors += check_commits(base)
    return errors


def main():
    parser = argparse.ArgumentParser(description="Check the AnyBox contribution rules.")
    parser.add_argument("--base", help="base ref for the commit subject check (default upstream/main, origin/main or main)")
    parser.add_argument("--no-commits", action="store_true", help="skip the commit subject check")
    args = parser.parse_args()
    errors = run(base=args.base, commits=not args.no_commits)
    for error in errors:
        print(error)
    print("conventions: ok" if not errors else f"conventions: {len(errors)} problem(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
