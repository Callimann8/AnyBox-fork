#include "SyntheticPe.hpp"

#include "pe/PeImage.hpp"

#include <cstring>

namespace anybox::test {

namespace {

constexpr std::uint32_t SectionRva = 0x1000;
constexpr std::uint32_t FileAlignment = 0x200;
constexpr std::uint32_t SectionAlignment = 0x1000;
constexpr std::uint32_t PeOffset = 0x80;

class Content {
public:
    std::uint32_t Allocate(std::size_t size, std::size_t alignment = 8) {
        while (bytes_.size() % alignment != 0) {
            bytes_.push_back(0);
        }
        const std::uint32_t rva = SectionRva + static_cast<std::uint32_t>(bytes_.size());
        bytes_.resize(bytes_.size() + size, 0);
        return rva;
    }

    std::uint32_t String(const std::string& text) {
        const std::uint32_t rva = Allocate(text.size() + 1, 2);
        std::memcpy(At(rva), text.data(), text.size());
        return rva;
    }

    std::uint8_t* At(std::uint32_t rva) { return bytes_.data() + (rva - SectionRva); }
    void U16(std::uint32_t rva, std::uint16_t value) { pe::WriteU16(bytes_, rva - SectionRva, value); }
    void U32(std::uint32_t rva, std::uint32_t value) { pe::WriteU32(bytes_, rva - SectionRva, value); }
    void U64(std::uint32_t rva, std::uint64_t value) { pe::WriteU64(bytes_, rva - SectionRva, value); }
    std::uint32_t End() const { return SectionRva + static_cast<std::uint32_t>(bytes_.size()); }
    std::vector<std::uint8_t>& Bytes() { return bytes_; }

private:
    std::vector<std::uint8_t> bytes_;
};

std::uint32_t Thunks(Content& content, const SyntheticImport& import, std::uint64_t boundValue) {
    const std::size_t count = import.functions.size() + import.ordinals.size();
    const std::uint32_t table = content.Allocate((count + 1) * 8);
    std::size_t index = 0;
    for (const std::string& name : import.functions) {
        const std::uint32_t hint = content.Allocate(2 + name.size() + 1, 2);
        content.U16(hint, static_cast<std::uint16_t>(index));
        std::memcpy(content.At(hint + 2), name.data(), name.size());
        content.U64(table + static_cast<std::uint32_t>(index++) * 8, boundValue != 0 ? boundValue + index : hint);
    }
    for (std::uint16_t ordinal : import.ordinals) {
        content.U64(table + static_cast<std::uint32_t>(index++) * 8, boundValue != 0 ? boundValue + index : 0x8000000000000000ull | ordinal);
    }
    return table;
}

}

std::vector<std::uint8_t> Build(const SyntheticPe& spec) {
    Content content;
    std::size_t normalCount = 0;
    std::size_t delayCount = 0;
    for (const SyntheticImport& import : spec.imports) {
        (import.delayLoaded ? delayCount : normalCount)++;
    }
    const std::uint32_t descriptors = normalCount != 0 ? content.Allocate((normalCount + 1) * 20, 4) : 0;
    const std::uint32_t delayDescriptors = delayCount != 0 ? content.Allocate((delayCount + 1) * 32, 4) : 0;
    std::uint32_t boundDirectory = 0;
    std::size_t normalIndex = 0;
    std::size_t delayIndex = 0;
    for (const SyntheticImport& import : spec.imports) {
        const std::uint32_t lookup = Thunks(content, import, 0);
        const std::uint32_t iat = Thunks(content, import, import.bound ? 0x7ff800000000ull : 0);
        const std::uint32_t name = content.String(import.dll);
        if (import.delayLoaded) {
            const std::uint32_t d = delayDescriptors + static_cast<std::uint32_t>(delayIndex++) * 32;
            content.U32(d, 1);
            content.U32(d + 4, name);
            content.U32(d + 8, content.Allocate(8));
            content.U32(d + 12, iat);
            content.U32(d + 16, lookup);
        } else {
            const std::uint32_t d = descriptors + static_cast<std::uint32_t>(normalIndex++) * 20;
            content.U32(d, lookup);
            content.U32(d + 4, import.bound ? 0xffffffffu : 0);
            content.U32(d + 12, name);
            content.U32(d + 16, iat);
            if (import.bound && boundDirectory == 0) {
                boundDirectory = content.Allocate(16);
            }
        }
    }

    std::uint32_t exportDirectory = 0;
    std::uint32_t exportSize = 0;
    if (!spec.exports.empty()) {
        const std::uint32_t count = static_cast<std::uint32_t>(spec.exports.size());
        exportDirectory = content.Allocate(40, 4);
        const std::uint32_t functions = content.Allocate(count * 4, 4);
        const std::uint32_t names = content.Allocate(count * 4, 4);
        const std::uint32_t ordinals = content.Allocate(count * 2, 2);
        content.U32(exportDirectory + 12, content.String("synthetic.dll"));
        content.U32(exportDirectory + 16, 1);
        content.U32(exportDirectory + 20, count);
        content.U32(exportDirectory + 24, count);
        content.U32(exportDirectory + 28, functions);
        content.U32(exportDirectory + 32, names);
        content.U32(exportDirectory + 36, ordinals);
        for (std::uint32_t i = 0; i < count; ++i) {
            const SyntheticExport& entry = spec.exports[i];
            content.U32(names + i * 4, content.String(entry.name));
            content.U16(ordinals + i * 2, static_cast<std::uint16_t>(i));
            content.U32(functions + i * 4, entry.forwarder ? content.String(*entry.forwarder) : 0x0f00);
        }
        exportSize = content.End() - exportDirectory;
    }

    const std::uint32_t contentSize = static_cast<std::uint32_t>(content.Bytes().size());
    const std::uint32_t rawOffset = pe::AlignUp(spec.sizeOfHeaders, FileAlignment);
    const std::uint32_t rawSize = pe::AlignUp(contentSize, FileAlignment);
    std::vector<std::uint8_t> file(rawOffset + rawSize, 0);
    std::memcpy(file.data() + rawOffset, content.Bytes().data(), contentSize);

    file[0] = 'M';
    file[1] = 'Z';
    pe::WriteU32(file, 0x3c, PeOffset);
    pe::WriteU32(file, PeOffset, 0x00004550);
    const std::uint32_t fh = PeOffset + 4;
    pe::WriteU16(file, fh, spec.machine);
    pe::WriteU16(file, fh + 2, 1);
    pe::WriteU16(file, fh + 16, 0xf0);
    pe::WriteU16(file, fh + 18, static_cast<std::uint16_t>(0x22 | (spec.dll ? pe::CharacteristicDll : 0)));
    const std::uint32_t o = fh + 20;
    pe::WriteU16(file, o, pe::MagicPe32Plus);
    pe::WriteU32(file, o + 8, rawSize);
    pe::WriteU32(file, o + 16, SectionRva);
    pe::WriteU64(file, o + 24, 0x140000000ull);
    pe::WriteU32(file, o + 32, SectionAlignment);
    pe::WriteU32(file, o + 36, FileAlignment);
    pe::WriteU16(file, o + 48, 10);
    pe::WriteU32(file, o + 56, pe::AlignUp(SectionRva + contentSize, SectionAlignment));
    pe::WriteU32(file, o + 60, spec.sizeOfHeaders);
    pe::WriteU16(file, o + 68, spec.subsystem);
    pe::WriteU16(file, o + 70, 0x8160);
    pe::WriteU64(file, o + 72, 0x100000);
    pe::WriteU64(file, o + 80, 0x1000);
    pe::WriteU64(file, o + 88, 0x100000);
    pe::WriteU64(file, o + 96, 0x1000);
    pe::WriteU32(file, o + 108, 16);
    const auto directory = [&](std::size_t index, std::uint32_t rva, std::uint32_t size) {
        pe::WriteU32(file, o + 112 + index * 8, rva);
        pe::WriteU32(file, o + 116 + index * 8, size);
    };
    if (exportDirectory != 0) {
        directory(pe::DirectoryExport, exportDirectory, exportSize);
    }
    if (descriptors != 0) {
        directory(pe::DirectoryImport, descriptors, static_cast<std::uint32_t>((normalCount + 1) * 20));
    }
    if (delayDescriptors != 0) {
        directory(pe::DirectoryDelayImport, delayDescriptors, static_cast<std::uint32_t>((delayCount + 1) * 32));
    }
    if (boundDirectory != 0) {
        directory(pe::DirectoryBoundImport, boundDirectory, 16);
    }

    const std::uint32_t s = o + 0xf0;
    std::memcpy(file.data() + s, ".rdata", 6);
    pe::WriteU32(file, s + 8, contentSize);
    pe::WriteU32(file, s + 12, SectionRva);
    pe::WriteU32(file, s + 16, rawSize);
    pe::WriteU32(file, s + 20, rawOffset);
    pe::WriteU32(file, s + 36, 0x40000040);

    if (spec.certificateBytes != 0) {
        const std::uint32_t certificate = pe::AlignUp(static_cast<std::uint32_t>(file.size()), 8);
        file.resize(certificate + spec.certificateBytes, 0xcc);
        directory(pe::DirectorySecurity, certificate, spec.certificateBytes);
    }
    return file;
}

}
