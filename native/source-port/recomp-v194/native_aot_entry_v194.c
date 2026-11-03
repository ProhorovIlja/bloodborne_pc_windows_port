/* V194: executable Win64/ELF64-native AOT *host skeleton*, not a playable game.
 * Linked directly to generated-style C. No EBOOT, PS4 ELF loader, JIT,
 * emulator, guest compatibility DLL or game asset file at process startup.
 * Full source-port still needs executable game compilation, native systems,
 * rendering, audio, streaming, save and network implementations.
 */
#include "full_cpu_abi_v194.h"
#include <inttypes.h>
#include <stdio.h>
#include <string.h>

/* Same entrypoint contract as the genuine upstream bbrecomp-generated C;
 * all C symbols resolve into the native executable at link time, not from
 * an EBOOT or runtime-loaded PS4 library. */
extern const RcFunction *bb_recomp_init(const RcApi *, size_t *);
static unsigned unexpected_callbacks;
static uint64_t missing_step(BbCpu *cpu) {
    ++unexpected_callbacks;
    return cpu->rip;
}
static void missing_call(BbCpu *cpu,uint64_t target,uint64_t next) {
    (void)cpu;(void)target;(void)next;++unexpected_callbacks;
}
static void missing_tail(BbCpu *cpu) {(void)cpu;++unexpected_callbacks;}
static void missing_bail(BbCpu *cpu,uint64_t sp) {(void)cpu;(void)sp;++unexpected_callbacks;}
static void missing_trace(uint64_t off,const uint64_t r[16],const BbCpu *cpu) {
    (void)off;(void)r;(void)cpu;++unexpected_callbacks;
}

int main(int argc, char **argv) {
    (void)argv;
    if (argc != 1 || sizeof(BbCpu) != 840u) return 2;
    RcApi api = {0};
    api.version = BB_RECOMP_API_VERSION;
    api.image_base = UINT64_C(0x400000);
    api.step = missing_step;
    api.call = missing_call;
    api.tail = missing_tail;
    api.bail = missing_bail;
    api.trace = missing_trace;
    size_t count = 0;
    const RcFunction *table = bb_recomp_init(&api, &count);
    if (!table || count != 2u || unexpected_callbacks) return 3;
    if (table[0].offset != 0x100u || table[0].size != 16u ||
        table[1].offset != 0x110u || table[1].size != 16u ||
        !table[0].fn || !table[1].fn || !table[0].direct || !table[1].direct ||
        *table[0].direct != table[0].fn || *table[1].direct != table[1].fn) return 4;
    uint64_t guest_stack[4] = {UINT64_C(0x123456789abcdef0), 0, 0, 0};
    BbCpu cpu;
    memset(&cpu, 0, sizeof cpu);
    cpu.mxcsr = 0x1f80u;
    cpu.r[4] = (uint64_t)(uintptr_t)guest_stack;
    cpu.r[0] = 40;
    const uint64_t first_stack = cpu.r[4];
    table[0].fn(&cpu);
    if (cpu.rip != guest_stack[0] || cpu.r[4] != first_stack + 8 ||
        cpu.r[0] != 41 || unexpected_callbacks) return 5;
    cpu.r[4] = first_stack;
    cpu.rip = 0;
    table[1].fn(&cpu);
    if (cpu.rip != guest_stack[0] || cpu.r[4] != first_stack + 8 ||
        cpu.r[0] != 82 || unexpected_callbacks) return 6;
    /* The executable boots without any eboot.bin at all. Neither code nor
     * assets from the game are embedded in this PUBLIC synthetic fixture. */
    puts("SHYT_V194_NATIVE_AOT_EXECUTABLE_NO_EBOOT_STARTUP_PASS");
    puts("SYNTHETIC ONLY: original game and Win32 engine not yet ported");
    return 0;
}
