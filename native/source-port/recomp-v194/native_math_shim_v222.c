/* SPDX-License-Identifier: GPL-2.0-or-later
 * Original implementation: host math wrappers, no third-party HLE copied.
 * Not a guest ABI bridge and does not replace PS4 DLL imports by itself.
 */
#include "native_math_shim_v222.h"
#include <math.h>

#define DEF_D1(name) double shyt_math_##name(double x) { return name(x); }
#define DEF_F1(name) float shyt_math_##name(float x) { return name(x); }
#define DEF_D2(name) double shyt_math_##name(double x,double y) { return name(x,y); }
#define DEF_F2(name) float shyt_math_##name(float x,float y) { return name(x,y); }

DEF_D2(atan2)
DEF_D2(fmod)
DEF_D1(acos)
DEF_D1(tan)
DEF_D1(asin)
DEF_D1(atan)
DEF_D1(exp)
DEF_D2(pow)
DEF_D1(exp2)
DEF_F1(tanf)
DEF_F2(fmodf)
DEF_F2(atan2f)
DEF_F2(powf)
DEF_F1(acosf)
DEF_F1(asinf)
DEF_F1(atanf)
DEF_F1(expf)
DEF_F1(tanhf)
DEF_F1(exp2f)
double shyt_math_frexp(double x,int *out) { return frexp(x,out); }
float shyt_math_frexpf(float x,int *out) { return frexpf(x,out); }
double shyt_math_ldexp(double x,int exponent) { return ldexp(x,exponent); }
float shyt_math_ldexpf(float x,int exponent) { return ldexpf(x,exponent); }
