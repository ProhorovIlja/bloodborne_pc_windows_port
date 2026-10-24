#pragma once

// FidelityFX FSR 3 SDK 1.1.4 assumes MSVC's _countof in its host C++ code.
// MinGW CLANG64 does not define it. Force-include this header ONLY for the
// ffx_vulkan_fsr3_host_1_1_4 target when building on Windows with Clang/GCC.
// Never change third_party/fsr-vulkan submodule contents or global macros.
#ifdef __cplusplus
#include <mutex>  // FSR Vulkan backend uses std::lock_guard without including <mutex>.
#endif

#ifndef _countof
#define _countof(array) (sizeof(array) / sizeof((array)[0]))
#endif
