/* SPDX-License-Identifier: GPL-2.0-or-later
 * V360: fault-injected cross-platform DCX Deflate streaming tests.
 * Only invented deterministic bytes: no Bloodborne/DS3 copyrighted data.
 */
#include "native_dcx_dflt_stream_core_v360.h"
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <zlib.h>

typedef struct TestSourceV360 {
    const unsigned char *data;
    size_t length;
    unsigned calls;
    unsigned fail_on;
} TestSourceV360;

static int read_exact_v360(void *ctx,uint64_t offset,void *dst,size_t size) {
    TestSourceV360 *source=(TestSourceV360 *)ctx;
    ++source->calls;
    if (source->fail_on && source->calls==source->fail_on)
        return 0;
    if (offset>source->length || size>source->length-(size_t)offset)
        return 0;
    memcpy(dst,source->data+(size_t)offset,size);
    return 1;
}
static void be32_v360(unsigned char *p,uint32_t n) {
    p[0]=(unsigned char)(n>>24);
    p[1]=(unsigned char)(n>>16);
    p[2]=(unsigned char)(n>>8);
    p[3]=(unsigned char)n;
}
static void header_v360(unsigned char *h,unsigned plain,unsigned packed) {
    memset(h,0,76);
    memcpy(h,"DCX\0",4);
    be32_v360(h+4,0x10000u);
    be32_v360(h+8,0x18u);
    be32_v360(h+12,0x24u);
    be32_v360(h+16,0x44u);
    be32_v360(h+20,0x4cu);
    memcpy(h+24,"DCS\0",4);
    be32_v360(h+28,plain);
    be32_v360(h+32,packed);
    memcpy(h+36,"DCP\0",4);
    memcpy(h+40,"DFLT",4);
    be32_v360(h+44,0x20u);
    h[48]=9;
    be32_v360(h+64,0x10100u);
    memcpy(h+68,"DCA\0",4);
    be32_v360(h+72,8u);
}
static void expect_refusal_v360(
    TestSourceV360 *source, void *out,size_t capacity) {
    size_t written=777;
    source->calls=0;
    assert(!shyt_native_dcx_dflt_stream_core_v360(
        read_exact_v360,source,(uint64_t)source->length,
        out,capacity,&written));
    assert(written==0);
}
static void expect_success_v360(
    TestSourceV360 *source,void *out,size_t capacity,
    const void *reference,size_t reference_bytes) {
    size_t written=777;
    source->calls=0;
    source->fail_on=0;
    assert(shyt_native_dcx_dflt_stream_core_v360(
        read_exact_v360,source,(uint64_t)source->length,
        out,capacity,&written));
    assert(written==reference_bytes);
    assert(memcmp(out,reference,reference_bytes)==0);
}

int main(void) {
    enum { UNPACKED=150000, ENCODED=160256, HEADER=76 };
    unsigned char *plaintext=(unsigned char *)malloc(UNPACKED);
    unsigned char *archive=(unsigned char *)calloc(ENCODED,1);
    unsigned char *output=(unsigned char *)malloc(UNPACKED+2);
    assert(plaintext && archive && output);
    unsigned state=0x5a17beefu;
    for(unsigned i=0;i<UNPACKED;++i) {
        state^=state<<13; state^=state>>17; state^=state<<5;
        plaintext[i]=(unsigned char)(state>>24);
    }
    uLongf compressed=compressBound(UNPACKED);
    assert(compressed+HEADER+20<ENCODED);
    assert(compress2(archive+HEADER,&compressed,plaintext,UNPACKED,
                     Z_BEST_SPEED)==Z_OK);
    assert(compressed>131072u && compressed+HEADER+20<ENCODED);
    header_v360(archive,UNPACKED,(unsigned)compressed);
    const size_t file_bytes=HEADER+(size_t)compressed;
    TestSourceV360 source={archive,file_bytes,0,0};
    /* More than two actual compressed 64 KiB blocks. */
    expect_success_v360(&source,output,UNPACKED+2,plaintext,UNPACKED);
    assert(source.calls>=4u);

    /* Two real-world envelope families, represented by invented data:
     * BB 1.09 uses 0x24/0x2C and DS3 uses 0x44/0x4C.
     * No game-owned bytes appear in these fixtures. */
    be32_v360(archive+16,0x24u);
    be32_v360(archive+20,0x2cu);
    expect_success_v360(&source,output,UNPACKED+2,plaintext,UNPACKED);
    be32_v360(archive+20,0x4cu); /* wrong pair */
    expect_refusal_v360(&source,output,UNPACKED+2);
    be32_v360(archive+16,0x44u);
    be32_v360(archive+20,0x2cu); /* wrong pair */
    expect_refusal_v360(&source,output,UNPACKED+2);
    be32_v360(archive+16,0x24u);
    archive[48]=8u; /* 0x24 is only accepted for BB's level 9 */
    expect_refusal_v360(&source,output,UNPACKED+2);
    archive[48]=9u;
    archive[56]=15u; /* reject another unknown 0x24 variant */
    expect_refusal_v360(&source,output,UNPACKED+2);
    archive[56]=0u;
    expect_success_v360(&source,output,UNPACKED+2,plaintext,UNPACKED);
    be32_v360(archive+16,0x44u);
    be32_v360(archive+20,0x4cu);
    expect_success_v360(&source,output,UNPACKED+2,plaintext,UNPACKED);

    /* Zero alignment bytes are permitted; nonzero hiding is not. */
    source.length=file_bytes+7;
    expect_success_v360(&source,output,UNPACKED+2,plaintext,UNPACKED);
    archive[file_bytes+4]=42;
    expect_refusal_v360(&source,output,UNPACKED+2);
    archive[file_bytes+4]=0;
    source.length=file_bytes+16;
    expect_refusal_v360(&source,output,UNPACKED+2);
    source.length=file_bytes;

    /* Fail closed on short destination, truncated source, Adler32 damage. */
    expect_refusal_v360(&source,output,UNPACKED-1);
    source.length=file_bytes-1;
    expect_refusal_v360(&source,output,UNPACKED+2);
    source.length=file_bytes;
    archive[file_bytes-1]^=0x5au;
    expect_refusal_v360(&source,output,UNPACKED+2);
    archive[file_bytes-1]^=0x5au;

    /* The reader may fail at header and at each of the 3 data blocks. */
    for(unsigned failure=1;failure<=4;++failure) {
        source.fail_on=failure;
        expect_refusal_v360(&source,output,UNPACKED+2);
    }
    source.fail_on=0;
    archive[40]='X';
    expect_refusal_v360(&source,output,UNPACKED+2);
    archive[40]='D';
    be32_v360(archive+28,UNPACKED+1);
    expect_refusal_v360(&source,output,UNPACKED+2);
    be32_v360(archive+28,UNPACKED);
    be32_v360(archive+32,(unsigned)compressed+1);
    expect_refusal_v360(&source,output,UNPACKED+2);
    be32_v360(archive+32,(unsigned)compressed);
    /* Revalidate source after every mutated-case refusal. */
    expect_success_v360(&source,output,UNPACKED+2,plaintext,UNPACKED);

    size_t written=99;
    assert(!shyt_native_dcx_dflt_stream_core_v360(
        NULL,&source,source.length,output,UNPACKED+2,&written));
    assert(written==0);
    written=99;
    assert(!shyt_native_dcx_dflt_stream_core_v360(
        read_exact_v360,&source,source.length,NULL,UNPACKED+2,&written));
    assert(written==0);
    assert(!shyt_native_dcx_dflt_stream_core_v360(
        read_exact_v360,&source,source.length,output,UNPACKED+2,NULL));
    written=99;
    assert(!shyt_native_dcx_dflt_stream_core_v360(
        read_exact_v360,&source,(uint64_t)UINT32_MAX+76u,
        output,UNPACKED+2,&written));
    assert(written==0);

    free(output);
    free(archive);
    free(plaintext);
    puts("NATIVE_V360_PORTABLE_DCX_DFLT_STREAM_FAULT_INJECTION_PASS");
    return 0;
}
