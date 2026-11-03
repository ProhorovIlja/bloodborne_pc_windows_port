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
#include <stddef.h>
#include <stdint.h>
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
    if (world_events.invalid_incremental && !reported_world_overflow) {
        host->log("shyt-bbhost-probe: world flags overflow, incremental stream INVALID; future signed full snapshot required");
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

BB_PLUGIN_EXPORT int bb_plugin_init(const BbHostApi *api) {
    /* Every call below is from the actual public bbhost plugin ABI.
     * API version 3 is the first with player_stat_get. The trailing
     * size fence protects us from truncated or foreign host structs.
     */
    if (!api || api->version < 3u ||
        api->size < offsetof(BbHostApi, player_stat_get) +
                    sizeof(api->player_stat_get) ||
        !api->log || !api->eboot_is_109 || !api->on_frame ||
        !api->player_stat_get) return 1;
    host = api;
    frame_count = 0;
    window_start_ms = 0;
    reported_world_overflow=0;
    shyt_world_ledger_reset_v4(&world_events);
    api->log("shyt-bbhost-probe: read-only plugin API accepted; no networking installed");
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
    if (api->version >= 4u &&
        api->size >= offsetof(BbHostApi,on_event_flag) +
                     sizeof(api->on_event_flag) &&
        api->on_event_flag &&
        api->on_event_flag(on_world_flag_v4,0)==0) {
        api->log("shyt-bbhost-probe: world progression callback captured, LOCAL ONLY");
    } else {
        api->log("shyt-bbhost-probe: world flag callback unavailable; disabled");
    }
    api->log("shyt-bbhost-probe: original Bloodborne 1.09 image accepted; observe-only");
    return 0;
}
