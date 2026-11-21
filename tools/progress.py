import argparse
import json
import os
import subprocess
import sys
from html import escape
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import anybox_scan

REPOSITORY = os.environ.get("GITHUB_REPOSITORY", "Dark3581/AnyBox")
SOURCE = f"https://github.com/{REPOSITORY}/blob/main"
DONE, FORWARDED, TODO, MISSING = "#2ea043", "#1f6feb", "#6e7681", "#21262d"
LEGEND = ((DONE, "implemented"), (FORWARDED, "forwarded"), (TODO, "stub"), (MISSING, "not declared"))
MAP_COLUMNS, TILE_W, TILE_H, GAP = 6, 160, 54, 6


def percent(done, total):
    return round(100.0 * done / total, 1) if total else 0.0


def plural(count, noun):
    return f"{count} {noun}" if count == 1 else f"{count} {noun}s"


def commit():
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=anybox_scan.ROOT, capture_output=True, text=True, check=True).stdout.strip() or None
    except (OSError, subprocess.CalledProcessError):
        return None


def snapshot(libraries, head=None, known=None, titles=None, hosts=()):
    known = known or {}
    titles = titles or {}
    served = {library.name: set() for library in libraries}
    unserved = {}
    for dll, functions in known.items():
        library = anybox_scan.route(libraries, dll)
        if library:
            served[library.name].update(functions)
        elif not any(anybox_scan.match_pattern(pattern, dll) for pattern in hosts):
            unserved[dll] = functions
    rows = []
    for library in libraries:
        missing = sorted(function for function in served[library.name] if library.status(function) == "absent")
        rows.append({
            "name": library.name,
            "dlls": library.dlls,
            "declared": library.declared,
            "implemented": len(library.implemented),
            "forwarded": len(library.forwarded),
            "stub": len(library.stubs),
            "missing": len(missing),
            "known": library.declared + len(missing),
            "surfaceKnown": bool(served[library.name]),
            "percent": percent(library.done, library.declared),
            "knownPercent": percent(library.done, library.declared + len(missing)),
            "implementedNames": library.implemented,
            "forwardedNames": sorted(library.forwarded),
            "stubNames": library.stubs,
            "missingNames": missing,
        })
    unserved_rows = [{"dll": dll, "missing": len(functions), "titles": len(titles.get(dll, ())), "missingNames": sorted(functions)}
                     for dll, functions in sorted(unserved.items(), key=lambda item: (-len(titles.get(item[0], ())), -len(item[1]), item[0]))]
    declared = sum(row["declared"] for row in rows)
    implemented = sum(row["implemented"] for row in rows)
    forwarded = sum(row["forwarded"] for row in rows)
    missing = sum(row["missing"] for row in rows) + sum(row["missing"] for row in unserved_rows)
    return {
        "format": "anybox-progress",
        "version": 1,
        "commit": head,
        "totals": {
            "libraries": len(rows),
            "declared": declared,
            "implemented": implemented,
            "forwarded": forwarded,
            "stub": declared - implemented - forwarded,
            "percent": percent(implemented + forwarded, declared),
            "missing": missing,
            "known": declared + missing,
            "knownPercent": percent(implemented + forwarded, declared + missing),
            "unservedDlls": len(unserved_rows),
        },
        "libraries": rows,
        "unserved": unserved_rows,
    }


def badge(label, value, color):
    left = 6 * len(label) + 12
    right = 6 * len(value) + 12
    width = left + right
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="20" role="img" aria-label="{escape(label)}: {escape(value)}">'
        f'<rect width="{left}" height="20" fill="#555"/><rect x="{left}" width="{right}" height="20" fill="{color}"/>'
        f'<g fill="#fff" font-family="Verdana,DejaVu Sans,sans-serif" font-size="11">'
        f'<text x="{left / 2}" y="14" text-anchor="middle">{escape(label)}</text>'
        f'<text x="{left + right / 2}" y="14" text-anchor="middle">{escape(value)}</text></g></svg>\n'
    )


def progress_map(data):
    rows = sorted(data["libraries"], key=lambda row: (-row.get("known", row["declared"]), row["name"]))
    unserved = data.get("unserved", [])
    count = max(len(rows) + len(unserved), 1)
    columns = min(MAP_COLUMNS, count)
    lines = (count + columns - 1) // columns
    width = max(columns * (TILE_W + GAP) + GAP, 620)
    top = 46
    height = lines * (TILE_H + GAP) + GAP + top
    totals = data["totals"]
    done = totals["implemented"] + totals["forwarded"]
    heading = f'AnyBox libraries: {done}/{totals.get("known", totals["declared"])} known functions done ({totals.get("knownPercent", totals["percent"])}%)'
    if unserved:
        heading += f', {plural(len(unserved), "DLL")} with no library'
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" font-family="Verdana,DejaVu Sans,sans-serif">',
             f'<rect width="{width}" height="{height}" fill="#0d1117"/>',
             f'<text x="{GAP}" y="17" fill="#fff" font-size="13">{escape(heading)}</text>']
    x = GAP
    for color, label in LEGEND:
        parts.append(f'<rect x="{x}" y="27" width="10" height="10" fill="{color}" stroke="#8b949e" stroke-width="0.5"/>')
        parts.append(f'<text x="{x + 14}" y="36" fill="#8b949e" font-size="10">{label}</text>')
        x += 14 + 7 * len(label) + 12
    parts.append(f'<text x="{x}" y="36" fill="#8b949e" font-size="10">* full export list not known yet</text>')
    for index, row in enumerate(rows):
        x = GAP + (index % columns) * (TILE_W + GAP)
        y = top + GAP + (index // columns) * (TILE_H + GAP)
        known = row.get("known", row["declared"])
        total = max(known, 1)
        offset = x
        tooltip = f'{row["name"]}: {row["implemented"]} implemented, {row["forwarded"]} forwarded, {row["stub"]} stubs, {row.get("missing", 0)} not declared'
        parts.append(f'<g><title>{escape(tooltip)}</title>')
        parts.append(f'<rect x="{x}" y="{y}" width="{TILE_W}" height="{TILE_H}" fill="{MISSING}" stroke="#30363d"/>')
        for color, value in ((DONE, row["implemented"]), (FORWARDED, row["forwarded"]), (TODO, row["stub"])):
            segment = TILE_W * value / total
            parts.append(f'<rect x="{offset:.1f}" y="{y}" width="{segment:.1f}" height="{TILE_H}" fill="{color}"/>')
            offset += segment
        marker = "" if row.get("surfaceKnown", True) else " *"
        parts.append(f'<text x="{x + 6}" y="{y + 20}" fill="#fff" font-size="12">{escape(row["name"])}{marker}</text>')
        parts.append(f'<text x="{x + 6}" y="{y + 40}" fill="#fff" font-size="11">{row["implemented"] + row["forwarded"]}/{known} done</text></g>')
    for index, row in enumerate(unserved, start=len(rows)):
        x = GAP + (index % columns) * (TILE_W + GAP)
        y = top + GAP + (index // columns) * (TILE_H + GAP)
        name = row["dll"] if len(row["dll"]) <= 22 else row["dll"][:21] + "…"
        tooltip = f'{row["dll"]}: no AnyBox library, {row["missing"]} known functions, needed by {row["titles"]} titles'
        parts.append(f'<g><title>{escape(tooltip)}</title>')
        parts.append(f'<rect x="{x + 0.5}" y="{y + 0.5}" width="{TILE_W - 1}" height="{TILE_H - 1}" fill="{MISSING}" stroke="#f85149" stroke-dasharray="4 3"/>')
        parts.append(f'<text x="{x + 6}" y="{y + 20}" fill="#fff" font-size="12">{escape(name)}</text>')
        parts.append(f'<text x="{x + 6}" y="{y + 40}" fill="#f85149" font-size="11">no library, 0/{row["missing"]}</text></g>')
    parts.append("</svg>\n")
    return "\n".join(parts)


def page(data):
    totals = data["totals"]
    rows = []
    for row in sorted(data["libraries"], key=lambda row: row["name"]):
        link = f'{SOURCE}/{anybox_scan.XDLL}/{row["name"]}'
        debt = f'{SOURCE}/docs/dev/debt/{row["name"]}.md'
        stubs = ", ".join(row["stubNames"][:40]) + (" ..." if len(row["stubNames"]) > 40 else "")
        missing = row.get("missing", 0)
        known = row.get("known", row["declared"])
        share = row.get("knownPercent", row["percent"])
        missing_cell = str(missing) if row.get("surfaceKnown", True) else f'{missing} <span class="note">(export list not known yet)</span>'
        rows.append(
            f'<tr><td><a href="{link}">{escape(row["name"])}</a></td><td>{escape(", ".join(row["dlls"]))}</td>'
            f'<td>{row["implemented"]}</td><td>{row["forwarded"]}</td><td>{row["stub"]}</td><td>{missing_cell}</td><td>{known}</td>'
            f'<td><div class="bar"><span style="width:{share}%"></span></div>{share}%</td>'
            f'<td><a href="{debt}">debt</a></td><td class="stubs">{escape(stubs)}</td></tr>')
    unserved = []
    for row in data.get("unserved", []):
        names = ", ".join(row["missingNames"][:40]) + (" ..." if len(row["missingNames"]) > 40 else "")
        stem = "".join(character if character.isalnum() or character == "_" else "_" for character in row["dll"].rsplit(".", 1)[0])
        unserved.append(
            f'<tr><td>{escape(row["dll"])}</td><td>{row["missing"]}</td><td>{row["titles"]}</td>'
            f'<td><code>python tools/stubgen.py --new-library {escape(stem)} --dll {escape(row["dll"])}</code></td><td class="stubs">{escape(names)}</td></tr>')
    unserved_html = (
        '<h2>DLLs with no AnyBox library</h2>\n<p>Known from title needs records or export inventories, but nothing serves them yet. A title that imports one cannot be converted.</p>\n'
        '<div class="wrap"><table><thead><tr><th>DLL</th><th>Known functions</th><th>Titles</th><th>Start it with</th><th>Functions</th></tr></thead>\n'
        f'<tbody>{"".join(unserved)}</tbody></table></div>\n') if unserved else \
        '<h2>DLLs with no AnyBox library</h2>\n<p>None known. Title needs records add any DLL a title imports that no library serves.</p>\n'
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>AnyBox progress</title>
<style>
body{{font-family:system-ui,sans-serif;background:#0d1117;color:#e6edf3;margin:0;padding:16px}}
a{{color:#58a6ff}} table{{border-collapse:collapse;width:100%;font-size:14px}}
th,td{{border-bottom:1px solid #30363d;padding:6px;text-align:left;vertical-align:top}}
.bar{{display:inline-block;width:90px;height:8px;background:{TODO};margin-right:6px}}
.bar span{{display:block;height:8px;background:{DONE}}} .stubs{{color:#8b949e;font-size:12px}}
.wrap{{overflow-x:auto}} img{{max-width:100%}} .note{{color:#8b949e;font-size:12px}}
</style></head><body>
<h1>AnyBox progress</h1>
<p>{totals["implemented"]} implemented and {totals["forwarded"]} forwarded of {totals.get("known", totals["declared"])} known functions ({totals.get("knownPercent", totals["percent"])}%):
{totals["declared"]} declared in {totals["libraries"]} libraries ({totals["percent"]}% of those done), {totals.get("missing", 0)} known but not declared yet, and {plural(totals.get("unservedDlls", 0), "DLL")} with no library.</p>
<p>Counted from the source: a function is a stub while its body calls <code>AbxNotImplemented</code>. Known functions come from the export inventories in <code>docs/inventory</code> and the title needs records in <code>docs/needs</code>; a library marked as not known yet has no inventory, so its count grows as titles are audited. A count says nothing about whether a title runs.
Compatibility lives in the <a href="https://github.com/{REPOSITORY}/discussions/categories/game-bring-up">Game bring-up</a> discussions; pick a stub to work on from the table.</p>
<p><img src="progress.svg" alt="progress map"></p>
<div class="wrap"><table><thead><tr><th>Library</th><th>Serves</th><th>Implemented</th><th>Forwarded</th><th>Stubs</th><th>Not declared</th><th>Known</th><th>Done</th><th>Known gaps</th><th>Stubs to pick up</th></tr></thead>
<tbody>{"".join(rows)}</tbody></table></div>
{unserved_html}<p><a href="needs.html">What titles still need</a> · <a href="history.html">Progress history</a> · commit {escape(data["commit"] or "unknown")}</p>
</body></html>
"""


def compare(base, head):
    base_rows = {row["name"]: row for row in base["libraries"]}
    head_rows = {row["name"]: row for row in head["libraries"]}
    lines = [
        f'**Library functions:** {base["totals"]["implemented"] + base["totals"]["forwarded"]}/{base["totals"]["declared"]} ({base["totals"]["percent"]}%)'
        f' → {head["totals"]["implemented"] + head["totals"]["forwarded"]}/{head["totals"]["declared"]} ({head["totals"]["percent"]}%)',
        "",
    ]
    changed = []
    for name in sorted(set(base_rows) | set(head_rows)):
        before, after = base_rows.get(name), head_rows.get(name)
        if before and after and all(before[key] == after[key] for key in ("implementedNames", "forwardedNames", "stubNames")):
            continue
        changed.append((name, before, after))
    if not changed:
        lines.append("No library changes.")
        return "\n".join(lines) + "\n"
    lines += ["| Library | Before | After | Change |", "|---|---|---|---|"]
    for name, before, after in changed:
        cell = lambda row: f'{row["implemented"] + row["forwarded"]}/{row["declared"]} ({row["percent"]}%)' if row else "Not present"
        delta = f'{after["percent"] - before["percent"]:+.1f}%' if before and after else "n/a"
        lines.append(f"| {name} | {cell(before)} | {cell(after)} | {delta} |")
    lines.append("")
    for name, before, after in changed:
        before_done = set((before or {}).get("implementedNames", [])) | set((before or {}).get("forwardedNames", []))
        after_done = set((after or {}).get("implementedNames", [])) | set((after or {}).get("forwardedNames", []))
        added, removed = sorted(after_done - before_done), sorted(before_done - after_done)
        if added:
            lines.append(f"- {name}: newly done {', '.join(added)}")
        if removed:
            lines.append(f"- {name}: **no longer done** {', '.join(removed)}")
    return "\n".join(lines) + "\n"


def write(directory, data):
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "progress.json").write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8")
    (directory / "progress.svg").write_text(progress_map(data), encoding="utf-8")
    (directory / "progress.html").write_text(page(data), encoding="utf-8")
    value = f'{data["totals"]["percent"]}%'
    (directory / "badge-libraries.svg").write_text(badge("libraries", value, DONE if data["totals"]["percent"] >= 50 else "#d29922"), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Count implemented, forwarded and stubbed AnyBox library functions.")
    parser.add_argument("output", nargs="?", type=Path, help="directory for progress.json, progress.html, progress.svg and the badge")
    parser.add_argument("--module", action="append", help="limit the totals to this library; repeatable")
    parser.add_argument("--json", action="store_true", help="print progress.json to stdout")
    parser.add_argument("--compare", nargs=2, type=Path, metavar=("BASE", "HEAD"), help="print a Markdown comparison of two progress.json files")
    args = parser.parse_args()

    if args.compare:
        base, head = (json.loads(path.read_text(encoding="utf-8")) for path in args.compare)
        sys.stdout.write(compare(base, head))
        return
    known, titles = anybox_scan.known_functions()
    libraries = anybox_scan.scan(only=args.module)
    if args.module:
        known = {dll: functions for dll, functions in known.items() if anybox_scan.route(libraries, dll)}
    data = snapshot(libraries, commit(), known, titles, anybox_scan.host_patterns())
    if args.json:
        print(json.dumps(data, indent=1))
    elif args.output is None and not args.module:
        parser.error("give an output directory, --json or --module")
    if args.output:
        write(args.output, data)
    if not args.json:
        totals = data["totals"]
        print(f'Library functions: {totals["implemented"]} implemented + {totals["forwarded"]} forwarded of {totals["declared"]} declared ({totals["percent"]}%), {totals["known"]} known ({totals["knownPercent"]}%)')
        for row in data["libraries"]:
            unknown = "" if row["surfaceKnown"] else "  export list not known yet"
            print(f'  {row["name"]:<16} {row["implemented"]:>4} impl {row["forwarded"]:>4} fwd {row["stub"]:>4} stub {row["missing"]:>4} not declared  {row["knownPercent"]:>5}%{unknown}')
        for row in data["unserved"]:
            print(f'  {row["dll"]:<16} no library, {row["missing"]} known functions, {row["titles"]} titles')


if __name__ == "__main__":
    main()
