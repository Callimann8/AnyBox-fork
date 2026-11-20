#pragma once

#include "AbxApi.hpp"
#include "xdll/xgameruntime/include/Types.hpp"

ABX_API HRESULT XGameRuntimeInitialize();
ABX_API void XGameRuntimeUninitialize();
ABX_API HRESULT XGameGetXboxTitleId(std::uint32_t* titleId);

ABX_API HRESULT XTaskQueueCreate(XTaskQueueDispatchMode workDispatchMode, XTaskQueueDispatchMode completionDispatchMode, XTaskQueueHandle* queue);
ABX_API HRESULT XTaskQueueDuplicateHandle(XTaskQueueHandle queue, XTaskQueueHandle* duplicated);
ABX_API void XTaskQueueCloseHandle(XTaskQueueHandle queue);
ABX_API HRESULT XTaskQueueSubmitCallback(XTaskQueueHandle queue, XTaskQueuePort port, void* context, XTaskQueueCallback* callback);
ABX_API HRESULT XTaskQueueSubmitDelayedCallback(XTaskQueueHandle queue, XTaskQueuePort port, std::uint32_t delayMs, void* context, XTaskQueueCallback* callback);
ABX_API bool XTaskQueueDispatch(XTaskQueueHandle queue, XTaskQueuePort port, std::uint32_t timeoutMs);
ABX_API bool XTaskQueueIsEmpty(XTaskQueueHandle queue, XTaskQueuePort port);
ABX_API HRESULT XTaskQueueTerminate(XTaskQueueHandle queue, bool wait, void* context, XTaskQueueTerminatedCallback* callback);
ABX_API bool XTaskQueueGetCurrentProcessTaskQueue(XTaskQueueHandle* queue);
ABX_API void XTaskQueueSetCurrentProcessTaskQueue(XTaskQueueHandle queue);

ABX_API HRESULT XGameRuntimeInitializeWithOptions();
ABX_API HRESULT XGameRuntimeIsFeatureAvailable();
ABX_API HRESULT XTaskQueueCreateComposite();
ABX_API HRESULT XTaskQueueGetPort();
ABX_API HRESULT XTaskQueueRegisterMonitor();
ABX_API HRESULT XTaskQueueUnregisterMonitor();
ABX_API HRESULT XTaskQueueRegisterWaiter();
ABX_API HRESULT XTaskQueueUnregisterWaiter();
ABX_API HRESULT XAsyncBegin();
ABX_API HRESULT XAsyncCancel();
ABX_API HRESULT XAsyncComplete();
ABX_API HRESULT XAsyncGetResult();
ABX_API HRESULT XAsyncGetResultSize();
ABX_API HRESULT XAsyncGetStatus();
ABX_API HRESULT XAsyncRun();
ABX_API HRESULT XAsyncSchedule();
ABX_API HRESULT XUserAddAsync();
ABX_API HRESULT XUserAddResult();
ABX_API HRESULT XUserCloseHandle();
ABX_API HRESULT XUserDuplicateHandle();
ABX_API HRESULT XUserGetGamertag();
ABX_API HRESULT XUserGetId();
ABX_API HRESULT XUserGetLocalId();
ABX_API HRESULT XUserGetState();
ABX_API HRESULT XUserRegisterForChangeEvent();
ABX_API HRESULT XUserUnregisterForChangeEvent();
ABX_API HRESULT XGameSaveInitializeProvider();
ABX_API HRESULT XGameSaveInitializeProviderAsync();
ABX_API HRESULT XGameSaveInitializeProviderResult();
ABX_API HRESULT XGameSaveCloseProvider();
ABX_API HRESULT XGameSaveCreateContainer();
ABX_API HRESULT XGameSaveCloseContainer();
ABX_API HRESULT XGameSaveCreateUpdate();
ABX_API HRESULT XGameSaveCloseUpdate();
ABX_API HRESULT XGameSaveSubmitBlobWrite();
ABX_API HRESULT XGameSaveSubmitUpdate();
ABX_API HRESULT XGameSaveReadBlobData();
ABX_API HRESULT XGameSaveGetRemainingQuota();
ABX_API HRESULT XPackageGetCurrentProcessPackageIdentifier();
ABX_API HRESULT XPackageIsPackagedProcess();
ABX_API HRESULT XSystemGetDeviceType();
ABX_API HRESULT XSystemGetConsoleId();
ABX_API HRESULT XSystemGetAppSpecificDeviceId();
ABX_API HRESULT XThreadIsTimeSensitive();
ABX_API HRESULT XThreadSetTimeSensitive();
ABX_API HRESULT XThreadAssertNotTimeSensitive();
