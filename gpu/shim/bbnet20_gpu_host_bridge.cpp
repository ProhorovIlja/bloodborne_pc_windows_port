// SPDX-License-Identifier: GPL-2.0-or-later
// Experimental Windows-only bridge for the REAL bbnet20 plugin.
//
// Linux links bbnet20 to a shared libbbgpu, while this port normally links
// bbgpu STATIC into bbport.exe. Calling bbgpu_* from the plugin's separate
// copy would silently register callbacks into an invisible SDL window state.
// Resolve only two narrowly exported C functions from the REAL executable.
// No game/online hooks are installed here, and missing exports fail closed.
#include "../bbgpu.h"
#ifdef _WIN32
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <cstdio>

namespace {
template <typename F>
F ResolveHost(const char* name) {
    const HMODULE game = GetModuleHandleW(nullptr);
    return game ? reinterpret_cast<F>(GetProcAddress(game, name)) : nullptr;
}
using EventRegister = void (*)(BbGpuEventFilter);
using BannerSet = void (*)(const char*);
} // namespace

extern "C" void bbnet20_host_add_event_filter(BbGpuEventFilter filter) {
    if (!filter) return;
    if (const auto host = ResolveHost<EventRegister>("bbgpu_add_event_filter")) {
        host(filter);
    } else {
        std::fputs("BBSC Win64: host event filter export unavailable; cinematic disabled\n", stderr);
    }
}

extern "C" void bbnet20_host_overlay_banner(const char* message) {
    if (const auto host = ResolveHost<BannerSet>("bbgpu_overlay_banner")) {
        host(message);
    }
}
#endif
