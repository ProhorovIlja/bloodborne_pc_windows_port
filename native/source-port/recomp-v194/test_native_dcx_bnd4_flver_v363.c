/* SPDX-License-Identifier: GPL-2.0-or-later
 * V363 in-memory end-to-end DCX->BND4->FLVER2 regression.
 * Entire archive, binder, and model are invented test fixtures.
 */
#include "native_dcx_bnd4_flver_v363.h"
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <zlib.h>
#define V363_FLVER_BYTES 0x1b4u
#define V363_FLVER_DATA 0x180u

typedef struct SourceV363 {
    const unsigned char *data;
    size_t bytes;
    unsigned calls;
    unsigned fail_at;
} SourceV363;
static int reader_v363(void *ctx, uint64_t offset, void *dest, size_t size) {
    SourceV363 *s = (SourceV363 *)ctx;
    ++s->calls;
    if (s->fail_at && s->calls == s->fail_at) return 0;
    if (offset > s->bytes || size > s->bytes - (size_t)offset) return 0;
    memcpy(dest, s->data + (size_t)offset, size);
    return 1;
}
static void w16_v363(unsigned char *p, size_t offset, uint16_t value) {
    p[offset]=(unsigned char)value;
    p[offset+1]=(unsigned char)(value>>8);
}
static void w32_v363(unsigned char *p, size_t offset, uint32_t value) {
    w16_v363(p,offset,(uint16_t)value);
    w16_v363(p,offset+2,(uint16_t)(value>>16));
}
static void w64_v363(unsigned char *p, size_t offset, uint64_t value) {
    w32_v363(p,offset,(uint32_t)value);
    w32_v363(p,offset+4,(uint32_t)(value>>32));
}
static void be32_v363(unsigned char *p, size_t offset, uint32_t value) {
    p[offset]=(unsigned char)(value>>24);
    p[offset+1]=(unsigned char)(value>>16);
    p[offset+2]=(unsigned char)(value>>8);
    p[offset+3]=(unsigned char)value;
}
static void make_flver_v363(unsigned char *p) {
    memset(p,0,V363_FLVER_BYTES);
    memcpy(p,"FLVER\0L\0",8);
    w32_v363(p,8,0x20014u);
    w32_v363(p,12,V363_FLVER_DATA);
    w32_v363(p,16,52u);
    w32_v363(p,24,1u); /* one invented material */
    w32_v363(p,32,1u); /* one mesh */
    w32_v363(p,36,1u); /* one vertex buffer */
    p[0x49]=1;
    w32_v363(p,0x50,1u);
    w32_v363(p,0x54,1u);
    p[0xa0]=1;
    w32_v363(p,0xa0+16,0xFFFFFFFFu);
    w32_v363(p,0xa0+32,1u);
    w32_v363(p,0xa0+36,0x138u);
    w32_v363(p,0xa0+40,1u);
    w32_v363(p,0xa0+44,0x13cu);
    w32_v363(p,0xd0+8,3u);
    w32_v363(p,0xd0+16,6u);
    w32_v363(p,0xd0+24,16u);
    w32_v363(p,0xf0+8,12u);
    w32_v363(p,0xf0+12,3u);
    w32_v363(p,0xf0+24,36u);
    w32_v363(p,0xf0+28,16u);
    w32_v363(p,0x110,1u);
    w32_v363(p,0x110+12,0x120u);
    w32_v363(p,0x120+8,2u); /* one Float3 position */
    w16_v363(p,V363_FLVER_DATA+0,0u);
    w16_v363(p,V363_FLVER_DATA+2,1u);
    w16_v363(p,V363_FLVER_DATA+4,2u);
    for (unsigned i=0;i<36u;++i)
        p[V363_FLVER_DATA+16u+i]=(unsigned char)(i*7u);
}
static size_t make_bnd_v363(unsigned char *p, int extended) {
    const uint32_t data_offset=extended?0xB0u:0x90u;
    memset(p,0,1024u);
    memcpy(p,"BND4",4);
    p[10]=1;
    w32_v363(p,12,1u);
    w64_v363(p,16,0x40u);
    memcpy(p+24,"TESTV363",8);
    w64_v363(p,32,0x24u);
    w64_v363(p,40,data_offset);
    p[48]=1;
    p[49]=0x74;
    p[50]=(unsigned char)(extended?4:0);
    p[0x40]=0x40;
    w32_v363(p,0x44,0xFFFFFFFFu);
    w64_v363(p,0x48,V363_FLVER_BYTES);
    w64_v363(p,0x50,V363_FLVER_BYTES);
    w32_v363(p,0x58,data_offset);
    w32_v363(p,0x5c,200u);
    w32_v363(p,0x60,0x64u);
    static const char name[]="fiction.flver";
    for(size_t i=0;i<sizeof(name);++i) {
        p[0x64u+i*2u]=(unsigned char)name[i];
        p[0x64u+i*2u+1u]=0;
    }
    if (extended) {
        w64_v363(p,0x38,0x90u);
        w64_v363(p,0x90,0xA8u);
        w32_v363(p,0x98,1u);
        p[0x9c]=0x10; p[0x9d]=8; p[0x9e]=8;
        w32_v363(p,0xa0,1u);
        w32_v363(p,0xa4,0u);
        w32_v363(p,0xa8,0x12345678u);
        w32_v363(p,0xac,0u);
    }
    make_flver_v363(p+data_offset);
    return (size_t)data_offset+V363_FLVER_BYTES;
}
static size_t make_dcx_v363(unsigned char *archive,
                           const unsigned char *bnd,size_t bnd_bytes,
                           int bloodborne_header) {
    memset(archive,0,2048u);
    memcpy(archive,"DCX\0",4);
    be32_v363(archive,4,0x10000u);
    be32_v363(archive,8,0x18u);
    be32_v363(archive,12,0x24u);
    be32_v363(archive,16,bloodborne_header?0x24u:0x44u);
    be32_v363(archive,20,bloodborne_header?0x2cu:0x4cu);
    memcpy(archive+24,"DCS\0",4);
    be32_v363(archive,28,(uint32_t)bnd_bytes);
    memcpy(archive+36,"DCP\0",4);
    memcpy(archive+40,"DFLT",4);
    be32_v363(archive,44,0x20u);
    archive[48]=9;
    be32_v363(archive,64,0x00010100u);
    memcpy(archive+68,"DCA\0",4);
    be32_v363(archive,72,8u);
    uLongf compressed=(uLongf)(2048u-76u);
    assert(compress2(archive+76,&compressed,bnd,(uLong)bnd_bytes,
                     Z_BEST_SPEED)==Z_OK);
    assert(compressed>2 && compressed<1972);
    be32_v363(archive,32,(uint32_t)compressed);
    return (size_t)compressed+76u;
}
static void open_refuses_v363(SourceV363 *src,
                             unsigned char *scratch,size_t capacity) {
    ShytNativeDcxBnd4ViewV363 v;
    memset(&v,0xA5,sizeof(v));
    src->calls=0;
    assert(!shyt_native_dcx_bnd4_open_v363(reader_v363,src,src->bytes,
                                          scratch,capacity,&v));
    assert(v.decoded_bnd4==NULL && v.decoded_bytes==0 &&
           v.index.file_count==0);
}
static void run_case_v363(int extended,int bloodborne_header) {
    unsigned char bnd[1024u], dcx[2048u], scratch[1024u];
    size_t bnd_bytes=make_bnd_v363(bnd,extended);
    size_t dcx_bytes=make_dcx_v363(dcx,bnd,bnd_bytes,bloodborne_header);
    SourceV363 source={dcx,dcx_bytes,0u,0u};
    ShytNativeDcxBnd4ViewV363 v={0};
    assert(shyt_native_dcx_bnd4_open_v363(
        reader_v363,&source,source.bytes,scratch,sizeof(scratch),&v));
    assert(v.decoded_bnd4==scratch && v.decoded_bytes==bnd_bytes);
    assert(v.index.file_count==1u && v.index.extended==(unsigned)(extended?4:0));
    unsigned before=source.calls;
    ShytNativeFlver2AssetV363 asset={0};
    assert(shyt_native_dcx_bnd4_flver_at_v363(&v,0u,&asset));
    assert(source.calls==before); /* no repeated I/O or DCX inflation */
    assert(asset.file.file_id==200u && asset.flver_bytes==V363_FLVER_BYTES);
    assert(asset.flver==scratch+asset.file.data_offset);
    uint32_t discovered=UINT32_MAX;
    ShytNativeFlver2AssetV363 found={0};
    assert(shyt_native_dcx_bnd4_first_flver_v363(&v,&discovered,&found));
    assert(discovered==0u && found.flver==asset.flver);
    assert(source.calls==before); /* discovery is memory-only */
    assert(asset.geometry.mesh_count==1u && asset.geometry.total_vertices==3u &&
           asset.geometry.total_index_elements==3u &&
           asset.geometry.validated_vertex_bytes==36u);
    assert(!shyt_native_dcx_bnd4_flver_at_v363(&v,1u,&asset));
    assert(asset.flver==NULL && asset.flver_bytes==0u);
    assert(!shyt_native_dcx_bnd4_flver_at_v363(&v,0u,NULL));
    /* A genuine decoded BND file may contain per-file compression;
     * V363 refuses it until a separately validated decoder is available. */
    bnd[0x40]=0xC0;
    source.bytes=make_dcx_v363(dcx,bnd,bnd_bytes,bloodborne_header);
    source.calls=0;
    assert(shyt_native_dcx_bnd4_open_v363(
        reader_v363,&source,source.bytes,scratch,sizeof(scratch),&v));
    memset(&asset,0xA5,sizeof(asset));
    assert(!shyt_native_dcx_bnd4_flver_at_v363(&v,0u,&asset));
    assert(asset.flver==NULL && asset.flver_bytes==0);
    discovered=0u;
    assert(!shyt_native_dcx_bnd4_first_flver_v363(&v,&discovered,&found));
    assert(discovered==UINT32_MAX && found.flver==NULL);
    /* Corrupt a triangle index: BND opens, FLVER rejects the model. */
    bnd[0x40]=0x40;
    bnd[(extended?0xB0u:0x90u)+V363_FLVER_DATA+4u]=8u;
    source.bytes=make_dcx_v363(dcx,bnd,bnd_bytes,bloodborne_header);
    source.calls=0;
    assert(shyt_native_dcx_bnd4_open_v363(
        reader_v363,&source,source.bytes,scratch,sizeof(scratch),&v));
    assert(!shyt_native_dcx_bnd4_flver_at_v363(&v,0u,&asset));
    discovered=0u;
    assert(!shyt_native_dcx_bnd4_first_flver_v363(&v,&discovered,&found));
    assert(discovered==UINT32_MAX && found.flver==NULL);
    bnd[(extended?0xB0u:0x90u)+V363_FLVER_DATA+4u]=2u;
    /* A malformed decoded BND must not publish an asset view. */
    bnd[0]='X';
    source.bytes=make_dcx_v363(dcx,bnd,bnd_bytes,bloodborne_header);
    open_refuses_v363(&source,scratch,sizeof(scratch));
    bnd[0]='B';
    source.bytes=make_dcx_v363(dcx,bnd,bnd_bytes,bloodborne_header);
    open_refuses_v363(&source,scratch,bnd_bytes-1u);
    source.bytes--;
    open_refuses_v363(&source,scratch,sizeof(scratch));
    source.bytes++;
    dcx[source.bytes-1u]^=0x3fu;
    open_refuses_v363(&source,scratch,sizeof(scratch));
    dcx[source.bytes-1u]^=0x3fu;
    for (unsigned i=1u;i<=2u;++i) {
        source.fail_at=i;
        open_refuses_v363(&source,scratch,sizeof(scratch));
    }
    source.fail_at=0;
    source.calls=0;
    assert(shyt_native_dcx_bnd4_open_v363(
        reader_v363,&source,source.bytes,scratch,sizeof(scratch),&v));
}
static size_t make_bnd_mixed_v363(unsigned char *p) {
    memset(p,0,1024u);
    memcpy(p,"BND4",4);
    p[10]=1;
    w32_v363(p,12,3u);
    w64_v363(p,16,0x40u);
    memcpy(p+24,"TESTMIX3",8);
    w64_v363(p,32,0x24u);
    w64_v363(p,40,0x110u);
    p[48]=1; p[49]=0x74;
    const uint32_t offsets[]={0x110u,0x120u,0x2d4u};
    const uint32_t sizes[]={16u,V363_FLVER_BYTES,8u};
    const uint32_t names[]={0xb0u,0xc8u,0xe0u};
    const char *const filenames[]={"fake.tpf","fake.flver","fake.hkx"};
    for (unsigned i=0;i<3u;++i) {
        const size_t rec=0x40u+(size_t)i*0x24u;
        p[rec]=0x40u;
        w32_v363(p,rec+4u,0xFFFFFFFFu);
        w64_v363(p,rec+8u,sizes[i]);
        w64_v363(p,rec+16u,sizes[i]);
        w32_v363(p,rec+24u,offsets[i]);
        w32_v363(p,rec+28u,(i+1u)*100u);
        w32_v363(p,rec+32u,names[i]);
        const size_t count=strlen(filenames[i]);
        assert(count<11u);
        for (size_t j=0;j<=count;++j) {
            p[names[i]+j*2u]=(unsigned char)filenames[i][j];
            p[names[i]+j*2u+1u]=0;
        }
    }
    memcpy(p+0x110u,"TPF0inventedXXXX",16u);
    make_flver_v363(p+0x120u);
    memcpy(p+0x2d4u,"HKX0xxxx",8u);
    return 0x2dcu;
}
static void run_mixed_v363(void) {
    unsigned char bnd[1024u],dcx[2048u],scratch[1024u];
    const size_t bnd_bytes=make_bnd_mixed_v363(bnd);
    const size_t packed=make_dcx_v363(dcx,bnd,bnd_bytes,1);
    SourceV363 source={dcx,packed,0u,0u};
    ShytNativeDcxBnd4ViewV363 view={0};
    assert(shyt_native_dcx_bnd4_open_v363(
        reader_v363,&source,source.bytes,scratch,sizeof(scratch),&view));
    assert(view.index.file_count==3u);
    ShytNativeFlver2AssetV363 asset={0};
    assert(!shyt_native_dcx_bnd4_flver_at_v363(&view,0u,&asset));
    uint32_t discovered=UINT32_MAX;
    unsigned previous_reads=source.calls;
    assert(shyt_native_dcx_bnd4_first_flver_v363(&view,&discovered,&asset));
    assert(discovered==1u && asset.file.file_id==200u &&
           asset.geometry.mesh_count==1u &&
           asset.geometry.total_vertices==3u);
    assert(source.calls==previous_reads);
    assert(!shyt_native_dcx_bnd4_flver_at_v363(&view,2u,&asset));
    assert(asset.flver==NULL);
    /* Failed FLVER selection must not accidentally fall through to HKX. */
    bnd[0x120u+V363_FLVER_DATA+4u]=99u;
    source.bytes=make_dcx_v363(dcx,bnd,bnd_bytes,1);
    assert(shyt_native_dcx_bnd4_open_v363(
        reader_v363,&source,source.bytes,scratch,sizeof(scratch),&view));
    discovered=0u;
    assert(!shyt_native_dcx_bnd4_first_flver_v363(&view,&discovered,&asset));
    assert(discovered==UINT32_MAX && asset.flver==NULL);
    /* A 3-entry binder may not contain a model at all. */
    bnd[0x120u]='X';
    source.bytes=make_dcx_v363(dcx,bnd,bnd_bytes,1);
    assert(shyt_native_dcx_bnd4_open_v363(
        reader_v363,&source,source.bytes,scratch,sizeof(scratch),&view));
    discovered=0u;
    assert(!shyt_native_dcx_bnd4_first_flver_v363(&view,&discovered,&asset));
    assert(discovered==UINT32_MAX && asset.flver==NULL);
}
int main(void) {
    run_case_v363(0,1); /* Bloodborne envelope, BND4 no hash */
    run_case_v363(1,0); /* Dark Souls III envelope, BND4 extended hash */
    run_mixed_v363(); /* Bloodborne character TPF -> FLVER -> HKX */
    puts("NATIVE_V363_SYNTHETIC_DCX_BND4_FLVER_PIPELINE_PASS");
    return 0;
}
