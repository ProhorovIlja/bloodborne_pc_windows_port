// SPDX-License-Identifier: GPL-2.0-or-later
// Smoke-test the REAL fully-linked native CLS bbnet20.dll, not a mock.
// This performs no game access, account login, socket use or save writes.
// The ordinary launcher dev build never contains this experimental module.
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#include <windows.h>
#include <array>
#include <cstdio>
#include <filesystem>
#include <string>

namespace fs = std::filesystem;

// Mirror the two primary EXE callbacks to ensure the same resolution surface
// as the real game. They are never invoked during this load-only smoke.
extern "C" __declspec(dllexport)
void bbnet20_exe_add_event_filter(void*) {}
extern "C" __declspec(dllexport)
void bbnet20_exe_overlay_banner(const char*) {}

int main() {
    wchar_t executable[32768]{};
    const DWORD n = GetModuleFileNameW(nullptr, executable, 32768);
    if (n == 0 || n >= 32768) {
        std::printf("Cannot locate native test host: %lu\n", GetLastError());
        return 1;
    }
    const fs::path dll = fs::path(std::wstring(executable, n)).parent_path()
                         / L"gpu" / L"bbnet20.dll";
    if (!fs::is_regular_file(dll)) {
        std::puts("Missing true native bbnet20.dll beside packaged EXE");
        return 2;
    }
    if (!SetDefaultDllDirectories(LOAD_LIBRARY_SEARCH_DEFAULT_DIRS)) {
        std::printf("Cannot configure Windows DLL search: %lu\n", GetLastError());
        return 3;
    }
    const HMODULE module = LoadLibraryExW(
        dll.c_str(), nullptr,
        LOAD_LIBRARY_SEARCH_DLL_LOAD_DIR | LOAD_LIBRARY_SEARCH_DEFAULT_DIRS);
    if (!module) {
        std::printf("Real native bbnet20.dll failed PE import resolution: %lu\n",
                    GetLastError());
        return 4;
    }
    constexpr std::array<const char*, 5> api = {
        "bbnet_init", "bbnet_resolve", "bbnet_image_mapped",
        "bbnet_image_ready", "bbnet_start"};
    for (const char* name : api) {
        if (!GetProcAddress(module, name)) {
            std::printf("Real native bbnet20.dll missing exported %s\n", name);
            FreeLibrary(module);
            return 5;
        }
    }
    if (!FreeLibrary(module)) {
        std::printf("Native DLL unload failed: %lu\n", GetLastError());
        return 6;
    }
    std::puts("REAL native Win64 CLS BBSC DLL: PE load, imports, exports PASS");
    return 0;
}
