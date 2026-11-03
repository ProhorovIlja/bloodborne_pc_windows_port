/* SPDX-License-Identifier: GPL-3.0-or-later
 * V1: load the ACTUAL compiler-produced bbhost plugin .so through dlopen,
 * feed bbhost's genuine public ABI and assert no mutation/network calls.
 * Synthetic 1.09 image verdict only; no game executable or data present.
 */
#define _POSIX_C_SOURCE 200809L
#include "bbhost_plugin.h"
#include <assert.h>
#include <dlfcn.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>
static int acceptable_image;
static int observed_register;
static int observed_mutations;
static int observed_cadence;
static void (*registered_frame)(void *);

static void fake_log(const char *fmt, ...) {
    char line[512];
    va_list args;
    va_start(args,fmt);
    vsnprintf(line,sizeof(line),fmt,args);
    va_end(args);
    if (strstr(line,"600-frame engine-main-thread") ||
        strstr(line,"timing unavailable"))
        observed_cadence++;
}
static int fake_image(void) { return acceptable_image; }
static int fake_frame(void (*fn)(void*),void *user) {
    assert(fn && !user);
    observed_register++;
    registered_frame=fn;
    return 0;
}
static int fake_stat(const char *key,int64_t *value) {
    assert(strcmp(key,"level")==0 && value);
    *value=70;
    return 0;
}
static int fake_mutation(uint64_t address,const void *bytes,size_t n) {
    (void)address;(void)bytes;(void)n;
    observed_mutations++;
    return 1;
}
static int fake_hook(uint64_t address,const void *signature,size_t n,
                     BbHookFn fn,void *user) {
    (void)address;(void)signature;(void)n;(void)fn;(void)user;
    observed_mutations++;
    return 2;
}
int main(int argc,char **argv) {
    assert(argc==2);
    void *dll=dlopen(argv[1],RTLD_NOW|RTLD_LOCAL);
    if(!dll){fprintf(stderr,"plugin load failed\n");return 1;}
    typedef int (*Entry)(const BbHostApi*);
    Entry init=(Entry)dlsym(dll,"bb_plugin_init");
    Entry image=(Entry)dlsym(dll,"bb_plugin_image");
    const BbPluginInfo *info=(const BbPluginInfo*)dlsym(dll,"bb_plugin_info");
    assert(init && image && info && info->api_version>=3);
    assert(strcmp(info->name,"shyt_bbhost_probe")==0);
    BbHostApi api={0};
    api.version=BB_PLUGIN_API_VERSION;
    api.size=sizeof(api);
    api.log=fake_log;
    api.eboot_is_109=fake_image;
    api.on_frame=fake_frame;
    api.player_stat_get=fake_stat;
    api.write=fake_mutation;
    api.hook=fake_hook;
    assert(init(0)!=0);
    api.version=2;
    assert(init(&api)!=0);
    api.version=BB_PLUGIN_API_VERSION;
    api.size=sizeof(api)-1;
    assert(init(&api)==0); /* future appended fields may be absent */
    api.size=sizeof(api);
    assert(init(&api)==0);
    assert(image(&api)!=0); /* missing actual pinned 1.09 is DENY */
    assert(!observed_register);
    acceptable_image=1;
    assert(init(&api)==0);
    assert(image(&api)==0);
    assert(observed_register==1 && registered_frame);
    for(int i=0;i<600;++i)registered_frame(0);
    assert(observed_cadence>=1 && observed_mutations==0);
    dlclose(dll);
    puts("SHYT_BBHOST_V1_REAL_PLUGIN_DLOPEN_API_READONLY_PASS");
    return 0;
}
