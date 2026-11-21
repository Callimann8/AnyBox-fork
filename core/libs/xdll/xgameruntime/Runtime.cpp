#include "xdll/xgameruntime/xgameruntime.hpp"

#include <cstdlib>
#include <string>

ABX_API HRESULT XGameRuntimeInitialize() {
    return S_OK;
}

ABX_API HRESULT XGameRuntimeInitializeWithOptions(const XGameRuntimeOptions* options) {
    if (options == nullptr) {
        AbxUnsupported(__func__, "options is null");
    }
    if (options->gameConfigSource != XGameRuntimeGameConfigSource::Default) {
        AbxUnsupported(__func__, "gameConfigSource is not Default: AnyBox reads only the MicrosoftGame.config beside the executable");
    }
    return XGameRuntimeInitialize();
}

ABX_API bool XGameRuntimeIsFeatureAvailable(XGameRuntimeFeature feature) {
    return static_cast<std::uint32_t>(feature) <= static_cast<std::uint32_t>(XGameRuntimeFeature::XGameStreaming);
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
