/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "native_display_contract_v378.h"
#include <math.h>
#include <stdio.h>
#include <string.h>
#include <stdint.h>
#define CHECK(x) do { if(!(x)) {fprintf(stderr,"V378_ASSERT_LINE_%d\n",__LINE__);return 1;} }while(0)
static int trial(uint32_t w,uint32_t h,uint32_t scale) {
    ShytDisplayCapsV378 caps={32768,32768,32768,300000000ULL,300000000ULL};
    ShytDisplayRequestV378 req={w,h,scale,900,60.};
    ShytDisplayPlanV378 result={0};
    CHECK(shyt_native_display_plan_v378(&req,&caps,&result));
    CHECK(result.output_width==w && result.output_height==h);
    CHECK(result.render_width>0 && !(result.render_width&1));
    CHECK(result.render_height>0 && !(result.render_height&1));
    CHECK(result.fov_vertical_degrees==60.);
    CHECK(result.fov_horizontal_degrees>0. && result.fov_horizontal_degrees<180.);
    CHECK(result.hud_safe.width<=result.fitted_16_9.width);
    CHECK(result.hud_safe.height<=result.fitted_16_9.height);
    CHECK((uint64_t)result.hud_safe.x+result.hud_safe.width<=w);
    CHECK((uint64_t)result.hud_safe.y+result.hud_safe.height<=h);
    CHECK((uint64_t)result.fitted_16_9.x+result.fitted_16_9.width<=w);
    CHECK((uint64_t)result.fitted_16_9.y+result.fitted_16_9.height<=h);
    return 0;
}
int main(void) {
    ShytDisplayCapsV378 caps={32768,32768,32768,300000000ULL,300000000ULL};
    ShytDisplayRequestV378 req={7680,2160,1000,1000,60.};
    ShytDisplayPlanV378 out={0};
    const uint32_t resolutions[][2]={{640,480},{1280,720},{1920,1080},
      {2560,1440},{3840,2160},{7680,4320},{2560,1600},{1920,1200},
      {2560,1080},{3440,1440},{5120,2160},{3840,1600},{5120,1440},
      {7680,2160},{1080,1920},{4096,2160},{7680,3200}};
    CHECK(shyt_native_x64_abi_v378());
    for(size_t i=0;i<sizeof(resolutions)/sizeof(resolutions[0]);i++) {
       CHECK(!trial(resolutions[i][0],resolutions[i][1],1000));
       CHECK(!trial(resolutions[i][0],resolutions[i][1],500));
    }
    CHECK(!trial(3440,1440,1500));
    CHECK(shyt_native_display_plan_v378(&req,&caps,&out));
    CHECK(out.fitted_16_9.width==3840 && out.fitted_16_9.height==2160);
    CHECK(out.fitted_16_9.x==1920 && out.fitted_16_9.y==0);
    CHECK(out.hud_safe.width==3840 && out.hud_safe.height==2160);
    CHECK(out.output_aspect>3.5);
    {ShytDisplayRequestV378 std={1920,1080,1000,900,60.};
      ShytDisplayPlanV378 regular={0};
      CHECK(shyt_native_display_plan_v378(&std,&caps,&regular));
      CHECK(regular.fov_horizontal_degrees<out.fov_horizontal_degrees);
    }
    /* One-side dimensions must not trigger attachment sharing. */
    {ShytDisplaySurfaceKeyV378 old={5120,2160,28,1,1,0};
     ShytDisplaySurfaceKeyV378 same=old;
     CHECK(shyt_native_surface_reuse_v378(&old,&same));
     same.width=3840;CHECK(!shyt_native_surface_reuse_v378(&old,&same));
     same=old;same.height=1440;CHECK(!shyt_native_surface_reuse_v378(&old,&same));
     same=old;same.format=29;CHECK(!shyt_native_surface_reuse_v378(&old,&same));
     same=old;same.samples=4;CHECK(!shyt_native_surface_reuse_v378(&old,&same));
     same=old;same.usage=2;CHECK(!shyt_native_surface_reuse_v378(&old,&same));
     same=old;same.color_space=1;CHECK(!shyt_native_surface_reuse_v378(&old,&same));
    }
    /* Fail closed and do not alter the prior valid output on error. */
    {ShytDisplayPlanV378 saved=out; req.output_width=0;
     CHECK(!shyt_native_display_plan_v378(&req,&caps,&out));
     CHECK(!memcmp(&saved,&out,sizeof(saved)));
     req.output_width=32769;CHECK(!shyt_native_display_plan_v378(&req,&caps,&out));
     req.output_width=7680;req.render_scale_per_mille=2500;
     CHECK(!shyt_native_display_plan_v378(&req,&caps,&out));
     req.render_scale_per_mille=1000;req.vertical_fov_degrees=NAN;
     CHECK(!shyt_native_display_plan_v378(&req,&caps,&out));
     req.vertical_fov_degrees=60.;caps.max_render_pixels=2;
     CHECK(!shyt_native_display_plan_v378(&req,&caps,&out));
     CHECK(!memcmp(&saved,&out,sizeof(saved)));
    }
    puts("NATIVE_V378_64BIT_43_169_1610_219_329_PORTRAIT_HDR_SAFE_RESIZE_PASS");
    return 0;
}
