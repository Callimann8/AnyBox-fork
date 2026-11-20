# Export inventories

Lists of every function a system DLL exports, so the needs page can show the whole surface of a DLL and not only what audited titles happen to import.

Make one from import libraries (`.lib`, short format, such as those in an installed Microsoft GDK) or from DLLs:

```
python tools/lib_inventory.py "<GDK install>\<version>\GRDK\GameKit\Lib\amd64" --label "GDK <version> GRDK" --json docs/inventory/gdk-<version>-grdk.json
```

An inventory holds DLL and function names only. Never commit the libraries, headers or DLLs themselves.
