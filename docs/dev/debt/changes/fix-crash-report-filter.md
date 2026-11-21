# runtime

## remove [the crash report depends on the unhandled exception filter set at load]

## add Functional

- [Runtime](../../../core/libs/runtime/src/Runtime.cpp) (runtime) - to keep the crash report when a C runtime or the title replaces the unhandled exception filter, a vectored handler puts the AnyBox filter back on top on every first-chance exception, not only fatal ones (C++ throws, `OutputDebugString`, thread naming, guard-page probes); a title's later `SetUnhandledExceptionFilter` call gets the AnyBox filter back as the previous one, and the title's own filter runs after the report is written
  Closes when: the crash report no longer needs the top-level filter
