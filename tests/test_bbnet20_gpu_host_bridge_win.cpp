/* Windows PE DLL ↔ primary EXE GPU callback bridge smoke.
 * Test-only host exports two GPU APIs. The adapter MUST forward to the actual
 * running .exe, not a duplicated graphics state inside its DLL.
 */
#include "../gpu/bbgpu.h"
#include <windows.h>
#include <cassert>
#include <cstdio>
#include <cstring>

static BbGpuEventFilter registered;
static unsigned banner_updates;
static char banner[200] = {0};

extern "C" void bbgpu_add_event_filter(BbGpuEventFilter callback) {
    registered = callback;
}
extern "C" void bbgpu_overlay_banner(const char* text) {
    ++banner_updates;
    if (!text) {
        banner[0] = 0;
    } else {
        std::snprintf(banner, sizeof(banner), "%s", text);
    }
}
/* These test-only exports emulate the two unique wrappers in the REAL
 * bbport.exe. The test DLL has NO copies of the renderer's callback state. */
extern "C" __declspec(dllexport)
void bbnet20_exe_add_event_filter(BbGpuEventFilter callback) {
    bbgpu_add_event_filter(callback);
}
extern "C" __declspec(dllexport)
void bbnet20_exe_overlay_banner(const char* message) {
    bbgpu_overlay_banner(message);
}
static int ConsumeEvent(const void* event, void* window) {
    return event == reinterpret_cast<const void*>(0x1234) && window == nullptr;
}

int main(int argc, char** argv) {
    assert(argc == 2 && argv[1][0]);
    HMODULE self = GetModuleHandleW(nullptr);
    assert(self);
    assert(GetProcAddress(self, "bbnet20_exe_add_event_filter"));
    assert(GetProcAddress(self, "bbnet20_exe_overlay_banner"));
    HMODULE plugin = LoadLibraryA(argv[1]);
    if (!plugin) {
        std::printf("LoadLibrary failed %lu\n", GetLastError());
        return 2;
    }
    typedef void (*Register)(BbGpuEventFilter);
    typedef void (*Banner)(const char*);
    const Register register_cb = reinterpret_cast<Register>(
        GetProcAddress(plugin, "bbnet20_host_add_event_filter"));
    const Banner show = reinterpret_cast<Banner>(
        GetProcAddress(plugin, "bbnet20_host_overlay_banner"));
    assert(register_cb && show);
    register_cb(&ConsumeEvent);
    assert(registered == &ConsumeEvent);
    assert(registered(reinterpret_cast<const void*>(0x1234), nullptr) == 1);
    show("Joining the host's world...");
    assert(banner_updates == 1);
    assert(std::strcmp(banner, "Joining the host's world...") == 0);
    show(nullptr);
    assert(banner_updates == 2 && banner[0] == 0);
    assert(FreeLibrary(plugin));
    std::puts("REAL Win64 bridge: separate DLL forwarded SDL + banner to host EXE PASS");
    return 0;
}
