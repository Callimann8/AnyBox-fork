# xgameruntime

## add Functional

- [XSystemGetConsoleId](../../../core/libs/xdll/xgameruntime/System.cpp) (xgameruntime) - always returns `00000000.00000000.00000000.00000000.00`, the value the GDK documentation gives for PC and for the retail sandbox; a buffer smaller than `XSystemConsoleIdBytes` (39) returns `HRESULT_FROM_WIN32(ERROR_INSUFFICIENT_BUFFER)` without touching `consoleIdUsed`; `consoleIdUsed` receives 39, counting the terminator; a null `consoleId` stops with `AbxUnsupported`; not checked against a console title
  Closes when: the size reported in `consoleIdUsed` and the short-buffer behaviour are measured on a console
