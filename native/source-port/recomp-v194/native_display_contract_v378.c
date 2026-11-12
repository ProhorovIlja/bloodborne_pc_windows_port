/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "native_display_contract_v378.h"
#include <float.h>
#include <limits.h>
#include <math.h>

#define SHYT_STATIC_ASSERT(c,n) _Static_assert(c,#n)
SHYT_STATIC_ASSERT(sizeof(void *)==8, port_requires_64_bit_pointers);
SHYT_STATIC_ASSERT(sizeof(uint64_t)==8, no_32_bit_offset_narrowing);

#define SHYT_V378_PI 3.14159265358979323846

static int fits(uint32_t w,uint32_t h,uint64_t max_pixels) {
    return w>0 && h>0 && (uint64_t)w*h<=max_pixels;
}
static ShytDisplayRectV378 centered(uint32_t outer_w,uint32_t outer_h,
                                    uint32_t rect_w,uint32_t rect_h) {
    ShytDisplayRectV378 r;
    r.width=rect_w;
    r.height=rect_h;
    r.x=(outer_w-rect_w)/2;
    r.y=(outer_h-rect_h)/2;
    return r;
}
int shyt_native_x64_abi_v378(void) {
#if defined(__x86_64__) || defined(_M_X64)
    return sizeof(void*)==8 && sizeof(size_t)==8;
#else
    return 0;
#endif
}
int shyt_native_display_plan_v378(const ShytDisplayRequestV378 *request,
                                   const ShytDisplayCapsV378 *caps,
                                   ShytDisplayPlanV378 *out) {
    ShytDisplayPlanV378 p={0};
    uint64_t rw,rh,scaled_w,scaled_h,rect_w,rect_h;
    double radians;
    if (!request || !caps || !out) return 0;
    if (!shyt_native_x64_abi_v378()) return 0;
    if (!caps->max_output_width || !caps->max_output_height ||
        !caps->max_texture_dim_2d || !caps->max_output_pixels ||
        !caps->max_render_pixels) return 0;
    if (!request->output_width || !request->output_height ||
        request->output_width>caps->max_output_width ||
        request->output_height>caps->max_output_height ||
        !fits(request->output_width,request->output_height,
              caps->max_output_pixels)) return 0;
    if (request->render_scale_per_mille<500 ||
        request->render_scale_per_mille>2000 ||
        request->hud_safe_per_mille<800 ||
        request->hud_safe_per_mille>1000 ||
        !isfinite(request->vertical_fov_degrees) ||
        request->vertical_fov_degrees<20. ||
        request->vertical_fov_degrees>140.) return 0;
    /* All intermediate products are 64-bit; never use silent 32-bit wrap.
     * Round scale to nearest EVEN to accommodate texture/video encoders. */
    scaled_w=(uint64_t)request->output_width*request->render_scale_per_mille;
    scaled_h=(uint64_t)request->output_height*request->render_scale_per_mille;
    rw=((scaled_w+1000)/2000)*2;
    rh=((scaled_h+1000)/2000)*2;
    if (!rw || !rh || rw>UINT32_MAX || rh>UINT32_MAX ||
        rw>caps->max_texture_dim_2d || rh>caps->max_texture_dim_2d ||
        rw*rh>caps->max_render_pixels) return 0;
    p.output_width=request->output_width;
    p.output_height=request->output_height;
    p.render_width=(uint32_t)rw;
    p.render_height=(uint32_t)rh;
    p.output_aspect=(double)p.output_width/(double)p.output_height;
    radians=request->vertical_fov_degrees*(SHYT_V378_PI/180.);
    p.fov_vertical_degrees=request->vertical_fov_degrees;
    p.fov_horizontal_degrees=2.*atan(tan(radians/2.)*p.output_aspect)*180./SHYT_V378_PI;
    if (!isfinite(p.fov_horizontal_degrees)) return 0;

    /* Entire 16:9 content fitted inside screen: rational comparison avoids
     * 32-bit overflow and noninteger ultrawide approximations. */
    if ((uint64_t)p.output_width*9 >= (uint64_t)p.output_height*16) {
        rect_h=p.output_height;
        rect_w=((uint64_t)p.output_height*16)/9;
    } else {
        rect_w=p.output_width;
        rect_h=((uint64_t)p.output_width*9)/16;
    }
    if (!rect_w || !rect_h || rect_w>p.output_width || rect_h>p.output_height)
        return 0;
    p.fitted_16_9=centered(p.output_width,p.output_height,
                            (uint32_t)rect_w,(uint32_t)rect_h);
    {
        uint64_t safe_w=(rect_w*request->hud_safe_per_mille)/1000;
        uint64_t safe_h=(rect_h*request->hud_safe_per_mille)/1000;
        if (!safe_w || !safe_h) return 0;
        p.hud_safe=centered(p.output_width,p.output_height,
                            (uint32_t)safe_w,(uint32_t)safe_h);
    }
    *out=p;
    return 1;
}
int shyt_native_surface_reuse_v378(const ShytDisplaySurfaceKeyV378 *a,
                                   const ShytDisplaySurfaceKeyV378 *b) {
    if (!a || !b || !a->width || !a->height || !b->width || !b->height ||
        !a->samples || !b->samples || !a->usage || !b->usage) return 0;
    return a->width==b->width && a->height==b->height &&
        a->format==b->format && a->samples==b->samples &&
        a->usage==b->usage && a->color_space==b->color_space;
}
