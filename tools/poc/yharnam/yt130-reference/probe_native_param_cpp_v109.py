#!/usr/bin/env python3
"""Compile and EXECUTE the unmodified original staged YT1.3 ParamTableSize C++.

Extract the actual function text from the true pinned emulator/src/core/
bloodborne_party.cpp staged AFTER native PR442 patch, not a second copy of
its implementation. Compile that function with g++ -std=c++20 under bounds,
overflow and stable-size assertions. Does NOT claim whole-game binary works.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess
import tempfile

TAG = "SHYT-YT130-PR442-PARAM-SPAN-V109"
START = "u64 ParamTableSize(std::span<const u8> param, u16 rows, u64 row_size) {"
END = "\n}\n\nRecreatePlan PlanRecreate"

def extract(source: str) -> str:
    if source.count(START) != 1 or source.count(END) != 1 or TAG not in source:
        raise ValueError("Pinned original C++ PARAM function location changed")
    start = source.index(START)
    end = source.index(END, start)
    body = source[start:end + 3]
    for mark in ("std::memcpy(&offset", "param.size() < entries",
                 "std::numeric_limits<u64>::max()", "offset + row_size"):
        if mark not in body:
            raise ValueError("Pinned C++ PARAM helper missing required safety guard: " + mark)
    return body

CPP_HEAD = """#include <algorithm>
#include <cassert>
#include <cstdint>
#include <cstring>
#include <limits>
#include <optional>
#include <ranges>
#include <span>
#include <string>
#include <string_view>
#include <utility>
#include <vector>
using u8=std::uint8_t;
using u16=std::uint16_t;
using u64=std::uint64_t;
"""

SLOT_CPP_TESTS = """
    LoadedParamSlots cache;
    assert(!cache.Slot("NPC_PARAM_ST"));
    cache.Found("NPC_PARAM_ST", 0x40);
    cache.Found("SP_EFFECT_PARAM_ST", 0x1f8);
    assert(cache.Slot("NPC_PARAM_ST") == std::optional<u64>{0x40});
    assert(cache.Slot("SP_EFFECT_PARAM_ST") == std::optional<u64>{0x1f8});
    cache.Found("NPC_PARAM_ST", 0x48);
    assert(cache.Slot("NPC_PARAM_ST") == std::optional<u64>{0x48});
    assert(!cache.Slot("UNKNOWN_PARAM_ST"));
"""

CPP_TESTS = """
int main() {
    std::vector<u8> rows(0x40 + 3 * 24);
    const auto set = [&](unsigned i, u64 v) {
        std::memcpy(rows.data() + 0x40 + i * 24 + 8, &v, sizeof(v));
    };
    set(0, 0x100); set(1, 0x400); set(2, 0x200);
    assert(ParamTableSize(rows, 3, 0x184) == 0x584);
    set(0, 0x30); set(1, 0x10); set(2, 0x20);
    assert(ParamTableSize(rows, 3, 0x10) == 0x40 + 3 * 24);
    assert(ParamTableSize(rows, 0, 0x10) == 0x40);
    assert(ParamTableSize(rows, 4, 0x10) == std::numeric_limits<u64>::max());
    set(0, std::numeric_limits<u64>::max() - 4);
    assert(ParamTableSize(rows, 3, 0x184) == std::numeric_limits<u64>::max());
    return 0;
}
"""

def extract_slots(header: str, source: str) -> tuple[str, str]:
    head_start = "class LoadedParamSlots {"
    head_end = "\n};\nu64 ParamTableSize"
    cpp_start = "std::optional<u64> LoadedParamSlots::Slot("
    cpp_end = "u64 ParamTableSize("
    if (header.count(head_start) != 1 or header.count(head_end) != 1 or
            source.count(cpp_start) != 1 or source.count(cpp_end) != 1 or
            "SHYT-YT130-PR442-PARAM-SLOTS-V110" not in header or
            "SHYT-YT130-PR442-PARAM-SLOTS-V110" not in source):
        raise ValueError("Pinned actual native slot cache class/methods source drift")
    a = header.index(head_start)
    b = header.index(head_end, a)
    declaration = header[a:b + 3]
    x = source.index(cpp_start)
    y = source.index(cpp_end, x)
    implementations = source[x:y]
    if (implementations.count("LoadedParamSlots::Found(") != 1 or
            "known->second = slot;" not in implementations or
            "slots.emplace_back(" not in implementations):
        raise ValueError("Native slot cache lost reload/creation semantics")
    return declaration, implementations


def probe(path: Path, header: Path) -> None:
    source = path.read_text(encoding="utf-8")
    body = extract(source)
    klass, methods = extract_slots(header.read_text(encoding="utf-8"), source)
    with tempfile.TemporaryDirectory(prefix="yt130-param-cpp-") as temporary:
        base = Path(temporary)
        src = base / "test.cpp"
        binary = base / "test"
        src.write_text(CPP_HEAD + "\n" + klass + "\n" + methods + "\n" + body +
                       "\n" + CPP_TESTS.replace("    return 0;", SLOT_CPP_TESTS + "    return 0;"),
                       encoding="utf-8")
        subprocess.run(["g++", "-std=c++20", "-O2", "-Wall", "-Wextra", "-Werror",
                        str(src), "-o", str(binary)], check=True, timeout=90)
        subprocess.run([str(binary)], check=True, timeout=15)
    print("SHYT_YT130_PR442_ACTUAL_ORIGINAL_CPP_PARAM_SPAN_AND_SLOT_CACHE_COMPILED_EXECUTED_PASS")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--header", type=Path, required=True)
    opts = parser.parse_args()
    probe(opts.source, opts.header)
