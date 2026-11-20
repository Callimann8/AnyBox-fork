#include "xdll/xgameruntime/xgameruntime.hpp"

#include <cstdlib>
#include <string>

ABX_API HRESULT XGameRuntimeInitialize() {
    return S_OK;
}

ABX_API void XGameRuntimeUninitialize() {
}

ABX_API HRESULT XGameGetXboxTitleId(std::uint32_t* titleId) {
    if (titleId == nullptr) {
        return E_INVALIDARG;
    }
    const char* configured = AbxTitleId();
    if (configured == nullptr) {
        AbxUnsupported(__func__, "MicrosoftGame.config beside the executable has no valid <TitleId>");
    }
    *titleId = static_cast<std::uint32_t>(std::strtoul(configured, nullptr, 16));
    return S_OK;
}
