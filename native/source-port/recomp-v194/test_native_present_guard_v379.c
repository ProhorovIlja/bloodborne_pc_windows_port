/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "native_present_guard_v379.h"
#include <limits.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#define CHECK(e) do { if (!(e)) {fprintf(stderr,"NATIVE_V379_LINE_%d\n",__LINE__);return 1;} } while(0)

static int modes_and_wsi(void) {
    const ShytNativeModeV379 modes[] = {
        {1920,1080,60,1}, {2560,1440,144,1},
        {3440,1440,60000,1001}, {3440,1440,60,1},
        {5120,1440,120,1}, {7680,4320,60,1},
        {1080,1920,60,1}, {0,0,0,0}, {3440,1440,144,1}
    };
    ShytNativeModeV379 requested={3440,1440,0,0};
    ShytNativeModeV379 selected={1,2,3,4};
    const ShytNativeModeV379 old=selected;
    ShytNativeWsiCapsV379 caps={64,64,8192,8192,UINT32_MAX,UINT32_MAX,
                               68000000ULL,1,1,1};
    CHECK(shyt_native_exact_mode_v379(modes,9,&requested,&selected));
    CHECK(selected.refresh_num==144 && selected.refresh_den==1);
    CHECK(shyt_native_surface_extent_v379(&selected,&caps));
    requested.refresh_num=60000;requested.refresh_den=1001;
    CHECK(shyt_native_exact_mode_v379(modes,9,&requested,&selected));
    CHECK(selected.refresh_num==60000 && selected.refresh_den==1001);
    requested.refresh_num=60000;requested.refresh_den=1000;
    CHECK(shyt_native_exact_mode_v379(modes,9,&requested,&selected));
    CHECK(selected.refresh_num==60 && selected.refresh_den==1);
    requested.refresh_num=165;requested.refresh_den=1;
    {ShytNativeModeV379 prev=selected;
     CHECK(!shyt_native_exact_mode_v379(modes,9,&requested,&selected));
     CHECK(!memcmp(&prev,&selected,sizeof(prev)));
    }
    requested.width=5120;requested.height=2160;requested.refresh_num=0;requested.refresh_den=0;
    CHECK(!shyt_native_exact_mode_v379(modes,9,&requested,&selected));
    requested.width=3440;requested.height=1440;requested.refresh_num=100;requested.refresh_den=0;
    CHECK(!shyt_native_exact_mode_v379(modes,9,&requested,&selected));
    requested.refresh_num=0;requested.refresh_den=0;
    CHECK(!shyt_native_exact_mode_v379(NULL,9,&requested,&selected));
    CHECK(!shyt_native_exact_mode_v379(modes,0,&requested,&selected));
    CHECK(!shyt_native_exact_mode_v379(modes,1025,&requested,&selected));
    CHECK(!shyt_native_exact_mode_v379(modes,9,&requested,NULL));
    CHECK(shyt_native_exact_mode_v379(modes,9,&requested,&selected));

    caps.current_width=3440;caps.current_height=1440;
    CHECK(shyt_native_surface_extent_v379(&selected,&caps));
    caps.current_height=1080; CHECK(!shyt_native_surface_extent_v379(&selected,&caps));
    caps.current_width=0;caps.current_height=0;
    CHECK(!shyt_native_surface_extent_v379(&selected,&caps)); /* minimized */
    caps.current_width=UINT32_MAX;caps.current_height=1440;
    CHECK(!shyt_native_surface_extent_v379(&selected,&caps)); /* invalid mixed */
    caps.current_height=UINT32_MAX;
    caps.format_colorspace_supported=0;
    CHECK(!shyt_native_surface_extent_v379(&selected,&caps));
    caps.format_colorspace_supported=1;caps.presentation_supported=0;
    CHECK(!shyt_native_surface_extent_v379(&selected,&caps));
    caps.presentation_supported=1;caps.usage_supported=0;
    CHECK(!shyt_native_surface_extent_v379(&selected,&caps));
    caps.usage_supported=1;caps.max_surface_pixels=200;
    CHECK(!shyt_native_surface_extent_v379(&selected,&caps));
    caps.max_surface_pixels=68000000ULL;caps.max_width=1920;
    CHECK(!shyt_native_surface_extent_v379(&selected,&caps));
    caps.max_width=8192;caps.min_height=8193;
    CHECK(!shyt_native_surface_extent_v379(&selected,&caps));
    CHECK(old.width==1 && old.height==2); /* no mutation of caller inputs */
    return 0;
}

static int target_lifetime(void) {
    const ShytDisplaySurfaceKeyV378 a={3440,1440,28,1,1,0};
    const ShytDisplaySurfaceKeyV378 b={3840,2160,28,1,1,0};
    const ShytDisplaySurfaceKeyV378 c={5120,1440,28,1,1,0};
    ShytDisplaySurfaceKeyV378 bad=a;
    ShytNativeTargetStateV379 s={0};
    CHECK(!shyt_native_target_init_v379(&s,NULL));
    CHECK(shyt_native_target_init_v379(&s,&a));
    CHECK(s.generation==1 && s.has_active==1);
    CHECK(!shyt_native_target_init_v379(&s,&b)); /* cannot reset in flight */
    CHECK(!shyt_native_target_submit_v379(&s,0));
    CHECK(shyt_native_target_submit_v379(&s,10));
    CHECK(!shyt_native_target_submit_v379(&s,10));
    CHECK(!shyt_native_target_submit_v379(&s,9));
    CHECK(!shyt_native_target_complete_v379(&s,11));
    CHECK(shyt_native_target_complete_v379(&s,4));
    bad.width=0;
    CHECK(!shyt_native_target_resize_v379(&s,&bad));
    CHECK(s.generation==1 && !s.has_retired);
    CHECK(shyt_native_target_resize_v379(&s,&a));
    CHECK(s.generation==1 && !s.has_retired); /* exact key = reuse */
    CHECK(shyt_native_target_resize_v379(&s,&b));
    CHECK(s.generation==2 && s.has_retired && s.retired_last_submit==10);
    CHECK(!shyt_native_target_may_destroy_retired_v379(&s));
    CHECK(!shyt_native_target_ack_destroy_v379(&s));
    CHECK(!shyt_native_target_resize_v379(&s,&c)); /* no unsafe second retire */
    CHECK(s.generation==2 && s.active_key.width==3840);
    CHECK(shyt_native_target_submit_v379(&s,11));
    CHECK(shyt_native_target_complete_v379(&s,10));
    CHECK(shyt_native_target_may_destroy_retired_v379(&s));
    CHECK(shyt_native_target_ack_destroy_v379(&s)); /* after actual GPU destroy */
    CHECK(!s.has_retired && s.active_last_submit==11);
    CHECK(shyt_native_target_resize_v379(&s,&c));
    CHECK(s.generation==3 && s.retired_last_submit==11);
    CHECK(!shyt_native_target_may_destroy_retired_v379(&s));
    CHECK(!shyt_native_target_complete_v379(&s,9)); /* old fence regression */
    CHECK(shyt_native_target_complete_v379(&s,11));
    CHECK(shyt_native_target_may_destroy_retired_v379(&s));
    CHECK(shyt_native_target_ack_destroy_v379(&s));
    CHECK(!shyt_native_target_ack_destroy_v379(&s));
    CHECK(shyt_native_target_resize_v379(&s,&a));
    CHECK(shyt_native_target_may_destroy_retired_v379(&s)); /* never submitted C */
    CHECK(shyt_native_target_ack_destroy_v379(&s));
    CHECK(!shyt_native_target_submit_v379(&s,UINT64_MAX)); /* no fence wrap */
    return 0;
}

int main(void) {
    CHECK(shyt_native_x64_abi_v378());
    CHECK(!modes_and_wsi());
    CHECK(!target_lifetime());
    puts("NATIVE_V379_ENUMERATED_MODE_WSI_FIXED_EXTENT_FENCE_RETIREMENT_PASS");
    return 0;
}
