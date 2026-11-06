/* Proves that a Windows PE/DLL can resolve the pinned upstream v4 ABI name,
 * invoke a synthetic recompiled function and reject an invalid native module.
 * No original PS4 ELF or original game code is loaded or executed.
 */
#include "recomp_abi.h"
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#ifdef _WIN32
#include <windows.h>
typedef HMODULE Lib;
static Lib open_lib(const char *name) { return LoadLibraryA(name); }
static void *get_sym(Lib lib, const char *name) { return (void *)GetProcAddress(lib, name); }
static void close_lib(Lib lib) { if (lib) FreeLibrary(lib); }
#else
#include <dlfcn.h>
typedef void *Lib;
static Lib open_lib(const char *name) { return dlopen(name, RTLD_NOW | RTLD_LOCAL); }
static void *get_sym(Lib lib, const char *name) { return dlsym(lib, name); }
static void close_lib(Lib lib) { if (lib) dlclose(lib); }
#endif
/* Synthetic opaque layout used ONLY by this test. Upstream BbCpu has more fields. */
struct BbCpu { uint64_t r[16]; uint64_t rip; };
static uint64_t step(BbCpu *cpu) { return cpu->rip + 4; }
static int inspect(const char *path, int should_succeed) {
    Lib lib = open_lib(path);
    if (!lib) return 12;
    RcInit init = (RcInit)get_sym(lib, BB_RECOMP_INIT);
    if (!init) { close_lib(lib); return 13; }
    RcApi api;
    memset(&api, 0, sizeof(api));
    api.version = BB_RECOMP_API_VERSION;
    api.image_base = 0x400000;
    api.step = step;
    size_t count = 0;
    const RcFunction *f = init(&api, &count);
    int ok = (f != NULL && count == 1 && f[0].offset == 0x1000 &&
              f[0].size == 12 && f[0].fn != NULL);
    if (ok && should_succeed) {
        BbCpu cpu;
        memset(&cpu, 0, sizeof(cpu));
        cpu.r[0] = 11;
        cpu.rip = 0x2000;
        f[0].fn(&cpu);
        ok = (cpu.r[0] == 18 && cpu.rip == 0x2004);
    }
    close_lib(lib);
    return ok == should_succeed ? 0 : 14;
}
int main(int argc, char **argv) {
    if (argc != 3) return 2;
    int a = inspect(argv[1], 1);
    int b = inspect(argv[2], 0);
    if (a || b) {
        fprintf(stderr, "V187 native module ABI smoke FAILED good=%d negative=%d\n", a, b);
        return 1;
    }
    puts("V187_NATIVE_WINDOWS_LINUX_RECOMP_ABI_V4_SYNTHETIC_DLL_PASS");
    puts("NOT a Bloodborne game library, actual recompilation, PS4-free game boot or graphics proof");
    return 0;
}
