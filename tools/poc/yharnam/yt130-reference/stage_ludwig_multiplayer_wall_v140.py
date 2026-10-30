#!/usr/bin/env python3
"""V140: source-exact Yharnam Together #451 Ludwig exit wall co-op QOL.

Only adds the m34_00 event 13400010 object's 3401801 to the existing
MultiplayerWalls() list and mirrors the original upstream regression test.
The original Protocol8 native YT1.3 code is retained. No networking, DLC
events, DBNO, server, save, or retail game files are changed.
"""
from __future__ import annotations
import argparse
import hashlib
from pathlib import Path
import subprocess

BASE_PIN = "0645740a33ae21c56df3b4a0d9777086dbca6053"
REVIEWED_PIN = "3b0a0d8dc86d9ae726e2b0e836a46b4f46a346ed"
GAME = "emulator/src/core/bloodborne_party.cpp"
TEST = "emulator/tests/bloodborne/test_bloodborne_party_controller.cpp"
BASE_BLOBS = {
    GAME: "5186b4ed9fa9387752f4dc21362950d70d062505",
    TEST: "e820d070ec751d9983c5ecf30e540bcf9a4029d5",
}
REVIEWED_BLOBS = {
    GAME: "3c54d313ea0312b647d6ae503abf306de4aba7b8",
    TEST: "1aca044d984b52d4430672540a31ba1f28d0d41f",
}
FUNCTION_START = "std::vector<MultiplayerWall> MultiplayerWalls() {\n"
FUNCTION_END = "\nbool IsParamOfType(std::span<const u8> param, std::string_view type) {"
TEST_START = "TEST(BloodborneMultiplayerWalls, ListsTheWallsOfEveryMap) {\n"
TEST_END = "\n// Player report 2026-10-22: the Forbidden Woods' wall"
EXPECTED_OLD_FUNCTION = """std::vector<MultiplayerWall> MultiplayerWalls() {
    // InitializeEvent(_, 7600, object, sfx) in m22-m35's event files (01.09).
    static constexpr std::array<s32, 18> Walls{
        2201999, 2301999, 2401999, 2401998, 2401997, 2401996, 2401995, 2411999, 2411998,
        2411997, 2421999, 2421998, 2701999, 2701998, 2801999, 2801998, 3201999, 3501990,
    };
    std::vector<MultiplayerWall> walls;
    for (const s32 object : Walls) {
        walls.push_back(MultiplayerWall{object, object + 2000});
    }
    return walls;
}
"""
EXPECTED_NEW_FUNCTION = """std::vector<MultiplayerWall> MultiplayerWalls() {
    // InitializeEvent(_, 7600, object, sfx) in m22-m35's event files (01.09), and the Hunter's
    // Nightmare's own wall at the exit of Ludwig's arena (m34_00 event 13400010: shown while in
    // multiplayer even after Ludwig's defeat; player report 2026-10-29).
    static constexpr std::array<s32, 19> Walls{
        2201999, 2301999, 2401999, 2401998, 2401997, 2401996, 2401995, 2411999, 2411998, 2411997,
        2421999, 2421998, 2701999, 2701998, 2801999, 2801998, 3201999, 3401801, 3501990,
    };
    std::vector<MultiplayerWall> walls;
    for (const s32 object : Walls) {
        walls.push_back(MultiplayerWall{object, object + 2000});
    }
    return walls;
}
"""
TEST_OLD = """    ASSERT_EQ(walls.size(), 18u);"""
TEST_NEW = """    ASSERT_EQ(walls.size(), 19u);"""
TEST_MAP_ANCHOR = """    EXPECT_EQ(on(0x15000000), 0) << "the Hunter's Dream has none";"""
TEST_MAP_NEW = (TEST_MAP_ANCHOR + "\n"
                '    EXPECT_EQ(on(0x22000000), 1) << '
                '"the Hunter\'s Nightmare\'s own (m34_00 event 13400010)";')

def blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + bytes([0]) + data).hexdigest()

def normalized(raw: bytes) -> bytes:
    return raw.replace(b"\r\n", b"\n")

def extract(src: str, begin: str, end: str) -> str:
    if src.count(begin) != 1 or src.count(end) != 1:
        raise ValueError("V140 original game source method boundary drift")
    first = src.index(begin)
    last = src.index(end, first)
    return src[first:last]

def replace_function(original: str, reviewed: str) -> str:
    old = extract(original, FUNCTION_START, FUNCTION_END)
    new = extract(reviewed, FUNCTION_START, FUNCTION_END)
    if old != EXPECTED_OLD_FUNCTION or new != EXPECTED_NEW_FUNCTION:
        raise ValueError("V140 upstream review or pinned native wall function drift")
    return original.replace(old, new, 1)

def replace_test(original: str, reviewed: str) -> str:
    old = extract(original, TEST_START, TEST_END)
    new = extract(reviewed, TEST_START, TEST_END)
    if old.count(TEST_OLD) != 1 or old.count(TEST_MAP_ANCHOR) != 1:
        raise ValueError("V140 pinned original regression anchors drift")
    expect = old.replace(TEST_OLD, TEST_NEW, 1).replace(
        TEST_MAP_ANCHOR, TEST_MAP_NEW, 1)
    if new != expect:
        raise ValueError("V140 reviewed upstream test includes unrelated modifications")
    return original.replace(old, new, 1)

def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()

def stage(original: Path, reviewed: Path) -> None:
    original = original.resolve()
    reviewed = reviewed.resolve()
    if git(original, "rev-parse", "HEAD") != BASE_PIN or (
            git(reviewed, "rev-parse", "HEAD") != REVIEWED_PIN):
        raise ValueError("V140 unapproved original or reviewed upstream revision")
    for name, base_sha in BASE_BLOBS.items():
        if git(original, "rev-parse", "HEAD:" + name) != base_sha:
            raise ValueError("V140 pinned original game Git blob changed: " + name)
        if git(reviewed, "rev-parse", "HEAD:" + name) != REVIEWED_BLOBS[name]:
            raise ValueError("V140 original upstream PR451 reviewed Git blob changed: " + name)
        target, candidate = original / name, reviewed / name
        if not target.is_file() or target.is_symlink() or not candidate.is_file() or candidate.is_symlink():
            raise ValueError("V140 unsafe original or reviewed source file")
        raw, reviewed_raw = normalized(target.read_bytes()), normalized(candidate.read_bytes())
        if blob_sha(raw) != base_sha or blob_sha(reviewed_raw) != REVIEWED_BLOBS[name]:
            raise ValueError("V140 target modified before staged patch")
        result = (replace_function if name == GAME else replace_test)(
            raw.decode("utf-8"), reviewed_raw.decode("utf-8"))
        target.write_bytes(result.encode("utf-8"))

def native_test_fragment(game: str) -> str:
    function = extract(game, FUNCTION_START, FUNCTION_END)
    if function != EXPECTED_NEW_FUNCTION:
        raise ValueError("V140 C++ test requires exact staged original native function")
    return ("""#include <array>
#include <cstdint>
#include <vector>
#include <set>
#include <algorithm>
using s32 = std::int32_t;
struct MultiplayerWall { s32 object; s32 sfx; };
""" + function + """
int main() {
    auto walls = MultiplayerWalls();
    if (walls.size() != 19) return 1;
    std::set<s32> objects;
    for (auto wall : walls) {
        if (wall.sfx != wall.object + 2000 || !objects.insert(wall.object).second)
            return 2;
    }
    if (objects.count(3401801) != 1 || objects.count(3501990) != 1)
        return 3;
    return 0;
}
""")

def write_native_test(root: Path, output: Path) -> None:
    game = normalized((root / GAME).read_bytes()).decode("utf-8")
    output.write_text(native_test_fragment(game), encoding="utf-8")

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--original", type=Path, required=True)
    p.add_argument("--reviewed", type=Path, required=True)
    p.add_argument("--native-test", type=Path, required=True)
    args = p.parse_args()
    stage(args.original, args.reviewed)
    write_native_test(args.original, args.native_test)
    print("SHYT_V140_ORIGINAL_NATIVE_LUDWIG_WALL_SOURCE_EXACT_STAGED_NOT_REAL_GAMEPLAY")
