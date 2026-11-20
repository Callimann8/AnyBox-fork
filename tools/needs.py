import argparse
import json
import sys
from html import escape
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import anybox_scan
import progress

ROOT = anybox_scan.ROOT
NEEDS_DIR = ROOT / "docs" / "needs"
INVENTORY_DIR = ROOT / "docs" / "inventory"
DONE = ("implemented", "forwarded")
ORDER = {"unrouted": 0, "absent": 1, "stub": 2, "implemented": 3, "forwarded": 3}


def load(directory, kind):
    records = []
    for path in sorted(directory.glob("*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        if record.get("format") != kind:
            raise SystemExit(f"{path}: format is not {kind}")
        records.append(record)
    return records


def build(titles, inventories, libraries, hosts):
    needed = {}
    for title in titles:
        label = title.get("titleId") or title.get("name") or "unknown"
        for dll, functions in title["imports"].items():
            for function in functions:
                needed.setdefault((dll.lower(), function), set()).add(label)
    exported = set()
    for inventory in inventories:
        for dll, functions in inventory["dlls"].items():
            exported.update((dll.lower(), function) for function in functions)

    rows = []
    for dll, function in sorted(set(needed) | exported):
        if any(anybox_scan.match_pattern(pattern, dll) for pattern in hosts) and anybox_scan.route(libraries, dll) is None:
            continue
        library = anybox_scan.route(libraries, dll)
        rows.append({
            "dll": dll,
            "function": function,
            "library": library.name if library else None,
            "status": library.status(function) if library else "unrouted",
            "titles": sorted(needed.get((dll, function), ())),
            "inInventory": (dll, function) in exported,
        })
    rows.sort(key=lambda row: (row["status"] in DONE, -len(row["titles"]), ORDER[row["status"]], row["dll"], row["function"]))

    dlls = {}
    for row in rows:
        entry = dlls.setdefault(row["dll"], {"dll": row["dll"], "library": row["library"], "known": 0, "needed": 0, "declared": 0, "done": 0, "neededDone": 0})
        entry["known"] += 1
        entry["needed"] += bool(row["titles"])
        entry["declared"] += row["status"] not in ("absent", "unrouted")
        entry["done"] += row["status"] in DONE
        entry["neededDone"] += bool(row["titles"]) and row["status"] in DONE

    summaries = []
    for title in titles:
        label = title.get("titleId") or title.get("name") or "unknown"
        mine = [row for row in rows if label in row["titles"]]
        blockers = [f"{row['dll']}!{row['function']}" for row in mine if row["status"] not in DONE]
        summaries.append({"titleId": title.get("titleId"), "name": title.get("name"), "version": title.get("version"),
                          "needed": len(mine), "done": len(mine) - len(blockers), "percent": progress.percent(len(mine) - len(blockers), len(mine)),
                          "blockers": blockers[:20]})
    summaries.sort(key=lambda summary: (-summary["percent"], summary["titleId"] or ""))
    return {"format": "anybox-needs-report", "version": 1, "titles": summaries,
            "dlls": sorted(dlls.values(), key=lambda entry: (-(entry["needed"] - entry["neededDone"]), entry["dll"])), "rows": rows}


def markdown(report, limit):
    lines = ["## Most needed, not done", "", "| Function | DLL | Library | Status | Titles |", "|---|---|---|---|---|"]
    for row in [row for row in report["rows"] if row["status"] not in DONE][:limit]:
        lines.append(f"| `{row['function']}` | {row['dll']} | {row['library'] or 'none'} | {row['status']} | {len(row['titles'])} |")
    lines += ["", "## DLLs", "", "| DLL | Library | Needed by titles | Done of needed | Known exports | Declared | Done |", "|---|---|---|---|---|---|---|"]
    for entry in report["dlls"]:
        lines.append(f"| {entry['dll']} | {entry['library'] or 'none'} | {entry['needed']} | {entry['neededDone']} | {entry['known']} | {entry['declared']} | {entry['done']} |")
    lines += ["", "## Titles", "", "| Title | Needed | Done | Next blockers |", "|---|---|---|---|"]
    for title in report["titles"]:
        name = f"{title['name'] or 'Unknown'} ({title['titleId'] or '?'})"
        lines.append(f"| {name} | {title['needed']} | {title['done']} ({title['percent']}%) | {', '.join(title['blockers'][:5]) or 'none'} |")
    return "\n".join(lines) + "\n"


def page(report):
    def table(headers, rows):
        head = "".join(f"<th>{escape(header)}</th>" for header in headers)
        body = "".join("<tr>" + "".join(f"<td>{escape(str(cell))}</td>" for cell in row) + "</tr>" for row in rows)
        return f'<div class="wrap"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'

    todo = [row for row in report["rows"] if row["status"] not in DONE]
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>AnyBox needs</title>
<style>body{{font-family:system-ui,sans-serif;background:#0d1117;color:#e6edf3;padding:16px}}a{{color:#58a6ff}}table{{border-collapse:collapse;width:100%;font-size:14px}}
th,td{{border-bottom:1px solid #30363d;padding:5px;text-align:left}}.wrap{{overflow-x:auto}}</style></head><body>
<h1>What AnyBox still needs</h1>
<p>Built by <code>tools/needs.py</code> from the title needs records in <code>docs/needs</code> (written by <code>import_audit.py --needs</code>) and the export inventories in <code>docs/inventory</code> (written by <code>lib_inventory.py</code>).
{len(report["titles"])} titles, {len(report["rows"])} known functions, {len(todo)} not done. Work from the top of the first table: it is sorted by how many titles need each function.</p>
<h2>Most needed, not done</h2>
{table(["Function", "DLL", "Library", "Status", "Titles"], [(row["function"], row["dll"], row["library"] or "none", row["status"], len(row["titles"])) for row in todo[:500]])}
<h2>DLLs</h2>
{table(["DLL", "Library", "Needed by titles", "Done of needed", "Known exports", "Declared", "Done"], [(e["dll"], e["library"] or "none", e["needed"], e["neededDone"], e["known"], e["declared"], e["done"]) for e in report["dlls"]])}
<h2>Titles</h2>
{table(["Title", "Version", "Needed", "Done", "Next blockers"], [(f'{t["name"] or "Unknown"} ({t["titleId"] or "?"})', t["version"] or "?", t["needed"], f'{t["done"]} ({t["percent"]}%)', ", ".join(t["blockers"][:5]) or "none") for t in report["titles"]])}
<p><a href="progress.html">Progress</a> · <a href="history.html">History</a></p></body></html>
"""


def main():
    parser = argparse.ArgumentParser(description="Rank every known GDK function by how many titles need it and what AnyBox does with it.")
    parser.add_argument("output", nargs="?", type=Path, help="directory for needs.json and needs.html")
    parser.add_argument("--needs-dir", type=Path, default=NEEDS_DIR)
    parser.add_argument("--inventory-dir", type=Path, default=INVENTORY_DIR)
    parser.add_argument("--limit", type=int, default=40, help="rows of the Markdown summary")
    args = parser.parse_args()
    report = build(load(args.needs_dir, "anybox-needs"), load(args.inventory_dir, "anybox-inventory"), anybox_scan.scan(), anybox_scan.host_patterns())
    if args.output:
        args.output.mkdir(parents=True, exist_ok=True)
        (args.output / "needs.json").write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
        (args.output / "needs.html").write_text(page(report), encoding="utf-8")
    sys.stdout.write(markdown(report, args.limit))


if __name__ == "__main__":
    main()
