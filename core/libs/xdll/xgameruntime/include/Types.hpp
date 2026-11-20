#pragma once

#include <windows.h>

#include <cstdint>

struct XTaskQueueObject;
using XTaskQueueHandle = XTaskQueueObject*;

enum class XTaskQueueDispatchMode : std::uint32_t {
    Manual,
    ThreadPool,
    SerializedThreadPool,
    Immediate,
};

enum class XTaskQueuePort : std::uint32_t {
    Work,
    Completion,
};

using XTaskQueueCallback = void(void* context, bool canceled);
using XTaskQueueTerminatedCallback = void(void* context);

inline constexpr std::uint32_t XTaskQueueNoWait = 0;
inline constexpr std::uint32_t XTaskQueueInfinite = 0xffffffffu;
