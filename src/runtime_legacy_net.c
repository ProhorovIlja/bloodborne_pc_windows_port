/* SPDX-License-Identifier: GPL-2.0-or-later
 * Optional, disabled-by-default legacy BBSC NP module loader for native Windows.
 *
 * The existing BBP3 encrypted party is NOT bridged by this file. It remains
 * separate and takes priority. This resolves guest NP imports for a FUTURE
 * Windows port of deadinside28's bbnet20. Missing DLL -> offline stubs.
 *
 * The Linux bbnet20 upstream exported BbNetHost ABI v2. We deliberately use
 * the matching host layout so the port can be tested against the real source
 * rather than inventing another incompatible game-network API.
 */
#define _GNU_SOURCE
#include "runtime.h"
#include "runtime_legacy_net.h"
#include "runtime_legacy_policy.h"
#include "../gpu/party_env.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifdef _WIN32
#include <windows.h>
#include <wchar.h>

typedef struct BbNetHost {
    uint32_t abi;
    const char *app0, *serial, *title, *app_ver;
    int32_t (*thread_spawn)(void **thread,
        void *(ABI *entry)(void *), void *argument, uint64_t stack_size, const char *name);
    int32_t (*thread_join)(void *thread, void **result);
    void (*thread_exit)(void *result);
    int (*memory_is_mapped)(uintptr_t address, uint64_t length);
} BbNetHost;
enum { BBNET_ABI_VERSION = 2 };
typedef int (*NetInit)(const BbNetHost *);
typedef uintptr_t (*NetResolve)(const char *);
typedef void (*NetImageMapped)(uint8_t *, uint64_t);
typedef void (*NetImageReady)(uint64_t, uint64_t);
typedef void (*NetStart)(void);

static char game_folder[4096], game_serial[16], game_title[128], game_ver[16];
static HMODULE module;
static NetResolve network_resolve;
static int tried_load;

static void safe_copy(char *dst, size_t limit, const char *source) {
    if (!source) source="";
    snprintf(dst,limit,"%s",source);
}

void runtime_legacy_net_configure(const char *app0, const char *serial,
                                  const char *title, const char *version) {
    safe_copy(game_folder,sizeof(game_folder),app0);
    safe_copy(game_serial,sizeof(game_serial),serial);
    safe_copy(game_title,sizeof(game_title),title);
    safe_copy(game_ver,sizeof(game_ver),version);
}
int runtime_legacy_net_requested(void) {
    return legacy_net_opted_in(getenv("BB_LEGACY_NET"), bb_party_enabled());
}

static NetResolve load_module(void) {
    if (tried_load) return network_resolve;
    tried_load=1;
    /* An absolute executable-relative path, NOT PATH/CWD or an arbitrary env path.
     * Module and dependencies will be hash-checked in the future release staging.
     */
    wchar_t path[32768];
    DWORD n=GetModuleFileNameW(NULL,path,(DWORD)(sizeof(path)/sizeof(path[0])));
    if (!n || n>=sizeof(path)/sizeof(path[0])) {
        puts("BBSC legacy: executable path unavailable, staying offline");
        return NULL;
    }
    wchar_t *slash=wcsrchr(path,L'\\');
    if (!slash) return NULL;
    const wchar_t suffix[]=L"\\gpu\\bbnet20.dll";
    size_t prefix=(size_t)(slash-path);
    if (prefix+wcslen(suffix)+1>=sizeof(path)/sizeof(path[0])) return NULL;
    wcscpy(path+prefix,suffix);
    HMODULE candidate=LoadLibraryExW(path,NULL,
                         LOAD_LIBRARY_SEARCH_DLL_LOAD_DIR|LOAD_LIBRARY_SEARCH_DEFAULT_DIRS);
    if (!candidate) {
        puts("BBSC legacy: native bbnet20.dll is not built or loadable, staying offline");
        return NULL;
    }
    NetInit init=(NetInit)(void*)GetProcAddress(candidate,"bbnet_init");
    NetResolve resolve=(NetResolve)(void*)GetProcAddress(candidate,"bbnet_resolve");
    if (!init || !resolve) {
        puts("BBSC legacy: module ABI functions missing, staying offline");
        FreeLibrary(candidate);
        return NULL;
    }
    const BbNetHost host={
        .abi=BBNET_ABI_VERSION, .app0=game_folder, .serial=game_serial,
        .title=game_title, .app_ver=game_ver,
        .thread_spawn=runtime_legacy_thread_spawn,
        .thread_join=runtime_legacy_thread_join,
        .thread_exit=runtime_legacy_thread_exit,
        .memory_is_mapped=runtime_memory_is_mapped,
    };
    if (init(&host)!=0) {
        puts("BBSC legacy: native module rejected host ABI, staying offline");
        FreeLibrary(candidate);
        return NULL;
    }
    module=candidate;
    network_resolve=resolve;
    puts("BBSC legacy: native module initialized (gameplay interoperability NOT verified)");
    return resolve;
}

uintptr_t runtime_legacy_net_resolve(const char *scoped_nid) {
    if (!runtime_legacy_net_requested()) return 0;
    const char *symbol=runtime_symbol(scoped_nid);
    if (!symbol) symbol=scoped_nid;
    if (!legacy_net_online_symbol(symbol)) return 0;
    NetResolve resolve=load_module();
    return resolve ? resolve(scoped_nid) : 0;
}

void runtime_legacy_net_image_mapped(uint8_t *image, uint64_t size) {
    if (module) {
        NetImageMapped cb=(NetImageMapped)(void*)GetProcAddress(module,"bbnet_image_mapped");
        if (cb) cb(image,size);
    }
}
void runtime_legacy_net_image_ready(uint64_t base, uint64_t size) {
    if (module) {
        NetImageReady cb=(NetImageReady)(void*)GetProcAddress(module,"bbnet_image_ready");
        if (cb) cb(base,size);
    }
}
void runtime_legacy_net_start(void) {
    if (module) {
        NetStart cb=(NetStart)(void*)GetProcAddress(module,"bbnet_start");
        if (cb) cb();
    }
}

#else
int runtime_legacy_net_requested(void) { return 0; }
uintptr_t runtime_legacy_net_resolve(const char *scoped_nid) {
    (void)scoped_nid; return 0;
}
void runtime_legacy_net_configure(const char *a,const char *b,const char *c,const char *d) {
    (void)a;(void)b;(void)c;(void)d;
}
void runtime_legacy_net_image_mapped(uint8_t *image,uint64_t size) { (void)image;(void)size; }
void runtime_legacy_net_image_ready(uint64_t base,uint64_t size) { (void)base;(void)size; }
void runtime_legacy_net_start(void) {}
#endif
