# Progress tracking

What is counted, where it is published, and how to read it.

## Library counts

[`tools/progress.py`](../../tools/progress.py) scans `core/libs/xdll/<library>/` (excluding `tests/`) through [`tools/anybox_scan.py`](../../tools/anybox_scan.py):

- **implemented:** an `ABX_API` function definition whose body does not call `AbxNotImplemented`;
- **stub:** an `ABX_API` definition whose body calls `AbxNotImplemented`;
- **forwarded:** a `Name=dll.Target` line in the library's `Forwards.def`.

Comments, string and character literals are blanked before matching, so braces or names inside them do not count. The percentage is `(implemented + forwarded) / declared`. Declared functions are those the project knows about so far, not every console export. The total grows as `stubgen.py` adds imports found by audits. A count says nothing about whether a title runs; compatibility lives in the Game bring-up discussions.

```
python tools/progress.py out/            # progress.json, progress.html, progress.svg, badge-libraries.svg
python tools/progress.py --module xgameruntime
python tools/progress.py --json
python tools/progress.py --compare base.json head.json   # Markdown table for a PR comment
```

## History

[`tools/progress_history.py`](../../tools/progress_history.py) measures the first-parent history: one point per UTC day, the last commit of that day, read through `git show` with today's counting rules. It writes `history.json`, `history.svg` and `history.html`. `--cache <file>` keeps measured commits between runs.

## Publishing

- [Pages workflow](../../.github/workflows/pages.yml): on pushes to `main` that touch `core/libs`, the tools or the docs, it publishes the progress page, map, badge and history to GitHub Pages.
- [Progress report workflow](../../.github/workflows/progress-report.yml): on pull requests, it compares the base and head trees and posts the Markdown table to the job summary.

## Title imports

[`tools/import_audit.py`](../../tools/import_audit.py) reads a title's PE files and classifies every import:

| Status | Meaning |
|---|---|
| implemented | the routed library implements it |
| forwarded | the routed library forwards it to the host |
| stub | declared; calling it stops the title with a run report |
| absent | the DLL is routed but the function is not declared; `stubgen.py --from-audit` adds it |
| bundled | the title ships the DLL itself |
| host | desktop Windows provides the DLL |
| unrouted | nothing serves the DLL; start a library with `stubgen.py --new-library` |

It exits with 1 when something is absent or unrouted (`--strict-stubs` also fails on stubs).
