/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "native_present_guard_v379.h"
#include <limits.h>
#include <string.h>

static int valid_key(const ShytDisplaySurfaceKeyV378 *key) {
    return key && key->width && key->height && key->format &&
           key->samples && key->usage;
}
static int valid_mode(const ShytNativeModeV379 *mode) {
    return mode && mode->width && mode->height &&
           mode->refresh_num && mode->refresh_den;
}
static int same_rate(const ShytNativeModeV379 *a,
                     const ShytNativeModeV379 *b) {
    /* Both operands fit UINT32, hence each product fits UINT64. */
    return (uint64_t)a->refresh_num*b->refresh_den ==
           (uint64_t)b->refresh_num*a->refresh_den;
}
static int faster(const ShytNativeModeV379 *a,
                  const ShytNativeModeV379 *b) {
    return (uint64_t)a->refresh_num*b->refresh_den >
           (uint64_t)b->refresh_num*a->refresh_den;
}

int shyt_native_exact_mode_v379(const ShytNativeModeV379 *enumerated,
                                size_t count,
                                const ShytNativeModeV379 *requested,
                                ShytNativeModeV379 *selected) {
    ShytNativeModeV379 pick={0};
    int found=0, any_rate;
    if (!enumerated || !requested || !selected || !count || count>1024 ||
        !requested->width || !requested->height) return 0;
    any_rate=!requested->refresh_num && !requested->refresh_den;
    if (!any_rate &&
        (!requested->refresh_num || !requested->refresh_den)) return 0;
    for (size_t i=0; i<count; ++i) {
        const ShytNativeModeV379 *m=&enumerated[i];
        if (!valid_mode(m) || m->width!=requested->width ||
            m->height!=requested->height) continue;
        if (!any_rate && !same_rate(m,requested)) continue;
        if (!found || faster(m,&pick)) {
            pick=*m;
            found=1;
        }
    }
    if (!found) return 0;
    *selected=pick;
    return 1;
}

int shyt_native_surface_extent_v379(const ShytNativeModeV379 *mode,
                                    const ShytNativeWsiCapsV379 *caps) {
    if (!valid_mode(mode) || !caps || !caps->format_colorspace_supported ||
        caps->format_colorspace_supported!=1 ||
        caps->presentation_supported!=1 || caps->usage_supported!=1 ||
        !caps->min_width || !caps->min_height ||
        caps->max_width<caps->min_width ||
        caps->max_height<caps->min_height ||
        !caps->max_surface_pixels) return 0;
    if (mode->width<caps->min_width || mode->width>caps->max_width ||
        mode->height<caps->min_height || mode->height>caps->max_height ||
        (uint64_t)mode->width*mode->height>caps->max_surface_pixels)
        return 0;
    if (caps->current_width==UINT32_MAX &&
        caps->current_height==UINT32_MAX) return 1;
    if (!caps->current_width || !caps->current_height ||
        caps->current_width==UINT32_MAX ||
        caps->current_height==UINT32_MAX) return 0;
    return mode->width==caps->current_width &&
           mode->height==caps->current_height;
}

int shyt_native_target_init_v379(ShytNativeTargetStateV379 *s,
                                 const ShytDisplaySurfaceKeyV378 *initial) {
    ShytNativeTargetStateV379 next={0};
    if (!s || !valid_key(initial) || s->has_active || s->has_retired)
        return 0;
    next.active_key=*initial;
    next.generation=1;
    next.has_active=1;
    *s=next;
    return 1;
}
int shyt_native_target_submit_v379(ShytNativeTargetStateV379 *s,
                                   uint64_t fence) {
    if (!s || s->has_active!=1 || !fence ||
        fence<=s->last_submitted || fence==UINT64_MAX) return 0;
    s->last_submitted=fence;
    s->active_last_submit=fence;
    return 1;
}
int shyt_native_target_complete_v379(ShytNativeTargetStateV379 *s,
                                     uint64_t completed) {
    if (!s || s->has_active!=1 || completed<s->completed_fence ||
        completed>s->last_submitted) return 0;
    s->completed_fence=completed;
    return 1;
}
int shyt_native_target_resize_v379(ShytNativeTargetStateV379 *s,
                                   const ShytDisplaySurfaceKeyV378 *next) {
    if (!s || s->has_active!=1 || !valid_key(next)) return 0;
    if (shyt_native_surface_reuse_v378(&s->active_key,next)) return 1;
    /* The old retirement MUST be explicitly destroyed first. */
    if (s->has_retired || s->generation==UINT64_MAX) return 0;
    s->retired_key=s->active_key;
    s->retired_last_submit=s->active_last_submit;
    s->has_retired=1;
    s->active_key=*next;
    s->active_last_submit=0;
    ++s->generation;
    return 1;
}
int shyt_native_target_may_destroy_retired_v379(
    const ShytNativeTargetStateV379 *s) {
    return s && s->has_active==1 && s->has_retired==1 &&
           s->completed_fence>=s->retired_last_submit;
}
int shyt_native_target_ack_destroy_v379(ShytNativeTargetStateV379 *s) {
    if (!shyt_native_target_may_destroy_retired_v379(s)) return 0;
    memset(&s->retired_key,0,sizeof(s->retired_key));
    s->retired_last_submit=0;
    s->has_retired=0;
    return 1;
}
