// Verify real native Windows CLS BBSC hook callbacks execute inside the
// System V ABI guest code, on executable pages. No game, saves or network.
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#include <windows.h>
#include <array>
#include <atomic>
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <span>
#include "bbport_guest_code_hooks.h"

static std::atomic<unsigned> calls{0};
static std::atomic<std::uint64_t> last_argument{0};

static void __attribute__((sysv_abi))
Observer(std::uint64_t tag, const Core::GuestRegisterSnapshot* regs) {
    assert(tag == 0xB00D);
    assert(regs);
    last_argument.store(regs->rdi, std::memory_order_relaxed);
    ++calls;
}

using Guest = int(__attribute__((sysv_abi)) *)(int);

int main() {
    constexpr std::array<std::uint8_t, 8> bytes = {
        0x48, 0x89, 0xf8,       // mov rax, rdi (guest SysV first argument)
        0x48, 0x83, 0xc0, 0x05, // add rax, 5
        0xc3};                  // ret
    void* code = VirtualAlloc(nullptr, 4096, MEM_RESERVE | MEM_COMMIT, PAGE_READWRITE);
    assert(code);
    std::memcpy(code, bytes.data(), bytes.size());
    DWORD old = 0;
    assert(VirtualProtect(code, 4096, PAGE_EXECUTE_READ, &old));
    auto guest = reinterpret_cast<Guest>(code);
    assert(guest(37) == 42);
    assert(Core::InstallGuestCodeHook(
        code, std::span<const std::uint8_t>(bytes.data(), bytes.size() - 1),
        0xB00D, &Observer));
    assert(guest(17) == 22);
    assert(calls.load() == 1);
    assert(last_argument.load() == 17);
    assert(guest(37) == 42);
    assert(calls.load() == 2);
    assert(last_argument.load() == 37);
    // No duplicate trampolines or partially matched game versions.
    assert(!Core::InstallGuestCodeHook(
        code, std::span<const std::uint8_t>(bytes.data(), bytes.size() - 1),
        0xB00D, &Observer));
    assert(VirtualFree(code, 0, MEM_RELEASE));
    std::puts("REAL CLS native Win64 System V guest hook trampoline PASS");
}
