/* SPDX-License-Identifier: GPL-2.0-or-later
 * Synthetic-only, cross-platform BND4 metadata and bounds regressions.
 * No original Bloodborne or Dark Souls III asset bytes.
 */
#include "native_bnd4_index_v361.h"
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#define BND_BUF_V361 512u
static void le32w_v361(unsigned char *p,uint32_t x) {
    p[0]=(unsigned char)x; p[1]=(unsigned char)(x>>8);
    p[2]=(unsigned char)(x>>16); p[3]=(unsigned char)(x>>24);
}
static void le64w_v361(unsigned char *p,uint64_t x) {
    le32w_v361(p,(uint32_t)x);le32w_v361(p+4,(uint32_t)(x>>32));
}
static size_t invented_bnd_v361(unsigned char *p,int extended) {
    memset(p,0,BND_BUF_V361);
    memcpy(p,"BND4",4);
    p[10]=1; /* verified LE and reversed format bit order */
    le32w_v361(p+12,1);
    le64w_v361(p+16,0x40);
    memcpy(p+24,"TESTV361",8);
    le64w_v361(p+32,0x24); /* per-file header */
    const uint32_t data_offset=extended?0xB0u:0x90u;
    le64w_v361(p+40,data_offset); /* metadata end */
    p[48]=1; /* UTF16 */
    p[49]=0x74; /* raw: IDs, Names1+2, Compression */
    p[50]=(unsigned char)(extended?4:0);
    p[0x40]=0x40; /* file is stored (uncompressed) */
    le32w_v361(p+0x44,0xFFFFFFFFu);
    le64w_v361(p+0x48,24u);
    le64w_v361(p+0x50,24u);
    le32w_v361(p+0x58,data_offset);
    le32w_v361(p+0x5c,200u);
    le32w_v361(p+0x60,0x64u);
    static const char name[]="fiction.flver";
    for(size_t i=0;i<sizeof(name);++i) {
        p[0x64u+i*2]=(unsigned char)name[i];
        p[0x64u+i*2+1]=0;
    }
    if (extended) {
        le64w_v361(p+0x38,0x90u);
        le64w_v361(p+0x90,0xA8u); /* hashes offset */
        le32w_v361(p+0x98,1u); /* 1 hash bucket */
        p[0x9c]=0x10;p[0x9d]=8;p[0x9e]=8;
        le32w_v361(p+0xA0,1); /* 1 entry */
        le32w_v361(p+0xA4,0); /* starts at 0 */
        le32w_v361(p+0xA8,0x12345678); /* fake name hash */
        le32w_v361(p+0xAC,0); /* file 0 */
    }
    for(unsigned i=0;i<24;++i)
        p[data_offset+i]=(unsigned char)(i+31);
    return (size_t)data_offset+24u;
}
static void rejects_v361(unsigned char *p,size_t n) {
    ShytNativeBnd4IndexV361 index={9,9,9,9};
    assert(!shyt_native_bnd4_index_probe_v361(p,n,&index));
    assert(index.file_count==0 && index.header_end==0 &&
           index.hash_table_offset==0 && index.extended==0);
}
static void verifies_v361(unsigned char *p,size_t n,int extended) {
    ShytNativeBnd4IndexV361 index={0};
    ShytNativeBnd4FileV361 f={0};
    assert(shyt_native_bnd4_index_probe_v361(p,n,&index));
    assert(index.file_count==1 && index.extended==(unsigned)(extended?4:0));
    assert(index.header_end==(extended?0xB0u:0x90u));
    assert(shyt_native_bnd4_file_at_v361(p,n,&index,0,&f));
    assert(f.file_id==200 && f.name_utf16_offset==0x64);
    assert(f.name_utf16_code_units==13 && f.stored_bytes==24 &&
           f.original_bytes==24 && f.compressed==0);
    assert(f.data_offset==(extended?0xB0u:0x90u));
    assert(p[(size_t)f.data_offset]==31);
    assert(!shyt_native_bnd4_file_at_v361(p,n,&index,1,&f));
    assert(f.stored_bytes==0 && f.file_id==0);
}
int main(void) {
    unsigned char p[BND_BUF_V361];
    size_t n=invented_bnd_v361(p,0);
    verifies_v361(p,n,0);
    rejects_v361(p,n-1);
    p[0]='X';rejects_v361(p,n);p[0]='B';
    p[9]=1;rejects_v361(p,n);p[9]=0; /* unsupported BE */
    p[49]=0x7c;rejects_v361(p,n);p[49]=0x74;
    p[50]=4;rejects_v361(p,n);p[50]=0;
    le64w_v361(p+16,0x41);rejects_v361(p,n);
    le64w_v361(p+16,0x40);
    le64w_v361(p+40,0x64);rejects_v361(p,n);
    le64w_v361(p+40,0x90);
    le32w_v361(p+12,0xFFFFFFFFu);rejects_v361(p,n);
    le32w_v361(p+12,1u);
    p[0x40]=0x80;rejects_v361(p,n);
    p[0x40]=0x40;
    le64w_v361(p+0x48,25);rejects_v361(p,n);
    le64w_v361(p+0x48,24);
    le32w_v361(p+0x58,(uint32_t)n);rejects_v361(p,n);
    le32w_v361(p+0x58,0x90);
    le32w_v361(p+0x60,0x2000);rejects_v361(p,n);
    le32w_v361(p+0x60,0x64);
    /* NUL terminator must occur before header end, not in asset bytes.
     * First overwrite only the name space: no artificial game content. */
    for(size_t i=0x64;i<0x90;++i) p[i]='x';
    rejects_v361(p,n);
    n=invented_bnd_v361(p,0);
    p[0x40]=0xC0; /* per-file compression flag */
    le64w_v361(p+0x50,99u); /* original length may differ */
    ShytNativeBnd4IndexV361 idx={0};
    ShytNativeBnd4FileV361 file={0};
    assert(shyt_native_bnd4_index_probe_v361(p,n,&idx));
    assert(shyt_native_bnd4_file_at_v361(p,n,&idx,0,&file));
    assert(file.compressed==1 && file.original_bytes==99);
    n=invented_bnd_v361(p,1);
    verifies_v361(p,n,1);
    le32w_v361(p+0xA0,2);rejects_v361(p,n);
    le32w_v361(p+0xA0,1);
    le32w_v361(p+0xAC,7);rejects_v361(p,n);
    le32w_v361(p+0xAC,0);
    le64w_v361(p+0x90,0xF0);rejects_v361(p,n);
    le64w_v361(p+0x90,0xA8);
    p[0x9c]=0;rejects_v361(p,n);p[0x9c]=0x10;
    verifies_v361(p,n,1);
    /* Fails before touching memory on an impossible large archive. */
    rejects_v361(p,(size_t)(512ull*1024ull*1024ull+1ull));
    assert(!shyt_native_bnd4_index_probe_v361(p,n,NULL));
    puts("NATIVE_V361_SYNTHETIC_BND4_INDEX_BOUNDS_AND_HASH_PASS");
    return 0;
}
