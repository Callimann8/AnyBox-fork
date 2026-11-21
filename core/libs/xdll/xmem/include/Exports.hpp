#pragma once

#include "AbxApi.hpp"

#include <windows.h>

ABX_API HRESULT XMemFree();
ABX_API HRESULT XMemGetWorkingSetStatistics();
ABX_API HRESULT XMemAlloc();
ABX_API HRESULT XMemVirtualQuery();
