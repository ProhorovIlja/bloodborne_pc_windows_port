/* SPDX-License-Identifier: GPL-2.0-or-later
 * V222: independent host-side math bridges for original PS4 import NAMES.
 * These are ordinary Win64 C ABI helpers, NOT guest SysV ABI entry points.
 * AOT guest->host argument/FP ABI translation must be verified separately.
 */
#ifndef SHYT_NATIVE_MATH_SHIM_V222_H
#define SHYT_NATIVE_MATH_SHIM_V222_H
#if defined(_WIN32)
# define SHYT_API __declspec(dllexport)
#else
# define SHYT_API __attribute__((visibility("default")))
#endif
#ifdef __cplusplus
extern "C" {
#endif
SHYT_API double shyt_math_atan2(double y, double x);
SHYT_API double shyt_math_fmod(double x, double y);
SHYT_API double shyt_math_acos(double x);
SHYT_API double shyt_math_tan(double x);
SHYT_API double shyt_math_asin(double x);
SHYT_API double shyt_math_atan(double x);
SHYT_API double shyt_math_exp(double x);
SHYT_API double shyt_math_pow(double x, double y);
SHYT_API double shyt_math_frexp(double x, int *exp_out);
SHYT_API double shyt_math_exp2(double x);
SHYT_API double shyt_math_ldexp(double x, int exponent);
SHYT_API float shyt_math_tanf(float x);
SHYT_API float shyt_math_fmodf(float x, float y);
SHYT_API float shyt_math_atan2f(float y, float x);
SHYT_API float shyt_math_powf(float x, float y);
SHYT_API float shyt_math_acosf(float x);
SHYT_API float shyt_math_asinf(float x);
SHYT_API float shyt_math_frexpf(float x, int *exp_out);
SHYT_API float shyt_math_ldexpf(float x, int exponent);
SHYT_API float shyt_math_atanf(float x);
SHYT_API float shyt_math_expf(float x);
SHYT_API float shyt_math_tanhf(float x);
SHYT_API float shyt_math_exp2f(float x);
#ifdef __cplusplus
}
#endif
#endif
