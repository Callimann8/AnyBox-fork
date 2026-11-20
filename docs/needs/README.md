# Title needs records

One `<TitleId>.json` per title, listing the DLLs and function names the title imports that desktop Windows does not provide. `tools/needs.py` merges every record here into the ranked list on the [needs page](https://dark3581.github.io/AnyBox/needs.html).

Make one for a title you own:

```
python tools/import_audit.py <decrypted package folder> --needs docs/needs/<TitleId>.json
```

Then open a pull request titled `docs(needs): add <TitleId>`. A record holds only names, the title ID, the display name and the content version. Never add game files, executables or anything else from the package.
