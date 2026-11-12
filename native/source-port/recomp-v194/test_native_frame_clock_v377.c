/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "native_frame_clock_v377.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static void render_fps_independent_ticks(unsigned presentation_hz) {
    ShytNativeFrameClockV377 c;
    ShytNativeFrameUpdateV377 out;
    assert(shyt_native_frame_init_v377(&c,presentation_hz));
    for(uint64_t i=0;i<=10ull*presentation_hz;++i) {
        const uint64_t now=i*10000000000ull/(10ull*presentation_hz);
        assert(shyt_native_frame_advance_v377(&c,now,&out));
        assert(out.steps<=SHYT_V377_MAX_SUBSTEPS);
        assert(out.interpolation_alpha>=0.0 && out.interpolation_alpha<1.0);
        assert(out.overload==0);
    }
    assert(c.simulated_steps==600);
}
static void basics(void) {
    ShytNativeFrameClockV377 c;
    ShytNativeFrameUpdateV377 out,prior;
    assert(!shyt_native_frame_init_v377(&c,144));
    assert(shyt_native_frame_init_v377(&c,0));
    assert(shyt_native_frame_advance_v377(&c,1000000,&out));
    assert(out.steps==0);
    assert(shyt_native_frame_advance_v377(&c,1000000+100000000,&out));
    assert(out.steps==6 && c.simulated_steps==6);
    prior=out;
    const uint64_t last=c.last_ns;
    assert(!shyt_native_frame_advance_v377(&c,last-1,&out));
    assert(c.last_ns==last && memcmp(&prior,&out,sizeof out)==0);
    assert(!shyt_native_frame_advance_v377(&c,last+250000001,&out));
    assert(c.last_ns==last);
    assert(shyt_native_frame_advance_v377(&c,last+250000000,&out));
    assert(out.steps==8 && out.backlog_steps==7 && out.overload);
    /* Clear outstanding 7 without a new wall-time advance. */
    assert(shyt_native_frame_advance_v377(&c,c.last_ns,&out));
    assert(out.steps==7 && out.backlog_steps==0 && !out.overload);
    assert(c.simulated_steps==21);
    assert(shyt_native_frame_pause_v377(&c,1,9999999999ull));
    assert(shyt_native_frame_advance_v377(&c,9999999999ull+200000000,&out));
    assert(out.steps==0 && c.simulated_steps==21);
    assert(shyt_native_frame_pause_v377(&c,0,9999999999ull+200000000));
    assert(shyt_native_frame_advance_v377(&c,9999999999ull+216666667,&out));
    assert(out.steps==1 && c.simulated_steps==22);
    assert(!shyt_native_frame_cap_v377(&c,99));
    assert(shyt_native_frame_cap_v377(&c,120));
    uint64_t deadline;
    assert(shyt_native_frame_present_deadline_v377(&c,9999999999ull,&deadline));
    assert(deadline>9999999999ull && deadline-9999999999ull<=8333334ull);
    uint64_t early;
    assert(shyt_native_frame_present_deadline_v377(&c,9999999999ull,&early));
    assert(early==deadline); /* early polling must never advance the cap */
    uint64_t at=deadline;
    for(unsigned i=0;i<119;++i){
        assert(shyt_native_frame_present_deadline_v377(&c,at,&at));
    }
    /* 120 successive 120Hz deadlines equal exactly one wall second. */
    assert(at==9999999999ull+1000000000ull);
    assert(shyt_native_frame_cap_v377(&c,0));
    assert(shyt_native_frame_present_deadline_v377(&c,123,&deadline));
    assert(deadline==123);
}
int main(void) {
    render_fps_independent_ticks(30);
    render_fps_independent_ticks(60);
    render_fps_independent_ticks(120);
    render_fps_independent_ticks(240);
    basics();
    puts("NATIVE_V377_FIXED60_SIM_30_60_120_240_UNLIMITED_RENDER_CAPS_PASS");
    return 0;
}
