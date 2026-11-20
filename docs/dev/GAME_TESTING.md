# Game testing

Every run is useful, including one that stops at once: the run report names the next function to implement. This page asks for the same information from every run, so reports can be compared.

## Before a run

- Build `main` (or the pull request you are testing) in a clean tree: `cmake --build build`.
- Audit the title first: `python tools/import_audit.py <package> --json audit.json`. Keep the summary line for the report.
- Convert with `--registry` and every folder of title DLLs as `--module-dir` ([USAGE](../user/USAGE.md)).
- Run one title at a time.

## Run

```
set ANYBOX_LOG_FILE=%CD%\anybox.log
out\game.exe
echo exit=%ERRORLEVEL%
```

## Report

Post to the title's **Game bring-up** discussion (one thread per title ID; search first):

- the line from `python tools/run_report_summary.py out\anybox-report.json`;
- the import audit summary line;
- the AnyBox commit and any pull requests merged on top;
- OS, CPU, GPU and driver;
- what was on screen and how far it got.

Attach `anybox-report.json` and the log. Never attach game files, executables, keys or anything you do not have the right to share.

## What to read

| Check | Where | Meaning |
|---|---|---|
| Exit code | shell | `0xAB01` (43777) stub, `0xAB02` (43778) unsupported, `0xC0000005` access violation, `0xC0000135` a DLL is missing beside the executable |
| Stop | `anybox-report.json` `stop` | the library and function, or the crash module and offset |
| Libraries | `anybox-report.json` `libraries` | which AnyBox DLLs the title loaded |
| Log | stderr or `ANYBOX_LOG_FILE` | `[anybox] not implemented: lib!func (file:line)` |
| Loader errors | message box at start-up | "The procedure entry point X could not be located in Y": a forwarded or host export the desktop lacks; report it as a library gap |
