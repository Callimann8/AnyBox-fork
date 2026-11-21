#include "xdll/xgameruntime/xgameruntime.hpp"

ABX_API bool XPackageIsPackagedProcess() {
    return false;
}

ABX_API HRESULT XPackageGetCurrentProcessPackageIdentifier(std::size_t bufferSize, char* buffer) {
    static_cast<void>(bufferSize);
    static_cast<void>(buffer);
    return E_GAMEPACKAGE_APP_NOT_PACKAGED;
}
