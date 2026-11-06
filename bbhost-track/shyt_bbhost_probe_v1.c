/* SPDX-License-Identifier: GPL-3.0-or-later
 * BBHost path V1: a READ-ONLY, version-gated host API integration probe.
 * No game memory writes, no arbitrary game function hooks, NO injected
 * multiplayer traffic and NO claim to port Yharnam Together yet.
 *
 * Purpose: prove bbhost's *real* loadable DLL/SO callback interface and
 * gather independently comparable main-thread frame cadence samples.
 * This is NOT presented FPS (does not include frame generation).
 */
#ifndef _WIN32
#define _POSIX_C_SOURCE 200809L
#endif
#include "bbhost_plugin.h"
#include "yt_world_event_ledger_v4.h"
#include "shyt_yt_native_channel_policy_v21.h"
#include "shyt_yt_packet_routes_v358.h"
#include "shyt_yt_game_frame_v362.h"
#include "shyt_yt_shlk_client_v401.h"
#include "shyt_yt_link_wire_v403.h"
#include "shyt_yt_secure_game_data_v405.h"
#include "shyt_yt_udp_endpoint_v406.h"
#include "shyt_yt_server_session_v408.h"
#include "shyt_yt_full_guest_preflight_v428.h"
#include "shyt_yt_game_link_observer_v429.h"
#include <stddef.h>
#include <stdint.h>
#include <stdatomic.h>
#include <string.h>
#ifdef _WIN32
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#else
#include <time.h>
#endif

static const BbHostApi *host;
static uint64_t frame_count;
static uint64_t window_start_ms;
static ShytWorldLedgerV4 world_events;
static int reported_world_overflow;
static unsigned world_load_count;
static uint32_t world_last_block;

/* V17: first real NetSync/SHAD game packet observation seam on BBHost.
 * The YT 1.09 docs identify 0x017894E0 at image base 0; BBHost hook2
 * takes Binary Ninja's 0x400000-based address. Never read payloads,
 * rewrite a channel or send a datagram. Opt-in diagnostic only.
 */
#define SHYT_V17_NETSYNC_SEND_BN (UINT64_C(0x017894E0)+UINT64_C(0x400000))
#define SHYT_V17_GAME_CHANNELS 68u
static atomic_ullong outgoing_channels_v17[SHYT_V17_GAME_CHANNELS];
/* V21: exact YT channel policies, to estimate the *candidate* data
 * needing map/owner/invasion-filtered relay. NOT a P2P authorization. */
static atomic_ullong outgoing_policy_v21[4];
static atomic_ullong malformed_sends_v17;
static int packet_hook_enabled_v17;
static ShytYtGameLinkObserverV429 yt_calls_v429;
static int yt_send_hook_enabled_v429;
static int yt_update_hook_enabled_v429;
/* Exact privately audited 1.09 code prefixes. Never use NULL expected
 * bytes in hook2: that could hook a previously modified game function. */
static const unsigned char yt_send_prologue_v429[14]={
    0x55,0x48,0x89,0xe5,0x41,0x57,0x41,0x56,
    0x41,0x55,0x41,0x54,0x53,0x50
};
static const unsigned char yt_update_prologue_v429[20]={
    0x55,0x48,0x89,0xe5,0x41,0x57,0x41,0x56,
    0x41,0x55,0x41,0x54,0x53,0x48,0x81,0xec,
    0x18,0x21,0x00,0x00
};
static const unsigned char netsync_prologue_v17[20] = {
    /* V428 privately audited exact Bloodborne 1.09 decrypted EBOOT
     * (SHA-256 pinned by BBHost); original YT site 0x017894E0.
     * Eight complete push/mov/sub instructions, 20-byte boundary.
     * Earlier V17 used a guessed 17-byte 48 83 EC prologue: the
     * actual 1.09 uses 48 81 EC. It could NEVER match in real play.
     * This OBSERVER is default-off and never alters a game packet.
     */
    0x55,0x48,0x89,0xe5,0x41,0x57,0x41,0x56,
    0x41,0x55,0x41,0x54,0x53,0x48,0x81,0xec,
    0x88,0x00,0x00,0x00
};
static int on_netsync_send_v17(BbHookCtx *ctx,void *user) {
    (void)user;
    if (!ctx) return 0;
    const uint64_t channel=ctx->arg[2]; /* edx; known YT NetSync ABI */
    const uint64_t size=ctx->arg[4];    /* r8d; no dereference of rcx */
    if (channel<SHYT_V17_GAME_CHANNELS && size<=0x6400u) {
        atomic_fetch_add_explicit(&outgoing_channels_v17[channel],1u,memory_order_relaxed);
        const enum ShytYtNativeChannelPolicyV21 policy =
            shyt_yt_channel_policy_v21((uint32_t)channel);
        atomic_fetch_add_explicit(&outgoing_policy_v21[(unsigned)policy],1u,memory_order_relaxed);
    } else {
        atomic_fetch_add_explicit(&malformed_sends_v17,1u,memory_order_relaxed);
    }
    return 0; /* NEVER intercept / alter gameplay, only observe */
}
static int attach_netsync_readonly_v17(const BbHostApi *api) {
    if (!api || api->version<8u ||
        api->size<offsetof(BbHostApi,hook2)+sizeof(api->hook2) ||
        !api->read || !api->hook2) return 0;
    unsigned char actual[sizeof(netsync_prologue_v17)] = {0};
    if (!api->eboot_is_109 || !api->eboot_is_109() ||
        !api->eboot_sha256 ||
        strcmp(api->eboot_sha256(),
               "941f887a562aae054fac35af8cc8f27cf075f3d4cc2e029fb5ae2a663aaa5ae7")!=0 ||
        api->read(SHYT_V17_NETSYNC_SEND_BN,actual,sizeof(actual))!=0 ||
        memcmp(actual,netsync_prologue_v17,sizeof(actual))!=0)
        return 0; /* exact 1.09 + full instruction boundary, no fallback */
    /* All 20 bytes are complete initial instructions without RIP-relative
     * operands. hook2 still verifies the live prologue before patching.
     * The callback returns 0 so the ORIGINAL function runs unchanged.
     */
    return api->hook2(SHYT_V17_NETSYNC_SEND_BN,actual,sizeof(actual),
                      on_netsync_send_v17,0)==0;
}

/* V429: opt-in live original YT game-link CALL observability only.
 * This is the FIRST real hook at YT's send/update source sites. Both
 * callbacks always return 0; the original Bloodborne functions execute
 * unchanged. Do not read payloads, re-route packets or change NetSync.
 * If only one passive hook attaches, keep the plugin loaded: BBHost
 * has no hook unregister API and unloading would create dangling stubs.
 */
static void attach_yt_game_calls_v429(const BbHostApi *api) {
    if (!api || api->version<8u ||
        api->size<offsetof(BbHostApi,hook2)+sizeof(api->hook2) ||
        !api->read || !api->hook2 || !api->eboot_is_109 ||
        !api->eboot_sha256 || !api->eboot_is_109()) return;
    ShytYtFullGuestPreflightV428 state={0};
    if (!shyt_yt_full_guest_preflight_v428(
         api->eboot_is_109(),api->eboot_sha256(),api->read,&state))
        return;
    const uint64_t send=SHYT_V427_PREFERRED_IMAGE_BASE+
                        SHYT_V427_TRANSPORT_SEND_RVA;
    const uint64_t update=SHYT_V427_PREFERRED_IMAGE_BASE+
                          SHYT_V427_NETSYNC_UPDATE_RVA;
    yt_send_hook_enabled_v429=
        api->hook2(send,yt_send_prologue_v429,
                   sizeof(yt_send_prologue_v429),
                   shyt_yt_v429_observe_send,&yt_calls_v429)==0;
    if (!yt_send_hook_enabled_v429)return;
    yt_update_hook_enabled_v429=
        api->hook2(update,yt_update_prologue_v429,
                   sizeof(yt_update_prologue_v429),
                   shyt_yt_v429_observe_update,&yt_calls_v429)==0;
}

/* V16: BBHost's version-8 on_world_load is the real main-thread transition.
 * A save/world load never implies an authenticated YT world snapshot.
 * Invalidate the incremental stream, keep all existing callbacks installed.
 */
static void on_world_load_v16(uint32_t block, void *user) {
    (void)user;
    ++world_load_count;
    world_last_block=block;
    shyt_world_ledger_invalidate_v4(&world_events);
    if (host && host->log && world_load_count==1u)
        host->log("shyt-bbhost-probe: first world load observed; incremental flag stream INVALID until full verified world snapshot");
}

static void on_world_flag_v4(uint32_t id,int value,void *user) {
    (void)user;
    /* Only the game's original main-thread flag callback is observed.
     * Never send an unauthenticated delta or alter the game in this pilot. */
    (void)shyt_world_ledger_push_v4(&world_events,id,value);
}


static uint64_t monotonic_ms(void) {
#ifdef _WIN32
    LARGE_INTEGER c, f;
    if (!QueryPerformanceCounter(&c) || !QueryPerformanceFrequency(&f) ||
        f.QuadPart <= 0 || c.QuadPart < 0) return 0;
    return ((uint64_t)c.QuadPart / (uint64_t)f.QuadPart) * 1000u +
           (((uint64_t)c.QuadPart % (uint64_t)f.QuadPart) * 1000u) /
           (uint64_t)f.QuadPart;
#else
    struct timespec t;
    if (clock_gettime(CLOCK_MONOTONIC, &t) != 0 || t.tv_sec < 0) return 0;
    return (uint64_t)t.tv_sec * 1000u + (uint64_t)t.tv_nsec / 1000000u;
#endif
}

static void on_game_frame(void *user) {
    uint64_t now, interval;
    int64_t level = 0;
    (void)user;
    if (!host) return;
    now = monotonic_ms();
    if (frame_count == 0) window_start_ms = now;
    ++frame_count;
    if ((frame_count % 600u) != 0u) return;
    if (packet_hook_enabled_v17) {
        unsigned long long total=0;
        for (unsigned i=0;i<SHYT_V17_GAME_CHANNELS;++i)
            total+=atomic_load_explicit(&outgoing_channels_v17[i],memory_order_relaxed);
        host->log("shyt-bbhost-probe: NetSync real outgoing channel observations=%llu player-ch6=%llu rejected-inputs=%llu; NO payload capture or forwarding",
                  total,
                  atomic_load_explicit(&outgoing_channels_v17[6],memory_order_relaxed),
                  atomic_load_explicit(&malformed_sends_v17,memory_order_relaxed));
        host->log("shyt-yt-policy-v21: outgoing observed pass=%llu same-map=%llu ours=%llu drop=%llu; pre-server, no auth/route decision",
                  atomic_load_explicit(&outgoing_policy_v21[SHYT_YT_CHANNEL_PASS_V21],memory_order_relaxed),
                  atomic_load_explicit(&outgoing_policy_v21[SHYT_YT_CHANNEL_SAME_MAP_V21],memory_order_relaxed),
                  atomic_load_explicit(&outgoing_policy_v21[SHYT_YT_CHANNEL_OURS_V21],memory_order_relaxed),
                  atomic_load_explicit(&outgoing_policy_v21[SHYT_YT_CHANNEL_DROP_V21],memory_order_relaxed));
    }
    if (yt_send_hook_enabled_v429 || yt_update_hook_enabled_v429) {
        host->log("shyt-yt-v429: original YT game-link CALLS outgoing=%llu valid=%llu bad=%llu no-member=%llu reliable=%llu unreliable=%llu native-game-bytes=%llu netSyncUpdates=%llu; counts since init, NOT WAN bytes, NO network capture",
                  atomic_load_explicit(&yt_calls_v429.outgoing_calls,memory_order_relaxed),
                  atomic_load_explicit(&yt_calls_v429.outgoing_valid,memory_order_relaxed),
                  atomic_load_explicit(&yt_calls_v429.outgoing_malformed,memory_order_relaxed),
                  atomic_load_explicit(&yt_calls_v429.outgoing_without_member,memory_order_relaxed),
                  atomic_load_explicit(&yt_calls_v429.outgoing_reliable,memory_order_relaxed),
                  atomic_load_explicit(&yt_calls_v429.outgoing_unreliable,memory_order_relaxed),
                  atomic_load_explicit(&yt_calls_v429.outgoing_game_bytes,memory_order_relaxed),
                  atomic_load_explicit(&yt_calls_v429.update_calls,memory_order_relaxed));
    }
    if (world_events.invalid_incremental && !reported_world_overflow) {
        host->log("shyt-bbhost-probe: world flag stream invalid (overflow or world load); future authenticated full snapshot required");
        reported_world_overflow=1;
    }
    if (!now || !window_start_ms || now <= window_start_ms) {
        host->log("shyt-bbhost-probe: timing unavailable; no FPS claim");
        window_start_ms = now;
        return;
    }
    interval = now - window_start_ms;
    /* x100 is integer main-thread frames per second (rough interval).
     * Must not be interpreted as rendered/presented FPS or a GPU benchmark.
     */
    if (host->player_stat_get && host->player_stat_get("level", &level) != 0)
        level = 0;
    host->log("shyt-bbhost-probe: 600-frame engine-main-thread window=%llu ms cadence_x100=%llu level_available=%d (NOT presented FPS)",
              (unsigned long long)interval,
              (unsigned long long)(60000000u / interval),level > 0);
    window_start_ms = now;
}

BB_PLUGIN_EXPORT const BbPluginInfo bb_plugin_info = {
    BB_PLUGIN_API_VERSION, 0,
    "shyt_bbhost_probe", "Seamless Hunt BBHost compatibility probe",
    "0.1.0", "Seamless Hunt contributors",
    "Read-only 1.09 API/cadence probe, not a co-op implementation."
};

/* V5: use the official BBHost plugin settings menu. This is a restart
 * option, not a live switch, because callback removal has no host API.
 * Default OFF: no world-flag hooks or local capture without opt-in. */
BB_PLUGIN_EXPORT const BbOption bb_plugin_options[] = {
    {BB_OPT_BOOL, "capture_world_flags", "Capture world flags (diagnostic)",
     "Records a bounded local YT progression observation stream. No network transmission. Restart required.",
     "false", 0, 0, 0},
    {BB_OPT_BOOL, "observe_netsync_sends", "Observe game packet channels (diagnostic)",
     "Only counts NetSync send channels, requires exact 1.09 safe prologue. No payloads, changes or network. Restart required.",
     "false", 0, 0, 0},
    {BB_OPT_BOOL, "inspect_yt_game_sites", "Inspect YT game send/NetSync code (diagnostic)",
     "Read-only full-instruction 14/20-byte compare of 1.09 YT send/NetSync sites. NO hooks, game changes or network. Restart required.",
     "false", 0, 0, 0},
    {BB_OPT_BOOL, "observe_yt_game_link_calls", "Observe original YT GameLink send/NetSync calls (experimental)",
     "Opt-in PASS-THROUGH game hooks. Counts native sends, reliability and NetSync updates; no packet payloads, game writes, forwarding or P2P. Restart required.",
     "false", 0, 0, 0},
    {0}
};

/* V363: executable compatibility self-check of the ACTUAL YT frame
 * codec and server routing imported into this BBHost plugin. No game
 * packets or network traffic are read or injected at startup. */
static int shyt_yt_transport_codec_selfcheck_v363(void) {
    /* This is an in-process check of the real original YT crypto wrapper.
     * No handshake or network session starts before user-controlled login.
     */
    // V406 real OS UDP is completely dormant until a launcher supplies
    // an authenticated server endpoint. A zero/malformed endpoint must
    // fail closed WITHOUT creating a network socket at plugin startup.
    if (shyt_yt_server_phase_v408(NULL)!=-1 ||
        shyt_yt_server_new_v408(0u,0u,NULL,NULL,NULL,NULL)!=NULL)
        return 0; /* no config => no socket, no login, no secrets */
    ShytYtUdpEndpointV406 *no_server=shyt_yt_udp_open_v406(0u,0u);
    if (no_server) {
        shyt_yt_udp_close_v406(no_server);
        return 0;
    }
    ShytYtShlkClientV401 *auth=shyt_yt_shlk_new_v401();
    if (!auth) return 0;
    const int not_linked=(shyt_yt_shlk_linked_v401(auth)==0);
    const uint8_t synthetic_game_v405[]={0xff,0xff,0xff,0xff,0x01};
    uint8_t no_wire_v405[96]={0};
    size_t no_wire_size_v405=99u;
    // Never allow original YT encrypted gameplay before an authenticated
    // room/server session. Actual outbound network IO is still disabled.
    const int refused_unlinked_v405=
        !shyt_yt_secure_send_data_v405(auth,0x12345678u,3658u,
            synthetic_game_v405,sizeof(synthetic_game_v405),
            no_wire_v405,sizeof(no_wire_v405),&no_wire_size_v405) &&
        no_wire_size_v405==0u;
    shyt_yt_shlk_free_v401(auth);
    if (!not_linked || !refused_unlinked_v405) return 0;
    /* Original outer SHLK Ping has its OWN 9-byte header and 12-byte
     * body. The inner V362 game frame must never be sent by itself. */
    uint8_t ping[32]={0};
    size_t ping_size=0;
    uint32_t ping_seq=0;
    uint64_t ping_time=0;
    if (!shyt_yt_link_encode_ping_v403(4u,17u,12345u,
            ping,sizeof(ping),&ping_size) ||
        ping_size!=21u || shyt_yt_link_kind_v403(ping,ping_size)!=4 ||
        !shyt_yt_link_decode_ping_v403(4u,ping,ping_size,
            &ping_seq,&ping_time) ||
        ping_seq!=17u || ping_time!=12345u)
        return 0;
    ShytYtGameFrameV362 source={0}, decoded={0};
    unsigned char wire[64]={0};
    size_t encoded=0;
    source.sender_len=4u;
    memcpy(source.sender,"test",4u);
    source.instance=0x12345678u;
    source.peer_instance=0x87654321u;
    source.ack=3u;
    source.entries_count=1u;
    source.entries[0].packet_class=0u;
    source.entries[0].seq=0u;
    source.entries[0].packet_size=0u;
    if (!shyt_yt_game_frame_encode_v362(&source,wire,sizeof(wire),&encoded) ||
        !shyt_yt_game_frame_decode_v362(wire,encoded,&decoded) ||
        decoded.sender_len!=4u ||
        memcmp(decoded.sender,"test",4u)!=0 ||
        decoded.instance!=source.instance ||
        decoded.peer_instance!=source.peer_instance ||
        decoded.ack!=source.ack ||
        decoded.entries_count!=1u)
        return 0;
    const struct ShytYtPacketEndsV358 fake={0};
    if (shyt_yt_routes_native_packet_v358(0x27u,&fake)!=0 ||
        shyt_yt_routes_native_packet_v358(0x06u,&fake)==0)
        return 0;
    return 1;
}

BB_PLUGIN_EXPORT int bb_plugin_init(const BbHostApi *api) {
    /* Every call below is from the actual public bbhost plugin ABI.
     * API version 3 is the first with player_stat_get. The trailing
     * size fence protects us from truncated or foreign host structs.
     */
    if (!api || api->version < 3u ||
        api->size < offsetof(BbHostApi, player_stat_get) +
                    sizeof(api->player_stat_get) ||
        !api->log || !api->config || !api->eboot_is_109 || !api->on_frame ||
        !api->player_stat_get) return 1;
    if (!shyt_yt_transport_codec_selfcheck_v363()) return 1;
    host = api;
    frame_count = 0;
    window_start_ms = 0;
    reported_world_overflow=0;
    world_load_count=0;
    world_last_block=0;
    packet_hook_enabled_v17=0;
    yt_send_hook_enabled_v429=0;
    yt_update_hook_enabled_v429=0;
    shyt_yt_v429_reset(&yt_calls_v429);
    for (unsigned i=0;i<SHYT_V17_GAME_CHANNELS;++i)
        atomic_store_explicit(&outgoing_channels_v17[i],0u,memory_order_relaxed);
    for (unsigned i=0;i<4u;++i)
        atomic_store_explicit(&outgoing_policy_v21[i],0u,memory_order_relaxed);
    atomic_store_explicit(&malformed_sends_v17,0u,memory_order_relaxed);
    shyt_world_ledger_reset_v4(&world_events);
    api->log("shyt-bbhost-probe: read-only plugin API accepted; no networking installed");
    api->log("shyt-bbhost-probe: original YT SHLK4 crypto C session linked, local unconnected; NO network socket/login or P2P installed");
    api->log("shyt-bbhost-probe: encrypted original YT GameData V405 linked; unauthenticated packets refused; NO live forwarding installed");
    api->log("shyt-bbhost-probe: native YT UDP endpoint V406 compiled; disabled until configured authenticated server");
    api->log("shyt-bbhost-probe: YT SHLK4 V408 session state machine compiled; manually opt-in only; game NetSync still not connected");
    api->log("shyt-bbhost-probe: actual YT GameFrame V362 codec + V358 packet policy linked; NO SHLK authentication or P2P installed");
    return 0;
}

BB_PLUGIN_EXPORT int bb_plugin_image(const BbHostApi *api) {
    if (!api || !host || api != host || !api->eboot_is_109 ||
        !api->eboot_is_109() || !api->on_frame) return 1;
    /* Register last. If this fails, no callback was installed, and
     * the host can unload the plugin without any dangling callback.
     */
    if (api->on_frame(on_game_frame, 0) != 0) return 1;
    /* V4: event flag callback is one real YT-required progression source.
     * Register AFTER on_frame: failure here MUST NOT unload the plugin,
     * otherwise the installed frame callback would dangle.
     * No sync transport is present, and no game state is modified. */
    const char *capture=api->config("shyt_bbhost_probe.capture_world_flags");
    const int opt_in=capture &&
        (strcmp(capture,"true")==0 || strcmp(capture,"1")==0);
    /* V16: never capture deltas if we cannot detect a world load.
     * Register the load boundary FIRST, then event deltas. Both callbacks
     * stay alive until process exit: no unload on partial registration.
     * World changes invalidate, never silently reset, the ledger. */
    const int world_boundary=opt_in && api->version>=8u &&
        api->size >= offsetof(BbHostApi,on_world_load)+
                     sizeof(api->on_world_load) &&
        api->on_world_load &&
        api->on_world_load(on_world_load_v16,0)==0;
    if (world_boundary && api->version>=4u &&
        api->size >= offsetof(BbHostApi,on_event_flag)+
                     sizeof(api->on_event_flag) &&
        api->on_event_flag &&
        api->on_event_flag(on_world_flag_v4,0)==0) {
        api->log("shyt-bbhost-probe: world-load boundary + local world flag callbacks registered; no sync transport");
    } else {
        api->log("shyt-bbhost-probe: flag capture refused unless opted in AND world-load boundary available");
    }
    /* Install last, after all existing callback registrations. Even when
     * the code's prologue differs, do not unload the plugin: an on_frame
     * callback is already installed and would otherwise dangle. */
    const char *packet_opt=api->config("shyt_bbhost_probe.observe_netsync_sends");
    const int packet_wanted=packet_opt &&
        (strcmp(packet_opt,"true")==0 || strcmp(packet_opt,"1")==0);
    packet_hook_enabled_v17=packet_wanted && attach_netsync_readonly_v17(api);
    if (packet_wanted)
        api->log("shyt-bbhost-probe: NetSync hook %s; exact game/ABI/prologue opt-in, counters only",
                 packet_hook_enabled_v17 ? "INSTALLED":"REFUSED");
    /* V428: private exact-SHA EBOOT proves the 14/20 byte initial
     * instruction boundaries at both original YT v1.4.0 game sites.
     * Optional source-pinned READ-ONLY diagnostic, NO game hooks.
     * Although the prefixes are now known, callback ABI + original
     * continuation, game-thread delivery and five-player behavior
     * remain unverified and hooking these sites is forbidden. */
    const char *site_opt=api->config("shyt_bbhost_probe.inspect_yt_game_sites");
    const int sites_wanted=site_opt &&
        (strcmp(site_opt,"true")==0 || strcmp(site_opt,"1")==0);
    if (sites_wanted) {
        ShytYtFullGuestPreflightV428 state={0};
        const int api_ready=api->size>=offsetof(BbHostApi,read)+
                                   sizeof(api->read) &&
                            api->read && api->eboot_sha256;
        const int found=shyt_yt_full_guest_preflight_v428(
            api->eboot_is_109(),
            api_ready ? api->eboot_sha256() : NULL,
            api_ready ? api->read : NULL, &state);
        api->log("shyt-bbhost-probe: YT v1.4.0 1.09 game hook-site preflight %s: transport=%u/%u update=%u/%u; hook installation DISABLED (unverified game ABI and continuation)",
                 found ? "MATCHED":"REFUSED",
                 (unsigned)state.transport_matched,(unsigned)state.transport_read,
                 (unsigned)state.update_matched,(unsigned)state.update_read);
    }
    /* Keep V429 last. hook2 is a persistent engine detour; any partial
     * installation is passive and must not cause plugin unload.
     * Both hooks default OFF and require verified game SHA + full bytes. */
    const char *game_opt=api->config("shyt_bbhost_probe.observe_yt_game_link_calls");
    const int game_wanted=game_opt &&
        (strcmp(game_opt,"true")==0 || strcmp(game_opt,"1")==0);
    if (game_wanted) {
        attach_yt_game_calls_v429(api);
        api->log("shyt-bbhost-probe: V429 passive original YT GameLink source hooks send=%s update=%s; original game always continues, NO forwarding",
                 yt_send_hook_enabled_v429?"INSTALLED":"REFUSED",
                 yt_update_hook_enabled_v429?"INSTALLED":"REFUSED");
    }
    api->log("shyt-bbhost-probe: original Bloodborne 1.09 image accepted; observe-only");
    return 0;
}
