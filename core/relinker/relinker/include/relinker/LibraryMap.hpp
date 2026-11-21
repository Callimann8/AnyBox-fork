#pragma once

#include <cstdint>
#include <optional>
#include <string>
#include <string_view>
#include <vector>

namespace anybox::relinker {

struct LibraryRoute {
    std::string pattern;
    std::string hostDll;
    std::string library;
};

struct LibraryOrdinal {
    std::string library;
    std::uint16_t ordinal = 0;
    std::string name;
};

enum class ImportKind {
    Library,
    Bundled,
    Host,
    Unknown,
};

struct Resolution {
    ImportKind kind = ImportKind::Unknown;
    std::string target;
    std::string library;
};

class LibraryMap {
public:
    LibraryMap(std::vector<LibraryRoute> routes, std::vector<std::string> hostPatterns, std::vector<LibraryOrdinal> ordinals = {});

    static LibraryMap Builtin();

    void SetBundled(std::vector<std::string> dllNames);
    Resolution Resolve(std::string_view dll) const;
    std::optional<std::string> OrdinalName(std::string_view library, std::uint16_t ordinal) const;

    const std::vector<LibraryRoute>& Routes() const { return routes_; }
    const std::vector<std::string>& HostPatterns() const { return hostPatterns_; }

private:
    std::vector<LibraryRoute> routes_;
    std::vector<std::string> hostPatterns_;
    std::vector<std::string> bundled_;
    std::vector<LibraryOrdinal> ordinals_;
};

std::string ToLower(std::string_view text);
bool MatchPattern(std::string_view pattern, std::string_view text);
std::string_view KindName(ImportKind kind);

}
