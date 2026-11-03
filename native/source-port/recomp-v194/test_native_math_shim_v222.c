/* V222 host-side only math semantics test. No retail game bytes. */
#include "native_math_shim_v222.h"
#include <assert.h>
#include <math.h>
#define NEAR(a,b,t) assert(fabs((a)-(b))<=(t))
#define NEARF(a,b,t) assert(fabsf((a)-(b))<=(t))
int main(void) {
    const double pi = 3.1415926535897932384626433832795;
    int exponent = -1;
    NEAR(shyt_math_atan2(0.0,-1.0), pi,1e-14);
    NEAR(shyt_math_fmod(-7.0,3.0),-1.0,0.0);
    NEAR(shyt_math_acos(-1.0),pi,1e-14);
    NEAR(shyt_math_tan(0.0),0.0,0.0);
    NEAR(shyt_math_asin(1.0),pi/2,1e-14);
    NEAR(shyt_math_atan(1.0),pi/4,1e-14);
    NEAR(shyt_math_exp(0.0),1.0,0.0);
    NEAR(shyt_math_pow(2.0,4.0),16.0,0.0);
    NEAR(shyt_math_frexp(8.0,&exponent),0.5,0.0);
    assert(exponent==4);
    NEAR(shyt_math_exp2(3.0),8.0,0.0);
    NEAR(shyt_math_ldexp(0.5,4),8.0,0.0);
    NEARF(shyt_math_tanf(0.0f),0.0f,0.0f);
    NEARF(shyt_math_fmodf(-7.0f,3.0f),-1.0f,0.0f);
    NEARF(shyt_math_atan2f(0.0f,-1.0f),(float)pi,1e-6f);
    NEARF(shyt_math_powf(2.0f,3.0f),8.0f,0.0f);
    NEARF(shyt_math_acosf(-1.0f),(float)pi,1e-6f);
    NEARF(shyt_math_asinf(1.0f),(float)(pi/2),1e-6f);
    NEARF(shyt_math_frexpf(8.0f,&exponent),0.5f,0.0f);
    assert(exponent==4);
    NEARF(shyt_math_ldexpf(0.5f,4),8.0f,0.0f);
    NEARF(shyt_math_atanf(1.0f),(float)(pi/4),1e-6f);
    NEARF(shyt_math_expf(0.0f),1.0f,0.0f);
    NEARF(shyt_math_tanhf(0.0f),0.0f,0.0f);
    NEARF(shyt_math_exp2f(3.0f),8.0f,0.0f);
    assert(signbit(shyt_math_fmod(-0.0,3.0)));
    assert(signbit(shyt_math_fmodf(-0.0f,3.0f)));
    assert(isnan(shyt_math_acos(2.0)));
    assert(isnan(shyt_math_acosf(2.0f)));
    assert(isinf(shyt_math_exp(1000.0)));
    return 0;
}
