/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "native_platform_caps_v380.h"
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#define CHECK(x) do {if(!(x)){fprintf(stderr,"V380_FAILED_LINE_%d\n",__LINE__);return 1;}}while(0)
static int all_tests(void) {
    ShytNativeTargetV380 host={0}, forged;
    ShytNativeRendererChoiceV380 choice={0}, saved;
    ShytNativeBackendProbeV380 p[3]={
        {SHYT_RENDER_D3D12_V380,
         SHYT_FEAT_HDR_V380|SHYT_FEAT_FSR_V380|SHYT_FEAT_DYNAMIC_RES_V380,
         1,1,1},
        {SHYT_RENDER_VULKAN_V380,
         SHYT_FEAT_HDR_V380|SHYT_FEAT_VRR_V380|SHYT_FEAT_DYNAMIC_RES_V380,
         1,1,1},
        {SHYT_RENDER_METAL_V380,
         SHYT_FEAT_DYNAMIC_RES_V380|SHYT_FEAT_FSR_V380,
         1,1,1}
    };
    ShytNativeBackendProbeV380 list[2];
    ShytNativeRendererRequestV380 req={0};
    uint32_t primary, secondary=0, os;
    CHECK(!shyt_native_detect_target_v380(NULL));
    CHECK(shyt_native_detect_target_v380(&host));
    CHECK(host.pointer_bits==64);
    CHECK(host.arch==SHYT_ARCH_AMD64_V380 ||
          host.arch==SHYT_ARCH_ARM64_V380);
    os=host.os;
#if defined(_WIN32)
    CHECK(os==SHYT_OS_WINDOWS_V380 && host.executable_format==SHYT_EXE_PE32PLUS_V380);
    CHECK(sizeof(void*)==8);
#elif defined(__APPLE__) && defined(__MACH__)
    CHECK(os==SHYT_OS_MACOS_V380 && host.executable_format==SHYT_EXE_MACHO64_V380);
#elif defined(__linux__)
    CHECK(os==SHYT_OS_LINUX_V380 && host.executable_format==SHYT_EXE_ELF64_V380);
#else
    CHECK(0);
#endif
    CHECK(shyt_native_allowed_renderers_v380(0)==0);
    CHECK(shyt_native_allowed_renderers_v380(SHYT_OS_WINDOWS_V380)==
          (SHYT_RENDER_D3D12_V380|SHYT_RENDER_VULKAN_V380));
    CHECK(shyt_native_allowed_renderers_v380(SHYT_OS_LINUX_V380)==
          SHYT_RENDER_VULKAN_V380);
    CHECK(shyt_native_allowed_renderers_v380(SHYT_OS_MACOS_V380)==
          (SHYT_RENDER_METAL_V380|SHYT_RENDER_VULKAN_V380));
    if (os==SHYT_OS_WINDOWS_V380) {
        primary=SHYT_RENDER_D3D12_V380;
        secondary=SHYT_RENDER_VULKAN_V380;
        list[0]=p[0];list[1]=p[1];
    } else if (os==SHYT_OS_LINUX_V380) {
        primary=SHYT_RENDER_VULKAN_V380;
        list[0]=p[1];list[1]=p[1];
    } else {
        primary=SHYT_RENDER_METAL_V380;
        secondary=SHYT_RENDER_VULKAN_V380;
        list[0]=p[2];list[1]=p[1];
    }
    req.optional_features=SHYT_FEAT_DYNAMIC_RES_V380|SHYT_FEAT_REFLEX_V380;
    CHECK(shyt_native_choose_renderer_v380(&host,list,1,&req,&choice));
    CHECK(choice.renderer==primary);
    CHECK(choice.enabled_features==SHYT_FEAT_DYNAMIC_RES_V380);
    CHECK(choice.unavailable_optional_features==SHYT_FEAT_REFLEX_V380);
    saved=choice;
    req.required_features=SHYT_FEAT_DLSS_V380;
    CHECK(!shyt_native_choose_renderer_v380(&host,list,1,&req,&choice));
    CHECK(!memcmp(&saved,&choice,sizeof(saved)));
    req.required_features=SHYT_FEAT_DYNAMIC_RES_V380;
    CHECK(shyt_native_choose_renderer_v380(&host,list,1,&req,&choice));
    CHECK(choice.enabled_features==SHYT_FEAT_DYNAMIC_RES_V380);
    req.preferred_renderer=SHYT_RENDER_METAL_V380;
    if (os!=SHYT_OS_MACOS_V380)
        CHECK(!shyt_native_choose_renderer_v380(&host,list,1,&req,&choice));
    req.preferred_renderer=primary;
    CHECK(shyt_native_choose_renderer_v380(&host,list,1,&req,&choice));
    req.preferred_renderer=SHYT_RENDER_D3D12_V380|SHYT_RENDER_VULKAN_V380;
    CHECK(!shyt_native_choose_renderer_v380(&host,list,1,&req,&choice));
    req.preferred_renderer=0;
    req.optional_features=SHYT_FEAT_ALL_V380+1u;
    CHECK(!shyt_native_choose_renderer_v380(&host,list,1,&req,&choice));
    req.optional_features=SHYT_FEAT_DYNAMIC_RES_V380;
    req.allow_fallback=2;
    CHECK(!shyt_native_choose_renderer_v380(&host,list,1,&req,&choice));
    req.allow_fallback=0;
    CHECK(!shyt_native_choose_renderer_v380(&host,list,0,&req,&choice));
    CHECK(!shyt_native_choose_renderer_v380(&host,list,4,&req,&choice));
    forged=host;forged.pointer_bits=32;
    CHECK(!shyt_native_choose_renderer_v380(&forged,list,1,&req,&choice));
    CHECK(!shyt_native_choose_renderer_v380(NULL,list,1,&req,&choice));
    CHECK(!shyt_native_choose_renderer_v380(&host,NULL,1,&req,&choice));
    CHECK(!shyt_native_choose_renderer_v380(&host,list,1,NULL,&choice));
    CHECK(!shyt_native_choose_renderer_v380(&host,list,1,&req,NULL));
    list[0].verified_features=SHYT_FEAT_ALL_V380+1u;
    CHECK(!shyt_native_choose_renderer_v380(&host,list,1,&req,&choice));
    list[0].verified_features=SHYT_FEAT_DYNAMIC_RES_V380;
    list[0].surface_ready=0;
    CHECK(!shyt_native_choose_renderer_v380(&host,list,1,&req,&choice));
    list[0].surface_ready=1;
    list[0].shader_pipeline_ready=0;
    CHECK(!shyt_native_choose_renderer_v380(&host,list,1,&req,&choice));
    list[0].shader_pipeline_ready=1;
    list[0].device_ready=0;
    CHECK(!shyt_native_choose_renderer_v380(&host,list,1,&req,&choice));
    list[0].device_ready=1;
    CHECK(shyt_native_choose_renderer_v380(&host,list,1,&req,&choice));
    if (secondary) {
        list[1]=p[1];
        req.preferred_renderer=primary;
        req.allow_fallback=1;
        list[0].device_ready=0;
        CHECK(shyt_native_choose_renderer_v380(&host,list,2,&req,&choice));
        CHECK(choice.renderer==secondary);
        CHECK(!shyt_native_choose_renderer_v380(&host,list,2,
              &(ShytNativeRendererRequestV380){primary,SHYT_FEAT_DLSS_V380,0,1},&choice));
        CHECK(!shyt_native_choose_renderer_v380(&host,
              (ShytNativeBackendProbeV380[]){list[1],list[1]},2,&req,&choice));
    } else {
        CHECK(!shyt_native_choose_renderer_v380(&host,list,2,&req,&choice));
    }
    return 0;
}
int main(void) {
    CHECK(!all_tests());
    puts("NATIVE_V380_WIN32_IS_NOT_32BIT_X64_LINUX_MACOS_BACKEND_CAPS_PASS");
    return 0;
}
