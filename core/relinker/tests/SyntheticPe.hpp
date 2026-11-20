#pragma once

#include <cstdint>
#include <optional>
#include <string>
#include <vector>

namespace anybox::test {

struct SyntheticImport {
    std::string dll;
    std::vector<std::string> functions;
    std::vector<std::uint16_t> ordinals;
    bool delayLoaded = false;
    bool bound = false;
};

struct SyntheticExport {
    std::string name;
    std::optional<std::string> forwarder;
};

struct SyntheticPe {
    std::uint16_t machine = 0x8664;
    std::uint16_t subsystem = 14;
    bool dll = false;
    std::uint32_t sizeOfHeaders = 0x400;
    std::uint32_t certificateBytes = 0;
    std::vector<SyntheticImport> imports;
    std::vector<SyntheticExport> exports;
};

std::vector<std::uint8_t> Build(const SyntheticPe& spec);

}
