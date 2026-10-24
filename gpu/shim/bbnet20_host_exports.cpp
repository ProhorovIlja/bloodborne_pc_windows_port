// SPDX-License-Identifier: GPL-2.0-or-later
// The *primary executable's* only two exports for experimental Win64 bbnet20.
//
// bbport.exe links the full bbgpu STATIC library. Exporting bbgpu's own
// callback symbols would also export duplicates when the same static
// library is transitively linked into bbnet20.dll. Instead, expose these
// uniquely named and narrowly scoped wrappers from the real process.
// The DLL loads them with GetModuleHandleW(nullptr)/GetProcAddress.
// No network hooks or renderer state are owned by these wrappers.
#include "../bbgpu.h"
#ifdef _WIN32
extern "C" __declspec(dllexport)
void bbnet20_exe_add_event_filter(BbGpuEventFilter filter) {
    bbgpu_add_event_filter(filter);
}

extern "C" __declspec(dllexport)
void bbnet20_exe_overlay_banner(const char* message) {
    bbgpu_overlay_banner(message);
}
#endif
