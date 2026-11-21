# xgameruntime

## add Functional

- [XSystemGetXboxLiveSandboxId](../../../core/libs/xdll/xgameruntime/System.cpp) (xgameruntime) - always returns `RETAIL`, the value the GDK documentation gives for the retail environment and when no sandbox is stored on the device; a development sandbox set on the PC is not read; a buffer smaller than `XSystemXboxLiveSandboxIdMaxBytes` (16) returns `HRESULT_FROM_WIN32(ERROR_INSUFFICIENT_BUFFER)` without touching `sandboxIdUsed`; `sandboxIdUsed` receives 7, counting the terminator; a null `sandboxId` stops with `AbxUnsupported`; not checked against a console title
  Closes when: the size reported in `sandboxIdUsed` is measured on a console, and a title that needs a development sandbox is reported
