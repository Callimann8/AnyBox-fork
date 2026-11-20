# runtime technical debt

### Functional

- [Runtime](../../../core/libs/runtime/src/Runtime.cpp) (runtime) - `system.gpu` is always `null` until a graphics library reports the device
- [Runtime](../../../core/libs/runtime/src/Runtime.cpp) (runtime) - a C++ exception escaping an AnyBox library is reported as a crash with code `0x20474343`, without the exception message
- [Runtime](../../../core/libs/runtime/src/Runtime.cpp) (runtime) - the crash report depends on the unhandled exception filter set at load; on GitHub's Windows runner a MinGW-built test title crashes without a report, so a C runtime that replaces the filter without chaining loses it. `e2e_crash` checks the report only when one is written
  Closes when: e2e_crash writes its report on the CI runner
