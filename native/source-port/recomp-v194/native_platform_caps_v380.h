/* SPDX-License-Identifier: GPL-2.0-or-later
 * V380: 64-bit native host identity, graphics-backend capability contracts.
 * This is source-only infrastructure; it cannot establish game readiness.
 */
#ifndef SHYT_NATIVE_PLATFORM_CAPS_V380_H
#define SHYT_NATIVE_PLATFORM_CAPS_V380_H
#include <stddef.h>
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif

enum {
    SHYT_OS_UNKNOWN_V380=0, SHYT_OS_WINDOWS_V380=1,
    SHYT_OS_LINUX_V380=2, SHYT_OS_MACOS_V380=3
};
enum {
    SHYT_ARCH_UNKNOWN_V380=0, SHYT_ARCH_AMD64_V380=1,
    SHYT_ARCH_ARM64_V380=2
};
enum {
    SHYT_EXE_UNKNOWN_V380=0, SHYT_EXE_PE32PLUS_V380=1,
    SHYT_EXE_ELF64_V380=2, SHYT_EXE_MACHO64_V380=3
};
enum {
    SHYT_RENDER_D3D12_V380=1u<<0,
    SHYT_RENDER_VULKAN_V380=1u<<1,
    SHYT_RENDER_METAL_V380=1u<<2,
    SHYT_RENDER_ALL_V380=(1u<<3)-1u
};
enum {
    SHYT_FEAT_HDR_V380=1u<<0,
    SHYT_FEAT_VRR_V380=1u<<1,
    SHYT_FEAT_FSR_V380=1u<<2,
    SHYT_FEAT_DLSS_V380=1u<<3,
    SHYT_FEAT_XESS_V380=1u<<4,
    SHYT_FEAT_FRAME_GEN_V380=1u<<5,
    SHYT_FEAT_REFLEX_V380=1u<<6,
    SHYT_FEAT_XELL_V380=1u<<7,
    SHYT_FEAT_DYNAMIC_RES_V380=1u<<8,
    SHYT_FEAT_ALL_V380=(1u<<9)-1u
};
typedef struct ShytNativeTargetV380 {
    uint32_t os, arch, executable_format, pointer_bits;
} ShytNativeTargetV380;

/* _WIN32 is defined in 64-bit Windows builds too; test _WIN64/ISA
 * separately. This detection tells us a HOST build target, not whether
 * proprietary original-game code has been successfully recompiled. */
int shyt_native_detect_target_v380(ShytNativeTargetV380 *out);
uint32_t shyt_native_allowed_renderers_v380(uint32_t os);

/* Each probe is a snapshot from one actual, initialized renderer. The
 * caller MUST perform genuine driver/device/surface/shader and optional
 * SDK/extension checks before setting the flags, separately for each GPU.
 * Never advertise DLSS/FSR/Reflex/etc merely because a platform is x64.
 */
typedef struct ShytNativeBackendProbeV380 {
    uint32_t renderer; /* exactly one SHYT_RENDER_* bit */
    uint32_t verified_features; /* backend-specific capability snapshot */
    uint8_t device_ready, surface_ready, shader_pipeline_ready;
} ShytNativeBackendProbeV380;
typedef struct ShytNativeRendererRequestV380 {
    uint32_t preferred_renderer; /* zero = OS default; else one bit */
    uint32_t required_features;
    uint32_t optional_features;
    uint8_t allow_fallback;
} ShytNativeRendererRequestV380;
typedef struct ShytNativeRendererChoiceV380 {
    uint32_t renderer;
    uint32_t enabled_features, unavailable_optional_features;
} ShytNativeRendererChoiceV380;

/* The target MUST match the actual process architecture and OS. Fail
 * without mutating previous choice when no verified backend qualifies.
 * Renderer policy is not evidence of a native Bloodborne game executable.
 */
int shyt_native_choose_renderer_v380(
    const ShytNativeTargetV380 *target,
    const ShytNativeBackendProbeV380 *probes, size_t probe_count,
    const ShytNativeRendererRequestV380 *request,
    ShytNativeRendererChoiceV380 *choice);
#ifdef __cplusplus
}
#endif
#endif
