/* SPDX-License-Identifier: GPL-2.0-or-later
 * Real zlib-wrapped Deflate fixture, actual native Windows mount on Win64.
 * Bytes are INVENTED, not Bloodborne or Dark Souls III assets.
 */
#include "native_dcx_dflt_inflate_v355.h"
#include "native_dcx_dflt_header_v354.h"
#include "native_win_asset_fs_v351.h"
#include "native_win_dcx_stream_v359.h"
#include <stdlib.h>
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <zlib.h>
#ifdef _WIN32
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <wchar.h>
#endif

static void be32(unsigned char *p, unsigned n) {
    p[0]=(unsigned char)(n>>24);
    p[1]=(unsigned char)(n>>16);
    p[2]=(unsigned char)(n>>8);
    p[3]=(unsigned char)n;
}
static void fake_dcx_header(unsigned char h[76],unsigned unpacked,unsigned packed) {
    memset(h,0,76);
    memcpy(h,"DCX\0",4);
    be32(h+4,0x10000);
    be32(h+8,0x18);
    be32(h+12,0x24);
    be32(h+16,0x44);
    be32(h+20,0x4C);
    memcpy(h+24,"DCS\0",4);
    be32(h+28,unpacked);
    be32(h+32,packed);
    memcpy(h+36,"DCP\0",4);
    memcpy(h+40,"DFLT",4);
    be32(h+44,0x20);
    h[48]=9;
    be32(h+64,0x10100);
    memcpy(h+68,"DCA\0",4);
    be32(h+72,8);
}
static void rejects(const void *src,size_t n,void *dst,size_t cap) {
    size_t written=99;
    assert(!shyt_native_dcx_dflt_inflate_v355(src,n,dst,cap,&written));
    assert(written==0);
}
int main(void) {
    static const unsigned char game_like_invented[] =
        "MADE_UP_YHARNAM_MAP_24_00_00_00__"
        "MEANINGLESS_EXAMPLE_0123456789"
        "BOUNDS_CHECKS_AND_REAL_ZLIB_INFLATE_"
        "NO_COPYRIGHTED_GAME_BYTES";
    const size_t n=sizeof(game_like_invented);
    unsigned char data[4096]={0};
    unsigned char decoded[512]={0};
    uLongf zbytes=compressBound((uLong)n);
    assert(zbytes<4000u);
    assert(compress2(data+76,&zbytes,game_like_invented,(uLong)n,
                     Z_BEST_COMPRESSION)==Z_OK);
    assert(zbytes>6 && zbytes<1000);
    fake_dcx_header(data,(unsigned)n,(unsigned)zbytes);
    const size_t full=76u+(size_t)zbytes;
    size_t written=0;
    assert(shyt_native_dcx_dflt_inflate_v355(data,full,decoded,sizeof(decoded),&written));
    assert(written==n && memcmp(decoded,game_like_invented,n)==0);
    rejects(data,full,decoded,n-1);
    rejects(data,full-1,decoded,sizeof(decoded));
    rejects(data,75,decoded,sizeof(decoded));
    rejects(data,full,decoded,0);
    rejects(data,full,NULL,sizeof(decoded));
    /* Re-run with genuine file before mutation, making accidental fixture
       corruption obvious. */
    assert(shyt_native_dcx_dflt_inflate_v355(data,full,decoded,sizeof(decoded),&written));
    /* Deflate payload checksum MUST be checked, even for correct header. */
    data[full-1]^=0xA5u;
    rejects(data,full,decoded,sizeof(decoded));
    data[full-1]^=0xA5u;
    data[40]='K';rejects(data,full,decoded,sizeof(decoded));data[40]='D';
    be32(data+28,(unsigned)n+1u);
    rejects(data,full,decoded,sizeof(decoded));
    be32(data+28,(unsigned)n);
    be32(data+32,(unsigned)zbytes+1u);
    rejects(data,full,decoded,sizeof(decoded));
    be32(data+32,(unsigned)zbytes);
    data[full]=1;
    rejects(data,full+1,decoded,sizeof(decoded));
    data[full]=0;
    assert(shyt_native_dcx_dflt_inflate_v355(data,full+1,decoded,sizeof(decoded),&written));
    /* zlib wrapper, not raw DEFLATE: reject invalid magic. */
    data[76]=0;
    rejects(data,full,decoded,sizeof(decoded));
    data[76]=0x78;
    assert(shyt_native_dcx_dflt_inflate_v355(data,full,decoded,sizeof(decoded),&written));

    /* Real Bloodborne 1.09 DCX_DFLT has 0x24/0x2C fields;
     * real DS3 uses the existing 0x44/0x4C pair. Payload is invented. */
    be32(data+16,0x24u);
    be32(data+20,0x2cu);
    assert(shyt_native_dcx_dflt_inflate_v355(data,full,decoded,sizeof(decoded),&written));
    assert(written==n && memcmp(decoded,game_like_invented,n)==0);
    be32(data+20,0x4cu);
    rejects(data,full,decoded,sizeof(decoded)); /* forbid mixed variant */
    be32(data+20,0x2cu);
    be32(data+16,0x44u);
    rejects(data,full,decoded,sizeof(decoded));
    be32(data+16,0x24u);
    assert(shyt_native_dcx_dflt_inflate_v355(data,full,decoded,sizeof(decoded),&written));
#ifdef _WIN32
    wchar_t temp[1024], root[1024], file[1024];
    DWORD m=GetTempPathW(1024,temp);
    assert(m>0 && m<1000);
    assert(GetTempFileNameW(temp,L"v35",0,root));
    assert(DeleteFileW(root) && CreateDirectoryW(root,NULL));
    assert(swprintf(file,1024,L"%ls\\map_asset.dcx",root)>0);
    HANDLE handle=CreateFileW(file,GENERIC_WRITE,0,NULL,CREATE_NEW,FILE_ATTRIBUTE_NORMAL,NULL);
    assert(handle!=INVALID_HANDLE_VALUE);
    DWORD count=0;
    assert(WriteFile(handle,data,(DWORD)full,&count,NULL) && count==full);
    CloseHandle(handle);
    ShytNativeWinAssetRootV351 mount={0};
    assert(shyt_native_win_asset_mount_v351(&mount,root));
    ShytNativeWinAssetStreamV352 stream={0};
    assert(shyt_native_win_asset_stream_open_v352(&mount,
        "/dvdroot_ps4/map_asset.dcx",&stream));
    assert(stream.file_size==full);
    unsigned char disk_bytes[4096];
    size_t got=0;
    assert(shyt_native_win_asset_stream_read_v352(&stream,0,disk_bytes,full,&got));
    assert(got==full);
    shyt_native_win_asset_stream_close_v352(&stream);
    assert(shyt_native_dcx_dflt_inflate_v355(disk_bytes,got,decoded,sizeof(decoded),&written));
    assert(written==n && memcmp(decoded,game_like_invented,n)==0);
    /* V359: entire DCX read/decompression from native owner-owned root,
     * without a monolithic compressed copy. */
    assert(shyt_native_win_dcx_stream_inflate_v359(
        &mount,"/dvdroot_ps4/map_asset.dcx",decoded,sizeof(decoded),&written));
    assert(written==n && memcmp(decoded,game_like_invented,n)==0);
    assert(!shyt_native_win_dcx_stream_inflate_v359(
        &mount,"/dvdroot_ps4/../outside.dcx",decoded,sizeof(decoded),&written));
    assert(written==0);
    /* Exercise >64 KiB COMPRESSED output, not merely the one-chunk fast path.
     * All generated bytes are synthetic and reproducible. */
    enum { BIG=150000, ENCODED_CAP=160000 };
    unsigned char *large=(unsigned char *)malloc(BIG);
    unsigned char *large_encoded=(unsigned char *)malloc(ENCODED_CAP);
    unsigned char *large_output=(unsigned char *)malloc(BIG);
    assert(large && large_encoded && large_output);
    unsigned state=0x12345678u;
    for (unsigned i=0;i<BIG;++i) {
        state^=state<<13;
        state^=state>>17;
        state^=state<<5;
        large[i]=(unsigned char)(state>>24);
    }
    uLongf large_packed=compressBound(BIG);
    assert(large_packed+76u<ENCODED_CAP);
    assert(compress2(large_encoded+76,&large_packed,large,BIG,Z_BEST_SPEED)==Z_OK);
    assert(large_packed>65536);
    fake_dcx_header(large_encoded,BIG,(unsigned)large_packed);
    handle=CreateFileW(file,GENERIC_WRITE,0,NULL,CREATE_ALWAYS,FILE_ATTRIBUTE_NORMAL,NULL);
    assert(handle!=INVALID_HANDLE_VALUE);
    const DWORD big_disk_size=(DWORD)(76u+large_packed);
    assert(WriteFile(handle,large_encoded,big_disk_size,&count,NULL) &&
           count==big_disk_size);
    CloseHandle(handle);
    assert(shyt_native_win_dcx_stream_inflate_v359(
        &mount,"/dvdroot_ps4/map_asset.dcx",large_output,BIG,&written));
    assert(written==BIG && memcmp(large_output,large,BIG)==0);
    assert(!shyt_native_win_dcx_stream_inflate_v359(
        &mount,"/dvdroot_ps4/map_asset.dcx",large_output,BIG-1,&written));
    assert(written==0);
    /* Tamper the compressed zlib checksum on disk and refuse to publish
     * an unverified decoded buffer. */
    large_encoded[big_disk_size-1]^=0xA5u;
    handle=CreateFileW(file,GENERIC_WRITE,0,NULL,CREATE_ALWAYS,FILE_ATTRIBUTE_NORMAL,NULL);
    assert(handle!=INVALID_HANDLE_VALUE);
    assert(WriteFile(handle,large_encoded,big_disk_size,&count,NULL) &&
           count==big_disk_size);
    CloseHandle(handle);
    assert(!shyt_native_win_dcx_stream_inflate_v359(
        &mount,"/dvdroot_ps4/map_asset.dcx",large_output,BIG,&written));
    assert(written==0);
    free(large_output);
    free(large_encoded);
    free(large);
    assert(DeleteFileW(file) && RemoveDirectoryW(root));
#else
    ShytNativeWinAssetRootV351 mount={0};
    assert(!shyt_native_win_dcx_stream_inflate_v359(
        &mount,"/dvdroot_ps4/fictional.dcx",decoded,sizeof(decoded),&written));
    assert(written==0);
#endif
    puts("SHYT_NATIVE_V359_REAL_ZLIB_DCX_STREAMING_WIN32_MULTI_CHUNK_INVENTED_ASSET_PASS");
    return 0;
}
