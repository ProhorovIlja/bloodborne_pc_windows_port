#!/usr/bin/env python3
"""Port original YT PR442 LoadedParamSlots into pinned native 1.3 client.

FindLoadedParamWhere rescanned up to 1,024 candidate slots each call. Cache a
type's last successful slot, re-VALIDATE the complete pointer chain and type
(and requested callback), and only re-scan if the cached slot went stale.
A mutex protects cache metadata only, never guest ReadValue or found callbacks.
This is a source-locked native game candidate, not measured in-game FPS.

Apply AFTER native V107 invasions and V109 PARAM span at pinned protocol-8
original upstream 0645740a33ae21c56df3b4a0d9777086dbca6053.
"""
from __future__ import annotations
from pathlib import Path
import subprocess

PIN = "0645740a33ae21c56df3b4a0d9777086dbca6053"
TAG = "SHYT-YT130-PR442-PARAM-SLOTS-V110"
CPP = "emulator/src/core/bloodborne_party.cpp"
HEADER = "emulator/src/core/bloodborne_party.h"
RULES = "emulator/src/core/bloodborne_party_rules.cpp"
TEST = "emulator/tests/bloodborne/test_bloodborne_harder_enemies.cpp"
FILES = (CPP, HEADER, RULES, TEST)

def one(source: str, old: str, new: str, name: str) -> str:
    matches = source.count(old)
    if matches != 1:
        raise ValueError(f"{TAG}: native 1.3 original source drift {name} {matches}")
    return source.replace(old, new, 1)

SLOT_CLASS = """// SHYT-YT130-PR442-PARAM-SLOTS-V110: verified native PR442 repo-slot cache.
class LoadedParamSlots {
public:
    std::optional<u64> Slot(std::string_view type) const;
    void Found(std::string_view type, u64 slot);
private:
    std::vector<std::pair<std::string, u64>> slots;
};
"""

SLOT_METHODS = """// SHYT-YT130-PR442-PARAM-SLOTS-V110: only last known table SLOT is cached.
// Each access still revalidates pointer chain, type, and caller's predicate.
std::optional<u64> LoadedParamSlots::Slot(std::string_view type) const {
    const auto known = std::ranges::find(slots, type, &std::pair<std::string, u64>::first);
    return known == slots.end() ? std::nullopt : std::optional<u64>{known->second};
}

void LoadedParamSlots::Found(std::string_view type, u64 slot) {
    const auto known = std::ranges::find(slots, type, &std::pair<std::string, u64>::first);
    if (known != slots.end()) {
        known->second = slot;
        return;
    }
    slots.emplace_back(std::string{type}, slot);
}

"""

RULE_FUNCTION = """template <typename Found>
u64 FindLoadedParamWhere(std::string_view type, Found&& found) {
    const u64 repository = ReadValue<u64>(image_base + SoloParamRepositoryPointerOffset, 0);
    if (repository < 0x10000 || !HasMemoryAccess(repository, 0x2000, MemoryProt::CpuRead)) {
        return 0;
    }
    // SHYT-YT130-PR442-PARAM-SLOTS-V110: preserve ALL pointer and type checks
    // even for cached entries, since PARAM tables can be unloaded/reloaded.
    const auto find_at = [&](u64 slot) -> u64 {
        const u64 holder = ReadValue<u64>(repository, slot);
        if (holder < 0x10000 || !HasMemoryAccess(holder, 0x78, MemoryProt::CpuRead))
            return 0;
        const u64 inner = ReadValue<u64>(holder, 0x70);
        if (inner < 0x10000 || !HasMemoryAccess(inner, 0x78, MemoryProt::CpuRead))
            return 0;
        const u64 param = ReadValue<u64>(inner, 0x70);
        if (param < 0x10000 || !HasMemoryAccess(param, 0x40, MemoryProt::CpuRead))
            return 0;
        return IsParamOfType({reinterpret_cast<const u8*>(param), 0x40}, type) && found(param)
                   ? param : 0;
    };
    static std::mutex cache_mutex;
    static LoadedParamSlots slots;
    std::optional<u64> remembered;
    {
        std::scoped_lock guard{cache_mutex};
        remembered = slots.Slot(type);
    }
    if (remembered) {
        if (const u64 result = find_at(*remembered); result != 0)
            return result;
    }
    for (u64 slot = 0; slot < 0x2000; slot += 8) {
        if (const u64 result = find_at(slot); result != 0) {
            std::scoped_lock guard{cache_mutex};
            slots.Found(type, slot);
            return result;
        }
    }
    return 0;
}
"""

OLD_RULE_FUNCTION = """template <typename Found>
u64 FindLoadedParamWhere(std::string_view type, Found&& found) {
    const u64 repository = ReadValue<u64>(image_base + SoloParamRepositoryPointerOffset, 0);
    if (repository < 0x10000 || !HasMemoryAccess(repository, 0x2000, MemoryProt::CpuRead)) {
        return 0;
    }
    for (u64 slot = 0; slot < 0x2000; slot += 8) {
        const u64 holder = ReadValue<u64>(repository, slot);
        if (holder < 0x10000 || !HasMemoryAccess(holder, 0x78, MemoryProt::CpuRead)) {
            continue;
        }
        const u64 inner = ReadValue<u64>(holder, 0x70);
        if (inner < 0x10000 || !HasMemoryAccess(inner, 0x78, MemoryProt::CpuRead)) {
            continue;
        }
        const u64 param = ReadValue<u64>(inner, 0x70);
        if (param < 0x10000 || !HasMemoryAccess(param, 0x40, MemoryProt::CpuRead)) {
            continue;
        }
        if (IsParamOfType({reinterpret_cast<const u8*>(param), 0x40}, type) && found(param)) {
            return param;
        }
    }
    return 0;
}
"""

TEST_CASE = """// SHYT-YT130-PR442-PARAM-SLOTS-V110: original game's native GTest.
TEST(LoadedParamSlots, RememberEachTypeAndUpdateAfterReload) {
    LoadedParamSlots slots;
    EXPECT_FALSE(slots.Slot("NPC_PARAM_ST"));
    slots.Found("NPC_PARAM_ST", 0x40);
    slots.Found("SP_EFFECT_PARAM_ST", 0x1F8);
    EXPECT_EQ(slots.Slot("NPC_PARAM_ST"), std::optional<u64>{0x40});
    EXPECT_EQ(slots.Slot("SP_EFFECT_PARAM_ST"), std::optional<u64>{0x1F8});
    slots.Found("NPC_PARAM_ST", 0x48);
    EXPECT_EQ(slots.Slot("NPC_PARAM_ST"), std::optional<u64>{0x48});
    EXPECT_FALSE(slots.Slot("UNKNOWN_PARAM_ST"));
}
"""

def patch(sources: dict[str, str]) -> dict[str, str]:
    if set(sources) != set(FILES):
        raise ValueError(f"{TAG}: all four original game sources required")
    if any(TAG in value for value in sources.values()):
        raise ValueError(f"{TAG}: reapplication of original client patch")
    if any("SHYT-YT130-PR442-PARAM-SPAN-V109" not in sources[x]
           for x in (CPP, HEADER, RULES, TEST)):
        raise ValueError(f"{TAG}: apply checked-span V109 before slot cache")
    out = dict(sources)
    out[CPP] = one(sources[CPP],
        "u64 ParamTableSize(std::span<const u8> param, u16 rows, u64 row_size) {",
        SLOT_METHODS + "u64 ParamTableSize(std::span<const u8> param, u16 rows, u64 row_size) {",
        "native game slot cache implementation")
    out[HEADER] = one(sources[HEADER],
        "u64 ParamTableSize(std::span<const u8> param, u16 rows, u64 row_size);",
        SLOT_CLASS + "u64 ParamTableSize(std::span<const u8> param, u16 rows, u64 row_size);",
        "native game slot-cache public contract")
    out[RULES] = one(sources[RULES], OLD_RULE_FUNCTION, RULE_FUNCTION,
                     "game actual 1024-slot lookup with repeat validation")
    out[TEST] = sources[TEST].rstrip() + "\n\n" + TEST_CASE.rstrip() + "\n"
    return out

def stage(root: Path) -> None:
    root = root.resolve(strict=True)
    head = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"],
                          capture_output=True, text=True, check=True).stdout.strip()
    if head != PIN:
        raise ValueError(f"{TAG}: wrong official v1.3 pin {head}")
    originals = {}
    for name in FILES:
        p = root / name
        if not p.is_file() or p.is_symlink():
            raise ValueError(f"{TAG}: missing source {name}")
        originals[name] = p.read_text(encoding="utf-8")
    result = patch(originals)
    for name, content in result.items():
        (root / name).write_text(content, encoding="utf-8")
    print(f"{TAG} ORIGINAL_NATIVE_CLIENT_SLOT_CACHE_STAGED")

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        raise SystemExit("usage: stage_native_param_slots_v110.py PINNED_YT130_CHECKOUT")
    stage(Path(sys.argv[1]))
