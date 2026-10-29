#!/usr/bin/env python3
"""Selective original YT 1.3 game optimization from official upstream PR #442.

The enemy-scaling WritableParam() checks memory once for the whole table of
row entries, but previously issues one ReadValue()/HasMemoryAccess() per row.
Port ParamTableSize from original upstream lKaniel/bloodborne-server PR #442,
with explicit malformed-span and offset-overflow guards. Game data and damage
multipliers do not change. Not a server or deployed-client FPS claim.

Run AFTER patch_original_multi_invader_client_v107.py on the pinned official
YT 1.3.0 commit 0645740a33ae21c56df3b4a0d9777086dbca6053.
"""
from __future__ import annotations
from pathlib import Path
import subprocess

PIN = "0645740a33ae21c56df3b4a0d9777086dbca6053"
TAG = "SHYT-YT130-PR442-PARAM-SPAN-V109"
CPP = "emulator/src/core/bloodborne_party.cpp"
HEADER = "emulator/src/core/bloodborne_party.h"
RULES = "emulator/src/core/bloodborne_party_rules.cpp"
TEST = "emulator/tests/bloodborne/test_bloodborne_harder_enemies.cpp"
FILES = (CPP, HEADER, RULES, TEST)

def replace_once(source: str, old: str, new: str, label: str) -> str:
    count = source.count(old)
    if count != 1:
        raise ValueError(f"{TAG} source anchor drift {label}: {count}")
    return source.replace(old, new, 1)

PARAM_FUNCTION = """// SHYT-YT130-PR442-PARAM-SPAN-V109: port upstream PR #442.
 // The original game has ALREADY validated this entire PARAM entry span.
 // The 21k per-row ReadValue/HasMemoryAccess checks caused guest stutters.
u64 ParamTableSize(std::span<const u8> param, u16 rows, u64 row_size) {
    const u64 entries = 0x40 + u64{rows} * 24;
    if (param.size() < entries) return std::numeric_limits<u64>::max();
    u64 size = entries;
    for (u64 row = 0; row < rows; ++row) {
        u64 offset = 0;
        std::memcpy(&offset, param.data() + 0x40 + row * 24 + 8, sizeof(offset));
        if (offset > std::numeric_limits<u64>::max() - row_size)
            return std::numeric_limits<u64>::max();
        size = std::max(size, offset + row_size);
    }
    return size;
}

""".replace("\n //", "\n//")

TEST_CASE = """// SHYT-YT130-PR442-PARAM-SPAN-V109: original GTest, not a mock implementation.
TEST(LoadedParamMemory, FullTableSpanFindsFurthestOffsetWithoutRowReads) {
    std::vector<u8> bytes(0x40 + 3 * 24);
    const auto put = [&](std::size_t row, u64 value) {
        std::memcpy(bytes.data() + 0x40 + 24 * row + 8, &value, sizeof(value));
    };
    put(0, 0x100);
    put(1, 0x400);
    put(2, 0x200);
    EXPECT_EQ(ParamTableSize(bytes, 3, 0x184), u64{0x584});
    put(0, 0x30);
    put(1, 0x10);
    put(2, 0x20);
    EXPECT_EQ(ParamTableSize(bytes, 3, 0x10), u64{0x40 + 3 * 24});
    EXPECT_EQ(ParamTableSize(bytes, 0, 0x10), u64{0x40});
}

TEST(LoadedParamMemory, RejectsTruncatedAndOverflowingEntries) {
    std::vector<u8> short_entries(0x40 + 24);
    EXPECT_EQ(ParamTableSize(short_entries, 2, 0x20),
              std::numeric_limits<u64>::max());
    u64 overflow = std::numeric_limits<u64>::max() - 4;
    std::memcpy(short_entries.data() + 0x40 + 8, &overflow, sizeof(overflow));
    EXPECT_EQ(ParamTableSize(short_entries, 1, 0x184),
              std::numeric_limits<u64>::max());
}

"""

def patch(sources: dict[str, str]) -> dict[str, str]:
    if set(sources) != set(FILES):
        raise ValueError(f"{TAG} exact four original game source files required")
    output = dict(sources)
    if any(TAG in body for body in sources.values()):
        raise ValueError(f"{TAG} already applied")
    output[CPP] = replace_once(
        sources[CPP],
        "RecreatePlan PlanRecreate(std::span<const std::optional<std::string>> found,",
        PARAM_FUNCTION +
        "RecreatePlan PlanRecreate(std::span<const std::optional<std::string>> found,",
        "shared native game PARAM span helper")
    output[HEADER] = replace_once(
        sources[HEADER],
        "bool IsParamOfType(std::span<const u8> param, std::string_view type);\n",
        ("bool IsParamOfType(std::span<const u8> param, std::string_view type);\n"
         "// SHYT-YT130-PR442-PARAM-SPAN-V109: one checked PARAM span, no repeated memory probes.\n"
         "u64 ParamTableSize(std::span<const u8> param, u16 rows, u64 row_size);\n"),
        "public PARAM size declaration")
    output[RULES] = replace_once(
        sources[RULES],
        ("    u64 size = entries;\n"
         "    for (u64 row = 0; row < rows; ++row) {\n"
         "        size = std::max(size, ReadValue<u64>(param, 0x40 + row * 24 + 8) + row_size);\n"
         "    }\n"),
        ("    // SHYT-YT130-PR442-PARAM-SPAN-V109: read already-checked rows directly.\n"
         "    const u64 size = ParamTableSize(\n"
         "        {reinterpret_cast<const u8*>(param), entries}, rows, row_size);\n"),
        "replace twenty-thousand independent memory probes")
    output[TEST] = sources[TEST].rstrip() + "\n\n" + TEST_CASE
    return output

def stage(root: Path) -> None:
    root = root.resolve(strict=True)
    revision = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"], text=True,
        capture_output=True, check=True).stdout.strip()
    if revision != PIN:
        raise ValueError(f"{TAG}: wrong original YT1.3 pin {revision}")
    originals = {}
    for name in FILES:
        target = root / name
        if not target.is_file() or target.is_symlink():
            raise ValueError(f"{TAG}: missing original game file {name}")
        originals[name] = target.read_text(encoding="utf-8")
    transformed = patch(originals)
    for name, updated in transformed.items():
        (root / name).write_text(updated, encoding="utf-8")
    print(f"{TAG} ORIGINAL_CLIENT_PARAM_SPAN_STAGED")

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        raise SystemExit("usage: stage_native_param_memory_v109.py PINNED_YT130_CHECKOUT")
    stage(Path(sys.argv[1]))
