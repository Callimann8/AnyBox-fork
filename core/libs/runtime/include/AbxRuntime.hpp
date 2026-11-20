#pragma once

#include "AbxApi.hpp"

#include <cstdint>

ABX_RUNTIME_API void AbxRegisterLibrary(const char* library);

struct AbxStop {
    const char* kind;
    const char* library;
    const char* function;
    const char* file;
    int line;
    const char* message;
    bool hasException;
    std::uint32_t exceptionCode;
    std::uint64_t exceptionAddress;
};

ABX_RUNTIME_API bool AbxWriteReport(const AbxStop* stop);

namespace abx::detail {

struct LibraryRegistration {
    explicit LibraryRegistration(const char* library) { AbxRegisterLibrary(library); }
};

}
