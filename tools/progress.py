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
PANEL_WIDTH, PANEL_GAP, MAP_HEIGHT, MAP_HEADER = 495, 10, 280, 30
GRID_COLUMNS, GRID_ROW = 12, 23
MAP_BACKGROUND = "#0d1117"


def percent(done, total):
    return round(100.0 * done / total, 1) if total else 0.0


def plural(count, noun):
    return f"{count} {noun}" if count == 1 else f"{count} {noun}s"


def commit(root=None):
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=root or anybox_scan.ROOT, capture_output=True, text=True, check=True).stdout.strip() or None
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


def aspect(row, side):
    total = sum(row)
    return max(max(side * side * area / (total * total), total * total / (side * side * area)) for area in row)


def lay_row(row, x, y, w, h, out):
    depth = sum(row) / min(w, h)
    offset = 0.0
    for area in row:
        length = area / depth
        out.append((x, y + offset, depth, length) if w >= h else (x + offset, y, length, depth))
        offset += length
    return (x + depth, y, w - depth, h) if w >= h else (x, y + depth, w, h - depth)


def squarify(sizes, x, y, w, h):
    total = sum(sizes)
    pending = [size * w * h / total for size in sizes]
    out, row = [], []
    while pending:
        side = min(w, h)
        if not row or aspect(row + [pending[0]], side) <= aspect(row, side):
            row.append(pending.pop(0))
        else:
            x, y, w, h = lay_row(row, x, y, w, h, out)
            row = []
    if row:
        lay_row(row, x, y, w, h, out)
    return out


def grid_cells(count, x, y, w, h):
    if count <= 0 or w <= 0 or h <= 0:
        return []
    rows = max(1, min(count, round((count * h / w) ** 0.5)))
    out = []
    for line in range(rows):
        across = count // rows + (line < count % rows)
        width = w / across
        out += [(x + column * width, y + line * h / rows, width, h / rows) for column in range(across)]
    return out


def map_tiles(data):
    tiles = []
    for row in data["libraries"]:
        size = row.get("known", row["declared"])
        if size:
            marker = "" if row.get("surfaceKnown", True) else "*"
            tiles.append({"label": row["name"] + marker, "size": size, "unserved": False,
                          "cells": [DONE] * row["implemented"] + [FORWARDED] * row["forwarded"] + [TODO] * row["stub"] + [MISSING] * row.get("missing", 0),
                          "tooltip": f'{row["name"]}: {row["implemented"]} implemented, {row["forwarded"]} forwarded, {row["stub"]} stubs, {row.get("missing", 0)} not declared'})
    for row in data.get("unserved", []):
        if row["missing"]:
            tiles.append({"label": row["dll"], "size": row["missing"], "unserved": True, "cells": [MISSING] * row["missing"],
                          "tooltip": f'{row["dll"]}: no AnyBox library, {row["missing"]} known functions, needed by {row["titles"]} titles'})
    return sorted(tiles, key=lambda tile: (-tile["size"], tile["label"]))


def tile_done(tiles):
    return sum(cell in (DONE, FORWARDED) for tile in tiles for cell in tile["cells"]), sum(tile["size"] for tile in tiles)


def fitting_label(label, w, h):
    room = int((w - 10) / 7)
    if h <= 22 or room < 3:
        return ""
    return label if len(label) <= room else label[:room - 1] + "…"


def readable_panel(tiles, width):
    shown = list(tiles)
    while len(shown) > 1:
        boxes = squarify([tile["size"] for tile in shown], 0, 0, width, MAP_HEIGHT)
        if all(fitting_label(tile["label"], w, h) == tile["label"] for tile, (_, _, w, h) in zip(shown, boxes)):
            break
        shown.pop()
    return shown


def svg_rect(x, y, w, h, fill, stroke=MAP_BACKGROUND, width=0.5, dash=""):
    dashes = f' stroke-dasharray="{dash}"' if dash else ""
    return f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" fill="{fill}" stroke="{stroke}" stroke-width="{width}"{dashes}/>'


def svg_text(x, y, value, size, color="#fff"):
    return (f'<text x="{x:.2f}" y="{y:.2f}" font-family="Verdana,DejaVu Sans,sans-serif" font-size="{size}" fill="{color}" '
            f'stroke="{MAP_BACKGROUND}" stroke-width="3" paint-order="stroke">{escape(value)}</text>')


def draw_tile(tile, x, y, w, h):
    parts = [f'<g><title>{escape(tile["tooltip"])}</title>']
    parts += [svg_rect(*cell, color) for cell, color in zip(grid_cells(len(tile["cells"]), x + 1, y + 1, w - 2, h - 2), tile["cells"])]
    if tile["unserved"]:
        parts.append(svg_rect(x + 1, y + 1, w - 2, h - 2, "none", "#f85149", 2, "5 3"))
    else:
        parts.append(svg_rect(x, y, w, h, "none", MAP_BACKGROUND, 2))
    label = fitting_label(tile["label"], w, h)
    if label:
        parts.append(svg_text(x + 5, y + 16, label, 12))
    return parts + ["</g>"]


def panel_heading(title, tiles, x, y):
    done, total = tile_done(tiles)
    return svg_text(x + 4, y + 21, f"{title}: {percent(done, total)}% ({done}/{total})", 15)


def progress_map(data):
    tiles = map_tiles(data)
    full = 2 * PANEL_WIDTH + PANEL_GAP
    rest, panels = list(tiles), []
    while rest and len(panels) < 2:
        shown = readable_panel(rest, PANEL_WIDTH if len(rest) > 1 else full)
        panels.append(shown)
        rest = rest[len(shown):]
    totals = data["totals"]
    done = totals["implemented"] + totals["forwarded"]
    known = totals.get("known", totals["declared"])
    heading = f'AnyBox libraries*: {totals.get("knownPercent", totals["percent"])}% ({done}/{known})'
    if data.get("unserved"):
        heading += f', {plural(len(data["unserved"]), "DLL")} with no library'
    body = [svg_text(4, 21, heading, 16)]
    x = 6
    for color, label in LEGEND:
        body.append(svg_rect(x, 31, 10, 10, color, "#8b949e", 0.5))
        body.append(svg_text(x + 14, 40, label, 10, "#c9d1d9"))
        x += 14 + 7 * len(label) + 12
    body.append(svg_text(x, 40, "* full export list not known yet", 10, "#c9d1d9"))
    top = MAP_HEADER + 18
    titles = ("Large libraries", "Medium libraries", "Small libraries")
    width_each = full if len(panels) == 1 else PANEL_WIDTH
    for index, shown in enumerate(panels):
        left = index * (PANEL_WIDTH + PANEL_GAP)
        body.append(panel_heading(titles[index] if len(panels) > 1 or rest else "Libraries", shown, left, top))
        for tile, box in zip(shown, squarify([tile["size"] for tile in shown], left, top + MAP_HEADER, width_each, MAP_HEIGHT)):
            body += draw_tile(tile, *box)
    height = top + (MAP_HEADER + MAP_HEIGHT if panels else 0)
    if rest:
        cell_w = full / GRID_COLUMNS
        top = height + 10
        body.append(panel_heading(titles[2], rest, 0, top))
        for index, tile in enumerate(sorted(rest, key=lambda tile: tile["label"].lower())):
            body += draw_tile(tile, index % GRID_COLUMNS * cell_w, top + MAP_HEADER + index // GRID_COLUMNS * GRID_ROW, cell_w, GRID_ROW)
        height = top + MAP_HEADER + -(-len(rest) // GRID_COLUMNS) * GRID_ROW
    height += 6
    return "\n".join([f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {full} {height}" width="{full}" height="{height}">',
                      svg_rect(0, 0, full, height, MAP_BACKGROUND, MAP_BACKGROUND, 0), *body, "</svg>"]) + "\n"


def name_list(names, label, open_up_to=12):
    if not names:
        return ""
    state = " open" if len(names) <= open_up_to else ""
    items = "".join(f"<li><code>{escape(name)}</code></li>" for name in names)
    return f'<details{state}><summary>{len(names)} {escape(label)}</summary><ol class="names">{items}</ol></details>'


def page(data):
    totals = data["totals"]
    rows = []
    for row in sorted(data["libraries"], key=lambda row: row["name"]):
        link = f'{SOURCE}/{anybox_scan.XDLL}/{row["name"]}'
        debt = f'{SOURCE}/docs/dev/debt/{row["name"]}.md'
        lists = name_list(row["stubNames"], "stubs") + name_list(row.get("missingNames", []), "not declared yet")
        missing = row.get("missing", 0)
        known = row.get("known", row["declared"])
        share = row.get("knownPercent", row["percent"])
        missing_cell = str(missing) if row.get("surfaceKnown", True) else f'{missing} <span class="note">(export list not known yet)</span>'
        rows.append(
            f'<tr><td><a href="{link}">{escape(row["name"])}</a></td><td>{escape(", ".join(row["dlls"]))}</td>'
            f'<td>{row["implemented"]}</td><td>{row["forwarded"]}</td><td>{row["stub"]}</td><td>{missing_cell}</td><td>{known}</td>'
            f'<td><div class="bar"><span style="width:{share}%"></span></div>{share}%</td>'
            f'<td><a href="{debt}">debt</a></td><td class="stubs">{lists}</td></tr>')
    unserved = []
    for row in data.get("unserved", []):
        stem = "".join(character if character.isalnum() or character == "_" else "_" for character in row["dll"].rsplit(".", 1)[0])
        unserved.append(
            f'<tr><td>{escape(row["dll"])}</td><td>{row["missing"]}</td><td>{row["titles"]}</td>'
            f'<td><code>python tools/stubgen.py --new-library {escape(stem)} --dll {escape(row["dll"])}</code></td><td class="stubs">{name_list(row["missingNames"], "functions")}</td></tr>')
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
.bar span{{display:block;height:8px;background:{DONE}}} .stubs{{color:#8b949e;font-size:12px;min-width:280px}}
summary{{cursor:pointer;color:#58a6ff}} ol.names{{margin:4px 0 8px;padding-left:2.6em;max-height:420px;overflow-y:auto}}
ol.names li{{line-height:1.6}} ol.names code{{color:#e6edf3;font-size:12px}}
.wrap{{overflow-x:auto}} img{{max-width:100%}} .note{{color:#8b949e;font-size:12px}}
</style></head><body>
<h1>AnyBox progress</h1>
<p>{totals["implemented"]} implemented and {totals["forwarded"]} forwarded of {totals.get("known", totals["declared"])} known functions ({totals.get("knownPercent", totals["percent"])}%):
{totals["declared"]} declared in {totals["libraries"]} libraries ({totals["percent"]}% of those done), {totals.get("missing", 0)} known but not declared yet, and {plural(totals.get("unservedDlls", 0), "DLL")} with no library.</p>
<p>Counted from the source: a function is a stub while its body calls <code>AbxNotImplemented</code>. Known functions come from the export inventories in <code>docs/inventory</code> and the title needs records in <code>docs/needs</code>; a library marked as not known yet has no inventory, so its count grows as titles are audited. A count says nothing about whether a title runs.
Compatibility lives in the <a href="https://github.com/{REPOSITORY}/discussions/categories/game-bring-up">Game bring-up</a> discussions; pick a stub to work on from the table.</p>
<p><img src="progress.svg" alt="progress map"></p>
<div class="wrap"><table><thead><tr><th>Library</th><th>Serves</th><th>Implemented</th><th>Forwarded</th><th>Stubs</th><th>Not declared</th><th>Known</th><th>Done</th><th>Known gaps</th><th>Functions to pick up</th></tr></thead>
<tbody>{"".join(rows)}</tbody></table></div>
{unserved_html}<p><a href="needs.html">What titles still need</a> · <a href="history.html">Progress history</a> · commit {escape(data["commit"] or "unknown")}</p>
</body></html>
"""


def number(value, digits):
    text = f"{value:.{digits}f}".rstrip("0").rstrip(".")
    return "0" if text in ("", "-0") else text


def exact_percent(totals):
    return 100.0 * (totals["implemented"] + totals["forwarded"]) / totals["declared"] if totals["declared"] else 0.0


def names(row, key):
    return set((row or {}).get(key, []))


def done_names(row):
    return names(row, "implementedNames") | names(row, "forwardedNames")


def declared_names(row):
    return done_names(row) | names(row, "stubNames")


def details(summary, entries, limit=100):
    if not entries:
        return []
    lines = ["<details>", f"<summary>{summary}</summary>", "", "| Library | Name |", "| - | - |"]
    lines += [f"| {library} | `{name}` |" for library, name in entries[:limit]]
    if len(entries) > limit:
        lines.append(f"| | and {len(entries) - limit} more |")
    return lines + ["", "</details>"]


def compare(base, head):
    base_rows = {row["name"]: row for row in base["libraries"]}
    head_rows = {row["name"]: row for row in head["libraries"]}
    implemented, forwarded, declared, undone, removed, changed = [], [], [], [], [], []
    for name in sorted(set(base_rows) | set(head_rows)):
        before, after = base_rows.get(name), head_rows.get(name)
        if before and after and all(set(before[key]) == set(after[key]) for key in ("implementedNames", "forwardedNames", "stubNames")):
            continue
        changed.append((name, before, after))
        implemented += [(name, entry) for entry in sorted(names(after, "implementedNames") - names(before, "implementedNames"))]
        forwarded += [(name, entry) for entry in sorted(names(after, "forwardedNames") - names(before, "forwardedNames"))]
        declared += [(name, entry) for entry in sorted(names(after, "stubNames") - declared_names(before))]
        undone += [(name, entry) for entry in sorted(done_names(before) - done_names(after))]
        removed += [(name, entry) for entry in sorted(declared_names(before) - declared_names(after))]
    if not changed:
        return ""
    before_percent, after_percent = exact_percent(base["totals"]), exact_percent(head["totals"])
    delta = after_percent - before_percent
    trend = "📈" if delta > 0 else "📉" if delta < 0 else "➖"
    values = [(label, value) for label, value in (("implemented", len(implemented)), ("forwarded", len(forwarded)), ("no longer done", -len(undone)),
                                                 ("declared", head["totals"]["declared"] - base["totals"]["declared"])) if value]
    counts = [f"{value:+d} {label}" for label, value in values]
    if counts:
        counts[-1] += " function" if abs(values[-1][1]) == 1 else " functions"
    sign = "+" if delta > 0 else ""
    headline = f"{trend} **Libraries**: {number(after_percent, 2)}% ({sign}{number(delta, 4)}%" + (", " + ", ".join(counts) if counts else "") + ")"
    lines = [headline, ""]
    if undone:
        lines += [f"⚠️ **{plural(len(undone), 'function')} no longer done**: " + ", ".join(f"`{library}!{name}`" for library, name in undone[:20]), ""]
    lines += details(f"✅ {len(implemented)} implemented", implemented)
    lines += details(f"➡️ {len(forwarded)} forwarded to Windows", forwarded)
    lines += details(f"🆕 {len(declared)} declared as stubs", declared)
    lines += details(f"🗑️ {len(removed)} removed", removed)
    lines += ["", "#### Changed libraries", "", "| Library | Before | After | Change |", "| - | - | - | - |"]
    for name, before, after in changed:
        def cell(row):
            if not row:
                return "Not present"
            return f'{row["implemented"] + row["forwarded"]}/{row["declared"]} ({number(exact_percent(row), 2)}%)'
        change = f"{exact_percent(after) - exact_percent(before):+.2f}%" if before and after else "n/a"
        lines.append(f"| {name} | {cell(before)} | {cell(after)} | {change} |")
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
    parser.add_argument("--compare", nargs=2, type=Path, metavar=("BASE", "HEAD"), help="print a Markdown comparison of two progress.json files; nothing when no library changed")
    parser.add_argument("--root", type=Path, help="count another checkout, such as a pull request's base, with this version of the tool")
    args = parser.parse_args()

    if args.compare:
        base, head = (json.loads(path.read_text(encoding="utf-8")) for path in args.compare)
        sys.stdout.flush()
        sys.stdout.buffer.write(compare(base, head).encode("utf-8"))
        sys.stdout.buffer.flush()
        return
    root = args.root.resolve() if args.root else anybox_scan.ROOT
    source = anybox_scan.TreeSource(root)
    known, titles = anybox_scan.known_functions(root / "docs" / "needs", root / "docs" / "inventory")
    libraries = anybox_scan.scan(source, only=args.module)
    if args.module:
        known = {dll: functions for dll, functions in known.items() if anybox_scan.route(libraries, dll)}
    data = snapshot(libraries, commit(root), known, titles, anybox_scan.host_patterns(source))
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
