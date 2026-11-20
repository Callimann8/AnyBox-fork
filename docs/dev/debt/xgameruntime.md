# xgameruntime technical debt

Serves `xgameruntime.dll`.

### Functional

- [XTaskQueue](../../../core/libs/xdll/xgameruntime/TaskQueue.cpp) (xgameruntime) - the enum values (`Manual` 0, `ThreadPool` 1, `SerializedThreadPool` 2, `Immediate` 3; `Work` 0, `Completion` 1) and the `E_ABORT` result after termination follow the public XTaskQueue header in libHttpClient; not checked against a console title
  Closes when: measured on a console
- [XTaskQueueTerminate](../../../core/libs/xdll/xgameruntime/TaskQueue.cpp) (xgameruntime) - pending and delayed callbacks are invoked with `canceled = true` on the terminating thread, not on their port's dispatcher; waiting from inside one of the queue's own callbacks stops with `AbxUnsupported`
- [XTaskQueueGetCurrentProcessTaskQueue](../../../core/libs/xdll/xgameruntime/TaskQueue.cpp) (xgameruntime) - returns a new handle the caller closes; the default process queue is created on first use with thread-pool work and completion ports
- [XTaskQueueSubmitCallback](../../../core/libs/xdll/xgameruntime/TaskQueue.cpp) (xgameruntime) - a null queue uses the process task queue; with none set it stops with `AbxUnsupported`
- [XGameGetXboxTitleId](../../../core/libs/xdll/xgameruntime/Runtime.cpp) (xgameruntime) - reads `<TitleId>` from `MicrosoftGame.config` beside the executable; stops with `AbxUnsupported` when it is missing

### Silent stubs

- [XGameRuntimeInitialize](../../../core/libs/xdll/xgameruntime/Runtime.cpp) (xgameruntime) - returns `S_OK` without starting any service; nothing in AnyBox needs initialization yet

### Unknown function info

- [Inventory](../../../core/libs/xdll/xgameruntime/Inventory.cpp) (xgameruntime) - XAsync, XUser, XGameSave, XPackage, XSystem, XThread and the remaining XTaskQueue exports are declared without parameters until implemented
