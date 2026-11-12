/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "native_platform_caps_v380.h"
#include <string.h>

static int single_backend(uint32_t x) {
    return x && !(x&(x-1u)) && !(x&~SHYT_RENDER_ALL_V380);
}
int shyt_native_detect_target_v380(ShytNativeTargetV380 *out) {
    ShytNativeTargetV380 target={0};
    if (!out) return 0;
    if (sizeof(void*)!=8 || sizeof(uint64_t)!=8) return 0;
    target.pointer_bits=64;
#if defined(_WIN32)
    target.os=SHYT_OS_WINDOWS_V380;
    target.executable_format=SHYT_EXE_PE32PLUS_V380;
    /* Windows also defines _WIN32 on native 64-bit compilation. */
# if !defined(_WIN64)
    return 0;
# endif
#elif defined(__APPLE__) && defined(__MACH__)
    target.os=SHYT_OS_MACOS_V380;
    target.executable_format=SHYT_EXE_MACHO64_V380;
#elif defined(__linux__)
    target.os=SHYT_OS_LINUX_V380;
    target.executable_format=SHYT_EXE_ELF64_V380;
#else
    return 0;
#endif
#if defined(__x86_64__) || defined(_M_X64)
    target.arch=SHYT_ARCH_AMD64_V380;
#elif defined(__aarch64__) || defined(_M_ARM64)
    target.arch=SHYT_ARCH_ARM64_V380;
#else
    return 0;
#endif
    *out=target;
    return 1;
}
uint32_t shyt_native_allowed_renderers_v380(uint32_t os) {
    switch (os) {
    case SHYT_OS_WINDOWS_V380:
        return SHYT_RENDER_D3D12_V380|SHYT_RENDER_VULKAN_V380;
    case SHYT_OS_LINUX_V380:
        return SHYT_RENDER_VULKAN_V380;
    case SHYT_OS_MACOS_V380:
        return SHYT_RENDER_METAL_V380|SHYT_RENDER_VULKAN_V380;
    default:
        return 0;
    }
}
static const ShytNativeBackendProbeV380 *locate(
    const ShytNativeBackendProbeV380 *probes, size_t n, uint32_t backend) {
    for (size_t i=0;i<n;i++) {
        if (probes[i].renderer==backend) return &probes[i];
    }
    return NULL;
}
static int compatible(const ShytNativeBackendProbeV380 *p,
                      const ShytNativeRendererRequestV380 *r) {
    return p && p->device_ready==1 && p->surface_ready==1 &&
           p->shader_pipeline_ready==1 &&
           (r->required_features & ~p->verified_features)==0;
}

int shyt_native_choose_renderer_v380(
    const ShytNativeTargetV380 *target,
    const ShytNativeBackendProbeV380 *probes, size_t n,
    const ShytNativeRendererRequestV380 *request,
    ShytNativeRendererChoiceV380 *out) {
    ShytNativeTargetV380 detected={0};
    uint32_t allowed, order[3]={0};
    if (!target || !probes || !request || !out ||
        !shyt_native_detect_target_v380(&detected) ||
        memcmp(target,&detected,sizeof(detected)) ||
        !n || n>3 || request->allow_fallback>1 ||
        (request->required_features|request->optional_features)&
          ~SHYT_FEAT_ALL_V380 ||
        (request->preferred_renderer &&
         !single_backend(request->preferred_renderer)))
        return 0;
    allowed=shyt_native_allowed_renderers_v380(detected.os);
    if (request->preferred_renderer &&
        !(allowed&request->preferred_renderer)) return 0;
    for (size_t i=0;i<n;i++) {
        if (!single_backend(probes[i].renderer) ||
            !(allowed&probes[i].renderer) ||
            (probes[i].verified_features&~SHYT_FEAT_ALL_V380) ||
            probes[i].device_ready>1 || probes[i].surface_ready>1 ||
            probes[i].shader_pipeline_ready>1) return 0;
        for (size_t j=0;j<i;j++) {
            if (probes[j].renderer==probes[i].renderer) return 0;
        }
    }
    if (detected.os==SHYT_OS_WINDOWS_V380) {
        order[0]=SHYT_RENDER_D3D12_V380;
        order[1]=SHYT_RENDER_VULKAN_V380;
    } else if (detected.os==SHYT_OS_LINUX_V380) {
        order[0]=SHYT_RENDER_VULKAN_V380;
    } else if (detected.os==SHYT_OS_MACOS_V380) {
        order[0]=SHYT_RENDER_METAL_V380;
        order[1]=SHYT_RENDER_VULKAN_V380;
    }
    if (request->preferred_renderer) {
        const ShytNativeBackendProbeV380 *p=locate(probes,n,request->preferred_renderer);
        if (compatible(p,request)) {
            ShytNativeRendererChoiceV380 next={0};
            next.renderer=p->renderer;
            next.enabled_features=(request->required_features|
                request->optional_features)&p->verified_features;
            next.unavailable_optional_features=
                request->optional_features&~p->verified_features;
            *out=next;
            return 1;
        }
        if (!request->allow_fallback) return 0;
    }
    for (size_t i=0;i<3;i++) {
        const ShytNativeBackendProbeV380 *p;
        ShytNativeRendererChoiceV380 next={0};
        if (!order[i] || (request->preferred_renderer &&
                          order[i]==request->preferred_renderer)) continue;
        p=locate(probes,n,order[i]);
        if (!compatible(p,request)) continue;
        next.renderer=p->renderer;
        next.enabled_features=(request->required_features|
            request->optional_features)&p->verified_features;
        next.unavailable_optional_features=
            request->optional_features&~p->verified_features;
        *out=next;
        return 1;
    }
    return 0;
}
