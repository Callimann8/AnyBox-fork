#include "xdll/xgameruntime/xgameruntime.hpp"

namespace {

thread_local bool t_timeSensitive = false;

}

ABX_API HRESULT XThreadSetTimeSensitive(bool isTimeSensitiveThread) {
    t_timeSensitive = isTimeSensitiveThread;
    return S_OK;
}

ABX_API bool XThreadIsTimeSensitive() {
    return t_timeSensitive;
}

ABX_API void XThreadAssertNotTimeSensitive() {
    if (t_timeSensitive) {
        AbxUnsupported(__func__, "called on a thread marked time-sensitive; what the console does then is unknown");
    }
}
