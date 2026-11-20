#pragma once

#include "AbxApi.hpp"

#include <windows.h>

ABX_API HRESULT D3D12XboxCreateDevice();
ABX_API HRESULT D3D12CreateDevice();
ABX_API HRESULT D3D12GetDebugInterface();
ABX_API HRESULT D3D12SerializeRootSignature();
ABX_API HRESULT D3D12SerializeVersionedRootSignature();
ABX_API HRESULT D3D12CreateRootSignatureDeserializer();
ABX_API HRESULT D3D12CreateVersionedRootSignatureDeserializer();
