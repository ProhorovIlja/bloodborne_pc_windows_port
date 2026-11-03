/* V195: compile ACTUAL unchanged upstream RcApi helpers and Win32 RDTSC
 * platform patch against a synthetic Zydis include placeholder only.
 * No decrypted game, no PS4 module, no gameplay and no private source.
 * The upstream generated-C runtime is NOT otherwise ported yet.
 */
#include "recomp/rc.h"
#include <stdint.h>
#include <stdio.h>
#include <string.h>
_Static_assert(sizeof(BbCpu)==840, "real upstream full CPU layout must match native ABI");
_Static_assert(sizeof(RcFunction)==40, "real upstream RcFunction ABI");
_Static_assert(sizeof(RcApi)==56, "real upstream v4 API");
int main(int argc, char **argv) {
    (void)argv;
    if (argc!=1) return 2;
    if (BB_RECOMP_API_VERSION!=4u || rc_mask(4)!=0xffffffffu ||
        rc_mask(8)!=UINT64_MAX || rc_sat8(200)!=127 ||
        rc_sat8(-200)!=-128 || rc_usat8(-2)!=0 ||
        rc_usat16(70000)!=65535) return 3;
    const uint64_t t1=rc_tsc();
    for (volatile uint32_t i=0;i<200000u;++i) { }
    const uint64_t t2=rc_tsc();
    if (!t1 || t2<t1) return 4;
    BbCpu cpu={0};
    cpu.mxcsr=0x1f80;
    cpu.r[RSP]=UINT64_C(0x1000);
    cpu.fs_base=UINT64_C(0x2222);
    if (cpu.r[RSP]!=UINT64_C(0x1000) || cpu.fs_base!=UINT64_C(0x2222)) return 5;
    puts("SHYT_V195_NATIVE_ORIGINAL_UPSTREAM_RC_H_WIN32_LINUX_PASS");
    return 0;
}
