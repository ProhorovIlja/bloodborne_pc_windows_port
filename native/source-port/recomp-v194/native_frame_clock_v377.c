/* SPDX-License-Identifier: GPL-2.0-or-later
 * Synthetic native frame scheduler V377. Fixed-rate integer arithmetic avoids
 * floating point tick drift across 30/60/120/240/uncapped presentation.
 */
#include "native_frame_clock_v377.h"
#include <string.h>
#define ONE_SEC 1000000000ull
#define MAX_QUEUED 30ull
static int valid_cap(uint32_t fps) {
    return fps==0 || fps==30 || fps==60 || fps==120 || fps==240;
}
int shyt_native_frame_init_v377(ShytNativeFrameClockV377 *c,uint32_t fps) {
    if(!c||!valid_cap(fps))return 0;
    memset(c,0,sizeof(*c));c->present_fps=fps;return 1;
}
int shyt_native_frame_advance_v377(ShytNativeFrameClockV377 *c,
    uint64_t now, ShytNativeFrameUpdateV377 *out) {
    if(!c||!out||!valid_cap(c->present_fps))return 0;
    ShytNativeFrameClockV377 next=*c;
    ShytNativeFrameUpdateV377 update={0};
    if(!next.initialized) {
        next.initialized=1;next.last_ns=now;
    } else {
        if(now<next.last_ns || now-next.last_ns>SHYT_V377_MAX_INTERVAL_NS)
            return 0; /* do not silently change simulation time */
        const uint64_t elapsed=now-next.last_ns;
        next.last_ns=now;
        if(!next.paused) {
            /* exact rational 60 ticks / 1e9ns; no rounding per frame */
            const uint64_t pending=next.phase_units+
                elapsed*(uint64_t)SHYT_V377_SIM_HZ;
            if(pending/ONE_SEC>MAX_QUEUED)return 0;
            uint64_t due=pending/ONE_SEC;
            if(due>SHYT_V377_MAX_SUBSTEPS)due=SHYT_V377_MAX_SUBSTEPS;
            next.phase_units=pending-due*ONE_SEC;
            if(UINT64_MAX-next.simulated_steps<due)return 0;
            next.simulated_steps+=due;
            update.steps=(uint32_t)due;
            update.backlog_steps=(uint32_t)(next.phase_units/ONE_SEC);
            update.overload=(uint8_t)(update.backlog_steps!=0);
            next.overloaded=update.overload;
        }
    }
    /* Interpolation is useful only when the simulation has caught up. */
    update.interpolation_alpha=next.paused || next.phase_units>=ONE_SEC ?
        0.0:(double)next.phase_units/(double)ONE_SEC;
    *out=update;*c=next;return 1;
}
int shyt_native_frame_pause_v377(ShytNativeFrameClockV377 *c,
    int pause,uint64_t now) {
    if(!c||!c->initialized)return 0;
    c->last_ns=now;
    c->paused=(uint8_t)(pause!=0);
    c->phase_units=0;
    c->overloaded=0;
    c->present_initialized=0;
    c->present_remainder=0;
    return 1;
}
int shyt_native_frame_cap_v377(ShytNativeFrameClockV377 *c,uint32_t fps) {
    if(!c||!valid_cap(fps))return 0;
    c->present_fps=fps;
    c->present_initialized=0;
    c->present_remainder=0;
    return 1;
}
int shyt_native_frame_present_deadline_v377(ShytNativeFrameClockV377 *c,
    uint64_t now,uint64_t *deadline) {
    if(!c||!deadline||!valid_cap(c->present_fps))return 0;
    if(c->present_fps==0) {*deadline=now;return 1;}
    const uint64_t ns_per=ONE_SEC/c->present_fps;
    const uint64_t rem=ONE_SEC%c->present_fps;
    if(c->present_initialized && now<c->last_present_ns) {
        /* Pacing is a deadline suggestion. Polling early must not move it. */
        *deadline=c->last_present_ns;
        return 1;
    }
    if(!c->present_initialized ||
       now-c->last_present_ns>SHYT_V377_MAX_INTERVAL_NS) {
        c->last_present_ns=now;
        c->present_remainder=0;
        c->present_initialized=1;
    } else if(now>c->last_present_ns) {
        /* Late: rebase from actual presentation rather than busy-waiting
         * across multiple elapsed intervals; cap is not simulation time. */
        c->last_present_ns=now;
        c->present_remainder=0;
    }
    uint64_t extra=0;
    c->present_remainder+=rem;
    if(c->present_remainder>=c->present_fps) {
        c->present_remainder-=c->present_fps;
        extra=1;
    }
    if(c->last_present_ns>UINT64_MAX-ns_per-extra)return 0;
    *deadline=c->last_present_ns+ns_per+extra;
    c->last_present_ns=*deadline;
    return 1;
}
