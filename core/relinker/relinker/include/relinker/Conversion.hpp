#pragma once

#include "pe/PeImage.hpp"
#include "relinker/LibraryMap.hpp"

#include <cstdint>
#include <string>
#include <vector>

namespace anybox::relinker {

enum class TargetSubsystem {
    Keep,
    Gui,
    Console,
};

struct ConversionOptions {
    TargetSubsystem subsystem = TargetSubsystem::Keep;
    bool allowUnknown = false;
};

struct ResolvedImport {
    std::string dll;
    std::string target;
    std::string library;
    ImportKind kind = ImportKind::Unknown;
    bool delayLoaded = false;
    std::vector<pe::ImportFunction> functions;
};

struct ConversionResult {
    std::vector<std::uint8_t> bytes;
    std::vector<ResolvedImport> imports;
    std::uint16_t subsystemBefore = 0;
    std::uint16_t subsystemAfter = 0;
    bool dll = false;
    bool certificateRemoved = false;
    bool boundImportsRemoved = false;
    bool sectionAdded = false;
    std::uint32_t checksum = 0;
};

inline constexpr char AddedSectionName[] = ".abximp";

ConversionResult Convert(std::vector<std::uint8_t> input, const ConversionOptions& options, const LibraryMap& map);

}
