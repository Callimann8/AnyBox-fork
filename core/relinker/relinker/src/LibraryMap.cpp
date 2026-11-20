#include "relinker/LibraryMap.hpp"

#include <algorithm>
#include <cctype>

namespace anybox::relinker {

namespace {

const LibraryRoute BuiltinRoutes[] = {
#include "LibraryMapData.inc"
    {"", "", ""},
};

const char* const BuiltinHostPatterns[] = {
#include "HostDllsData.inc"
    "",
};

}

std::string ToLower(std::string_view text) {
    std::string lower(text);
    std::transform(lower.begin(), lower.end(), lower.begin(), [](unsigned char c) { return static_cast<char>(std::tolower(c)); });
    return lower;
}

bool MatchPattern(std::string_view pattern, std::string_view text) {
    std::size_t p = 0;
    std::size_t t = 0;
    std::size_t star = std::string_view::npos;
    std::size_t resume = 0;
    while (t < text.size()) {
        if (p < pattern.size() && pattern[p] == '*') {
            star = p++;
            resume = t;
        } else if (p < pattern.size() && pattern[p] == text[t]) {
            ++p;
            ++t;
        } else if (star != std::string_view::npos) {
            p = star + 1;
            t = ++resume;
        } else {
            return false;
        }
    }
    while (p < pattern.size() && pattern[p] == '*') {
        ++p;
    }
    return p == pattern.size();
}

std::string_view KindName(ImportKind kind) {
    switch (kind) {
    case ImportKind::Library: return "library";
    case ImportKind::Bundled: return "bundled";
    case ImportKind::Host: return "host";
    case ImportKind::Unknown: return "unknown";
    }
    return "unknown";
}

LibraryMap::LibraryMap(std::vector<LibraryRoute> routes, std::vector<std::string> hostPatterns)
    : routes_(std::move(routes)), hostPatterns_(std::move(hostPatterns)) {
    for (LibraryRoute& route : routes_) {
        route.pattern = ToLower(route.pattern);
    }
    for (std::string& pattern : hostPatterns_) {
        pattern = ToLower(pattern);
    }
}

LibraryMap LibraryMap::Builtin() {
    std::vector<LibraryRoute> routes;
    for (const LibraryRoute& route : BuiltinRoutes) {
        if (!route.pattern.empty()) {
            routes.push_back(route);
        }
    }
    std::vector<std::string> hosts;
    for (const char* pattern : BuiltinHostPatterns) {
        if (*pattern != '\0') {
            hosts.emplace_back(pattern);
        }
    }
    return LibraryMap(std::move(routes), std::move(hosts));
}

void LibraryMap::SetBundled(std::vector<std::string> dllNames) {
    bundled_.clear();
    for (const std::string& name : dllNames) {
        bundled_.push_back(ToLower(name));
    }
}

Resolution LibraryMap::Resolve(std::string_view dll) const {
    const std::string name = ToLower(dll);
    if (std::find(bundled_.begin(), bundled_.end(), name) != bundled_.end()) {
        return {ImportKind::Bundled, std::string(dll), {}};
    }
    for (const LibraryRoute& route : routes_) {
        if (MatchPattern(route.pattern, name)) {
            return {ImportKind::Library, route.hostDll, route.library};
        }
    }
    for (const std::string& pattern : hostPatterns_) {
        if (MatchPattern(pattern, name)) {
            return {ImportKind::Host, std::string(dll), {}};
        }
    }
    return {ImportKind::Unknown, std::string(dll), {}};
}

}
