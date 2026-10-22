/* Win64 smoke test of the actual opt-in loader, without game files or network.
 * Run absent first (no DLL), then present with the fixture compiled to gpu/bbnet20.dll.
 */
#include "../src/runtime_legacy_host.h"
#include "../src/runtime_legacy_net.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <windows.h>

/* Minimal game/runtime adapters for the native loader under test. */
const char *runtime_symbol(const char *nid) { return nid; }
int runtime_memory_is_mapped(uintptr_t address,uint64_t length) {
    return address == 0x1234 && length == 16;
}
int32_t runtime_legacy_thread_spawn(void **t,void *(__attribute__((sysv_abi)) *f)(void *),
                                   void *arg,uint64_t stack,const char *name) {
    (void)t;(void)f;(void)arg;(void)stack;(void)name;
    return -1;
}
int32_t runtime_legacy_thread_join(void *t,void **ret) {
    (void)t;(void)ret;return -1;
}
__attribute__((noreturn)) void runtime_legacy_thread_exit(void *p) {
    (void)p;ExitProcess(1);
}
int main(int argc,char **argv) {
    assert(argc==2);
    assert(SetEnvironmentVariableA("BB_LEGACY_NET","1"));
    assert(SetEnvironmentVariableA("BB_PARTY",NULL));
    runtime_legacy_net_configure("C:/user/game","CUSA03173","Bloodborne","1.09");
    assert(runtime_legacy_net_requested());
    if (!strcmp(argv[1],"absent")) {
        assert(runtime_legacy_net_resolve("sceNetSocket")==0);
        assert(runtime_legacy_net_resolve("sceAudioOutOpen")==0);
        puts("BBSC DLL absent: offline fallback PASS"); return 0;
    }
    if (!strcmp(argv[1],"conflict")) {
        SetEnvironmentVariableA("BB_PARTY","host");
        assert(!runtime_legacy_net_requested());
        assert(runtime_legacy_net_resolve("sceNetSocket")==0);
        puts("BBSC vs BBP3 conflict: party wins PASS"); return 0;
    }
    if (strcmp(argv[1],"present")) return 2;
    assert(runtime_legacy_net_resolve("sceAudioOutOpen")==0);
    assert(runtime_legacy_net_resolve("sceNetSocket")==0x567890);
    assert(runtime_legacy_net_resolve("sceNpMatching2JoinRoom")==0);
    uint8_t scratch[32]={0};
    runtime_legacy_net_image_mapped(scratch,sizeof(scratch));
    runtime_legacy_net_image_ready(0x1234,sizeof(scratch));
    runtime_legacy_net_start();
    HMODULE dll=GetModuleHandleW(L"bbnet20.dll");
    assert(dll);
    typedef unsigned (*Status)(void);
    Status status=(Status)(void*)GetProcAddress(dll,"bbnet_mock_status");
    assert(status && status()==15);
    SetEnvironmentVariableA("BB_PARTY","host");
    assert(!runtime_legacy_net_requested());
    assert(runtime_legacy_net_resolve("sceNetSocket")==0);
    puts("BBSC DLL host ABI, callbacks, image hooks, and party isolation PASS");
    return 0;
}
