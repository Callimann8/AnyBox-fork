import struct
import sys
import tempfile
from pathlib import Path

TOOLS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(TOOLS))


def write(root, relative, text):
    path = Path(root) / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def library(root, name, dlls, header="", sources=None, forwards=None):
    base = f"core/libs/xdll/{name}"
    write(root, f"{base}/Imports.txt", "".join(f"{dll}\n" for dll in dlls))
    write(root, f"{base}/CMakeLists.txt", f"anybox_add_xdll({name} SOURCES Export.cpp)\n")
    write(root, f"{base}/{name}.hpp", f'#pragma once\n#include "xdll/{name}/include/Exports.hpp"\n')
    write(root, f"{base}/include/Exports.hpp", '#pragma once\n#include "AbxApi.hpp"\n' + header)
    for file, text in (sources or {}).items():
        write(root, f"{base}/{file}", text)
    if forwards:
        write(root, f"{base}/Forwards.def", "EXPORTS\n" + "".join(f"    {line}\n" for line in forwards))


def temp_root():
    directory = tempfile.TemporaryDirectory()
    write(directory.name, "core/relinker/HostDlls.txt", "kernel32.dll\napi-ms-win-*\n")
    return directory


def synthetic_pe(imports):
    section_rva, raw = 0x1000, 0x200
    content = bytearray()

    def allocate(size, align=8):
        while len(content) % align:
            content.append(0)
        rva = section_rva + len(content)
        content.extend(b"\0" * size)
        return rva

    def put(rva, fmt, *values):
        struct.pack_into(fmt, content, rva - section_rva, *values)

    descriptors = allocate((len(imports) + 1) * 20, 4)
    for index, (dll, functions) in enumerate(imports):
        table = allocate((len(functions) + 1) * 8)
        for slot, function in enumerate(functions):
            if isinstance(function, int):
                put(table + slot * 8, "<Q", (1 << 63) | function)
            else:
                hint = allocate(2 + len(function) + 1, 2)
                content[hint - section_rva + 2:hint - section_rva + 2 + len(function)] = function.encode()
                put(table + slot * 8, "<Q", hint)
        name = allocate(len(dll) + 1, 2)
        content[name - section_rva:name - section_rva + len(dll)] = dll.encode()
        put(descriptors + index * 20, "<IIIII", table, 0, 0, name, table)
    size = (len(content) + 0x1FF) & ~0x1FF
    data = bytearray(raw + size)
    data[raw:raw + len(content)] = content
    data[0:2] = b"MZ"
    struct.pack_into("<I", data, 0x3C, 0x40)
    data[0x40:0x44] = b"PE\0\0"
    struct.pack_into("<HHIIIHH", data, 0x44, 0x8664, 1, 0, 0, 0, 0xF0, 0x22)
    optional = 0x58
    struct.pack_into("<H", data, optional, 0x20B)
    struct.pack_into("<I", data, optional + 60, raw)
    struct.pack_into("<H", data, optional + 68, 14)
    struct.pack_into("<I", data, optional + 108, 16)
    struct.pack_into("<II", data, optional + 112 + 8, descriptors, (len(imports) + 1) * 20)
    section = optional + 0xF0
    data[section:section + 6] = b".rdata"
    struct.pack_into("<IIII", data, section + 8, len(content), section_rva, size, raw)
    return bytes(data)
