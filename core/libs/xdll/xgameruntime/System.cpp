#include "xdll/xgameruntime/xgameruntime.hpp"

#include <cstring>
#include <string_view>

ABX_API XSystemDeviceType XSystemGetDeviceType() {
    const char* configured = AbxTitleDeviceFamily();
    if (configured == nullptr) {
        AbxUnsupported(__func__, "MicrosoftGame.config beside the executable is missing or has no <Executable>");
    }
    const std::string_view family(configured);
    if (family == "Scarlett") {
        return XSystemDeviceType::XboxScarlettAnaconda;
    }
    if (family == "XboxOne") {
        return XSystemDeviceType::XboxOneX;
    }
    if (family == "PC") {
        return XSystemDeviceType::Pc;
    }
    AbxUnsupported(__func__, "TargetDeviceFamily in MicrosoftGame.config is not XboxOne, Scarlett or PC");
}

ABX_API HRESULT XSystemGetConsoleId(std::size_t consoleIdSize, char* consoleId, std::size_t* consoleIdUsed) {
    static constexpr char PcConsoleId[] = "00000000.00000000.00000000.00000000.00";
    static_assert(sizeof(PcConsoleId) == XSystemConsoleIdBytes);
    if (consoleIdSize < XSystemConsoleIdBytes) {
        return HRESULT_FROM_WIN32(ERROR_INSUFFICIENT_BUFFER);
    }
    if (consoleId == nullptr) {
        AbxUnsupported(__func__, "consoleId is null");
    }
    std::memcpy(consoleId, PcConsoleId, sizeof(PcConsoleId));
    if (consoleIdUsed != nullptr) {
        *consoleIdUsed = sizeof(PcConsoleId);
    }
    return S_OK;
}
