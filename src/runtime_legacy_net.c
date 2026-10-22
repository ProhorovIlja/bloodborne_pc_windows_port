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
#include "runtime_legacy_net.h"
#include "runtime_legacy_policy.h"
#include "runtime_legacy_host.h"
#include "../gpu/party_env.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* Keep this native Win64 DLL adapter independent of the guest thread/runtime
 * implementation headers. The production runtime supplies these two callbacks.
 * This also allows a genuine Windows loader/DLL integration smoke in isolation.
 */
extern const char *runtime_symbol(const char *nid);
extern int runtime_memory_is_mapped(uintptr_t address, uint64_t size);

#ifdef _WIN32
#include <windows.h>
#include <wchar.h>

static char game_folder[4096], game_serial[16], game_title[128], game_ver[16];
static HMODULE module;
static BbNetResolveFn network_resolve;
static int tried_load;
static int valid_game_identity;

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
    /* Only the real gameplay boot configures this. CPU-only/import analysis
     * must NEVER start a network module with an uninitialized title.
     */
    valid_game_identity=game_folder[0] &&
                        legacy_net_supported_game(game_serial,game_title,game_ver);
}
int runtime_legacy_net_requested(void) {
    return valid_game_identity &&
           legacy_net_bbsc_enabled(getenv("BB_BBSC")) &&
           legacy_net_opted_in(getenv("BB_LEGACY_NET"), bb_party_enabled());
}

static BbNetResolveFn load_module(void) {
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
    BbNetInitFn init=(BbNetInitFn)(void*)GetProcAddress(candidate,"bbnet_init");
    BbNetResolveFn resolve=(BbNetResolveFn)(void*)GetProcAddress(candidate,"bbnet_resolve");
    if (!init || !resolve) {
        puts("BBSC legacy: module ABI functions missing, staying offline");
        FreeLibrary(candidate);
        return NULL;
    }
    const BbNetHost host={
.abi=BBNET_HOST_ABI_VERSION, .app0=game_folder, .serial=game_serial,
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
    if (!scoped_nid) return 0;
    const char *symbol=runtime_symbol(scoped_nid);
    /* Known names remain strictly limited to NP/Net/HTTP/SSL. For an
     * unrecognized hash, let the network module's own explicit NID registry
     * decide: imported NIDs are not necessarily all in our diagnostics map.
     */
    if (symbol ? !legacy_net_online_symbol(symbol)
               : !legacy_net_scoped_nid(scoped_nid)) return 0;
    BbNetResolveFn resolve=load_module();
    return resolve ? resolve(scoped_nid) : 0;
}

void runtime_legacy_net_image_mapped(uint8_t *image, uint64_t size) {
    /* The public party transport takes precedence even when the experimental
     * DLL was already initialized earlier in this process. No BBSC callback
     * may hook an image or start its sockets once that priority changes.
     */
    if (module && runtime_legacy_net_requested()) {
        BbNetImageMappedFn cb=(BbNetImageMappedFn)(void*)GetProcAddress(module,"bbnet_image_mapped");
        if (cb) cb(image,size);
    }
}
void runtime_legacy_net_image_ready(uint64_t base, uint64_t size) {
    /* The public party transport takes precedence even when the experimental
     * DLL was already initialized earlier in this process. No BBSC callback
     * may hook an image or start its sockets once that priority changes.
     */
    if (module && runtime_legacy_net_requested()) {
        BbNetImageReadyFn cb=(BbNetImageReadyFn)(void*)GetProcAddress(module,"bbnet_image_ready");
        if (cb) cb(base,size);
    }
}
void runtime_legacy_net_start(void) {
    /* The public party transport takes precedence even when the experimental
     * DLL was already initialized earlier in this process. No BBSC callback
     * may hook an image or start its sockets once that priority changes.
     */
    if (module && runtime_legacy_net_requested()) {
        BbNetStartFn cb=(BbNetStartFn)(void*)GetProcAddress(module,"bbnet_start");
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
