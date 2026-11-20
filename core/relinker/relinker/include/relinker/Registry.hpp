#pragma once

#include "relinker/Conversion.hpp"

#include <string>
#include <string_view>

namespace anybox::relinker {

std::string JsonEscape(std::string_view text);

std::string RegistryJson(const ConversionResult& result, std::string_view input, std::string_view output);

}
