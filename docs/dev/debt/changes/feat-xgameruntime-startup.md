# xgameruntime

## add Functional

- [XGameRuntimeIsFeatureAvailable](../../../core/libs/xdll/xgameruntime/Runtime.cpp) (xgameruntime) - returns `true` for every feature in the public `XGameRuntimeFeature.h` (2610), as a console runtime does, although many of their exports are still stubs that stop the title; values above `XGameStreaming` return `false`
- [XGameRuntimeInitializeWithOptions](../../../core/libs/xdll/xgameruntime/Runtime.cpp) (xgameruntime) - only `XGameRuntimeGameConfigSource::Default` is supported; `Inline`, `File` and null options stop with `AbxUnsupported`
  Closes when: the runtime can read a game config from a string or another path
- [XThreadSetTimeSensitive](../../../core/libs/xdll/xgameruntime/Thread.cpp) (xgameruntime) - only records the flag per thread; AnyBox functions that can block do not check it, and `XThreadAssertNotTimeSensitive` on a time-sensitive thread stops with `AbxUnsupported` because the console's reaction is unknown
  Closes when: the console's behaviour for a blocking call on a time-sensitive thread is measured
- [XPackageGetCurrentProcessPackageIdentifier](../../../core/libs/xdll/xgameruntime/Package.cpp) (xgameruntime) - always returns `E_GAMEPACKAGE_APP_NOT_PACKAGED` without writing the buffer, consistent with `XPackageIsPackagedProcess` returning `false`
