/* V224/V226: invented import offsets, actual pinned BbCpu layout. */
#include "native_math_import_dispatch_v224.h"
#include <assert.h>
#include <stdint.h>
#include <string.h>

typedef struct { uint64_t begin, end; int deny; } Bounds;
static int permitted(void *context, uint64_t address, size_t n, int write) {
    const Bounds *b = (const Bounds *)context;
    return write && !b->deny && n && address >= b->begin &&
           address <= b->end && n <= b->end - address;
}

int main(void) {
    const char *names[23] = {
        "acos","acosf","asin","asinf","atan","atan2","atan2f","atanf",
        "exp","exp2","exp2f","expf","fmod","fmodf","frexp","frexpf",
        "ldexp","ldexpf","pow","powf","tan","tanf","tanhf"
    };
    ShytMathImportDesc descs[23];
    for (size_t i = 0; i < 23; ++i) {
        descs[i].name = names[i];
        descs[i].offset = 0x100 + i * 16;
    }
    ShytMathImportTable table;
    assert(shyt_math_import_table_v224_init(&table, 0x1000000, descs, 23));
    BbCpu cpu;
    memset(&cpu, 0, sizeof(cpu));
    uint64_t stack[8] = {0};
    Bounds bound = {(uint64_t)(uintptr_t)&stack[0],
                    (uint64_t)(uintptr_t)&stack[8], 0};
    cpu.r[RSP] = (uint64_t)(uintptr_t)&stack[4];
    cpu.r[RAX] = 42;
    cpu.v[0].fd[0] = 2.0;
    cpu.v[1].fd[0] = 4.0;
    cpu.rip = 0x334455;
    const uint64_t old_rsp = cpu.r[RSP];
    const uint64_t pow_target = 0x1000000 + descs[18].offset;
    assert(!shyt_math_import_v224_try_call(&table, &cpu, pow_target, 0x500000));
    assert(cpu.r[RSP] == old_rsp && cpu.rip == 0x334455);
    assert(shyt_math_import_v224_try_call_checked(
        &table, &cpu, 0xdeadbeef, 0x500000, permitted, &bound) == 0);
    assert(shyt_math_import_v224_try_call_checked(
        &table, &cpu, pow_target, 0, permitted, &bound) == -1);
    assert(shyt_math_import_v224_try_call_checked(
        &table, &cpu, pow_target, 0x500000, NULL, &bound) == -1);
    assert(shyt_math_import_v224_try_call_checked(
        &table, NULL, pow_target, 0x500000, permitted, &bound) == -1);
    bound.deny = 1;
    assert(shyt_math_import_v224_try_call_checked(
        &table, &cpu, pow_target, 0x500000, permitted, &bound) == -1);
    assert(cpu.r[RSP] == old_rsp && cpu.rip == 0x334455);
    bound.deny = 0;
    assert(shyt_math_import_v224_try_call_checked(
        &table, &cpu, pow_target, 0x500000, permitted, &bound) == 1);
    assert(cpu.v[0].fd[0] == 16.0 && cpu.r[RSP] == old_rsp);
    assert(cpu.rip == 0x500000 && cpu.r[RAX] == 42);
    descs[22].offset = descs[21].offset;
    assert(!shyt_math_import_table_v224_init(&table, 0x1000000, descs, 23));
    descs[22].offset = 0x300;
    descs[22].name = "unknown";
    assert(!shyt_math_import_table_v224_init(&table, 0x1000000, descs, 23));
    return 0;
}
