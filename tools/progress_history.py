import argparse
import json
import subprocess
import sys
from html import escape
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import anybox_scan
import progress


def git(*args):
    return subprocess.run(["git", *args], cwd=anybox_scan.ROOT, capture_output=True, text=True, check=True, encoding="utf-8", errors="replace").stdout


class GitSource:
    def __init__(self, commit):
        self.commit = commit
        self.cache = {}

    def files(self, prefix):
        if prefix not in self.cache:
            output = git("ls-tree", "-r", "--name-only", self.commit, "--", prefix)
            self.cache[prefix] = sorted(line for line in output.splitlines() if line)
        return self.cache[prefix]

    def read(self, path):
        return git("show", f"{self.commit}:{path}")


def daily_commits(ref):
    days = {}
    for line in git("log", "--first-parent", "--format=%H %cs", ref).splitlines():
        commit, day = line.split()
        days.setdefault(day, commit)
    return sorted(days.items())


def measure(ref, cache_path):
    cache = json.loads(cache_path.read_text(encoding="utf-8")) if cache_path and cache_path.exists() else {}
    points = []
    for day, commit in daily_commits(ref):
        if commit not in cache:
            source = GitSource(commit)
            if not source.files(anybox_scan.XDLL):
                continue
            libraries = [anybox_scan.scan_library(source, name) for name in anybox_scan.library_names(source)]
            cache[commit] = progress.snapshot(libraries, commit)["totals"]
        points.append({"day": day, "commit": commit, **cache[commit]})
    if cache_path:
        cache_path.write_text(json.dumps(cache, indent=1) + "\n", encoding="utf-8")
    return points


def chart(points, width=720, height=240, pad=36):
    if not points:
        return '<svg xmlns="http://www.w3.org/2000/svg" width="300" height="40"><text x="8" y="24">No history yet</text></svg>\n'
    top = max(point["declared"] for point in points) or 1
    step = (width - 2 * pad) / max(len(points) - 1, 1)

    def line(key, color, dash=""):
        coords = " ".join(f"{pad + i * step:.1f},{height - pad - (height - 2 * pad) * point[key] / top:.1f}" for i, point in enumerate(points))
        return f'<polyline fill="none" stroke="{color}" stroke-width="2" {dash} points="{coords}"/>'

    done = [dict(point, done=point["implemented"] + point["forwarded"]) for point in points]
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" font-family="sans-serif" font-size="11">',
             f'<rect width="{width}" height="{height}" fill="#0d1117"/>']
    points_done = done
    coords = " ".join(f"{pad + i * step:.1f},{height - pad - (height - 2 * pad) * point['done'] / top:.1f}" for i, point in enumerate(points_done))
    parts.append(f'<polyline fill="none" stroke="{progress.DONE}" stroke-width="2" points="{coords}"/>')
    parts.append(line("declared", "#8b949e", 'stroke-dasharray="4 3"'))
    for i, point in enumerate(points_done):
        x = pad + i * step
        parts.append(f'<circle cx="{x:.1f}" cy="{height - pad - (height - 2 * pad) * point["done"] / top:.1f}" r="3" fill="{progress.DONE}">'
                     f'<title>{point["day"]}: {point["done"]}/{point["declared"]} done</title></circle>')
    parts.append(f'<text x="{pad}" y="{height - 10}" fill="#e6edf3">{escape(points[0]["day"])}</text>')
    parts.append(f'<text x="{width - pad}" y="{height - 10}" fill="#e6edf3" text-anchor="end">{escape(points[-1]["day"])}</text>')
    parts.append(f'<text x="{pad}" y="20" fill="#e6edf3">done (solid) and declared (dashed) library functions, max {top}</text>')
    parts.append("</svg>\n")
    return "\n".join(parts)


def page(points):
    rows = []
    previous = None
    for point in points:
        done = point["implemented"] + point["forwarded"]
        delta = "n/a" if previous is None else f"{done - previous:+d}"
        rows.append(f'<tr><td>{point["day"]}</td><td>{done}</td><td>{point["declared"]}</td><td>{point["percent"]}%</td><td>{delta}</td><td><code>{point["commit"][:10]}</code></td></tr>')
        previous = done
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>AnyBox history</title>
<style>body{{font-family:system-ui,sans-serif;background:#0d1117;color:#e6edf3;padding:16px}}table{{border-collapse:collapse}}td,th{{padding:4px 10px;border-bottom:1px solid #30363d}}img{{max-width:100%}}</style>
</head><body><h1>AnyBox progress history</h1><p><img src="history.svg" alt="history chart"></p>
<p>One point per UTC day, the last first-parent commit of that day, measured with today's counting rules.</p>
<table><thead><tr><th>Day</th><th>Done</th><th>Declared</th><th>%</th><th>Functions done since previous day</th><th>Commit</th></tr></thead>
<tbody>{"".join(reversed(rows))}</tbody></table><p><a href="progress.html">Current progress</a></p></body></html>
"""


def main():
    parser = argparse.ArgumentParser(description="Measure library progress for each day of the first-parent history.")
    parser.add_argument("output", type=Path)
    parser.add_argument("--ref", default="HEAD")
    parser.add_argument("--cache", type=Path)
    args = parser.parse_args()
    points = measure(args.ref, args.cache)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "history.json").write_text(json.dumps(points, indent=1) + "\n", encoding="utf-8")
    (args.output / "history.svg").write_text(chart(points), encoding="utf-8")
    (args.output / "history.html").write_text(page(points), encoding="utf-8")
    print(f"{len(points)} days measured")


if __name__ == "__main__":
    main()
