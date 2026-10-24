// SPDX-License-Identifier: GPL-2.0-or-later
// End-to-end native Win64 clang64 test against the ACTUAL adapted CLS source.
// No game files, network, credentials, DLL injection, emulation or real saves.
#include "core/bbsc_memscan.h"
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#include <windows.h>

#include <array>
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <span>
#include <vector>

int main() {
    constexpr std::size_t MiB = 1u << 20;
    constexpr std::size_t Size = 3 * MiB;
    auto* memory = static_cast<std::uint8_t*>(
        VirtualAlloc(nullptr, Size, MEM_RESERVE | MEM_COMMIT, PAGE_READWRITE));
    assert(memory != nullptr);
    std::memset(memory, 0x21, Size);
    constexpr std::array<std::uint8_t, 7> Signature =
        {0x42, 0x42, 0x53, 0x43, 0x2a, 0x3d, 0x79};
    const std::array<std::size_t, 3> positions =
        {1227, MiB - 3, MiB + 2345};
    for (std::size_t pos : positions)
        std::memcpy(memory + pos, Signature.data(), Signature.size());

    const std::uint64_t start = reinterpret_cast<std::uint64_t>(memory);
    const auto pattern = std::span<const std::uint8_t>(Signature);
    const auto all = Core::Bbsc::FindInMemory(pattern, start, start + Size, 6);
    assert(all.size() == positions.size());
    for (std::size_t i = 0; i < positions.size(); ++i)
        assert(all[i] == start + positions[i]);
    const auto two = Core::Bbsc::FindInMemory(pattern, start, start + Size, 2);
    assert(two.size() == 2 && two[0] == start + positions[0]);
    assert(two[1] == start + positions[1]);
    // The old upstream scanner incorrectly scanned beyond requested hi
    // when VirtualQuery returned a bigger allocation region.
    const auto first = Core::Bbsc::FindInMemory(pattern, start, start + 2000, 6);
    assert(first.size() == 1 && first[0] == start + positions[0]);
    const auto omitted = Core::Bbsc::FindInMemory(
        pattern, start + positions[0] + 1, start + positions[1], 6);
    assert(omitted.empty());
    assert(Core::Bbsc::FindInMemory({}, start, start + Size, 6).empty());
    assert(Core::Bbsc::FindInMemory(pattern, start, start + Size, 0).empty());

    DWORD old_protect = 0;
    assert(VirtualProtect(memory + 2 * MiB, 4096, PAGE_NOACCESS, &old_protect));
    const auto safe = Core::Bbsc::FindInMemory(pattern, start, start + Size, 6);
    assert(safe.size() == 3); // No crashes on an inaccessible nearby page.
    assert(VirtualFree(memory, 0, MEM_RELEASE));
    std::puts("CLS BBSC clang64 ReadProcessMemory scan PASS");
}
