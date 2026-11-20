#include "relinker/Registry.hpp"

#include <format>

namespace anybox::relinker {

std::string JsonEscape(std::string_view text) {
    std::string escaped;
    escaped.reserve(text.size() + 2);
    for (const char c : text) {
        switch (c) {
        case '"': escaped += "\\\""; break;
        case '\\': escaped += "\\\\"; break;
        case '\n': escaped += "\\n"; break;
        case '\r': escaped += "\\r"; break;
        case '\t': escaped += "\\t"; break;
        default:
            if (static_cast<unsigned char>(c) < 0x20) {
                escaped += std::format("\\u{:04x}", static_cast<unsigned char>(c));
            } else {
                escaped += c;
            }
        }
    }
    return escaped;
}

std::string RegistryJson(const ConversionResult& result, std::string_view input, std::string_view output) {
    std::string json = "{\n";
    json += "  \"format\": \"anybox-registry\",\n  \"version\": 1,\n";
    json += std::format("  \"input\": \"{}\",\n  \"output\": \"{}\",\n", JsonEscape(input), JsonEscape(output));
    json += std::format("  \"dll\": {},\n", result.dll ? "true" : "false");
    json += std::format("  \"subsystem\": {{\"before\": \"{}\", \"after\": \"{}\"}},\n", pe::SubsystemName(result.subsystemBefore), pe::SubsystemName(result.subsystemAfter));
    json += std::format("  \"certificateRemoved\": {},\n  \"boundImportsRemoved\": {},\n", result.certificateRemoved ? "true" : "false", result.boundImportsRemoved ? "true" : "false");
    json += "  \"imports\": [";
    for (std::size_t i = 0; i < result.imports.size(); ++i) {
        const ResolvedImport& module = result.imports[i];
        json += i == 0 ? "\n" : ",\n";
        json += std::format("    {{\"dll\": \"{}\", \"kind\": \"{}\", \"target\": \"{}\", \"library\": {}, \"delayLoaded\": {}, \"functions\": [",
            JsonEscape(module.dll), KindName(module.kind), JsonEscape(module.target),
            module.library.empty() ? std::string("null") : "\"" + JsonEscape(module.library) + "\"",
            module.delayLoaded ? "true" : "false");
        for (std::size_t j = 0; j < module.functions.size(); ++j) {
            const pe::ImportFunction& function = module.functions[j];
            json += j == 0 ? "\n" : ",\n";
            if (function.ordinal) {
                json += std::format("      {{\"name\": null, \"ordinal\": {}}}", *function.ordinal);
            } else {
                json += std::format("      {{\"name\": \"{}\", \"ordinal\": null}}", JsonEscape(function.name));
            }
        }
        json += module.functions.empty() ? "]}" : "\n    ]}";
    }
    json += result.imports.empty() ? "]\n}\n" : "\n  ]\n}\n";
    return json;
}

}
