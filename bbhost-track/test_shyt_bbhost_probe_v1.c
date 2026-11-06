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
static int user_opted_in_world_flags;
static int user_opted_in_packet_channels;
static int user_opted_in_site_inspection;
static int acceptable_sha;
static int observed_site_reads;
static int observed_site_logs;
static int acceptable_prologue;
static int observed_hook_placements;
static int observed_packet_cadence;
static int observed_yt_policy_v21;
static unsigned long long classified_policy_v21[4];
static int observed_probe_reads;
static int (*registered_packet_hook)(BbHookCtx*,void*);
static int observed_register;
static int observed_mutations;
static int observed_cadence;
static int observed_world_overflow;
static int observed_world_register;
static int observed_load_register;
static int observed_load_invalidation;
static void (*registered_world_load)(uint32_t,void*);
static void (*registered_frame)(void *);
static void (*registered_world_flag)(uint32_t,int,void*);

static void fake_log(const char *fmt, ...) {
    char line[512];
    va_list args;
    va_start(args,fmt);
    vsnprintf(line,sizeof(line),fmt,args);
    va_end(args);
    if (strstr(line,"600-frame engine-main-thread") ||
        strstr(line,"timing unavailable"))
        observed_cadence++;
    if (strstr(line,"game hook-site preflight"))
        observed_site_logs++;
    if (strstr(line,"world flag stream invalid"))
        observed_world_overflow++;
    if (strstr(line,"incremental flag stream INVALID"))
        observed_load_invalidation++;
    if (strstr(line,"NetSync real outgoing channel observations="))
        observed_packet_cadence++;
    if (strstr(line,"shyt-yt-policy-v21: outgoing observed")) {
        observed_yt_policy_v21++;
        assert(sscanf(line,
          "shyt-yt-policy-v21: outgoing observed pass=%llu same-map=%llu ours=%llu drop=%llu",
          &classified_policy_v21[0],&classified_policy_v21[1],
          &classified_policy_v21[2],&classified_policy_v21[3])==4);
    }
}
static const char *fake_config(const char *name) {
    if (strcmp(name,"shyt_bbhost_probe.capture_world_flags")==0)
        return user_opted_in_world_flags ? "true" : "";
    if (strcmp(name,"shyt_bbhost_probe.observe_netsync_sends")==0)
        return user_opted_in_packet_channels ? "true" : "";
    assert(strcmp(name,"shyt_bbhost_probe.inspect_yt_game_sites")==0);
    return user_opted_in_site_inspection ? "true" : "";
}
static int fake_image(void) { return acceptable_image; }
static const char *fake_sha(void) {
    return acceptable_sha ?
        "941f887a562aae054fac35af8cc8f27cf075f3d4cc2e029fb5ae2a663aaa5ae7" :
        "wrong";
}
static int fake_frame(void (*fn)(void*),void *user) {
    assert(fn && !user);
    observed_register++;
    registered_frame=fn;
    return 0;
}
static int fake_world_event(void (*fn)(uint32_t,int,void*),void *user) {
    assert(fn && !user);
    observed_world_register++;
    registered_world_flag=fn;
    return 0;
}
static int fake_world_load(void (*fn)(uint32_t,void*),void *user) {
    assert(fn && !user);
    observed_load_register++;
    registered_world_load=fn;
    return 0;
}
static const unsigned char expected_netsync_head[20] = {
    0x55,0x48,0x89,0xe5,0x41,0x57,0x41,0x56,
    0x41,0x55,0x41,0x54,0x53,0x48,0x81,0xec,
    0x88,0x00,0x00,0x00
};
static int fake_net_read(uint64_t address,void *out,size_t n) {
    if(n==14u || n==20u) {
        static const unsigned char yt_transport[14]={
            0x55,0x48,0x89,0xe5,0x41,0x57,0x41,0x56,
            0x41,0x55,0x41,0x54,0x53,0x50
        };
        static const unsigned char yt_update[20]={
            0x55,0x48,0x89,0xe5,0x41,0x57,0x41,0x56,
            0x41,0x55,0x41,0x54,0x53,0x48,0x81,0xec,
            0x18,0x21,0x00,0x00
        };
        assert(out);
        if(address==UINT64_C(0x00C8F0A0)+UINT64_C(0x400000)) {
            assert(n==sizeof(yt_transport));
            memcpy(out,yt_transport,n);
        } else {
            assert(address==UINT64_C(0x01789B60)+UINT64_C(0x400000));
            assert(n==sizeof(yt_update));
            memcpy(out,yt_update,n);
        }
        ++observed_site_reads;
        if(!acceptable_prologue) ((unsigned char*)out)[n-1u]^=1u;
        return 0;
    }
    assert(address==UINT64_C(0x017894E0)+UINT64_C(0x400000));
    assert(out && n==sizeof(expected_netsync_head));
    ++observed_probe_reads;
    memcpy(out,expected_netsync_head,n);
    if(!acceptable_prologue) ((unsigned char*)out)[0]=0xcc;
    return 0;
}
static int fake_hook2(uint64_t address,const void *bytes,size_t n,
                      BbHookFn2 fn,void *user) {
    assert(address==UINT64_C(0x017894E0)+UINT64_C(0x400000));
    assert(bytes && n==sizeof(expected_netsync_head));
    assert(memcmp(bytes,expected_netsync_head,n)==0);
    assert(fn && !user);
    ++observed_hook_placements;
    registered_packet_hook=fn;
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
    const BbOption *settings=(const BbOption*)dlsym(dll,"bb_plugin_options");
    assert(settings && settings[0].type==BB_OPT_BOOL);
    assert(strcmp(settings[0].key,"capture_world_flags")==0);
    assert(strcmp(settings[0].def,"false")==0);
    assert(settings[1].type==BB_OPT_BOOL);
    assert(strcmp(settings[1].key,"observe_netsync_sends")==0);
    assert(strcmp(settings[1].def,"false")==0);
    assert(settings[2].type==BB_OPT_BOOL);
    assert(strcmp(settings[2].key,"inspect_yt_game_sites")==0);
    assert(strcmp(settings[2].def,"false")==0);
    assert(settings[3].type==0);
    BbHostApi api={0};
    api.version=BB_PLUGIN_API_VERSION;
    api.size=sizeof(api);
    api.log=fake_log;
    api.config=fake_config;
    api.eboot_is_109=fake_image;
    api.eboot_sha256=fake_sha;
    api.on_frame=fake_frame;
    api.on_event_flag=fake_world_event;
    api.on_world_load=fake_world_load;
    api.player_stat_get=fake_stat;
    api.write=fake_mutation;
    api.hook=fake_hook;
    api.read=fake_net_read;
    api.hook2=fake_hook2;
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
    /* On the default empty config, the real engine never registers
     * a progression event callback or captures a single world flag. */
    user_opted_in_world_flags=0;
    assert(init(&api)==0);
    assert(image(&api)==0);
    assert(observed_register==1 && registered_frame);
    assert(observed_world_register==0 && !registered_world_flag);
    assert(observed_load_register==0 && !registered_world_load);
    assert(observed_hook_placements==0 && observed_probe_reads==0);
    /* Explicit opt-in. Reinit is synthetic lifecycle fixture only. */
    user_opted_in_world_flags=1;
    assert(init(&api)==0);
    assert(image(&api)==0);
    assert(observed_register==2 && registered_frame);
    assert(observed_world_register==1 && registered_world_flag);
    assert(observed_load_register==1 && registered_world_load);
    /* Any real world load invalidates old deltas until a future
     * authenticated full snapshot. No gameplay state is modified. */
    registered_world_load(0x18010000u,0);
    assert(observed_load_invalidation==1);
    /* Version 7 host lacks on_world_load. In strict mode capture MUST
     * fail closed; no orphan flag callback may be registered. */
    api.version=7;
    assert(init(&api)==0);
    assert(image(&api)==0);
    assert(observed_world_register==1 && observed_load_register==1);
    api.version=BB_PLUGIN_API_VERSION;
    user_opted_in_world_flags=1;
    api.on_world_load=0;
    assert(init(&api)==0);
    assert(image(&api)==0);
    assert(observed_world_register==1 && observed_load_register==1);
    api.on_world_load=fake_world_load;
    /* V17: actual 1.09 exact-prologue-aware hook stays off by default,
     * and a nonmatching prologue may NEVER be patched. */
    user_opted_in_packet_channels=1;
    acceptable_sha=1; /* v428 exact 1.09 is a prerequisite */
    acceptable_prologue=0;
    assert(init(&api)==0);
    assert(image(&api)==0);
    assert(observed_probe_reads==1 && observed_hook_placements==0);
    acceptable_prologue=1;
    api.version=7;
    assert(init(&api)==0);
    assert(image(&api)==0);
    assert(observed_probe_reads==1 && observed_hook_placements==0);
    api.version=BB_PLUGIN_API_VERSION;
    assert(init(&api)==0);
    assert(image(&api)==0);
    assert(observed_probe_reads==2 && observed_hook_placements==1);
    assert(registered_packet_hook);
    BbHookCtx packet={0};
    packet.arg[0]=0x12345;
    packet.arg[2]=6; /* player movement channel */
    packet.arg[4]=128;
    assert(registered_packet_hook(&packet,0)==0);
    assert(packet.arg[0]==0x12345 && packet.arg[2]==6 && packet.arg[4]==128);
    for (unsigned i=0;i<3;++i) {
        static const uint64_t policies[]={0x10u,0x2Cu,0x27u};
        packet.arg[2]=policies[i];
        assert(registered_packet_hook(&packet,0)==0);
    }
    packet.arg[2]=UINT64_C(0xffff);
    assert(registered_packet_hook(&packet,0)==0); /* invalid never forwarded */
    for(int i=0;i<600;++i)registered_frame(0);
    assert(observed_packet_cadence==1);
    assert(observed_yt_policy_v21==1);
    for (unsigned i=0;i<4;++i)
        assert(classified_policy_v21[i]==1u);
    for(unsigned i=0;i<130;++i)
        registered_world_flag(100000u+i,i&1u,0);
    for(int i=0;i<600;++i)registered_frame(0);
    assert(observed_world_overflow==1);
    assert(observed_cadence>=1 && observed_mutations==0);
    /* Run V427 source-site audit after V17 cadence assertions:
     * bb_plugin_init resets the prior V17 observation flag by design. */
    /* V427: optional official YT source-site read-only preflight in the
     * ACTUAL compiled plugin. Unlike V17, it NEVER installs game hooks. */
    user_opted_in_world_flags=0;
    user_opted_in_packet_channels=0;
    user_opted_in_site_inspection=1;
    acceptable_sha=1;
    acceptable_prologue=1;
    assert(init(&api)==0);
    assert(image(&api)==0);
    assert(observed_site_reads==2 && observed_site_logs==1 &&
           observed_hook_placements==1 && observed_mutations==0);
    /* Even when BBHost says 1.09, a mismatched SHA prevents guest reads. */
    acceptable_sha=0;
    assert(init(&api)==0);
    assert(image(&api)==0);
    assert(observed_site_reads==2 && observed_site_logs==2 &&
           observed_hook_placements==1);
    /* A mutated YT NetSync prologue refuses rather than enabling a hook. */
    acceptable_sha=1;
    acceptable_prologue=0;
    assert(init(&api)==0);
    assert(image(&api)==0);
    assert(observed_site_reads==4 && observed_site_logs==3 &&
           observed_hook_placements==1 && observed_mutations==0);
    user_opted_in_site_inspection=0;
    acceptable_prologue=1;
    dlclose(dll);
    puts("SHYT_BBHOST_V1_REAL_PLUGIN_DLOPEN_API_READONLY_PASS");
    return 0;
}
