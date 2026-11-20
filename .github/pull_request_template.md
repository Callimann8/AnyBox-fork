### What

### Tested
<!-- OS, title or test, what was checked. "Not tested" is a valid answer. -->

### Checklist
<!-- Rules behind each item: CONTRIBUTING.md -->
- [ ] Based on current `main`; no other open PR implements the same functions
- [ ] One topic per PR; follow-ups go in a new PR
- [ ] `python tools/check_conventions.py` passes (no comments in code, one declaration per export, Conventional Commit subjects)
- [ ] Unimplemented paths stop (`AbxNotImplemented` / `AbxUnsupported`); silent stubs are listed under Silent stubs through a debt fragment
- [ ] Known gaps added, changed or removed through `docs/dev/debt/changes/<branch>.md`
- [ ] Generic behaviour, not specific to one title
- [ ] No game files, keys, notes or logs added to the repository
- [ ] Depends on: <!-- #PR, or none -->
- [ ] Fixes: <!-- Fixes #N, or none -->
- [ ] Unblocks: <!-- title ID and Game bring-up discussion, e.g. 4D5307E6 #12, or none -->
- [ ] Source of behaviour: <!-- public header / documentation link, measured on console, or n/a -->
- [ ] AI-assisted: <!-- yes / no -->
