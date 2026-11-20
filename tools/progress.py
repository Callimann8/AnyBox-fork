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
DONE, FORWARDED, TODO = "#2ea043", "#1f6feb", "#6e7681"
MAP_COLUMNS, TILE_W, TILE_H, GAP = 6, 160, 54, 6


def percent(done, total):
    return round(100.0 * done / total, 1) if total else 0.0


def commit():
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=anybox_scan.ROOT, capture_output=True, text=True, check=True).stdout.strip() or None
    except (OSError, subprocess.CalledProcessError):
        return None


def snapshot(libraries, head=None):
    rows = []
    for library in libraries:
        rows.append({
            "name": library.name,
            "dlls": library.dlls,
            "declared": library.declared,
            "implemented": len(library.implemented),
            "forwarded": len(library.forwarded),
            "stub": len(library.stubs),
            "percent": percent(library.done, library.declared),
            "implementedNames": library.implemented,
            "forwardedNames": sorted(library.forwarded),
            "stubNames": library.stubs,
        })
    declared = sum(row["declared"] for row in rows)
    implemented = sum(row["implemented"] for row in rows)
    forwarded = sum(row["forwarded"] for row in rows)
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
        },
        "libraries": rows,
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
    rows = sorted(data["libraries"], key=lambda row: (-row["declared"], row["name"]))
    count = max(len(rows), 1)
    columns = min(MAP_COLUMNS, count)
    lines = (count + columns - 1) // columns
    width = columns * (TILE_W + GAP) + GAP
    height = lines * (TILE_H + GAP) + GAP + 24
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" font-family="Verdana,DejaVu Sans,sans-serif">',
             f'<rect width="{width}" height="{height}" fill="#0d1117"/>',
             f'<text x="{GAP}" y="17" fill="#fff" font-size="13">AnyBox libraries: {data["totals"]["implemented"] + data["totals"]["forwarded"]}/{data["totals"]["declared"]} functions ({data["totals"]["percent"]}%)</text>']
    for index, row in enumerate(rows):
        x = GAP + (index % columns) * (TILE_W + GAP)
        y = 24 + GAP + (index // columns) * (TILE_H + GAP)
        total = max(row["declared"], 1)
        implemented_w = TILE_W * row["implemented"] / total
        forwarded_w = TILE_W * row["forwarded"] / total
        parts.append(f'<g><title>{escape(row["name"])}: {row["implemented"]} implemented, {row["forwarded"]} forwarded, {row["stub"]} stubs</title>')
        parts.append(f'<rect x="{x}" y="{y}" width="{TILE_W}" height="{TILE_H}" fill="{TODO}"/>')
        parts.append(f'<rect x="{x}" y="{y}" width="{implemented_w:.1f}" height="{TILE_H}" fill="{DONE}"/>')
        parts.append(f'<rect x="{x + implemented_w:.1f}" y="{y}" width="{forwarded_w:.1f}" height="{TILE_H}" fill="{FORWARDED}"/>')
        parts.append(f'<text x="{x + 6}" y="{y + 20}" fill="#fff" font-size="12">{escape(row["name"])}</text>')
        parts.append(f'<text x="{x + 6}" y="{y + 40}" fill="#fff" font-size="11">{row["percent"]}% of {row["declared"]}</text></g>')
    parts.append("</svg>\n")
    return "\n".join(parts)


def page(data):
    totals = data["totals"]
    rows = []
    for row in sorted(data["libraries"], key=lambda row: row["name"]):
        link = f'{SOURCE}/{anybox_scan.XDLL}/{row["name"]}'
        debt = f'{SOURCE}/docs/dev/debt/{row["name"]}.md'
        stubs = ", ".join(row["stubNames"][:40]) + (" ..." if len(row["stubNames"]) > 40 else "")
        rows.append(
            f'<tr><td><a href="{link}">{escape(row["name"])}</a></td><td>{escape(", ".join(row["dlls"]))}</td>'
            f'<td>{row["implemented"]}</td><td>{row["forwarded"]}</td><td>{row["stub"]}</td><td>{row["declared"]}</td>'
            f'<td><div class="bar"><span style="width:{row["percent"]}%"></span></div>{row["percent"]}%</td>'
            f'<td><a href="{debt}">debt</a></td><td class="stubs">{escape(stubs)}</td></tr>')
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>AnyBox progress</title>
<style>
body{{font-family:system-ui,sans-serif;background:#0d1117;color:#e6edf3;margin:0;padding:16px}}
a{{color:#58a6ff}} table{{border-collapse:collapse;width:100%;font-size:14px}}
th,td{{border-bottom:1px solid #30363d;padding:6px;text-align:left;vertical-align:top}}
.bar{{display:inline-block;width:90px;height:8px;background:{TODO};margin-right:6px}}
.bar span{{display:block;height:8px;background:{DONE}}} .stubs{{color:#8b949e;font-size:12px}}
.wrap{{overflow-x:auto}} img{{max-width:100%}}
</style></head><body>
<h1>AnyBox progress</h1>
<p>{totals["implemented"]} implemented and {totals["forwarded"]} forwarded of {totals["declared"]} declared functions in {totals["libraries"]} libraries ({totals["percent"]}%).
Counted from the source: a function is a stub while its body calls <code>AbxNotImplemented</code>. Declared functions are the ones the project knows about so far, not every console export, and a count says nothing about whether a title runs.
Compatibility lives in the <a href="https://github.com/{REPOSITORY}/discussions/categories/game-bring-up">Game bring-up</a> discussions; pick a stub to work on from the table.</p>
<p><img src="progress.svg" alt="progress map"></p>
<div class="wrap"><table><thead><tr><th>Library</th><th>Serves</th><th>Implemented</th><th>Forwarded</th><th>Stubs</th><th>Declared</th><th>Done</th><th>Known gaps</th><th>Stubs to pick up</th></tr></thead>
<tbody>{"".join(rows)}</tbody></table></div>
<p><a href="history.html">Progress history</a> · commit {escape(data["commit"] or "unknown")}</p>
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
    data = snapshot(anybox_scan.scan(only=args.module), commit())
    if args.json:
        print(json.dumps(data, indent=1))
    elif args.output is None and not args.module:
        parser.error("give an output directory, --json or --module")
    if args.output:
        write(args.output, data)
    if not args.json:
        totals = data["totals"]
        print(f'Library functions: {totals["implemented"]} implemented + {totals["forwarded"]} forwarded of {totals["declared"]} ({totals["percent"]}%)')
        for row in data["libraries"]:
            print(f'  {row["name"]:<16} {row["implemented"]:>4} impl {row["forwarded"]:>4} fwd {row["stub"]:>4} stub  {row["percent"]:>5}%')


if __name__ == "__main__":
    main()
